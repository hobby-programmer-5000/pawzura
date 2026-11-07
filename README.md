# Pawzura

**English** | [한국어](README.ko.md)

A small SD desktop companion that walks across monitors above the Windows taskbar, reacts to hover/clicks and helps you stay focused with optional app and website allowlists. It jumps and bites before requesting an unlisted app window to close.

Windows 10 (1809+) / Windows 11 · x64 · Python 3.12–3.15 for source use · MIT

> [!WARNING]
> **Start with preview mode ON.** We do not recommend disabling it until your application allowlist and the site allowlists for every browser you control are complete and tested. Turning preview off can close unlisted windows/tabs and lose unsaved work. **Proceed at your own risk. The authors and maintainers disclaim liability for any resulting loss, damage or other consequences, to the extent permitted by law.**

## Start here

1. Download the **standalone Windows EXE** or **Windows ZIP** from [Releases](https://github.com/hobby-programmer-5000/pawzura/releases).
2. Double-click the standalone EXE, or extract the **entire ZIP** and run `Pawzura/Pawzura.exe`. [Formats and single-instance behavior](doc/en/SINGLE-EXE.md).
3. Try **General → Preview bite animation**. The guardian is **off** and preview is **on** until you choose otherwise.

The app starts in English. Switch with **General → Language → 한국어 → Save settings**. Source users can double-click **run.bat** instead of building.

**Before you start:** unsigned builds may trigger **Windows SmartScreen**. Verify the official download and checksum before choosing **More info → Run anyway**, if offered. [Launch help](doc/en/GETTING_STARTED.md).

**AI design needs Ollama running and enough free RAM/VRAM.** For Qwen traits: Character → **Copy command** → PowerShell → wait for `success` → Generate. For new GPU artwork: **Create original artwork…** → review the model license → **Prepare runtime and selected models**. [Artwork setup](doc/en/CREATIVE-ART.md) · [Qwen commands](doc/en/ADVANCED-MODELS.md). Default/random characters need no model.

## Browser control is optional

**Website control requires the Pawzura browser extension.** For applications only, leave **Browsers → Website control OFF**; no extension is needed. Blocked tabs close after navigation; their animations use a separate marker near the taskbar.
**Allowlist entries match the protocol and port.** HTTP and HTTPS are separate rules. Omitted ports use 80 for HTTP or 443 for HTTPS. To allow a different port, enter it explicitly, for example `http://127.0.0.1:3000`. Enter just `127.0.0.1` to allow HTTP and HTTPS on all ports of that IP.

For websites, choose your browser and click **Install/connect extension…**. On the extensions page it opens, enable **Developer mode** (Chrome: upper-right switch on `chrome://extensions`), then **Load unpacked** using the copied folder. **Ctrl+Shift+I opens Developer Tools, not this switch.** Finish loading before opening the connection page. [Steps and button locations](doc/en/BROWSERS.md).

## 3D motion needs a separate preparation step

**Generating artwork or preparing its runtime does not create 3D motion.** Optional experimental 3D requires an NVIDIA CUDA GPU with at least **8 GB VRAM**.

1. Open **Settings → Character → Create original artwork…** and check the license acknowledgement. An existing drawing loads automatically; you do not need to draw it again.
2. **Scroll inside that window, below the picture and “Edit hand/foot motion…”**. Click **Prepare 3D motion · 8 GB · pose-assisted**. This is separate from **1. Prepare runtime and selected models** near the top.
3. Wait for completion, then click **Use this character → Save settings** in the main window. Preparation alone does not change the desktop character. [Full 3D guide and troubleshooting](doc/en/3D-MOTION.md).

## Guides

| I want to… | Read this |
| --- | --- |
| Run the app, change language, use the tray | [Getting started](doc/en/GETTING_STARTED.md) |
| Connect Chrome/Edge/Firefox, with examples | [Browser setup](doc/en/BROWSERS.md) |
| Move/pin the companion, recover it or separate work/leisure lists | [Profiles and recovery](doc/en/PROFILES-AND-RECOVERY.md) |
| Create, save, restore or delete characters | [Artwork and licenses](doc/en/CREATIVE-ART.md) · [Character library](doc/en/CHARACTER-LIBRARY.md) |
| Run source or build an EXE | [Setup and builds](doc/en/BUILD.md) |
| Check test coverage, limits and the maintainer's Windows 11 manual report | [Validation](doc/en/VALIDATION.md) |
| Review library/model licenses | [Third-party notices](doc/en/THIRD-PARTY-NOTICES.md) |

| Product direction and maintenance | AI implementation assistance |
| --- | --- |
| [hobby-programmer-5000](https://github.com/hobby-programmer-5000) | [ChatGPT (Codex)](https://github.com/apps/chatgpt-codex-connector) |

App code: [MIT](LICENSE) · [Artwork policy](doc/en/ASSET-LICENSING.md). [Roles](doc/en/CONTRIBUTORS.md) · [0.6.0 changes](doc/en/RELEASE-v0.6.0.md) · [All guides](doc/README.md).
