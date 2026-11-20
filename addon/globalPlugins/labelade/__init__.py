# Labelade: names unlabelled buttons with a local vision model running in AMD Lemonade Server.
# Copyright (C) 2026 Labelade contributors. Released under the GNU General Public License v2 or later.

import os
import re
import threading
import time
from dataclasses import dataclass

import addonHandler
import api
import config
import controlTypes
import globalPluginHandler
import globalVars
import gui
import queueHandler
import screenBitmap
import tones
import ui
import wx
from gui import guiHelper
from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel
from logHandler import log
from scriptHandler import script

from .core import imaging
from .core.client import DEFAULT_URL, LemonadeClient, LemonadeError, is_local
from .core.heuristics import needs_label
from .core.labeller import Labeller, Worker
from .core.store import Label, LabelStore

addonHandler.initTranslation()

CATEGORY = "Labelade"
config.conf.spec["labelade"] = {
	"serverUrl": f"string(default='{DEFAULT_URL}')",
	"apiKey": "string(default='')",
	"model": "string(default='')",
	"autoLabel": "boolean(default=True)",
	"beep": "boolean(default=True)",
}

_ROLE_KEYS = {}
for _name in (
	"BUTTON", "TOGGLEBUTTON", "MENUBUTTON", "SPLITBUTTON", "DROPDOWNBUTTON", "LINK", "GRAPHIC", "ICON",
	"MENUITEM", "TAB", "CHECKBOX", "RADIOBUTTON", "LISTITEM", "TREEVIEWITEM",
):
	_role = getattr(controlTypes.Role, _name, None)
	if _role is not None:
		_ROLE_KEYS[_role] = _name.lower()
# How each role is named in the prompt.
_ROLE_WORDS = {
	"togglebutton": "toggle button", "menubutton": "menu button", "splitbutton": "split button",
	"dropdownbutton": "drop-down button", "menuitem": "menu item", "checkbox": "check box",
	"radiobutton": "radio button", "listitem": "list item", "treeviewitem": "tree item",
}
# Ids that web frameworks regenerate on every page load are useless for finding a control again.
_UNSTABLE_ID = re.compile(r"^(:r|react|ember|uid|ext-gen|mui-)|\d{4,}", re.I)
_MAX_SCAN = 400


def _conf():
	return config.conf["labelade"]


def _app_name(obj) -> str:
	name = getattr(getattr(obj, "appModule", None), "appName", "") or "unknown"
	return re.sub(r"[^A-Za-z0-9_.\-]", "_", name)[:64]


def _automation_id(obj) -> str:
	aid = getattr(obj, "UIAAutomationId", "") or ""
	if aid and not aid.isdigit() and not _UNSTABLE_ID.search(aid):
		return "uia:" + aid
	attrs = getattr(obj, "IA2Attributes", None) or {}
	dom_id = attrs.get("id", "") if hasattr(attrs, "get") else ""
	if dom_id and not _UNSTABLE_ID.search(dom_id):
		return "ia2:" + dom_id
	return ""


@dataclass
class Target:
	obj: object
	app: str
	role: str
	aid: str
	rect: tuple[int, int, int, int]
	window: str
	image_hash: str | None = None

	@property
	def role_words(self) -> str:
		return _ROLE_WORDS.get(self.role, self.role)


def _target(obj, force: bool = False) -> Target | None:
	"""The control as Labelade sees it, or None if it isn't one we label."""
	role = _ROLE_KEYS.get(getattr(obj, "role", None))
	if role is None or (not force and not needs_label(obj.name, role)):
		return None
	states = getattr(obj, "states", set())
	if controlTypes.State.INVISIBLE in states or controlTypes.State.OFFSCREEN in states:
		return None
	loc = obj.location
	if not loc:
		return None
	left, top, width, height = loc
	if width < 4 or height < 4 or (not force and width * height > 400 * 300):
		return None  # large areas are panes and pictures, not controls; describe them instead
	fg = api.getForegroundObject()
	return Target(obj, _app_name(obj), role, _automation_id(obj), (left, top, width, height), (fg.name or "") if fg else "")


def _capture(rect, out_w: int, out_h: int) -> imaging.Image:
	left, top, width, height = rect
	pixels = screenBitmap.ScreenBitmap(out_w, out_h).captureImage(left, top, width, height)
	return imaging.Image(out_w, out_h, bytes(pixels))


def _control_hash(rect) -> str | None:
	left, top, width, height = rect
	# Trim the edges, where focus rings and hover borders change between visits.
	dx, dy = max(2, width // 8), max(2, height // 8)
	if width - 2 * dx < 4 or height - 2 * dy < 4:
		dx = dy = 0
	return _capture((left + dx, top + dy, width - 2 * dx, height - 2 * dy), 36, 32).dhash()


def _screen_bounds():
	desktop = api.getDesktopObject()
	return tuple(desktop.location) if desktop and desktop.location else (0, 0, 1920, 1080)


def _context_image(target: Target):
	"""Capture the control with its surroundings; return the image and the control's box inside it."""
	left, top, width, height = target.rect
	ctx = imaging.context_rect(left, top, width, height, _screen_bounds())
	out_w, out_h = imaging.fit_size(ctx[2], ctx[3])
	img = _capture(ctx, out_w, out_h)
	sx, sy = out_w / ctx[2], out_h / ctx[3]
	box = (round((left - ctx[0]) * sx), round((top - ctx[1]) * sy), max(1, round(width * sx)), max(1, round(height * sy)))
	return img, box, max(2, round(2 * sx))


def _spoken(entry: Label) -> str:
	if entry.confidence == "low":
		# Translators: spoken for a label the AI was not sure about, e.g. "Send, unsure".
		return _("{label}, unsure").format(label=entry.label)
	return entry.label


def _apply(obj, entry: Label) -> None:
	try:
		obj.name = _spoken(entry)  # NVDA lets a plain assignment override the name property
	except Exception:
		log.debugWarning("Labelade couldn't set a name", exc_info=True)


def _error_text(error: Exception) -> str:
	if isinstance(error, LemonadeError):
		return str(error)
	log.error("Labelade request failed", exc_info=error)
	# Translators: spoken when something unexpected went wrong.
	return _("Something went wrong. Details are in the NVDA log.")


def _post(func, *args):
	queueHandler.queueFunction(queueHandler.eventQueue, func, *args)


def _ask_text(title: str, prompt: str, default: str, callback) -> None:
	def show():
		dlg = wx.TextEntryDialog(gui.mainFrame, prompt, title, default)
		gui.mainFrame.prePopup()
		try:
			ok = dlg.ShowModal() == wx.ID_OK
			value = dlg.GetValue()
		finally:
			dlg.Destroy()
			gui.mainFrame.postPopup()
		if ok:
			callback(value)

	wx.CallAfter(show)


def _show_text(text: str, title: str) -> None:
	try:
		ui.browseableMessage(text, title, closeButton=True, copyButton=True)
	except TypeError:  # NVDA before 2025.1 has no button options
		ui.browseableMessage(text, title)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = CATEGORY

	def __init__(self):
		super().__init__()
		self.store = LabelStore(os.path.join(globalVars.appArgs.configPath, "labelade", "labels"))
		self.labeller = Labeller(
			lambda: LemonadeClient(_conf()["serverUrl"], _conf()["apiKey"]),
			lambda: _conf()["model"].strip(),
		)
		self.worker = Worker(_post)
		self._quiet_until = 0.0
		self._scan = None  # [queued, done, labelled, failed] while a window scan runs
		NVDASettingsDialog.categoryClasses.append(LabeladePanel)
		self._build_menu()

	def terminate(self):
		self.worker.stop()
		if LabeladePanel in NVDASettingsDialog.categoryClasses:
			NVDASettingsDialog.categoryClasses.remove(LabeladePanel)
		try:
			gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self._menu_item)
		except Exception:
			pass
		super().terminate()

	# Finding and applying labels

	def _lookup(self, target: Target) -> Label | None:
		entry = self.store.find(target.app, target.role, target.aid) if target.aid else None
		if entry is None:
			target.image_hash = _control_hash(target.rect)
			entry = self.store.find(target.app, target.role, target.aid, target.image_hash)
		return entry

	def event_gainFocus(self, obj, nextHandler):
		entry = None
		try:
			target = _target(obj)
			if target:
				entry = self._lookup(target)
				if entry:
					_apply(obj, entry)  # before nextHandler, so NVDA announces the label
				elif _conf()["autoLabel"]:
					self._request(target, announce=True)
		except Exception:
			log.error("Labelade focus handling failed", exc_info=True)
		nextHandler()
		# Browse mode (web pages) speaks from its own buffer and ignores obj.name, so say the label after it.
		ti = getattr(obj, "treeInterceptor", None)
		if entry and ti is not None and not getattr(ti, "passThrough", True):
			ui.message(_spoken(entry))

	def event_becomeNavigatorObject(self, obj, nextHandler, isFocus=False):
		# Object navigation reaches graphics and controls that never take focus: use saved labels there too.
		try:
			if not isFocus and (target := _target(obj)) and (entry := self._lookup(target)):
				_apply(obj, entry)
		except Exception:
			log.error("Labelade navigator handling failed", exc_info=True)
		nextHandler()

	def _request(self, target: Target, announce: bool, on_done=None) -> bool:
		img, box, thickness = _context_image(target)
		key = (target.app, target.role, target.aid or target.image_hash or target.rect)

		def work():
			return self.labeller.label(img.draw_box(*box, thickness=thickness).to_png(), target.role_words, target.app, target.window)

		def done(result, error):
			entry = None
			if error:
				quiet = time.monotonic() < self._quiet_until
				if isinstance(error, LemonadeError) and "reach" in str(error):
					self._quiet_until = time.monotonic() + 60  # don't repeat "can't reach" on every Tab press
				if announce and not quiet:
					ui.message(_error_text(error))
			else:
				label, confidence, model = result
				if label:
					entry = Label(target.role, label, "ai", confidence, target.aid, target.image_hash or "", model)
					if entry.automationId or entry.hash:
						entry = self.store.put(target.app, entry)
					_apply(target.obj, entry)
					# Speak it whenever the user is on this control, even if a window scan queued it.
					if self._is_current(target.obj):
						if _conf()["beep"]:
							tones.beep(1200, 25)
						ui.message(_spoken(entry))
				elif announce and self._is_current(target.obj):
					# Translators: spoken when the model could not work out what a control does.
					ui.message(_("Labelade couldn't tell what this control does."))
			if on_done:
				on_done(entry, error)

		return self.worker.submit(key, work, done)

	@staticmethod
	def _is_current(obj) -> bool:
		try:
			return obj == api.getFocusObject() or obj == api.getNavigatorObject()
		except Exception:
			return False

	# Commands

	@script(
		# Translators: input help for a command.
		description=_("Labels the current control with AI now, replacing an AI label it already has."),
		gesture="kb:NVDA+alt+l",
	)
	def script_labelNow(self, gesture):
		obj = api.getNavigatorObject()
		target = _target(obj, force=True)
		if not target:
			# Translators: spoken when the current object can't be labelled.
			ui.message(_("Labelade labels buttons, links, graphics, tabs and menu items. Describe other things with NVDA+alt+D."))
			return
		existing = self._lookup(target)
		if existing and existing.source == "user":
			# Translators: spoken when the user already labelled this control.
			ui.message(_("Your label: {label}. Press NVDA+alt+E to change it.").format(label=existing.label))
			return
		if self._request(target, announce=True):
			# Translators: spoken while a label is generated.
			ui.message(_("Labelling"))

	@script(
		description=_("Finds every unlabelled control in the current window and labels them in the background. Press again to stop."),
		gesture="kb:NVDA+alt+w",
	)
	def script_labelWindow(self, gesture):
		if self._scan:
			self.worker.cancel_all()
			self._scan = None
			ui.message(_("Stopped labelling."))
			return
		fg = api.getForegroundObject()
		targets, seen = [], set()
		stack, visited = [fg], 0
		while stack and visited < _MAX_SCAN:
			obj = stack.pop()
			visited += 1
			try:  # objects can vanish mid-scan (a chat message scrolls away); skip them, keep scanning
				target = _target(obj)
				if target and not self._lookup(target):
					key = target.aid or target.image_hash
					if key and key not in seen:
						seen.add(key)
						targets.append(target)
				stack.extend(reversed(obj.children or []))
			except Exception:
				log.debugWarning("Labelade skipped an object during the scan", exc_info=True)
		if not targets:
			ui.message(_("No new unlabelled controls in this window."))
			return
		scan = self._scan = [len(targets), 0, 0, 0]

		def one_done(entry, error):
			if self._scan is not scan:
				return
			scan[1] += 1
			scan[2 if entry else 3] += 1
			if scan[1] == scan[0]:
				self._scan = None
				# Translators: summary after labelling a window.
				ui.message(_("Labelade finished: {labelled} labelled, {failed} not sure.").format(labelled=scan[2], failed=scan[3]))
		for target in targets:
			if not self._request(target, announce=False, on_done=one_done):
				one_done(None, None)
		# Translators: spoken when a window scan starts.
		ui.message(_("Labelling {count} controls. Press NVDA+alt+W again to stop.").format(count=len(targets)))

	@script(
		description=_("Edits the label of the current control. Clear the text to remove it."),
		gesture="kb:NVDA+alt+e",
	)
	def script_editLabel(self, gesture):
		obj = api.getNavigatorObject()
		target = _target(obj, force=True)
		if not target:
			ui.message(_("Labelade can't label this object."))
			return
		existing = self._lookup(target)

		def save(text):
			text = " ".join(text.split())[:80]
			if not text:
				if existing:
					self.store.remove(target.app, existing)
				ui.message(_("Label removed."))
				return
			entry = Label(target.role, text, "user", "high", target.aid, target.image_hash or "")
			if entry.automationId or entry.hash:
				self.store.put(target.app, entry)
				ui.message(_("Label saved."))
			else:
				ui.message(_("Label set for now. Labelade can't recognise this control again later."))
			_apply(obj, entry)

		_ask_text(_("Labelade"), _("Label for this {role}:").format(role=target.role_words), existing.label if existing else (obj.name or ""), save)

	def _describe(self, obj, what: str):
		loc = obj.location if obj else None
		if not loc or loc[2] < 2 or loc[3] < 2:
			ui.message(_("Nothing on screen to describe."))
			return
		out_w, out_h = imaging.fit_size(loc[2], loc[3], smallest=336, largest=1280)
		img = _capture(tuple(loc), out_w, out_h)
		fg = api.getForegroundObject()
		app, window = _app_name(obj), (fg.name or "") if fg else ""

		def done(text, error):
			if error:
				ui.message(_error_text(error))
			else:
				_show_text(text + "\n\n" + _("Press NVDA+alt+A to ask a follow-up question."), _("Labelade description"))

		self.worker.cancel_all()  # a description is what the user wants now; drop queued labels
		self._scan = None
		self.worker.submit(("describe", time.monotonic()), lambda: self.labeller.describe(img.to_png(), what, app, window), done)
		# Translators: spoken while a description is generated.
		ui.message(_("Describing"))

	@script(description=_("Describes the current object with AI."), gesture="kb:NVDA+alt+d")
	def script_describeObject(self, gesture):
		self._describe(api.getNavigatorObject(), "part of the screen")

	@script(description=_("Describes the whole current window with AI."), gesture="kb:NVDA+alt+s")
	def script_describeWindow(self, gesture):
		self._describe(api.getForegroundObject(), "window")

	@script(description=_("Asks a follow-up question about the last description."), gesture="kb:NVDA+alt+a")
	def script_askFollowUp(self, gesture):
		if not self.labeller.can_follow_up:
			ui.message(_("Describe something first with NVDA+alt+D or NVDA+alt+S."))
			return

		def send(question):
			question = question.strip()
			if not question:
				return

			def done(text, error):
				if error:
					ui.message(_error_text(error))
				else:
					_show_text(f"{question}\n\n{text}", _("Labelade answer"))

			self.worker.submit(("ask", time.monotonic()), lambda: self.labeller.ask(question), done)
			ui.message(_("Thinking"))

		_ask_text(_("Labelade"), _("Your question about the last description:"), "", send)

	@script(description=_("Turns automatic labelling on focus on or off."), gesture="kb:NVDA+alt+t")
	def script_toggleAuto(self, gesture):
		conf = _conf()
		conf["autoLabel"] = not conf["autoLabel"]
		ui.message(_("Automatic labelling on") if conf["autoLabel"] else _("Automatic labelling off"))

	# Tools menu: label packs

	def _build_menu(self):
		menu = wx.Menu()
		items = (
			(_("&Settings..."), lambda e: gui.mainFrame.popupSettingsDialog(NVDASettingsDialog, LabeladePanel)),
			(_("&Export labels for an app..."), self._on_export),
			(_("&Import a label pack..."), self._on_import),
			(_("&Open labels folder"), lambda e: os.startfile(self.store.directory)),
		)
		for text, handler in items:
			item = menu.Append(wx.ID_ANY, text)
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, handler, item)
		self._menu_item = gui.mainFrame.sysTrayIcon.toolsMenu.AppendSubMenu(menu, _("&Labelade"))

	def _on_export(self, evt):
		apps = self.store.apps()
		if not apps:
			gui.messageBox(_("You have no labels yet."), _("Labelade"))
			return
		with wx.SingleChoiceDialog(gui.mainFrame, _("Which app's labels do you want to export?"), _("Export labels"), apps) as choose:
			if choose.ShowModal() != wx.ID_OK:
				return
			app = apps[choose.GetSelection()]
		with wx.FileDialog(
			gui.mainFrame, _("Save label pack"), defaultFile=f"{app}.json",
			wildcard=_("Label packs (*.json)|*.json"), style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
		) as save:
			if save.ShowModal() != wx.ID_OK:
				return
			count = self.store.export_pack(app, save.GetPath())
		gui.messageBox(_("Exported {count} labels for {app}.").format(count=count, app=app), _("Labelade"))

	def _on_import(self, evt):
		with wx.FileDialog(
			gui.mainFrame, _("Open label pack"), wildcard=_("Label packs (*.json)|*.json"),
			style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
		) as pick:
			if pick.ShowModal() != wx.ID_OK:
				return
			path = pick.GetPath()
		try:
			app, count = self.store.import_pack(path)
		except (OSError, ValueError) as e:
			gui.messageBox(_("This isn't a valid label pack: {error}").format(error=e), _("Labelade"), wx.OK | wx.ICON_ERROR)
			return
		gui.messageBox(
			_("Imported {count} labels for {app}. Labels you wrote yourself were kept.").format(count=count, app=app),
			_("Labelade"),
		)


class LabeladePanel(SettingsPanel):
	# Translators: settings category name.
	title = _("Labelade")

	def makeSettings(self, sizer):
		helper = guiHelper.BoxSizerHelper(self, sizer=sizer)
		conf = _conf()
		self.url = helper.addLabeledControl(_("Lemonade Server &address:"), wx.TextCtrl)
		self.url.SetValue(conf["serverUrl"])
		self.key = helper.addLabeledControl(_("API &key (only if you set LEMONADE_API_KEY):"), wx.TextCtrl, style=wx.TE_PASSWORD)
		self.key.SetValue(conf["apiKey"])
		self.model = helper.addLabeledControl(_("Vision &model (empty picks one automatically):"), wx.TextCtrl)
		self.model.SetValue(conf["model"])
		self.auto = helper.addItem(wx.CheckBox(self, label=_("&Label unlabelled controls automatically when they get focus")))
		self.auto.SetValue(conf["autoLabel"])
		self.beep = helper.addItem(wx.CheckBox(self, label=_("&Beep before a new AI label is spoken")))
		self.beep.SetValue(conf["beep"])
		test = helper.addItem(wx.Button(self, label=_("&Test connection")))
		test.Bind(wx.EVT_BUTTON, self._on_test)

	def _on_test(self, evt):
		url, key, model = self.url.GetValue().strip(), self.key.GetValue().strip(), self.model.GetValue().strip()

		def run():
			client = LemonadeClient(url, key, timeout=10)
			try:
				ids = [m.get("id") for m in client.models()]
				if model and model not in ids:
					raise LemonadeError(_("The model {model} isn't downloaded in Lemonade.").format(model=model))
				text = _("Connected. Labelade will use {model}.").format(model=client.pick_vision_model(model))
				if not is_local(url):
					text += " " + _("Warning: this address is not on this computer, so screenshots leave your PC.")
			except LemonadeError as e:
				text = str(e)
			wx.CallAfter(gui.messageBox, text, _("Labelade"))

		threading.Thread(target=run, daemon=True).start()

	def onSave(self):
		conf = _conf()
		conf["serverUrl"] = self.url.GetValue().strip() or DEFAULT_URL
		conf["apiKey"] = self.key.GetValue().strip()
		conf["model"] = self.model.GetValue().strip()
		conf["autoLabel"] = self.auto.GetValue()
		conf["beep"] = self.beep.GetValue()


if globalVars.appArgs.secure:
	# Never capture the screen on secure screens (sign-in, UAC prompts).
	GlobalPlugin = globalPluginHandler.GlobalPlugin  # noqa: F811
