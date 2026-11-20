# Labelade

**Your screen reader says "button". Labelade tells you which one.**

Labelade is an add-on for the [NVDA](https://www.nvaccess.org) screen reader. It names unlabelled buttons, links and icons using a vision model that runs on your own PC in [AMD Lemonade Server](https://lemonade-server.ai). It remembers every label, so each control is only labelled once, and it lets people share labels for whole apps as label packs. It can also describe the screen and answer questions about it.

No cloud, no API key, no GPU from another vendor: it runs on the Radeon graphics of an ordinary Ryzen AI laptop.

[![CI](https://github.com/soumyadipkarforma/labelade/actions/workflows/ci.yml/badge.svg)](https://github.com/soumyadipkarforma/labelade/actions/workflows/ci.yml) · GPL-2.0 · NVDA 2025.1+ · Lemonade Server

> Built for the [AMD Lemonade Developer Challenge](https://www.amd.com/en/developer/resources/technical-articles/2026/join-the-lemonade-developer-challenge.html).

## The problem

Unlabelled controls are one of the most common reasons an app is unusable for a blind person. A developer forgets a label, and the screen reader can only say "button, button, button". WebAIM's yearly audit of a million home pages lists empty links and empty buttons among the most common failures year after year. Desktop apps are no better.

The paid screen reader JAWS has started selling an AI labeller for this. NVDA users, many of whom picked NVDA because it's free, had no local equivalent. The existing NVDA AI add-ons describe images on request, mostly through cloud services.

## What Labelade does

| | |
|---|---|
| **Labels on focus** | Tab to an unlabelled button. NVDA says "button" as usual, then a beep and "Send message". |
| **Labels a whole window** | NVDA+alt+W labels every unlabelled control in the window in the background. |
| **Remembers** | Labels are saved per app and matched by automation id or by an image fingerprint, so the next visit is instant and needs no model. |
| **Honest about doubt** | Labels the model wasn't sure about are spoken with "unsure". If it can't tell, it says so instead of guessing. |
| **You stay in charge** | NVDA+alt+E types your own label. Yours are never overwritten by the AI or by a pack. |
| **Label packs** | Export an app's labels and share them. One person labels an app, everyone benefits. |
| **Describe and ask** | NVDA+alt+D or NVDA+alt+S describes an object or window. NVDA+alt+A asks a follow-up question. |
| **Private by design** | Screenshots go only to the Lemonade address in settings, by default this PC. Nothing runs on secure screens. |

## Quick start

1. Install [Lemonade Server](https://lemonade-server.ai) and start it.
2. In the Lemonade app's model manager, download **Qwen3-VL-4B-Instruct-GGUF** (about 3.3 GB).
3. Download `labelade-0.1.0.nvda-addon` from [Releases](https://github.com/soumyadipkarforma/labelade/releases), open it and restart NVDA.
4. NVDA menu, Preferences, Settings, Labelade, then **Test connection**.
5. Tab through any app with unlabelled buttons.

The full guide, also included in the add-on, is [docs/USER-GUIDE.md](docs/USER-GUIDE.md).

## Commands

| Keys | Command |
|---|---|
| NVDA+alt+L | Label the current control now |
| NVDA+alt+W | Label the whole window (again to stop) |
| NVDA+alt+E | Edit or remove a label |
| NVDA+alt+D | Describe the current object |
| NVDA+alt+S | Describe the window |
| NVDA+alt+A | Ask a follow-up question |
| NVDA+alt+T | Automatic labelling on or off |

All of them can be changed in NVDA's Input gestures dialog.

## How it works

```
 focus lands on a control        NVDA main thread                  background thread
 ─────────────────────────►  needs a label? (empty, "button",
                             "ic_send.png", a GUID...)
                                    │ yes
                             saved label? ─── yes ──► name it before NVDA speaks
                                    │ no
                             capture the control + its
                             surroundings, red box around it ──►  PNG ──► Lemonade Server
                                                                         /api/v1/chat/completions
                                                                         (vision model on the iGPU)
                             speak "Send message", save it  ◄──  {"label": "Send message",
                             by automation id + image hash        "confidence": "high"}
```

Details are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Why Lemonade

- **It runs where blind users are.** Lemonade runs vision models on the integrated Radeon graphics of AMD Ryzen AI laptops through Vulkan or ROCm. You don't need a gaming GPU, and many blind people don't have one.
- **One local server, OpenAI-compatible.** Labelade uses standard `/chat/completions` with images, plus Lemonade's `enable_thinking: false` extension so reasoning models answer in a second.
- **It picks the model for you.** Labelade asks Lemonade which models are downloaded and loaded, and chooses a vision model automatically. If you use Lemonade's Omni bundle, its Qwen3.5-4B language model can see images and works too.
- **No pip, no Python setup.** The add-on uses only the standard library, so installing it is one file.

## Label packs

Community packs live in [`packs/`](packs/). The format is plain JSON ([schema](schema/label-pack.schema.json)) with role, label, and an automation id or image fingerprint. It never contains screenshots. Every pull request is validated with the add-on's own rules. See [docs/LABEL-PACKS.md](docs/LABEL-PACKS.md).

## Status

Version 0.1.0. The core (label rules, image capture encoding, fingerprints, storage, packs, the Lemonade client) is covered by unit tests, and the NVDA integration is tested against stubs of the NVDA APIs it uses, all run in CI on Windows and Linux with Python 3.11 and 3.13. It has been run end to end in real NVDA 2026.3.1 with a real Lemonade model ([results](docs/MANUAL-TESTING.md#results-2026-11-20)), but it has not yet been through wide testing by blind users across many apps. [docs/MANUAL-TESTING.md](docs/MANUAL-TESTING.md) is the checklist we use, and reports are very welcome.

## Documentation

- [User guide](docs/USER-GUIDE.md): install, commands, settings, models, privacy, limits.
- [Label packs](docs/LABEL-PACKS.md): format, matching, how to share one.
- [Architecture](docs/ARCHITECTURE.md): how the pieces fit and why.
- [Developing](docs/DEVELOPING.md): tests, mock server, build, release.
- [Manual testing](docs/MANUAL-TESTING.md): checklist for testing in real NVDA.
- [Labelade on AMD Ryzen AI](docs/AMD.md): test results on a Radeon 860M laptop, impact, and what's next.
- [Challenge submission](docs/SUBMISSION.md) and [demo script](docs/DEMO.md).
- [Contributing](CONTRIBUTING.md) and [changelog](CHANGELOG.md).

## License

GPL-2.0-or-later, like NVDA itself. See [LICENSE](LICENSE).
