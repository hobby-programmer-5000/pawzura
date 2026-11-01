[English](../en/BUILD.md) | [한국어](../ko/BUILD.md) · [Documentation](../README.md)

# Source setup and EXE builds

Run commands in the repository folder on Windows. Standard CPython 3.12–3.15 is supported; the pinned Qt does not support 3.16+. Conda caused Qt DLL conflicts in local testing.

## Run without building

Double-click `run.bat`. On first use it runs `setup.ps1`, creates `.venv-standard` and installs Qt. With `uv`, setup uses managed CPython 3.14; otherwise it tries `py -3.14`.

For an existing Python 3.12 installation, choose it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Python C:\Python312\python.exe
.\.venv-standard\Scripts\python.exe -m pawzura --settings
```

`--tray` starts quietly at sign-in. `--settings` opens settings. Default launches also open settings. Windows startup uses only the current user's `Run` entry named Pawzura; disable it in General.

## Build

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Output: `dist/Pawzura/Pawzura.exe` and `dist/Pawzura-<version>-windows-x64.zip`. Development builds are not published releases. The executable is a portable folder with replaceable Qt DLLs; distribute the whole folder. Ollama and model weights are not bundled. A distribution privacy check runs before ZIP creation; see [local settings and privacy](PRIVACY.md).

The build copies both documentation languages, the [character rights notice](../../CHARACTER-POLICY.md) and original third-party licenses. `BUILD-INFO.json` records Python and dependency versions. `BINARY-MANIFEST.json` records SHA-256 of each executable/DLL/PYD. MSVC redistributable copies are unified to the newest unmodified shipped version to avoid loader-order conflicts.

When updating Qt, update `scripts/fetch_licenses.py` and collect the matching upstream notices before building:

```powershell
.\.venv-standard\Scripts\python.exe scripts/fetch_licenses.py
```

## Checks

To preserve an existing output folder while building another version, use `python scripts/build.py --dist-dir dist/0.1.4`. The EXE folder and ZIP are written inside that directory; the default remains `dist`.

```powershell
.\.venv-standard\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-standard\Scripts\python.exe -m pawzura --smoke-check --capture artifacts/settings.png
node --test tests/*.test.cjs
.\.venv-standard\Scripts\python.exe scripts/check_docs.py
```

The opt-in `python tests/native_probe.py` opens and closes only its own test window. Normal checks do not close user applications or edit startup registration.

After changing shared extension files, run `python scripts/sync_extensions.py` to refresh Firefox. GitHub Actions checks Python 3.12, 3.14 and 3.15. The separate Build workflow is manual. See [validation](VALIDATION.md) for actual results.

Optional real-browser probe: install the `test-browser` extra (Playwright), then run `python tests/browser_probe.py --chromium C:\path\to\chrome.exe`. Use a Chromium build that supports unpacked extension loading. The probe uses a new temporary profile and test-only bridge; it acknowledges approval and animation events itself, without altering user settings. Playwright is a test tool and is not bundled with the EXE.
