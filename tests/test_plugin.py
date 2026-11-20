import importlib
import os
import sys
import tempfile
import time
import types
import unittest

from mock_lemonade import MockLemonade
from tests import ROOT
from tests import nvda_stubs as nv

nv.install()
sys.path.insert(0, os.path.join(ROOT, "addon", "globalPlugins"))
plugin_module = importlib.import_module("labelade")


def wait_for(cond, timeout=5):
	end = time.time() + timeout
	while time.time() < end:
		nv.run_queue()
		if cond():
			return True
		time.sleep(0.02)
	return False


class PluginTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.mock = MockLemonade()
		sys.modules["config"].conf["labelade"]["serverUrl"] = cls.mock.url

	@classmethod
	def tearDownClass(cls):
		cls.mock.close()

	def setUp(self):
		nv.spoken.clear()
		nv.beeps.clear()
		nv.shown.clear()
		sys.modules["globalVars"].appArgs.configPath = tempfile.mkdtemp()  # no labels leak between tests
		self.plugin = plugin_module.GlobalPlugin()
		nv.state.foreground = nv.FakeObject("General - Discord", nv.Role.WINDOW, (0, 0, 1280, 800))

	def tearDown(self):
		self.plugin.terminate()

	def focus(self, obj):
		nv.state.focus = nv.state.navigator = obj
		order = []
		self.plugin.event_gainFocus(obj, lambda: order.append(obj.name))
		return order

	def test_scripts_have_gestures_and_help(self):
		scripts = [getattr(self.plugin, n) for n in dir(self.plugin) if n.startswith("script_")]
		self.assertEqual(len(scripts), 7)
		gestures = [s.meta["gesture"] for s in scripts]
		self.assertEqual(len(set(gestures)), len(gestures))
		self.assertTrue(all(s.meta["description"] for s in scripts))

	def test_unlabelled_button_gets_labelled_and_remembered(self):
		button = nv.FakeObject("", aid="sendButton")
		self.focus(button)
		self.assertTrue(wait_for(lambda: nv.spoken), "no label was spoken")
		self.assertEqual(nv.spoken, ["Send message"])
		self.assertEqual(button.name, "Send message")
		self.assertEqual(len(nv.beeps), 1)
		# Next visit: a new object for the same control is named before NVDA speaks it, with no model call.
		calls = len(self.mock.requests)
		again = nv.FakeObject("", aid="sendButton")
		self.assertEqual(self.focus(again), ["Send message"])
		self.assertEqual(len(self.mock.requests), calls)

	def test_saved_label_is_spoken_in_browse_mode(self):
		# Found in a real NVDA + Edge run: browse mode reads its own buffer, so a set name alone stays silent.
		self.focus(nv.FakeObject("", aid="sendButton"))
		self.assertTrue(wait_for(lambda: nv.spoken))
		nv.spoken.clear()
		web = nv.FakeObject("", aid="sendButton")
		web.treeInterceptor = types.SimpleNamespace(passThrough=False)
		self.focus(web)
		self.assertEqual(nv.spoken, ["Send message"])
		nv.spoken.clear()
		web.treeInterceptor.passThrough = True  # focus mode reads obj.name itself: don't say it twice
		self.focus(nv.FakeObject("", aid="sendButton"))
		self.assertEqual(nv.spoken, [])

	def test_labelled_controls_are_left_alone(self):
		self.focus(nv.FakeObject("Send"))
		self.focus(nv.FakeObject("", role=nv.Role.EDITABLETEXT))
		time.sleep(0.2)
		nv.run_queue()
		self.assertEqual(nv.spoken, [])

	def test_hash_finds_controls_without_ids(self):
		self.focus(nv.FakeObject("", rect=(300, 40, 32, 32)))
		self.assertTrue(wait_for(lambda: nv.spoken))
		named = nv.FakeObject("", rect=(300, 40, 32, 32))
		self.assertEqual(self.focus(named), ["Send message"])

	def test_edit_label_and_window_scan(self):
		target = nv.FakeObject("", aid="mute")
		nv.state.navigator = target

		class Dialog:
			def __init__(self, parent, prompt, title, default):
				pass

			def ShowModal(self):
				return 5100

			def GetValue(self):
				return "  Mute   microphone "

			def Destroy(self):
				pass

		sys.modules["wx"].TextEntryDialog = Dialog
		self.plugin.script_editLabel(None)
		self.assertEqual(nv.spoken[-1], "Label saved.")
		self.assertEqual(target.name, "Mute microphone")
		# The AI must never replace a label the user typed.
		self.plugin.script_labelNow(None)
		self.assertIn("Your label: Mute microphone", nv.spoken[-1])

		nv.state.foreground = nv.FakeObject("Win", nv.Role.WINDOW, (0, 0, 800, 600), children=[
			nv.FakeObject("", aid="a"), nv.FakeObject("OK"), nv.FakeObject("", aid="mute"), nv.FakeObject("", aid="b"),
		])
		nv.spoken.clear()
		self.plugin.script_labelWindow(None)
		self.assertEqual(nv.spoken[0], "Labelling 2 controls. Press NVDA+alt+W again to stop.")
		self.assertTrue(wait_for(lambda: len(nv.spoken) == 2))
		self.assertEqual(nv.spoken[1], "Labelade finished: 2 labelled, 0 not sure.")

	def test_describe_and_follow_up(self):
		nv.state.navigator = nv.FakeObject("Photo", nv.Role.GRAPHIC, (0, 0, 400, 300))
		self.plugin.script_askFollowUp(None)
		self.assertIn("Describe something first", nv.spoken[-1])
		self.plugin.script_describeObject(None)
		self.assertTrue(wait_for(lambda: nv.shown))
		self.assertIn("chat window", nv.shown[-1][1])

	def test_server_down_is_reported_once(self):
		conf = sys.modules["config"].conf["labelade"]
		conf["serverUrl"] = "http://127.0.0.1:9/api/v1"
		try:
			self.focus(nv.FakeObject("", aid="x1"))
			self.assertTrue(wait_for(lambda: nv.spoken, timeout=10))
			self.assertIn("Can't reach Lemonade", nv.spoken[0])
			self.focus(nv.FakeObject("", aid="x2"))
			time.sleep(0.5)
			nv.run_queue()
			self.assertEqual(len(nv.spoken), 1)  # quiet for a minute instead of on every Tab
		finally:
			conf["serverUrl"] = self.mock.url
		# The server comes back within the quiet minute: labels must be spoken again at once.
		self.focus(nv.FakeObject("", aid="x3"))
		self.assertTrue(wait_for(lambda: len(nv.spoken) == 2))
		self.assertEqual(nv.spoken[1], "Send message")

	def test_scan_survives_vanishing_objects_and_speaks_the_focused_one(self):
		class Gone(nv.FakeObject):
			@property
			def location(self):
				raise RuntimeError("object died")

			@location.setter
			def location(self, value):
				pass

		focused = nv.FakeObject("", aid="b")
		nv.state.foreground = nv.FakeObject("Win", nv.Role.WINDOW, (0, 0, 800, 600), children=[
			nv.FakeObject("", aid="a"), Gone(""), focused,
		])
		nv.state.focus = nv.state.navigator = focused
		self.plugin.script_labelWindow(None)
		self.assertEqual(nv.spoken[0], "Labelling 2 controls. Press NVDA+alt+W again to stop.")
		self.assertTrue(wait_for(lambda: "Labelade finished: 2 labelled, 0 not sure." in nv.spoken))
		self.assertIn("Send message", nv.spoken)  # the scan's label for the control the user is on is spoken


if __name__ == "__main__":
	unittest.main()
