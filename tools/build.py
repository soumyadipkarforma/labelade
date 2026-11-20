"""Build dist/labelade-<version>.nvda-addon (a zip NVDA installs) from addon/ and docs/USER-GUIDE.md.

Run:  python tools/build.py
"""

import hashlib
import html
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ADDON = {
	"name": "labelade",
	"summary": "Labelade: AI labels for unlabelled controls",
	"description": (
		"Names unlabelled buttons, links and icons with a vision model that runs on your own PC in AMD "
		"Lemonade Server, remembers the labels, and lets you share them as label packs. Also describes "
		"the screen and answers questions about it. Nothing leaves your computer."
	),
	"author": "soumyadipkarforma",
	"url": "https://github.com/soumyadipkarforma/labelade",
	"version": "0.1.0",
	"docFileName": "readme.html",
	"minimumNVDAVersion": "2025.1.0",
	"lastTestedNVDAVersion": "2026.3.0",
}


def manifest() -> str:
	lines = []
	for key, value in ADDON.items():
		quoted = f'"""{value}"""' if key == "description" else (f'"{value}"' if " " in value else value)
		lines.append(f"{key} = {quoted}")
	return "\n".join(lines) + "\n"


def _inline(text: str) -> str:
	text = html.escape(text)
	text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
	text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
	return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)


def markdown_to_html(md: str, title: str) -> str:
	"""Enough Markdown for the user guide: headings, paragraphs, lists, tables and code blocks."""
	out, para, in_list, in_code, table = [], [], False, False, []

	def flush():
		nonlocal in_list, para, table
		if para:
			out.append(f"<p>{_inline(' '.join(para))}</p>")
			para = []
		if in_list:
			out.append("</ul>")
			in_list = False
		if table:
			rows = [r for r in table if not re.match(r"^\|[\s:|-]+\|$", r)]
			cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
			head = "".join(f"<th>{_inline(c)}</th>" for c in cells[0])
			body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
			out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
			table = []

	for line in md.splitlines():
		if line.startswith("```"):
			flush()
			out.append("</pre>" if in_code else "<pre>")
			in_code = not in_code
		elif in_code:
			out.append(html.escape(line))
		elif m := re.match(r"^(#{1,4})\s+(.*)", line):
			flush()
			level = len(m.group(1))
			out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
		elif m := re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", line):
			if para:
				out.append(f"<p>{_inline(' '.join(para))}</p>")
				para = []
			if not in_list:
				out.append("<ul>")
				in_list = True
			out.append(f"<li>{_inline(m.group(1))}</li>")
		elif line.startswith("|"):
			if para or in_list:
				flush()
			table.append(line)
		elif not line.strip():
			flush()
		else:
			para.append(line.strip())
	flush()
	body = "\n".join(out)
	return (
		f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>'
		f"<body>\n{body}\n</body></html>\n"
	)


def build() -> str:
	with open(os.path.join(ROOT, "docs", "USER-GUIDE.md"), encoding="utf-8") as f:
		guide = markdown_to_html(f.read(), "Labelade user guide")
	os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
	path = os.path.join(ROOT, "dist", f"labelade-{ADDON['version']}.nvda-addon")
	with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
		z.writestr("manifest.ini", manifest())
		z.writestr("doc/en/readme.html", guide)
		src = os.path.join(ROOT, "addon")
		for folder, dirs, files in os.walk(src):
			dirs[:] = [d for d in dirs if d != "__pycache__"]
			for name in files:
				if name.endswith((".py", ".ini", ".mo", ".html")):
					full = os.path.join(folder, name)
					z.write(full, os.path.relpath(full, src).replace(os.sep, "/"))
	return path


if __name__ == "__main__":
	built = build()
	with open(built, "rb") as f:
		digest = hashlib.sha256(f.read()).hexdigest()
	print(f"{os.path.relpath(built, ROOT)}  sha256 {digest}")
