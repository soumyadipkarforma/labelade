# Lemonade Developer Challenge submission

**Project:** Labelade: private AI labels for unlabelled controls, for the NVDA screen reader, running on AMD Lemonade.
**Repository:** https://github.com/soumyadipkarforma/labelade
**License:** GPL-2.0-or-later

## The problem

When a developer forgets to label a button, a screen reader can only say "button". For a blind person, an app full of unnamed buttons is a guessing game: which one sends, which one deletes? This is one of the most common accessibility failures on the web and in desktop apps. The paid screen reader JAWS now sells an AI labeller for it. NVDA, the free screen reader used by many blind people worldwide, had no local equivalent. Existing NVDA AI add-ons describe images on request, mostly through cloud services.

## What we built

An NVDA add-on that:

- **Labels unlabelled controls automatically** when they get focus, or a whole window at once.
- **Remembers every label**, matched by automation id or image fingerprint, so each control is labelled only once.
- **Is honest:** unsure labels are spoken as "unsure", and the add-on says when it can't tell instead of guessing.
- **Keeps the user in charge:** typed labels always win over the AI and over imported packs.
- **Shares the work:** label packs for whole apps, validated in CI with the add-on's own rules, collected in the repo.
- **Describes the screen** and answers follow-up questions.

## How it uses Lemonade

- Vision models in Lemonade's catalogue, such as Qwen3-VL-4B, Qwen3.5-4B (the LLM of Lemonade's Omni Lite bundle) and Gemma, run on the integrated Radeon GPU of a Ryzen AI laptop. That's hardware blind users can actually afford.
- Standard `/chat/completions` with images, plus Lemonade's `enable_thinking: false` so reasoning models answer quickly.
- `/models` labels and `/health` loaded models drive automatic model selection, so users don't need to know model names.
- One local server with an OpenAI-compatible API means no cloud keys and no Python environment. The add-on is one file with no dependencies.

## Impact on the local AI ecosystem

- **A new kind of Lemonade user.** Blind and low-vision people get a concrete, daily reason to run local AI, and a privacy story that matters: screens contain email, banking and medical records.
- **Free where the alternative is paid.** The equivalent JAWS feature is commercial. Labelade is GPL like NVDA.
- **Compounding community value.** Every shared label pack makes an app accessible for everyone, without anyone running a model.
- **A reusable pattern.** The pure-Python Lemonade client and image pipeline in `core/` work in any Python app that can't install packages.

## Engineering

- Tested end to end in real NVDA 2026.3.1 with Qwen3-VL-4B on Lemonade 2026.46.2, on an AMD Ryzen AI 7 350 with Radeon 860M integrated graphics: six of six test buttons labelled correctly, saved labels spoken instantly, about 1.4 seconds per label with the model loaded. See [Labelade on AMD Ryzen AI](AMD.md) and [the full results](MANUAL-TESTING.md#results-2026-11-20).

- 40 automated tests, including the NVDA plugin driven against stubs of NVDA's APIs, run on Windows and Linux with Python 3.11 and 3.13.
- Atomic saves, corrupt-file recovery and per-entry validation, so a bad file never costs users their labels.
- One background thread with de-duplication and cancellation, so NVDA never freezes waiting for a model.
- Never runs on secure screens, and warns when the server isn't on this computer.

## Roadmap

1. Testing with blind users across popular apps, and the first community packs.
2. Listing in NVDA's Add-on Store.
3. Voice questions using Lemonade's Whisper (`/audio/transcriptions`), so you can ask "what's this?" aloud.
4. Labels when reading web pages with the arrow keys and say all, not just when tabbing.
5. Running small labelling models on the Ryzen AI NPU, leaving the GPU free.
6. A shared online pack index, so packs install automatically for the app you open.
