"""Decide which controls need a label, and clean up labels a model returns."""

import json
import re

# Names that are as good as no name: what developers leave behind when they forget a label.
_JUNK_WORDS = {
	"button", "btn", "icon", "image", "img", "graphic", "picture", "link", "unlabeled", "unlabelled",
	"untitled", "null", "undefined", "none", "click", "click here", "item", "menu item", "tab", "toggle",
	"svg", "path", "div", "span", "label", "control", "element",
}
_FILE_RE = re.compile(r"\.(png|jpe?g|gif|svg|ico|bmp|webp)$", re.I)
_RESOURCE_RE = re.compile(r"^(ic|icon|img|btn|res|drawable|asset)[_\-.]", re.I)
_HEXISH_RE = re.compile(r"^[0-9a-f\-{}]{8,}$", re.I)
_THINK_RE = re.compile(r"<think>.*?</think>", re.S | re.I)
_JSON_RE = re.compile(r"\{.*?\}", re.S)


def needs_label(name: str | None, role: str) -> bool:
	"""True when a control's accessible name tells a screen reader user nothing useful."""
	text = (name or "").strip()
	if not text:
		return True
	low = text.lower()
	if low == role.lower() or low in _JUNK_WORDS:
		return True
	if _FILE_RE.search(low) or _RESOURCE_RE.match(low) or _HEXISH_RE.match(low):
		return True
	# Single symbols and digits ("…", "+", "3") rarely describe an action on their own.
	return len(text) <= 1 and not text.isalpha()


def strip_thinking(text: str) -> str:
	"""Remove reasoning blocks some models emit before the answer."""
	text = _THINK_RE.sub("", text or "")
	if "</think>" in text:  # an unclosed opening tag got cut off by the server
		text = text.split("</think>", 1)[1]
	return text.strip()


def parse_label(text: str, role: str) -> tuple[str | None, str]:
	"""Turn a model reply into (label, confidence). label is None when the model could not tell."""
	text = strip_thinking(text)
	label, confidence = None, "high"
	for blob in _JSON_RE.findall(text):
		try:
			data = json.loads(blob)
		except ValueError:
			continue
		if isinstance(data, dict) and "label" in data:
			label = str(data.get("label") or "")
			confidence = "low" if str(data.get("confidence", "high")).lower().startswith("low") else "high"
			break
	if label is None:
		# Small models sometimes ignore the JSON instruction; take the first non-empty line.
		label = next((ln for ln in text.splitlines() if ln.strip()), "")
		confidence = "low"
	return sanitize_label(label, role), confidence


def sanitize_label(label: str, role: str) -> str | None:
	"""Short, speakable label without quotes, trailing punctuation or the role word."""
	s = re.sub(r"^(label|name)\s*[:=]\s*", "", label.strip(), flags=re.I)
	s = s.strip().strip("\"'`*.:;,!").strip()
	s = re.sub(r"\s+", " ", s)
	for word in {role.lower(), "button", "icon"}:
		s = re.sub(rf"\s+{re.escape(word)}$", "", s, flags=re.I)
	if not s or s.lower() in {"unknown", "n/a", "none", "unclear", "?"} or needs_label(s, role):
		return None
	if len(s) > 48:
		s = s[:48].rsplit(" ", 1)[0]
	return s[0].upper() + s[1:]
