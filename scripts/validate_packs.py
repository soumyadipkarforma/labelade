"""Check every community label pack in packs/. Used by CI on pull requests.

Run:  python scripts/validate_packs.py [files...]
"""

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "addon", "globalPlugins", "labelade"))

from core.store import validate_pack  # noqa: E402  (the add-on's own rules are the source of truth)


def check(path: str) -> list[str]:
	try:
		with open(path, encoding="utf-8") as f:
			data = json.load(f)
	except (OSError, ValueError) as e:
		return [f"not valid JSON: {e}"]
	errors = validate_pack(data)
	if not errors:
		if os.path.basename(path) != f"{data['app']}.json":
			errors.append(f"file must be named {data['app']}.json")
		keys = [(x["role"], x.get("automationId") or x.get("hash")) for x in data["labels"]]
		if len(keys) != len(set(keys)):
			errors.append("the same control appears twice")
		if not data["labels"]:
			errors.append("pack has no labels")
	return errors


def main(paths: list[str]) -> int:
	paths = paths or sorted(glob.glob(os.path.join(ROOT, "packs", "*.json")))
	failed = 0
	for path in paths:
		errors = check(path)
		name = os.path.relpath(path, ROOT)
		if errors:
			failed += 1
			print(f"FAIL {name}")
			for e in errors:
				print(f"  - {e}")
		else:
			print(f"ok   {name}")
	print(f"{len(paths)} pack(s), {failed} failed")
	return 1 if failed else 0


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
