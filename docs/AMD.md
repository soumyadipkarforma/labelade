# Labelade on AMD Ryzen AI

**Thank you, AMD.** Labelade exists because Lemonade makes a local vision model something anyone can install with one click and use from a few lines of plain Python. For blind and low-vision people that matters more than for most users: their screens carry email, banking and medical records, and a screen reader add-on that sends every screenshot to a cloud service is a hard thing to trust. Lemonade on a Ryzen AI laptop removes that problem. Nothing leaves the PC.

This page sets out what Labelade does, how it performed on AMD hardware, why that matters, and what we would do next with more of it.

## What Labelade is

An add-on for NVDA, the free screen reader used by blind people around the world. When NVDA can only say "button" because a developer forgot a label, Labelade:

1. takes a screenshot of the control and its surroundings and marks the control with a red box,
2. asks a vision model running in Lemonade Server what the control does,
3. speaks the answer ("Send message") and saves it, matched by automation id or by an image fingerprint,
4. speaks the saved label straight away on every later visit, with no model call at all.

It can also label a whole window in the background, describe an object or window and answer follow-up questions. Users can type their own labels, which always take priority over the AI. Labels for whole apps can be shared as label packs. See the [README](../README.md) and [user guide](USER-GUIDE.md).

## Test results on an AMD integrated GPU

Measured on 2026-11-20. Nothing is estimated.

| | |
|---|---|
| Tested on | AMD Ryzen AI 7 350 with Radeon 860M integrated graphics and XDNA 2 NPU, 16 GB RAM |
| Software | Windows 11, Lemonade Server 2026.46.2, NVDA 2026.3.1 |
| Model | Qwen3-VL-4B-Instruct-GGUF (Q4_K_M), on the Radeon 860M through llama.cpp Vulkan, chosen automatically by Lemonade |
| GPU memory in use | 5.9 GB of shared memory, with the model loaded |

**In real NVDA, on a test page of six unlabelled icon buttons in Edge:**

| Button | Labelade said | Expected |
|---|---|---|
| 1 | Send message | Send |
| 2 | Add attachment | Attach file |
| 3 | Microphone | Microphone |
| 4 | Smile | Emoji |
| 5 | Delete | Delete |
| 6 | Settings | Settings |

- Six of six correct, all marked as sure.
- First visit: NVDA says "button", then a beep and the label about 1.5 to 5 seconds later.
- Every later visit: the label is spoken immediately. All six were found again from their fingerprints, with no model call and no GPU work.
- "Label now" (NVDA+alt+L): 1.6 seconds.
- "Describe" (NVDA+alt+D): a correct, detailed description in about 12 seconds.

**Repeated label requests on a real taskbar screenshot** (10 runs with the model already loaded and the image already cached): median 1.42 seconds, fastest 1.40, slowest 2.81, with the same answer ("Wi-Fi", sure) every time. The model generated about 13 tokens per second, and Lemonade's prompt cache made repeat requests fast. Labels are only a few tokens, so these timings feel fine in practice.

The full method and results are in [MANUAL-TESTING.md](MANUAL-TESTING.md#results-2026-11-20).

## Why this matters

- **It runs on the laptops people actually buy.** No discrete GPU and no subscription: the integrated Radeon in a mainstream Ryzen AI laptop is enough. Many blind people pick NVDA because it is free, so the hardware bar matters.
- **Every label is paid for once.** The model runs only the first time a control is seen. After that, recognising it costs a fingerprint lookup, so battery and GPU use go to near zero during everyday use.
- **Labelling an app once helps everyone.** A label pack made on one AMD laptop makes that app usable for every NVDA user, including people with no model at all.
- **It's free where the alternative is paid.** The equivalent JAWS feature is commercial. Labelade is GPL, like NVDA.
- **Lemonade gains a new kind of user.** Accessibility is a daily, practical reason to keep a local AI server running, and a community (screen reader users, accessibility testers, NVDA add-on authors) that local AI hasn't reached yet.

## What a Strix Halo machine would unlock

The Ryzen AI Max series (Strix Halo) pairs a much larger Radeon GPU with up to 128 GB of unified memory. On the 16 GB test machine, one 4B model already takes 5.9 GB. These are the things we would build and measure next. **None of them is measured yet.**

1. **Bigger, more accurate vision models.** The hard cases are icons with no conventional meaning and dense toolbars. Larger vision models that don't fit in 16 GB should cut "unsure" labels, and we would publish the accuracy difference on a fixed test set.
2. **Many models at once.** One vision model for labels, Whisper for spoken questions ("what's this?"), and a small text model for follow-ups, all loaded together, so no request waits for a model swap.
3. **Labelling whole apps in minutes.** A window scan of fifty controls is fifty model calls. More GPU means label packs for popular apps, such as Discord, Spotify and Microsoft Teams, can be built and checked quickly, then shared with everyone.
4. **Testing across Ryzen AI tiers.** One codebase, measured from a mainstream laptop to the top of the range, so users know what each tier gives them. That includes moving small labelling models to the XDNA NPU.
5. **A public benchmark.** Label accuracy and speed by model and AMD device, published in this repository so other developers can build on it.

## Our commitment

Whatever hardware we have, Labelade stays free, open source and local-first. Everything we measure on AMD hardware will be published here with the method, including the parts that don't go well.
