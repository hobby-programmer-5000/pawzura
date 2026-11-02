# Pawzura

**English** | [한국어](README.ko.md)

A small SD desktop companion that walks above the Windows taskbar and helps you stay focused with optional app and website allowlists.

Windows 10 (1809+) / Windows 11 · x64 · Python 3.12–3.15 for source use · MIT

## Start here

1. Download the latest **Windows ZIP** from [Releases](https://github.com/hobby-programmer-5000/pawzura/releases).
2. **Extract the entire ZIP**, open the `Pawzura` folder and double-click **Pawzura.exe**. Keep `_internal` beside it. No Python or model is needed.
3. Try **General → Preview bite animation**. The guardian is **off** and preview is **on** until you choose otherwise.

The app starts in English. Switch with **General → Language → 한국어 → Save settings**. Source users can double-click **run.bat** instead of building.

**Before you start:** unsigned builds may trigger **Windows SmartScreen**. Verify the official download and checksum before choosing **More info → Run anyway**, if offered. [Launch help](doc/en/GETTING_STARTED.md).

**AI design needs Ollama running and enough free RAM/VRAM.** For Qwen traits: Character → **Copy command** → PowerShell → wait for `success` → Generate. For new GPU artwork: **Create original artwork…** → review the model license → **Prepare runtime and selected models**. [Artwork setup](doc/en/CREATIVE-ART.md) · [Qwen commands](doc/en/ADVANCED-MODELS.md). Default/random characters need no model.

## Browser control is optional

**Website control requires the Pawzura browser extension.** For applications only, leave **Browsers → Website control OFF**; no extension is needed.

For websites, choose your browser and click **Install/connect extension…**. On the extensions page it opens, enable **Developer mode** (Chrome: upper-right switch on `chrome://extensions`), then **Load unpacked** using the copied folder. **Ctrl+Shift+I opens Developer Tools, not this switch.** Finish loading before opening the connection page. [Steps and button locations](doc/en/BROWSERS.md).

## What it does

- Walks across monitors, animates configured artwork hands/feet and reacts to hover/clicks. [Motion setup](doc/en/ARTWORK-MOTION.md).
- Jumps, bites and shows a fading crack before requesting an unlisted window to close.
- Protects browser windows; its extension closes blocked tabs and connects with desktop approval, without code entry.
- Offers light/dark settings, a lightweight Qwen trait designer and optional GPU [original artwork generation](doc/en/CREATIVE-ART.md). Advanced image models require separate downloads and license review.

## Guides

| I want to… | Read this |
| --- | --- |
| Run the app, change language, use the tray | [Getting started](doc/en/GETTING_STARTED.md) |
| Connect Chrome/Edge/Firefox, with examples | [Browser setup](doc/en/BROWSERS.md) |
| Separate work/leisure lists or recover the companion | [Profiles and recovery](doc/en/PROFILES-AND-RECOVERY.md) |
| Create GPU artwork and review model licenses | [Creative artwork](doc/en/CREATIVE-ART.md) |
| Run source or build an EXE | [Setup and builds](doc/en/BUILD.md) |
| Check test results and current limits | [Validation](doc/en/VALIDATION.md) |
| See ownership and AI contribution roles | [Contributors](doc/en/CONTRIBUTORS.md) |
| Review library/model licenses | [Third-party notices](doc/en/THIRD-PARTY-NOTICES.md) |

**Browser behavior:** monitoring closes tabs after navigation; tab animations use a separate marker near the taskbar.

**Validation:** the maintainer reports a manual usage check on Windows 11. See [test results and remaining coverage](doc/en/VALIDATION.md) for the scope of that report and automated checks.

| Product direction and maintenance | AI implementation assistance |
| --- | --- |
| [hobby-programmer-5000](https://github.com/hobby-programmer-5000) | [ChatGPT (Codex)](https://github.com/apps/chatgpt-codex-connector) |

App code: [MIT](LICENSE). [Roles and GitHub display limits](doc/en/CONTRIBUTORS.md) · [All documentation](doc/README.md).
