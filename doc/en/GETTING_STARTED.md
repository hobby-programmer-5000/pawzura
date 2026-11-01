[English](../en/GETTING_STARTED.md) | [한국어](../ko/GETTING_STARTED.md) · [Documentation](../README.md)

# Getting started

## 1. Start the app

Download the Windows ZIP from [Releases](https://github.com/hobby-programmer-5000/pawzura/releases), right-click it → **Extract All**, then open the extracted `Pawzura` folder and double-click **Pawzura.exe**. Keep `_internal`, `extensions`, `doc` and `licenses` beside the EXE. Do not launch it from inside the ZIP.

You do not need Python, Ollama or a model to use the companion. To run the source instead, install standard CPython and double-click `run.bat`; see [source setup](BUILD.md).

The settings window opens. The character appears above the taskbar. The guardian starts **off**, and preview mode starts **on**.

## 2. Choose a language

The default is **English**. Open **General → Language → 한국어 → Save settings** to switch to Korean. The window and tray menu update after saving. To switch back, use **일반 → 언어 → English → 설정 저장**. A previously saved language is preserved during upgrades.

## 3. Try the companion without closing anything

On **General**, click **Preview bite animation**. This demonstration does not close a window. Use **Character → Random character → Save settings** to change the companion without installing a model. [Qwen generation](MODELS.md) is optional.

## 4. Configure allowed applications

Open **Applications**. Codex can run as `ChatGPT.exe`; listing `codex.exe` protects both names, including older saved settings. Known browser windows are always protected from native closing. Add the other programs you want to keep open using **Add executable…** or **Add open application…**, then save. Names such as `code.exe` are used, rather than window titles. Standard allowed apps and detected startup apps are already included. System windows and Pawzura itself are protected.

Return to **General**, leave **Preview mode** checked, enable **Enable focus guardian**, and save. Unlisted windows now receive an animation, but stay open. Once the list looks right, uncheck **Preview mode** and save to allow normal close requests. Save prompts are not bypassed.

## 5. Connect a browser (optional)

The desktop app alone cannot inspect browser addresses. Install the included extension in each browser, then click Connect automatically and approve the request in the desktop app. Follow the [Chrome/Edge walkthrough with examples](BROWSERS.md). Opening `options.html` as a local file only previews the page; it does not install the extension.

## Everyday controls

| What you want | Where to go |
| --- | --- |
| Open settings | Click the Pawzura icon near the Windows clock; check the hidden-icon arrow if needed |
| Pause closing | Right-click that icon → Pause guardian |
| Hide only the character | Right-click → Hide companion |
| Recover a missing/broken companion | Right-click → Recover companion on screen |
| Separate work/leisure lists | Settings top → Allowlist profile; [instructions](PROFILES-AND-RECOVERY.md) |
| Exit the whole app | Right-click → Quit |
| Start at sign-in | General → Run when I sign in to Windows → Save settings |
| Change language | General → Language → Save settings |

The settings window's close button returns to the tray. **Hide companion** keeps the guardian running; **Quit** stops it.

## If something does not work

- **Missing DLLs:** extract the complete ZIP and keep `_internal` beside `Pawzura.exe`.
- **Nothing closes:** verify that the guardian is enabled and preview is off. For websites, the browser setting and extension connection must also be enabled.
- **Browser connection fails:** keep the app running, click Connect automatically and approve in the app. Check the port if it cannot connect. The extension now explains rejected codes and unreachable apps directly.
- **A previous version is running:** choose Quit from its tray icon before starting the updated EXE.
- **Qt fails in Conda:** use the [standard CPython setup](BUILD.md).

See [validation and current limits](VALIDATION.md) before relying on preview functionality. Settings are stored in `%LOCALAPPDATA%\Pawzura\settings.json`.
