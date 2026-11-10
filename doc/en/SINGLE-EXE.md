[English](../en/SINGLE-EXE.md) | [한국어](../ko/SINGLE-EXE.md) · [Documentation](../README.md)

# Standalone Windows EXE

Download `Pawzura-<version>-windows-x64.exe` from Releases and double-click it. It expands its bundled libraries and support files into a temporary directory during startup. First launch can take longer than the ZIP build. Settings and generated characters are stored in the user's existing local Pawzura data directory. Unsigned builds can trigger SmartScreen.

The **Windows ZIP** remains available for users who want an extracted folder. Extract that entire ZIP and run `Pawzura/Pawzura.exe`.

## One active companion

Source, ZIP and standalone launches share the application lock in the same settings directory. A second launch shows an already-running message and exits. Use the existing Pawzura tray icon to open settings. Folder access and disk errors receive a storage-error message. A process crash releases the operating-system lock so a later launch can recover.

For isolated testing, run `Pawzura.exe --settings-file <new-folder>/settings.json`. Use a dedicated directory. Instances using the same directory share its lock. Keep guardian OFF while testing.

## Browser extension and artwork

Use **Browsers → Install/connect extension…**. The helper copies the bundled extension to a stable local folder before the browser loads it. Advanced image and motion preparation uses the bundled worker scripts. Ollama, optional image/3D runtimes and model weights use their existing separate installation steps. [Browser guide](BROWSERS.md) · [Artwork setup](CREATIVE-ART.md).

Open **About → Open license notices** to read the bundled original license files while the app is running.

## Rebuilding with compatible libraries

Original Pawzura code uses MIT. Qt/PySide/Shiboken use their applicable LGPLv3 options. The standalone build follows the LGPLv3 section 4(d)(0) source-and-recombination route. Its matching application source is provided by the release tag's **Source code** download, including the build scripts, requirements and notices. Releases also provide the unmodified Qt Base, Qt SVG and PySide/Shiboken 6.12.0 source archives.

1. Download the exact release tag's source and install standard CPython 3.14 x64.
2. Run `setup.ps1` in that checkout to create the pinned environment.
3. Build your modified compatible Qt/PySide/Shiboken libraries using the upstream source and instructions linked in [the notices](THIRD-PARTY-NOTICES.md#qt-source-and-user-replacement). Install them into that environment, preserving Python/Qt ABI and x64 compatibility.
4. Run `python scripts/build.py --dist-dir dist/custom --onefile` with the environment's Python. The build bundles the libraries from that environment and permits rebuilding with your changes.
5. Run the resulting EXE with `--smoke-check`, then test with a fresh explicit settings directory.

The ZIP build's `_internal` directory also supports compatible library replacement. Retain the original notices, corresponding source access and rebuilding information when redistributing. [Original LGPLv3 text](../../licenses/upstream/pyside-setup/LICENSES/LGPL-3.0-only.txt).
