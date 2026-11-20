# Label packs

A label pack holds the labels for one app's controls. You can make one by labelling an app and exporting it, and you can share it so other people don't have to label that app again.

## Format

```json
{
 "schemaVersion": 1,
 "app": "discord",
 "labels": [
  {"role": "button", "label": "Mute microphone", "source": "user", "confidence": "high",
   "automationId": "uia:mute-button", "hash": "", "model": "", "updated": 0},
  {"role": "button", "label": "Add attachment", "source": "ai", "confidence": "high",
   "automationId": "", "hash": "3c7e7e3c181c3c00", "model": "Qwen3-VL-4B-Instruct-GGUF", "updated": 0}
 ]
}
```

| Field | Meaning |
|---|---|
| `app` | NVDA's app module name, usually the program file name without `.exe`. The file must be named `<app>.json`. |
| `role` | The control's role in NVDA, such as `button`, `link`, `graphic`, `togglebutton`, `menuitem`, `tab`, `listitem`. |
| `label` | What NVDA will say. 1 to 80 characters. |
| `automationId` | `uia:<id>` from UI Automation, or `ia2:<id>` from a web page element's id. Matches exactly, on any computer. |
| `hash` | A 64-bit difference hash of the control's pixels. A stored hash within 6 bits counts as a match. |
| `source` | `user` (typed by a person), `ai`, or `pack` (imported). |
| `confidence` | `high` or `low`. Low labels are spoken with "unsure". |

Each entry needs an `automationId` or a `hash`. The full rules are in [`schema/label-pack.schema.json`](../schema/label-pack.schema.json), and the add-on itself enforces them in `validate_pack()`.

## What a pack contains

Only roles, labels, ids and fingerprints: no screenshots, no window titles, no text from your screen. Open the file before you share it. The labels are words you or the AI chose for buttons. Check that none of them is personal, such as a contact's name used as a label.

## Matching

- **Automation ids** work on every computer and in every theme. Apps built with WinUI, WPF, UWP or Qt often have them.
- **Hashes** work without ids, but they depend on how the control looks. A pack made in dark mode may not match in light mode, and a very different display scale can change the picture. If a pack only half works for you, please say so in an issue, and mention your theme and scale.
- Your own labels always win. Importing a pack never replaces a label you typed.

## Sharing a pack

1. Label the app: Tab through it, or use NVDA+alt+W on each screen. Fix wrong labels with NVDA+alt+E.
2. NVDA menu, Tools, Labelade, Export labels for an app.
3. Fork this repository, add the file as `packs/<app>.json`, and open a pull request titled `pack: <app>`. In the description, say the app version, your Windows theme (light or dark) and display scale.
4. The **Validate label packs** check runs the add-on's own rules on your file. It also checks the file name and duplicate entries.

To update a pack someone else made, import it, label what's missing, export it and send the new file.

## Using a community pack

Download the `.json` file from [`packs/`](../packs/), then go to NVDA menu, Tools, Labelade, Import a label pack.
