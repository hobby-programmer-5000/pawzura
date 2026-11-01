# Pawzura

**English** | [한국어](README.ko.md)

A small SD desktop companion that walks above the Windows taskbar and helps you stay focused with optional app and website allowlists.

Windows 10 (1809+) / Windows 11 · x64 · Python 3.12–3.15 for source use · MIT

## Start here

1. Download the latest **Windows ZIP** from [Releases](https://github.com/hobby-programmer-5000/pawzura/releases).
2. **Extract the entire ZIP**, open the `Pawzura` folder and double-click **Pawzura.exe**. Keep `_internal` beside it. No Python or model is needed.
3. Try **General → Preview bite animation**. The guardian is **off** and preview is **on** until you choose otherwise.

The app starts in English. Switch with **General → Language → 한국어 → Save settings**. Source users can double-click **run.bat** instead of building.

## What it does

- Walks across connected monitors with an original, changeable character.
- Jumps, bites and shows a fading crack before requesting an unlisted window to close.
- Protects browser windows; its extension closes blocked tabs and connects with desktop approval, without code entry.
- Offers optional local Hugging Face Qwen character design through Ollama.

## Guides

| I want to… | Read this |
| --- | --- |
| Run the app, change language, use the tray | [Getting started](doc/en/GETTING_STARTED.md) |
| Connect Chrome/Edge/Firefox, with examples | [Browser setup](doc/en/BROWSERS.md) |
| Separate work/leisure lists or recover the companion | [Profiles and recovery](doc/en/PROFILES-AND-RECOVERY.md) |
| Generate characters with Qwen | [Models and characters](doc/en/MODELS.md) |
| Run source or build an EXE | [Setup and builds](doc/en/BUILD.md) |
| Check test results and current limits | [Validation](doc/en/VALIDATION.md) |
| See ownership and AI contribution roles | [Contributors](doc/en/CONTRIBUTORS.md) |
| Review library/model licenses | [Third-party notices](doc/en/THIRD-PARTY-NOTICES.md) |
| Understand character rights and provenance | [Character rights](doc/en/CHARACTER-RIGHTS.md) |

**Preview limitations:** browser monitoring closes tabs after navigation; tab animations use a separate marker near the taskbar. Windows 11 device testing and user-profile browser E2E remain pending. See the validation guide.

App code: [MIT](LICENSE). Product direction: [hobby-programmer-5000](https://github.com/hobby-programmer-5000). Implementation assistance: ChatGPT via Codex. [All documentation](doc/README.md).
