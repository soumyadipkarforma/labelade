# Developing

You need Python 3.11 or later. There are no dependencies to install; the linter is optional.

```bash
python -m unittest discover -v     # all tests
python tools/build.py              # dist/labelade-<version>.nvda-addon
python scripts/validate_packs.py   # check packs/
pip install ruff==0.17.6 && ruff check .
```

Use 3.11 to match NVDA 2025.x and 3.13 to match NVDA 2026.x. CI runs both on Windows and Linux.

## Tests

- `tests/test_core.py` covers the core: label rules, PNG encoding, red box, hashes, store, packs, the client against the mock server, the labeller and the worker thread.
- `tests/test_plugin.py` imports the real NVDA plugin with stand-ins for NVDA's modules (`tests/nvda_stubs.py`) and drives its events and commands: focus labelling, recall by id and by hash, editing, window scan, describe and follow-up, and the server-down message. The stubs copy the NVDA APIs Labelade uses, as checked against NVDA 2026.3 source. They catch wiring mistakes, but they don't replace testing in real NVDA ([MANUAL-TESTING.md](MANUAL-TESTING.md)).
- `tests/test_tools.py` covers the builder, the Markdown converter and the pack validator.

## Mock Lemonade

```bash
python tools/mock_lemonade.py          # port 13305, like the real server
```

It serves `/api/v1/models`, `/api/v1/health` and `/api/v1/chat/completions`, rejects images that aren't PNG, and answers every label request with "Send message". So you can install the add-on in NVDA and try every command without downloading a model.

## Trying changes in NVDA

1. Build and install `dist/labelade-*.nvda-addon`, or copy `addon/globalPlugins/labelade` to `%APPDATA%\nvda\scratchpad\globalPlugins\` and turn on NVDA's developer scratchpad (Settings, Advanced).
2. Reload plugins with NVDA+control+F3.
3. Read errors in the NVDA log (NVDA+F1). Labelade logs failed requests with their traceback.

## Releasing

1. Update `ADDON["version"]` in `tools/build.py` and `CHANGELOG.md`.
2. Tag and push, for example `git tag v0.1.1 && git push --tags`. The **Release** workflow tests, builds, checks the tag matches the version and publishes the add-on with its SHA-256.
3. To list it in NVDA's Add-on Store, submit the release URL and SHA-256 to [nvaccess/addon-datastore](https://github.com/nvaccess/addon-datastore) following its submission guide.

## Code style

Tabs, like NVDA. Keep `core/` free of NVDA imports so it stays testable. Every user-facing string in the plugin goes through `_()` so it can be translated.
