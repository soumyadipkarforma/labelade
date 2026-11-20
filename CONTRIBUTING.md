# Contributing

Thank you for helping. The most useful contributions, in order:

1. **Try it and report.** Which apps did it label well or badly? Open a "Wrong or missing label" issue with the app name and version.
2. **Share a label pack.** See [docs/LABEL-PACKS.md](docs/LABEL-PACKS.md).
3. **Translate.** All interface strings go through gettext. NVDA's translation tooling can produce `addon/locale/<lang>/LC_MESSAGES/nvda.po`.
4. **Code.** Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DEVELOPING.md](docs/DEVELOPING.md) first.

## Pull requests

- Keep NVDA imports out of `addon/globalPlugins/labelade/core/`.
- Add or update tests: `python -m unittest discover` must pass, and so must `ruff check .`.
- If you change something users hear or press, update [docs/USER-GUIDE.md](docs/USER-GUIDE.md), which ships inside the add-on.
- Changes that affect what is captured or where it's sent need a note in the pull request explaining the privacy impact.

## Conduct

Be kind and patient. Many people here use a screen reader. Describe screenshots in text, and don't post images without a description.
