# Changelog

## 0.1.0 (2026-11-20)

First version.

- Labels unlabelled buttons, links, graphics, tabs, menu items and similar controls with a local vision model in AMD Lemonade Server, on focus or for a whole window (NVDA+alt+W).
- Labels are remembered per app, matched by automation id or image fingerprint.
- Unsure labels are spoken as "unsure"; labels you type (NVDA+alt+E) are never replaced.
- Label packs: export, import, community folder with CI validation.
- Describe an object or window and ask follow-up questions (NVDA+alt+D, NVDA+alt+S, NVDA+alt+A).
- Settings panel with connection test; automatic model selection.
- First-run setup: if Lemonade has no vision model, Labelade downloads Qwen3-VL-4B-Instruct-GGUF through Lemonade and says when it's ready (can be turned off).
- Never runs on secure screens.
