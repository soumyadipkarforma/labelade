# Labelade user guide

Labelade gives names to unlabelled buttons, links and icons, so NVDA says "Send message, button" instead of just "button". It asks a vision model that runs on your own computer in AMD Lemonade Server, then remembers the answer. Nothing is sent to the internet.

## What you need

- NVDA 2025.1 or later.
- Lemonade Server running on the same computer, from [lemonade-server.ai](https://lemonade-server.ai).
- A vision model in Lemonade. You don't have to get one yourself: if Lemonade has none, Labelade downloads Qwen3-VL-4B-Instruct-GGUF (about 3.3 GB), which reads small icons and text well. See "Choosing a model" below.

## Getting started

1. Install Lemonade Server and start it.
2. Install Labelade: open the `labelade-0.1.0.nvda-addon` file and confirm, then restart NVDA.
3. If Lemonade has no vision model yet, Labelade says "Labelade is downloading its vision model" and fetches Qwen3-VL-4B-Instruct-GGUF through Lemonade in the background. When it says "Labelade's vision model is ready", you can start. Controls you Tab to during the download are labelled as soon as it finishes. If Lemonade wasn't running when NVDA started, the download starts the first time Labelade tries to label something.
4. To check the setup, open NVDA's menu, then Preferences, Settings, Labelade, and press Test connection. NVDA should say which model Labelade will use.
5. Tab through an app that has unlabelled buttons. When you land on one, NVDA says "button" as usual. A moment later you hear a short beep and the new label.

The first label after starting Lemonade takes longer, because Lemonade loads the model. After that labels come back much faster. How fast depends on the model and your PC.

## Commands

| Command | What it does |
|---|---|
| NVDA+alt+L | Label the current control now. Replaces an AI label it already has. |
| NVDA+alt+W | Label every unlabelled control in the current window, in the background. Press again to stop. |
| NVDA+alt+E | Type your own label for the current control. Clear the text to remove the label. |
| NVDA+alt+D | Describe the current object, such as a picture, chart or an area of the screen. |
| NVDA+alt+S | Describe the whole current window. |
| NVDA+alt+A | Ask a follow-up question about the last description. |
| NVDA+alt+T | Turn automatic labelling on focus on or off. |

"Current control" means NVDA's navigator object, which is normally the focus. So you can also use object navigation to reach icons that never take focus, then press NVDA+alt+L.

You can change any of these keys in NVDA's menu: Preferences, Input gestures, Labelade.

## How labels are spoken

- A label the model was sure about is spoken as is, for example "Mute microphone, toggle button".
- A label it wasn't sure about ends with "unsure", for example "Attach file, unsure, button". Check it, and if it's wrong, fix it with NVDA+alt+E.
- If the model can't tell, Labelade says so and leaves the control unnamed.
- Labels you type yourself are never replaced by the AI or by a label pack.

## Label packs

Labels are saved per app, so each control is only labelled once. You can share them:

- **Export:** NVDA menu, Tools, Labelade, Export labels for an app. Choose the app and save the file.
- **Import:** NVDA menu, Tools, Labelade, Import a label pack. Your own labels are kept.

Community packs are collected in the `packs` folder of the Labelade repository. If you've labelled an app well, please share your pack there.

## Settings

NVDA menu, Preferences, Settings, Labelade:

- **Lemonade Server address.** Default `http://localhost:13305/api/v1`. Only change it if you moved Lemonade to another port. If you point it at another computer, your screenshots go to that computer.
- **API key.** Only needed if you started Lemonade with `LEMONADE_API_KEY`.
- **Vision model.** Leave empty and Labelade picks one: a vision model already loaded in Lemonade if there is one, otherwise the best one you've downloaded.
- **Label unlabelled controls automatically when they get focus.** On by default. Turn it off to label only when you press NVDA+alt+L or NVDA+alt+W.
- **Beep before a new AI label is spoken.** A short high tone tells you the name came from the AI.
- **Download a vision model automatically if Lemonade has none.** On by default. Turn it off on a metered connection, or if you want to choose and download a model yourself in the Lemonade app.
- **Test connection.** Checks that Lemonade is reachable and says which model will be used.

## Choosing a model

| Model | Download | Notes |
|---|---|---|
| Qwen3-VL-4B-Instruct-GGUF | 3.3 GB | Recommended. Good at icons and screen text. |
| Qwen3.5-4B-GGUF | 3.6 GB | Also the language model in Lemonade's LMX-Omni-5.5B-Lite bundle. |
| Gemma-4-E4B-it-GGUF | 6.0 GB | Strong descriptions; slower. |
| Qwen3.5-2B-GGUF | 2.0 GB | For PCs with 8 GB of memory. Less accurate. |

Any Lemonade model labelled "vision" works.

## Privacy

- Labelade captures only the control it's labelling, plus a small area around it, or the area you ask it to describe.
- It sends the picture only to the Lemonade address in settings. By default that's your own computer.
- It never runs on secure screens such as the Windows sign-in screen or UAC prompts.
- Labels are stored as JSON files in your NVDA configuration folder, under `labelade\labels`. A label pack contains only role names, labels, control ids and short image fingerprints, not screenshots.

## Limits

- On web pages in browse mode, NVDA reads from its own copy of the page. When you Tab to a control you hear NVDA's "button" and then the label. Reading with the arrow keys or say all still says only "button".
- A label found by its picture depends on your theme: a pack made in dark mode may not match in light mode. Controls with an automation id match everywhere.
- Small models sometimes get labels wrong. That's why unsure labels say so, and why you can always fix them.

## Troubleshooting

- **"Can't reach Lemonade":** start Lemonade Server, then press Test connection in settings. After this error Labelade stays quiet for a minute while you Tab around, rather than repeating it.
- **"No vision model is downloaded":** download one in the Lemonade app's model manager.
- **It's slow:** the first request loads the model. If every label is slow, try a smaller model, or close other apps that use the GPU.
- **A wrong label:** press NVDA+alt+E and type the right one.
