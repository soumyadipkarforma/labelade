"""Just enough fake NVDA to import the plugin and drive its event handlers in a test.

These stubs mirror the NVDA APIs Labelade calls (checked against NVDA 2026.3 source). They don't
prove the add-on works inside NVDA; they catch wiring mistakes before a manual test does.
"""

import builtins
import enum
import sys
import tempfile
import types
from collections import namedtuple

Rect = namedtuple("Rect", "left top width height")
spoken: list[str] = []
beeps: list[tuple] = []
shown: list[tuple] = []
queued = []
state = types.SimpleNamespace(focus=None, navigator=None, foreground=None, secure=False)


class Role(enum.IntEnum):
	BUTTON = 9
	LINK = 19
	GRAPHIC = 16
	EDITABLETEXT = 8
	WINDOW = 1


class State(enum.IntEnum):
	INVISIBLE = 1
	OFFSCREEN = 2


class FakeObject:
	def __init__(self, name="", role=Role.BUTTON, rect=(100, 100, 24, 24), app="discord", aid="", children=()):
		self.name, self.role, self.location = name, role, Rect(*rect)
		self.appModule = types.SimpleNamespace(appName=app)
		self.UIAAutomationId = aid
		self.states = set()
		self.children = list(children)


def _module(name, **attrs):
	mod = types.ModuleType(name)
	mod.__dict__.update(attrs)
	sys.modules[name] = mod
	return mod


class _Conf(dict):
	spec: dict = {}


def install():
	builtins._ = lambda s: s
	conf = _Conf()
	conf["labelade"] = {"serverUrl": "", "apiKey": "", "model": "", "autoLabel": True, "beep": True}
	_module("addonHandler", initTranslation=lambda: None)
	_module("api",
		getFocusObject=lambda: state.focus, getNavigatorObject=lambda: state.navigator,
		getForegroundObject=lambda: state.foreground,
		getDesktopObject=lambda: types.SimpleNamespace(location=Rect(0, 0, 1920, 1080)))
	_module("config", conf=conf)
	_module("controlTypes", Role=Role, State=State)

	class GlobalPlugin:
		def __init__(self):
			pass

		def terminate(self):
			pass

	_module("globalPluginHandler", GlobalPlugin=GlobalPlugin)
	_module("globalVars", appArgs=types.SimpleNamespace(configPath=tempfile.mkdtemp(), secure=state.secure))
	# queueHandler runs functions later on NVDA's main thread; tests run them with run_queue().
	_module("queueHandler", eventQueue="events", queueFunction=lambda q, fn, *a: queued.append((fn, a)))

	class ScreenBitmap:
		def __init__(self, width, height):
			self.width, self.height = width, height

		def captureImage(self, x, y, w, h):
			# Stripes that depend on where we look, so different controls hash differently.
			px = bytearray()
			for row in range(self.height):
				for col in range(self.width):
					v = 255 if ((col + row + x) // 3) % 2 else 0
					px += bytes((v, v, v, 0))
			return px

	_module("screenBitmap", ScreenBitmap=ScreenBitmap)
	_module("tones", beep=lambda hz, ms: beeps.append((hz, ms)))
	_module("ui", message=spoken.append, browseableMessage=lambda text, title, **kw: shown.append((title, text)))

	class _Anything:
		def __init__(self, *a, **k):
			pass

		def __getattr__(self, name):
			return _Anything()

		def __call__(self, *a, **k):
			return _Anything()

	wx = _module("wx", CallAfter=lambda fn, *a: fn(*a), ID_OK=5100, ID_ANY=-1, EVT_MENU=1, EVT_BUTTON=2,
		Menu=_Anything, TextCtrl=_Anything, CheckBox=_Anything, Button=_Anything, TE_PASSWORD=0)
	wx.TextEntryDialog = None  # set per test

	class SettingsPanel:
		pass

	class NVDASettingsDialog:
		categoryClasses: list = []

	gui = _module("gui", mainFrame=_Anything(), messageBox=lambda *a, **k: shown.append(a))
	gui.guiHelper = _module("gui.guiHelper", BoxSizerHelper=_Anything)
	gui.settingsDialogs = _module("gui.settingsDialogs", SettingsPanel=SettingsPanel, NVDASettingsDialog=NVDASettingsDialog)

	class _Log:
		def __getattr__(self, name):
			return lambda *a, **k: None

	_module("logHandler", log=_Log())

	def script(**meta):
		def wrap(fn):
			fn.meta = meta
			return fn
		return wrap

	_module("scriptHandler", script=script)


def run_queue():
	while queued:
		fn, args = queued.pop(0)
		fn(*args)
