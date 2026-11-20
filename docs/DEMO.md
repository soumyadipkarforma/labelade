# Demo video: 3 minutes

Record on the Ryzen AI laptop with Lemonade and Qwen3-VL-4B-Instruct-GGUF loaded. Turn on NVDA's speech viewer (NVDA menu, Tools, Speech viewer) so viewers can read what NVDA says, and record system audio. Use a real app or a simple test page with icon-only buttons. Warm the model up once before recording, so the first label isn't slow on camera.

| Time | On screen | Voice-over (approximate) |
|---|---|---|
| 0:00–0:20 | Speech viewer showing "button, button, button" while tabbing through an app's toolbar. | "This is what a blind person hears in many apps. Three buttons, no names. Which one sends the message? Which one deletes it?" |
| 0:20–0:50 | Same toolbar with Labelade. Each Tab: "button", beep, "Send message". Show Lemonade's window with the model running on the Radeon GPU. | "Labelade asks a vision model running on this laptop's own Radeon graphics, through AMD Lemonade. No cloud, no API key." |
| 0:50–1:10 | Tab back through: the labels are instant, with no beep. | "It remembers. Each button is labelled once, then it's as fast as if the developer had done it right." |
| 1:10–1:35 | NVDA+alt+W on a new window: "Labelling 9 controls", then "Labelade finished: 8 labelled, 1 not sure". Tab to the unsure one: "Attach file, unsure". NVDA+alt+E to fix it. | "Label a whole window at once. When the model isn't sure, it says so, and you can correct it. Your labels always win." |
| 1:35–2:05 | NVDA+alt+D on a chart or photo, the description in a browseable window. NVDA+alt+A: "What's the highest value?" | "Describe anything on screen and ask follow-up questions, all local." |
| 2:05–2:35 | Export a label pack, show the JSON (just labels and ids), then the `packs/` folder and a pull request with the green validation check. | "Label packs: one person labels an app, everyone benefits. Every pack is checked automatically." |
| 2:35–3:00 | README hero and the GitHub repo. | "Labelade is open source and free, like NVDA. Private AI that makes inaccessible apps usable, on the AMD laptop you already have." |

## Before recording

- [ ] Real labels only. Don't show anything produced by the mock server.
- [ ] Speech viewer font large enough to read; NVDA speech rate slowed a little.
- [ ] Notifications off; close apps with personal information.
