"""Label storage. One JSON file per app; the same format is the shareable label pack."""

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass

from .imaging import hamming

PACK_VERSION = 1
HASH_DISTANCE = 6  # of 64 bits; tolerates focus rings, hover tints and small scaling differences
SOURCES = ("user", "ai", "pack")
_APP_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
_HASH_RE = re.compile(r"^[0-9a-f]{16}$")


@dataclass
class Label:
	role: str
	label: str
	source: str = "ai"
	confidence: str = "high"
	automationId: str = ""
	hash: str = ""
	model: str = ""
	updated: int = 0


def validate_pack(data) -> list[str]:
	"""Return problems with a pack (empty list means valid). Packs come from strangers, so check everything."""
	if not isinstance(data, dict):
		return ["pack must be a JSON object"]
	errors = []
	if data.get("schemaVersion") != PACK_VERSION:
		errors.append(f"schemaVersion must be {PACK_VERSION}")
	if not isinstance(data.get("app"), str) or not _APP_RE.match(data["app"]):
		errors.append("app must be the NVDA app module name (letters, digits, _ . -)")
	labels = data.get("labels")
	if not isinstance(labels, list):
		return errors + ["labels must be a list"]
	allowed = set(Label.__dataclass_fields__)
	for i, item in enumerate(labels):
		where = f"labels[{i}]"
		if not isinstance(item, dict):
			errors.append(f"{where} must be an object")
			continue
		extra = set(item) - allowed
		if extra:
			errors.append(f"{where} has unknown fields: {', '.join(sorted(extra))}")
		if not isinstance(item.get("role"), str) or not item["role"]:
			errors.append(f"{where}.role is required")
		text = item.get("label")
		if not isinstance(text, str) or not 0 < len(text.strip()) <= 80 or any(ord(ch) < 32 for ch in text):
			errors.append(f"{where}.label must be 1-80 printable characters")
		for key in ("automationId", "hash", "model"):
			if not isinstance(item.get(key, ""), str):
				errors.append(f"{where}.{key} must be a string")
		if not isinstance(item.get("updated", 0), int) or isinstance(item.get("updated"), bool):
			errors.append(f"{where}.updated must be a whole number")
		if not item.get("automationId") and not item.get("hash"):
			errors.append(f"{where} needs an automationId or a hash")
		if item.get("hash") and not _HASH_RE.match(str(item["hash"])):
			errors.append(f"{where}.hash must be 16 lowercase hex characters")
		if item.get("source", "ai") not in SOURCES:
			errors.append(f"{where}.source must be one of {', '.join(SOURCES)}")
		if item.get("confidence", "high") not in ("high", "low"):
			errors.append(f"{where}.confidence must be high or low")
	return errors


class LabelStore:
	def __init__(self, directory: str):
		self.directory = directory
		self._apps: dict[str, list[Label]] = {}
		self._lock = threading.Lock()
		os.makedirs(directory, exist_ok=True)

	def _path(self, app: str) -> str:
		return os.path.join(self.directory, f"{app}.json")

	def _load(self, app: str) -> list[Label]:
		if app not in self._apps:
			labels = []
			path = self._path(app)
			try:
				with open(path, encoding="utf-8") as f:
					data = json.load(f)
				for item in data.get("labels", []) if isinstance(data, dict) else []:
					# Keep every good entry; one bad line must not cost the user all their labels.
					if not validate_pack({"schemaVersion": PACK_VERSION, "app": app, "labels": [item]}):
						labels.append(Label(**item))
			except FileNotFoundError:
				pass
			except (OSError, ValueError):
				try:
					os.replace(path, path + ".corrupt")  # keep it for the user instead of overwriting it
				except OSError:
					pass
			self._apps[app] = labels
		return self._apps[app]

	def _save(self, app: str) -> None:
		data = {"schemaVersion": PACK_VERSION, "app": app, "labels": [asdict(x) for x in self._apps.get(app, [])]}
		tmp = self._path(app) + ".tmp"
		with open(tmp, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=1, ensure_ascii=False)
		os.replace(tmp, self._path(app))  # atomic: a crash mid-write never loses existing labels

	def apps(self) -> list[str]:
		names = {f[:-5] for f in os.listdir(self.directory) if f.endswith(".json")}
		return sorted(names | {a for a, labels in self._apps.items() if labels})

	def find(self, app: str, role: str, automation_id: str = "", image_hash: str | None = None) -> Label | None:
		"""Exact automation id first, then the nearest image hash within HASH_DISTANCE."""
		if not _APP_RE.match(app):
			return None
		with self._lock:
			labels = [x for x in self._load(app) if x.role == role]
			if automation_id:
				for x in labels:
					if x.automationId == automation_id:
						return x
			if image_hash:
				best, best_d = None, HASH_DISTANCE + 1
				for x in labels:
					if x.hash and not (automation_id and x.automationId):
						d = hamming(x.hash, image_hash)
						if d < best_d:
							best, best_d = x, d
				return best
		return None

	def put(self, app: str, entry: Label) -> Label:
		"""Add or replace a label. Never lets an AI or pack guess overwrite a label the user typed."""
		if not _APP_RE.match(app):
			raise ValueError(f"bad app name {app!r}")
		if not entry.automationId and not entry.hash:
			raise ValueError("a label needs an automationId or a hash to be found again")
		entry.updated = entry.updated or int(time.time())
		with self._lock:
			labels = self._load(app)
			for i, x in enumerate(labels):
				same = x.role == entry.role and (
					(entry.automationId and x.automationId == entry.automationId)
					or (not entry.automationId and not x.automationId and entry.hash and x.hash and hamming(x.hash, entry.hash) <= HASH_DISTANCE)
				)
				if same:
					if x.source == "user" and entry.source != "user":
						return x
					labels[i] = entry
					break
			else:
				labels.append(entry)
			self._save(app)
		return entry

	def remove(self, app: str, entry: Label) -> None:
		with self._lock:
			labels = self._load(app)
			if entry in labels:
				labels.remove(entry)
				self._save(app)

	def export_pack(self, app: str, path: str) -> int:
		with self._lock:
			labels = [asdict(x) for x in self._load(app)]
		for item in labels:
			item["updated"] = 0  # keep packs diff-friendly
		with open(path, "w", encoding="utf-8") as f:
			json.dump({"schemaVersion": PACK_VERSION, "app": app, "labels": labels}, f, indent=1, ensure_ascii=False)
		return len(labels)

	def import_pack(self, path: str) -> tuple[str, int]:
		"""Merge a pack. Returns (app, number of labels added or updated). Raises ValueError if invalid."""
		with open(path, encoding="utf-8") as f:
			data = json.load(f)
		errors = validate_pack(data)
		if errors:
			raise ValueError("; ".join(errors[:5]))
		app, count = data["app"], 0
		for item in data["labels"]:
			entry = Label(**{**item, "source": "pack", "updated": 0})
			if self.put(app, entry) is entry:
				count += 1
		return app, count
