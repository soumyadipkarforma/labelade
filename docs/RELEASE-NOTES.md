Labelade gives names to unlabelled buttons, links and icons in the NVDA screen reader, using a vision model that runs on your own PC in AMD Lemonade Server.

## Install

1. Install [Lemonade Server](https://lemonade-server.ai) and start it.
2. Download **`labelade-0.1.0.nvda-addon`** below and open it while NVDA is running. Confirm, then restart NVDA.
3. If Lemonade has no vision model, Labelade downloads Qwen3-VL-4B-Instruct-GGUF (about 3.3 GB) by itself and tells you when it's ready.

## Files

| File | What it is |
|---|---|
| `labelade-0.1.0.nvda-addon` | The installer. Open it with NVDA running. |
| `labelade-0.1.0.zip` | The same add-on as a zip, for installing by hand: extract it into `%APPDATA%\nvda\addons\labelade` and restart NVDA. |
| `SHA256SUMS.txt` | Checksums for both files. |

Labelade runs on Windows only, because NVDA is a Windows screen reader. Lemonade can run on another computer (for example Linux) if you point Labelade's settings at it, but then your screenshots leave your PC.

## Tested

End to end in NVDA 2026.3.1 with Qwen3-VL-4B on Lemonade 2026.46.2, on an AMD Ryzen AI 7 350 with Radeon 860M integrated graphics: six of six test buttons labelled correctly, saved labels spoken instantly, about 1.4 seconds per label with the model loaded. Details: [Labelade on AMD Ryzen AI](https://github.com/soumyadipkarforma/labelade/blob/main/docs/AMD.md).

See the [changelog](https://github.com/soumyadipkarforma/labelade/blob/main/CHANGELOG.md) and the [user guide](https://github.com/soumyadipkarforma/labelade/blob/main/docs/USER-GUIDE.md).
