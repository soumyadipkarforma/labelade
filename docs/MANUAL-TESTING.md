# Manual testing in NVDA

Automated tests run without NVDA. Before each release, run through this list in real NVDA with real Lemonade. Note the NVDA version, Windows version, model and laptop in the results.

## Setup

- [ ] Lemonade Server running, a vision model downloaded (Qwen3-VL-4B-Instruct-GGUF).
- [ ] Add-on installed from the built `.nvda-addon`; NVDA restarted.
- [ ] Settings, Labelade, Test connection names the model.
- [ ] Test connection with Lemonade stopped gives "Can't reach Lemonade".
- [ ] Input gestures lists a Labelade category with 7 commands.

## Labelling

Good test targets: [`tools/test-page.html`](../tools/test-page.html), which has icon-only buttons with no labels; an Electron app such as Discord or Slack; and an older Win32 app with toolbar icons.

- [ ] Tab to an unlabelled button: NVDA says "button", then a beep and a sensible label, within a few seconds.
- [ ] Tab away and back: the label is spoken at once, with no beep (it came from the store).
- [ ] Restart NVDA, return to the control: still labelled.
- [ ] NVDA+alt+L on a labelled control gives a fresh label.
- [ ] NVDA+alt+E, type a label, Enter: "Label saved", and it's used from then on. NVDA+alt+L then says "Your label: …".
- [ ] NVDA+alt+E, clear the text: "Label removed".
- [ ] NVDA+alt+W in a window with several unlabelled controls: a count, then a summary. Pressing it again mid-scan says "Stopped labelling".
- [ ] Controls that already have a good name are never re-labelled.
- [ ] Object navigation (NVDA+numpad) to an unfocusable icon, then NVDA+alt+L.
- [ ] Browse mode: NVDA+alt+L on a link speaks a label.
- [ ] NVDA+alt+T toggles auto-labelling and is remembered after a restart.

## Describe

- [ ] NVDA+alt+D on a picture opens a readable description in a browseable window.
- [ ] NVDA+alt+S describes the window.
- [ ] NVDA+alt+A asks a follow-up and gets an answer about the same image.

## Packs

- [ ] Export labels for an app, open the JSON: no screenshots, no window titles.
- [ ] Import that pack on another NVDA profile or PC: labels work. Own labels are kept.
- [ ] Import a broken file: a clear error, nothing changed.

## Robustness

- [ ] Stop Lemonade mid-use: one "Can't reach Lemonade" message, then a quiet minute, and NVDA stays responsive.
- [ ] Rapid Tab through 20 unlabelled controls: NVDA never freezes, labels arrive for the control you're on.
- [ ] Windows sign-in screen and a UAC prompt: Labelade does nothing (secure screens).
- [ ] Disable and re-enable the add-on: no errors in the log (NVDA+F1).

## Results 2026-11-20

Tested on an AMD Ryzen AI 7 350 with Radeon 860M integrated graphics (model on the iGPU through llama.cpp Vulkan). NVDA 2026.3.1 (portable copy), Windows 11 26H2, Lemonade 2026.46.2, Qwen3-VL-4B-Instruct-GGUF, Edge on `tools/test-page.html`. Speech was read from the NVDA log.

| Button | Label spoken | Expected |
|---|---|---|
| 1 | Send message | Send |
| 2 | Add attachment | Attach file |
| 3 | Microphone | Microphone |
| 4 | Smile | Emoji |
| 5 | Delete | Delete |
| 6 | Settings | Settings |

- First visit: NVDA says "button", then about 1.5 to 5 seconds later a short beep and the label. All six were marked sure.
- Return visits, Tab and Shift+Tab: all six found again by image fingerprint (Hamming distance 0), spoken at once with no model call.
- NVDA+alt+L on a labelled button: new label in 1.6 seconds with the model already loaded.
- NVDA+alt+D: an accurate description in NVDA's text window after about 12 seconds.
- A blank square sent to the model gets `unknown`, which Labelade treats as "couldn't tell" instead of saving a guess.
- Bug found and fixed in this run: in browse mode, saved labels were found but not spoken, because NVDA reads web pages from its own buffer and ignores the name the add-on sets. Labelade now speaks the saved label after NVDA's announcement. A test covers it.
- Not covered: reading with arrow keys in browse mode (still says only "button"), desktop apps other than Edge, packs and settings dialogs in real NVDA, and testing by blind users.

