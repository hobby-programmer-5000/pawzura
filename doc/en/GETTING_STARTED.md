[English](../en/GETTING_STARTED.md) | [한국어](../ko/GETTING_STARTED.md) · [Documentation](../README.md)

# Getting started

## 1. Start the app

Download the Windows ZIP from [Releases](https://github.com/hobby-programmer-5000/pawzura/releases), right-click it → **Extract All**, then open the extracted `Pawzura` folder and double-click **Pawzura.exe**. Keep `_internal`, `extensions`, `doc` and `licenses` beside the EXE. Do not launch it from inside the ZIP.

You do not need Python, Ollama or a model to use the companion. To run the source instead, install standard CPython and double-click `run.bat`; see [source setup](BUILD.md).

**SmartScreen may appear on first launch:** this project distributes unsigned builds. Download from the official Releases page and compare the ZIP's SHA-256 with its `SHA256SUMS` file (`Get-FileHash .\Pawzura-<version>-windows-x64.zip -Algorithm SHA256`). If you trust that verified download and Windows offers **More info → Run anyway**, you may choose it. A reputation warning is not a malware clearance; a malware detection or organization policy needs separate review. Do not disable Windows protection globally. [Microsoft's reputation explanation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

The settings window opens. The character appears above the taskbar. The guardian starts **off**, and preview mode starts **on**.

## 2. Choose a language

The default is **English**. Open **General → Language → 한국어 → Save settings** to switch to Korean. The window and tray menu update after saving. To switch back, use **일반 → 언어 → English → 설정 저장**. A previously saved language is preserved during upgrades.

## 3. Try the companion without closing anything

To choose a white settings window, use **General → Theme → Light (white) → Save settings**. Selection previews immediately; saving persists it. **Dark** remains the default for existing and fresh settings. The browser extension's own page keeps its separate appearance. Advanced model setup is in [models and memory](ADVANCED-MODELS.md).

On **General**, click **Preview bite animation**. This demonstration does not close a window. Use **Character → Random character → Save settings** to change the companion without installing a model. [Qwen generation](MODELS.md) is optional.

## 4. Configure allowed applications

Open **Applications**. Codex can run as `ChatGPT.exe`; listing `codex.exe` protects both names, including older saved settings. Known browser windows are always protected from native closing. Add the other programs you want to keep open using **Add executable…** or **Add open application…**, then save. Names such as `code.exe` are used, rather than window titles. Standard allowed apps and detected startup apps are already included. System windows and Pawzura itself are protected.

Return to **General**, check **Enable focus guardian** and **Enable application control**, leave **Preview mode** checked, and save. Unlisted windows now receive an animation, but stay open. Once the list looks right, uncheck **Preview mode** and save to allow normal close requests. Save prompts are not bypassed.

## 5. Connect a browser (optional)

**Website control requires the extension.** Start with **Browsers → choose browser → Install/connect extension…**. The helper opens installation, copies the correct folder and opens connection without code copying. [Short Chrome/Edge steps](BROWSERS.md). For applications only, leave **Website control OFF**; this applies immediately and needs no extension. Opening `options.html` from Explorer only previews a file.

For tab-only control, connect the extension and enable **Website control** and **Apply website allowlist to this browser** for your browser. In **General**, keep **Enable focus guardian** checked, clear **Enable application control**, and click **Save settings**. The application control setting applies across allowlist profiles. Keep **Preview mode** checked while testing the browser's allowlist.

## Everyday controls

| What you want | Where to go |
| --- | --- |
| Open settings | Click the Pawzura icon near the Windows clock; check the hidden-icon arrow if needed |
| Pause closing | Right-click that icon → Pause guardian |
| Control applications while browsing freely | Browsers → Website control OFF, or the tray's website-control switch |
| Hide only the character | Right-click → Hide companion |
| Recover a missing/broken companion | Right-click → Recover companion on screen |
| Separate work/leisure lists | Settings top → Allowlist profile; [instructions](PROFILES-AND-RECOVERY.md) |
| Exit the whole app | Right-click → Quit |
| Start at sign-in | General → Run when I sign in to Windows → Save settings |
| Change language | General → Language → Save settings |
| Play with the companion | Hover to greet; click to cycle wave/hop/cheer; double-click/right-click to open settings |
| Animate generated hands/feet | Character → Edit hand/foot motion… → Use motion settings → Save settings; [guide](ARTWORK-MOTION.md) |

The settings window's close button returns to the tray. **Hide companion** keeps the guardian running; **Quit** stops it.

## If something does not work

- **Missing DLLs:** extract the complete ZIP and keep `_internal` beside `Pawzura.exe`.
- **Nothing closes:** check that the guardian is on and preview is off. For application windows, check **Enable application control**. For tabs, check **Website control**, the selected browser's site filtering, and the extension connection.
- **Browser connection fails:** keep the app running, click Connect automatically and approve in the app. Check the port if it cannot connect. The extension now explains rejected codes and unreachable apps directly.
- **A previous version is running:** choose Quit from its tray icon before starting the updated EXE.
- **Qt fails in Conda:** use the [standard CPython setup](BUILD.md).

See [validation and current limits](VALIDATION.md) before relying on preview functionality. Settings are stored in `%LOCALAPPDATA%\Pawzura\settings.json`.

## Walking direction

In **Settings → General → Walking direction**, choose **Left** or **Right**, then **Save settings**. Right is the default for new and older settings. The preference applies to vector, 2D artwork and prepared 3D characters, and survives restarting or recovering the companion. It is a global setting, independent of allowlist profiles. During a bite the character faces the target, then returns to the selected walking direction. The motion dropdown in the artwork window only previews clips; it does not save this preference.

The companion keeps a 144 × 146 logical-pixel window when crossing display scales. A real Windows 10 100%/125% boundary check in both directions exposed and corrected repeated tool-window resizing. For an optional test with your own monitor arrangement, run `.venv-standard/Scripts/python.exe tests/pet_dpi_probe.py --output .cache/pet-dpi-probe.json` from the checkout. It displays only a test-owned vector pet; it performs no guardian actions. Exit 2 means NOT RUN because Windows or different monitor scale factors are unavailable. A pass covers that connected arrangement, not every DPI/layout.
