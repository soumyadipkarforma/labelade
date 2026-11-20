import json
import os
import struct
import tempfile
import threading
import unittest
import zlib

from core import heuristics, imaging
from core.client import LemonadeClient, LemonadeError, is_local
from core.labeller import Labeller, Worker
from core.store import Label, LabelStore, validate_pack
from mock_lemonade import MockLemonade


def pattern(width, height, seed=0):
	"""A non-flat test image: diagonal stripes."""
	px = bytearray()
	for y in range(height):
		for x in range(width):
			v = 255 if ((x + y + seed) // 4) % 2 else 0
			px += bytes((v, v, v, 255))
	return imaging.Image(width, height, bytes(px))


class Heuristics(unittest.TestCase):
	def test_needs_label(self):
		for name in ("", "  ", None, "button", "Button", "ic_send_24", "send.png", "3f2a9c1e-77", "…", "img"):
			self.assertTrue(heuristics.needs_label(name, "button"), name)
		for name in ("Send", "OK", "Mute microphone", "X"):
			self.assertFalse(heuristics.needs_label(name, "button"), name)

	def test_parse_json(self):
		self.assertEqual(heuristics.parse_label('{"label": "Send message", "confidence": "high"}', "button"), ("Send message", "high"))
		self.assertEqual(heuristics.parse_label('Sure! {"label":"mute","confidence":"low"}', "button"), ("Mute", "low"))

	def test_parse_strips_thinking_and_role(self):
		reply = '<think>it looks like a paper plane</think>{"label": "Send button"}'
		self.assertEqual(heuristics.parse_label(reply, "button"), ("Send", "high"))
		self.assertEqual(heuristics.parse_label('done thinking</think>\n{"label": "Close"}', "button")[0], "Close")

	def test_parse_fallback_is_low_confidence(self):
		self.assertEqual(heuristics.parse_label('"Attach file".\nExtra', "button"), ("Attach file", "low"))

	def test_unknown_is_none(self):
		for reply in ('{"label": "unknown"}', '{"label": ""}', "", '{"label": "button"}', '{"label": "icon.png"}'):
			self.assertIsNone(heuristics.parse_label(reply, "button")[0], reply)

	def test_long_label_is_cut_at_a_word(self):
		label = heuristics.sanitize_label("Open the settings for this conversation and all of its many members now", "button")
		self.assertLessEqual(len(label), 48)
		self.assertFalse(label.endswith(" "))


class Imaging(unittest.TestCase):
	def test_png_round_trip(self):
		img = imaging.Image(2, 1, bytes((10, 20, 30, 255, 40, 50, 60, 255)))  # BGRX
		png = img.to_png()
		self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
		width, height = struct.unpack(">II", png[16:24])
		self.assertEqual((width, height), (2, 1))
		idat = png.index(b"IDAT")
		length = struct.unpack(">I", png[idat - 4:idat])[0]
		raw = zlib.decompress(png[idat + 4:idat + 4 + length])
		self.assertEqual(raw, bytes((0, 30, 20, 10, 60, 50, 40)))  # filter byte, then RGB

	def test_rejects_wrong_buffer(self):
		with self.assertRaises(ValueError):
			imaging.Image(2, 2, b"\x00" * 4)

	def test_draw_box(self):
		img = imaging.Image(10, 10, b"\x00" * 400).draw_box(2, 2, 4, 4, thickness=1)
		red = bytes((0, 0, 255, 255))
		at = lambda x, y: img.bgra[(y * 10 + x) * 4:(y * 10 + x) * 4 + 4]
		self.assertEqual(at(2, 2), red)
		self.assertEqual(at(5, 5), red)
		self.assertEqual(at(3, 3), b"\x00" * 4)  # inside stays untouched
		imaging.Image(10, 10, b"\x00" * 400).draw_box(-5, -5, 30, 30, thickness=3)  # off the edges must not crash

	def test_hash(self):
		self.assertIsNone(imaging.Image(9, 8, b"\x80" * 288).dhash())  # flat: would match everything
		a, b = pattern(36, 32).dhash(), pattern(36, 32, seed=4).dhash()
		self.assertEqual(len(a), 16)
		self.assertEqual(a, pattern(36, 32).dhash())
		self.assertGreater(imaging.hamming(a, b), 6)

	def test_context_and_fit(self):
		self.assertEqual(imaging.context_rect(0, 0, 20, 20, (0, 0, 1920, 1080)), (0, 0, 68, 68))
		left, top, width, height = imaging.context_rect(1900, 1060, 20, 20, (0, 0, 1920, 1080))
		self.assertEqual((left + width, top + height), (1920, 1080))
		self.assertEqual(imaging.fit_size(68, 34), (336, 168))
		self.assertEqual(imaging.fit_size(2048, 1024), (1024, 512))
		self.assertEqual(imaging.fit_size(500, 400), (500, 400))


class Store(unittest.TestCase):
	def setUp(self):
		self.dir = tempfile.mkdtemp()
		self.store = LabelStore(self.dir)

	def test_find_by_id_and_hash(self):
		self.store.put("discord", Label("button", "Mute", automationId="uia:mute"))
		self.store.put("discord", Label("button", "Send", hash="ffff0000ffff0000"))
		self.assertEqual(self.store.find("discord", "button", "uia:mute").label, "Mute")
		self.assertEqual(self.store.find("discord", "button", "", "ffff0000ffff0001").label, "Send")  # 1 bit off
		self.assertIsNone(self.store.find("discord", "button", "", "0000ffff0000ffff"))
		self.assertIsNone(self.store.find("discord", "link", "uia:mute"))  # role must match
		self.assertEqual(LabelStore(self.dir).find("discord", "button", "uia:mute").label, "Mute")  # persisted

	def test_user_label_wins(self):
		self.store.put("app", Label("button", "My name", source="user", automationId="uia:x"))
		self.store.put("app", Label("button", "AI guess", source="ai", automationId="uia:x"))
		self.assertEqual(self.store.find("app", "button", "uia:x").label, "My name")
		self.store.put("app", Label("button", "Renamed", source="user", automationId="uia:x"))
		self.assertEqual(self.store.find("app", "button", "uia:x").label, "Renamed")

	def test_needs_a_key(self):
		with self.assertRaises(ValueError):
			self.store.put("app", Label("button", "Nothing to find it by"))
		with self.assertRaises(ValueError):
			self.store.put("../evil", Label("button", "x", automationId="uia:x"))

	def test_pack_round_trip(self):
		self.store.put("spotify", Label("button", "Shuffle", automationId="uia:shuffle", model="m"))
		self.store.put("spotify", Label("button", "Mine", source="user", automationId="uia:mine"))
		path = os.path.join(self.dir, "out.pack")
		self.assertEqual(self.store.export_pack("spotify", path), 2)
		with open(path, encoding="utf-8") as f:
			self.assertEqual(validate_pack(json.load(f)), [])
		other = LabelStore(tempfile.mkdtemp())
		other.put("spotify", Label("button", "Kept", source="user", automationId="uia:shuffle"))
		self.assertEqual(other.import_pack(path), ("spotify", 1))  # "Kept" is not overwritten
		self.assertEqual(other.find("spotify", "button", "uia:shuffle").label, "Kept")
		self.assertEqual(other.find("spotify", "button", "uia:mine").source, "pack")

	def test_validate_rejects_bad_packs(self):
		self.assertTrue(validate_pack([]))
		bad = {"schemaVersion": 1, "app": "a b", "labels": [{"role": "button", "label": "x\n", "hash": "XYZ", "evil": 1}]}
		errors = " ".join(validate_pack(bad))
		for word in ("app", "unknown fields", "printable", "hash"):
			self.assertIn(word, errors)

	def test_wrong_types_are_rejected(self):
		# A number that looks like a hash used to pass and then crash every lookup in the app.
		bad = {"schemaVersion": 1, "app": "discord", "labels": [
			{"role": "button", "label": "Send", "hash": 1234567890123456},
			{"role": "button", "label": "Mute", "automationId": ["a"]},
			{"role": "button", "label": "X", "automationId": "uia:x", "updated": "soon"},
		]}
		errors = " ".join(validate_pack(bad))
		for field in ("hash must be a string", "automationId must be a string", "updated must be a whole number"):
			self.assertIn(field, errors)

	def test_bad_entries_dont_lose_good_ones(self):
		good = {"role": "button", "label": "Good", "automationId": "uia:g"}
		with open(os.path.join(self.dir, "app.json"), "w", encoding="utf-8") as f:
			json.dump({"schemaVersion": 1, "app": "app", "labels": [good, {"role": "button"}]}, f)
		self.assertEqual(self.store.find("app", "button", "uia:g").label, "Good")

	def test_corrupt_file_is_kept_aside(self):
		with open(os.path.join(self.dir, "app.json"), "w", encoding="utf-8") as f:
			f.write("{not json")
		self.assertIsNone(self.store.find("app", "button", "uia:x"))
		self.assertTrue(os.path.exists(os.path.join(self.dir, "app.json.corrupt")))


class Client(unittest.TestCase):
	def test_local(self):
		self.assertTrue(is_local("http://localhost:13305/api/v1"))
		self.assertTrue(is_local("http://[::1]:13305"))
		self.assertFalse(is_local("http://192.168.1.4:13305"))

	def test_picks_loaded_then_preferred(self):
		mock = MockLemonade(loaded=["Gemma-3-4b-it-GGUF"])
		try:
			self.assertEqual(LemonadeClient(mock.url).pick_vision_model(), "Gemma-3-4b-it-GGUF")
			mock.loaded = ["Qwen3-0.6B-GGUF"]  # loaded but can't see images
			self.assertEqual(LemonadeClient(mock.url).pick_vision_model(), "Qwen3-VL-4B-Instruct-GGUF")
			self.assertEqual(LemonadeClient(mock.url).pick_vision_model("Custom"), "Custom")
		finally:
			mock.close()

	def test_no_vision_model(self):
		mock = MockLemonade(models=[{"id": "Text-Only", "labels": ["chat"]}])
		try:
			with self.assertRaisesRegex(LemonadeError, "No vision model"):
				LemonadeClient(mock.url).pick_vision_model()
		finally:
			mock.close()

	def test_errors_are_speakable(self):
		mock = MockLemonade(api_key="secret")
		try:
			with self.assertRaisesRegex(LemonadeError, "API key"):
				LemonadeClient(mock.url).models()
			self.assertTrue(LemonadeClient(mock.url, "secret").models())
		finally:
			mock.close()
		with self.assertRaisesRegex(LemonadeError, "reach Lemonade"):
			LemonadeClient("http://127.0.0.1:9", timeout=2).models()


class LabellerFlow(unittest.TestCase):
	def setUp(self):
		self.mock = MockLemonade()
		self.labeller = Labeller(lambda: LemonadeClient(self.mock.url), lambda: "")

	def tearDown(self):
		self.mock.close()

	def test_label(self):
		png = pattern(40, 40).draw_box(10, 10, 20, 20).to_png()
		self.assertEqual(self.labeller.label(png, "button", "discord", "General"), ("Send message", "high", "Qwen3-VL-4B-Instruct-GGUF"))
		sent = self.mock.requests[-1]
		self.assertIs(sent["enable_thinking"], False)
		self.assertEqual(sent["temperature"], 0)
		self.assertTrue(sent["messages"][1]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,"))

	def test_describe_then_follow_up(self):
		self.assertFalse(self.labeller.can_follow_up)
		with self.assertRaises(LemonadeError):
			self.labeller.ask("What colour?")
		self.assertIn("chat window", self.labeller.describe(pattern(20, 20).to_png(), "window", "app", "w"))
		self.assertEqual(self.labeller.ask("What colour?"), "(mock) You asked: What colour?")
		history = self.mock.requests[-1]["messages"]
		self.assertEqual([m["role"] for m in history], ["system", "user", "assistant", "user"])

	def test_model_is_picked_again_after_an_error(self):
		self.labeller.label(pattern(8, 8).to_png(), "button", "a", "w")
		self.mock.models = [{"id": "Gemma-3-4b-it-GGUF", "labels": ["vision"]}]  # the old model was deleted
		with self.assertRaises(LemonadeError):
			self.labeller.label(pattern(8, 8).to_png(), "button", "a", "w")
		self.assertEqual(self.labeller.label(pattern(8, 8).to_png(), "button", "a", "w")[2], "Gemma-3-4b-it-GGUF")


class WorkerTests(unittest.TestCase):
	def test_results_errors_duplicates_and_cancel(self):
		results, gate, started, finished = [], threading.Event(), threading.Event(), threading.Event()
		worker = Worker(lambda fn, *a: fn(*a))

		def slow():
			started.set()
			gate.wait(5)
			return "slow"

		def boom():
			raise RuntimeError("bad")

		self.assertTrue(worker.submit("a", slow, lambda r, e: results.append(r)))
		self.assertTrue(started.wait(5))
		self.assertFalse(worker.submit("a", slow, lambda r, e: results.append(r)))  # duplicate key
		worker.submit("b", boom, lambda r, e: (results.append(type(e).__name__), finished.set()))
		worker.submit("c", lambda: "newest", lambda r, e: results.append(r))
		gate.set()
		self.assertTrue(finished.wait(5))
		# Newest first: the control the user tabbed to last is labelled before older ones.
		self.assertEqual(results, ["slow", "newest", "RuntimeError"])

		gate.clear()
		started.clear()
		worker.submit("d", slow, lambda r, e: results.append("cancelled one ran"))
		self.assertTrue(started.wait(5))
		worker.submit("e", lambda: "x", lambda r, e: results.append("cancelled two ran"))
		worker.cancel_all()
		gate.set()
		done = threading.Event()
		worker.submit("f", lambda: "ok", lambda r, e: done.set())
		self.assertTrue(done.wait(5))
		self.assertNotIn("cancelled two ran", results)
		self.assertNotIn("cancelled one ran", results)
		worker.stop()


if __name__ == "__main__":
	unittest.main()
