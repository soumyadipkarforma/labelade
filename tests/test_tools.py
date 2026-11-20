import importlib.util
import json
import os
import tempfile
import unittest
import zipfile

import build
from tests import ROOT

spec = importlib.util.spec_from_file_location("validate_packs", os.path.join(ROOT, "scripts", "validate_packs.py"))
validate_packs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_packs)


class BuildTests(unittest.TestCase):
	def test_addon_package(self):
		path = build.build()
		with zipfile.ZipFile(path) as z:
			names = z.namelist()
			manifest = z.read("manifest.ini").decode()
			guide = z.read("doc/en/readme.html").decode()
		self.assertIn("globalPlugins/labelade/__init__.py", names)
		self.assertIn("globalPlugins/labelade/core/store.py", names)
		self.assertFalse(any("__pycache__" in n for n in names))
		self.assertIn("name = labelade", manifest)
		self.assertIn("minimumNVDAVersion = 2025.1.0", manifest)
		self.assertIn("<h1>", guide)
		self.assertIn("<table>", guide)

	def test_markdown(self):
		out = build.markdown_to_html("# T\n\nA `x` & **b**\n\n- one\n- [two](u)\n\n| a | b |\n|---|---|\n| 1 | 2 |\n", "t")
		for piece in ("<h1>T</h1>", "<p>A <code>x</code> &amp; <strong>b</strong></p>", '<li><a href="u">two</a></li>', "<td>2</td>"):
			self.assertIn(piece, out)


class ValidatePacksTests(unittest.TestCase):
	def write(self, name, data):
		path = os.path.join(tempfile.mkdtemp(), name)
		with open(path, "w", encoding="utf-8") as f:
			json.dump(data, f)
		return path

	def test_good_and_bad(self):
		label = {"role": "button", "label": "Mute", "automationId": "uia:mute"}
		good = self.write("discord.json", {"schemaVersion": 1, "app": "discord", "labels": [label]})
		self.assertEqual(validate_packs.check(good), [])
		misnamed = self.write("other.json", {"schemaVersion": 1, "app": "discord", "labels": [label]})
		self.assertIn("file must be named discord.json", validate_packs.check(misnamed))
		twice = self.write("discord.json", {"schemaVersion": 1, "app": "discord", "labels": [label, label]})
		self.assertIn("the same control appears twice", validate_packs.check(twice))
		self.assertEqual(validate_packs.main([good]), 0)
		self.assertEqual(validate_packs.main([twice]), 1)

	def test_schema_file_is_valid_json(self):
		with open(os.path.join(ROOT, "schema", "label-pack.schema.json"), encoding="utf-8") as f:
			schema = json.load(f)
		self.assertEqual(schema["properties"]["schemaVersion"]["const"], 1)


if __name__ == "__main__":
	unittest.main()
