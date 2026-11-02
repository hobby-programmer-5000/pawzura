[English](../en/THIRD-PARTY-NOTICES.md) | [한국어](../ko/THIRD-PARTY-NOTICES.md) · [Documentation](../README.md)

# Third-party notices

Pawzura's original application, browser extension and support-script code is released under the [MIT License](../../LICENSE). The programming language, runtime, libraries, build tools and optional model retain **their own licenses**. MIT does not relicense those components.

## Components and distribution

| Component | Version / source | License | Distribution |
| --- | --- | --- | --- |
| CPython | Build interpreter, currently 3.14.7; source supports 3.12–3.15 | Python Software Foundation License v2 and incorporated notices | Python DLL/stdlib included in EXE folder; full build's LICENSE.txt copied to `licenses/installed/CPython-LICENSE.txt` |
| PySide6 Essentials | 6.12.0 | LGPL-3.0-only (chosen from upstream LGPL/GPL alternatives) | QtCore/QtGui/QtWidgets Python bindings and required Qt DLLs, dynamically loaded |
| Shiboken6 | 6.12.0 | LGPL-3.0-only (chosen from upstream alternatives) | Binding runtime, dynamically loaded |
| Qt Base (Core, Gui, Widgets, Network, supporting plugins) | 6.12.0 | LGPL-3.0-only with upstream exceptions for applicable files; included third-party components retain their licenses | Dynamic DLLs/plugins selected by PyInstaller |
| Qt SVG and image format plugins | If selected by the Qt packaging hook | LGPL-3.0-only and included notices | Presence is recorded in the release's BINARY-MANIFEST.json |
| Microsoft VC runtime / Universal CRT | As shipped by CPython/Qt | Microsoft Distributable Code terms | Unmodified Windows DLLs; see CPython Windows build conditions |
| OpenSSL | 3.5.8 in initial build | Apache-2.0 | `libssl-3-x64.dll`, `libcrypto-3-x64.dll`; original license and copyright notices in `licenses/upstream/OpenSSL-LICENSE.txt` |
| libffi | As shipped with CPython | MIT | `libffi-8.dll`; original copyright/license in `licenses/upstream/libffi-LICENSE.txt` |
| zlib, liblzma/XZ, mpdecimal, bzip2, Zstandard, Unicode data | As incorporated in the selected CPython build | zlib, 0BSD/public-domain terms for liblzma, BSD-2-Clause, bzip2 license, BSD/GPL alternatives, Unicode terms respectively | CPython LICENSE plus additional unmodified texts in `licenses/upstream/` |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with the PyInstaller bootloader exception | EXE stub; the exception permits the resulting application's own license |
| PyInstaller hooks contrib | 2026.9 in initial build, inspect BUILD-INFO.json | Apache-2.0 / GPL-2.0-or-later depending on files | Build-time hooks; not the application license |
| altgraph | 0.17.5 in initial build | MIT | Build-time dependency |
| packaging | 26.3 in initial build | Apache-2.0 OR BSD-2-Clause | Build-time dependency; tool-selected runtime use may appear in bundle |
| pefile | 2024.8.26 in initial build | MIT | Build-time dependency |
| pywin32-ctypes | 0.2.3 in initial build | BSD-3-Clause | Build-time dependency |
| setuptools | 84.2.1 in initial build | MIT and vendored dependency licenses | Build-time dependency; collect installed notices |
| Qwen2.5-0.5B-Instruct / official GGUF | Q4_K_M, Qwen Team / Alibaba Cloud | Apache-2.0 | **Optional external download**, no weights in repository/EXE |
| Qwen2.5-1.5B-Instruct / official GGUF | Q4_K_M, Qwen Team / Alibaba Cloud; [official source](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | Apache-2.0 | Optional detailed-description model; no weights in repository/EXE; original text in `licenses/upstream/Qwen-1.5B-LICENSE.txt` |
| Qwen3 4B / official GGUF | Q4_K_M and Q8_0; [official source](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | Apache-2.0 | Optional advanced designer; weights not bundled. Original text: `licenses/upstream/Qwen3-4B-LICENSE.txt` |
| Qwen3 8B / official GGUF | Q4_K_M; [official source](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | Apache-2.0 | Optional advanced designer; weights not bundled. Original text: `licenses/upstream/Qwen3-8B-LICENSE.txt` |
| Ollama | User-installed external service | MIT for the main project; its bundled components have individual licenses | Not redistributed with Pawzura |

The executable includes CPython standard-library binary extensions. Their incorporated dependencies can include OpenSSL, zlib, bzip2, liblzma/XZ, libffi, SQLite, mpdecimal, Zstandard and Unicode data depending on Python version and PyInstaller's import graph. The actual binaries are recorded by hash in each build's `BINARY-MANIFEST.json`; Python's complete Windows license file is included unchanged, even where a section does not apply to that artifact. Windows system DLLs loaded from the OS remain part of Windows.

## Original notices and attributions

Optional browser testing uses Playwright (Apache-2.0) and a separately installed Chromium with its own notices. These are development/test tools and are not redistributed in Pawzura's EXE ZIP. The `test-browser` extra is optional; keep the tools' installed license files if distributing a test environment.

`licenses/upstream/qtbase`, `licenses/upstream/pyside-setup` and `licenses/upstream/qtsvg` contain unmodified upstream license texts and `qt_attribution.json` files collected at **v6.12.0**. They include the copyright holders and individual terms for Qt's bundled third-party sources (for example FreeType, HarfBuzz, libpng, libjpeg-turbo, PCRE2, double-conversion, zlib, Zstandard, Vulkan headers, md4c, and other selected or optional source components). The collection deliberately also retains notices for upstream components a given binary might not use. File/source mappings are in [licenses/SOURCES.json](../../licenses/SOURCES.json).

Installed wheel/build-tool license files and the exact CPython license are copied unchanged by `scripts/build.py` to the release's `licenses/installed/`. Some Qt wheels list only a commercial-license reference in their dist-info; the selected LGPL/GPL texts are supplied separately from the matching official source repositories in `licenses/upstream/`. The wheel's metadata declares its LGPL/GPL alternatives. No commercial Qt license is asserted for this project.

Model license: [Qwen original license text](../../licenses/upstream/Qwen-LICENSE.txt), [Apache-2.0 text](../../licenses/upstream/Apache-2.0.txt). No model fine-tuning, weight modification or redistribution is performed. Character designs use the model's output plus original application geometry; they are not copies of external sprite assets.

## Qt source and user replacement

This build uses **dynamic** Qt/PySide/Shiboken libraries in a portable folder. Recipients may replace the compatible LGPL libraries and debug/reverse-engineer the application to exercise their rights under LGPL. Pawzura imposes no additional restriction on those activities. Preserve the EXE folder and its `_internal` DLL/plugin structure; a single self-extracting EXE is deliberately not the default.

Unmodified corresponding upstream sources and build instructions:

- Qt Base 6.12.0: https://github.com/qt/qtbase/tree/v6.12.0
- Qt SVG 6.12.0: https://github.com/qt/qtsvg/tree/v6.12.0
- PySide / Shiboken 6.12.0: https://github.com/pyside/pyside-setup/tree/v6.12.0
- Qt for Python build instructions: https://doc.qt.io/qtforpython-6/building_from_source/index.html
- Qt LGPL guidance: https://www.qt.io/development/open-source-lgpl-obligations
- PyInstaller exception: https://pyinstaller.org/en/stable/license.html
- CPython 3.14.7: https://github.com/python/cpython/tree/v3.14.7
- Ollama: https://github.com/ollama/ollama

Before redistributing a changed binary, preserve these notices, its build inventory, the corresponding source availability and replacement rights for the versions actually shipped. App code may remain private under MIT; the third-party LGPL obligations still apply to distributed copies.
