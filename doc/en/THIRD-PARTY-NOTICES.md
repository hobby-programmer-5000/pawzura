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


## Optional creative artwork runtime and models

The app ZIP contains only trusted setup/worker source and the pinned [catalog](../../art_runtime/catalog.json), **not weights, Python 3.12, uv, PyTorch or CUDA binaries**. The user explicitly requests their installation into a separate local environment. App MIT does not relicense anything downloaded. Read each advanced model's original terms before use; the UI requires a fresh acknowledgement when selecting a guide. Model licenses do not clear generated content's third-party rights.

| Optional component | Terms / source | Role |
| --- | --- | --- |
| SD 1.5 maintained weight repository | [CreativeML OpenRAIL-M](../../licenses/upstream/creative-models/SD15-LICENSE.txt); [model card](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) | 2/4 GB image generation; restricted open weights, not OSI-approved open source |
| SDXL base 1.0 | [CreativeML Open RAIL++-M](../../licenses/upstream/creative-models/SDXL-LICENSE.txt); [model card](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 6/8 GB image generation; separate use restrictions |
| Qwen3-VL 2B Instruct / Ollama `qwen3-vl:2b` | Apache-2.0; [official model](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct), [Ollama package](https://ollama.com/library/qwen3-vl:2b) | Local image review; Qwen2.5 1.5B above reviews descriptions |
| Falconsai/nsfw_image_detection | Apache-2.0; [model card](https://huggingface.co/Falconsai/nsfw_image_detection), [Apache text](../../licenses/upstream/Apache-2.0.txt) | CPU ViT classifier; not a perfect safety guarantee |
| U2NetP ONNX | Apache-2.0; [mirror](https://huggingface.co/edgetools/u2netp), [original U-2-Net license](../../licenses/upstream/creative-models/U2Net-LICENSE.txt) | CPU background removal |
| ViTPose base simple | Apache-2.0; [model card](https://huggingface.co/usyd-community/vitpose-base-simple), [original license](../../licenses/upstream/creative-models/ViTPose-LICENSE.txt) | Optional CPU hand/foot joint estimation; weights pinned in the catalog, not bundled |
| SciPy 1.16.3 | BSD-3-Clause and incorporated notices; [original license](../../licenses/upstream/creative-models/SciPy-LICENSE.txt) | Optional pose preprocessing/postprocessing; installed-wheel notices include incorporated dependencies |
| uv 0.13.6 | MIT OR Apache-2.0; [MIT](../../licenses/upstream/creative-models/uv-LICENSE-MIT.txt), [Apache](../../licenses/upstream/creative-models/uv-LICENSE-APACHE.txt) | Checksum-verified official runtime bootstrap |
| Standalone CPython 3.12.14 | PSF and incorporated notices; [python-build-standalone](https://github.com/astral-sh/python-build-standalone) | Isolated image interpreter; upstream distribution's notices remain installed |
| PyTorch 2.7.1 CUDA 11.8 | BSD-3-Clause and incorporated notices; [PyTorch license](https://github.com/pytorch/pytorch/blob/v2.7.1/LICENSE) | Image inference; downloaded NVIDIA CUDA/cuDNN components retain their own proprietary terms, including [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html) |
| Diffusers 0.35.2, Transformers 4.57.1, Accelerate 1.11.0, Safetensors 0.6.2, Hugging Face Hub 0.36.0 | Apache-2.0; individual upstream copyright/notices remain in installed packages | Fixed safetensors-only local pipelines; no remote/custom model code |
| Pillow 12.0.0 | HPND/Pillow terms and incorporated notices; [license](https://github.com/python-pillow/Pillow/blob/12.0.0/LICENSE) | Pixels and PNG encoding |
| NumPy 2.2.6 | BSD-3-Clause and incorporated notices; [license](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt) | Mask processing |
| ONNX Runtime 1.23.2 | MIT and third-party notices; [license](https://github.com/microsoft/onnxruntime/blob/v1.23.2/LICENSE) | CPU cutout inference |

The optional environment also resolves transitive packages (for example requests/urllib3/certifi, tokenizers, filelock, fsspec, Jinja2/MarkupSafe, SymPy/mpmath, networkx, packaging, PyYAML, regex, tqdm, psutil, protobuf, coloredlogs/humanfriendly, flatbuffers, typing-extensions and setuptools). Their individual license files and package metadata remain in the installed environment; they are not relicensed or bundled in the app ZIP. Preparation writes a local `DEPENDENCIES.json` inventory and copies available installed license/notice texts into `art-runtime/licenses/`. Model snapshots and library revisions are separate. Preserve all applicable terms if redistributing a prepared runtime yourself; the app's lightweight EXE notices are not a complete license inventory for such a redistribution.

## Optional pose-assisted 3D connection

[Usage and limitations](3D-MOTION.md). No weights or prepared runtime are shipped. All dependencies retain their own terms, including existing PyTorch/NVIDIA components. Exact installed/transitive notices are copied into the local runtime inventory during preparation.

| Component | Version / original terms | Role |
| --- | --- | --- |
| TripoSR code and checkpoint | Source `107cefdc244c39106fa830359024f6a2f1c78871`; weights `5b521936b01fbe1890f6f9baed0254ab6351c04a`; **MIT**, [original license](../../licenses/upstream/triposr/LICENSE), [model card](https://huggingface.co/stabilityai/TripoSR) | Shared single-image scene, camera views and geometry. Original source retained; separate adapted copy defers unused rembg/torchmcubes imports. Surface extraction/rigging/baking are Pawzura code |
| DINO ViT-B/16 configuration | `f205d5d8e640a89a2b8ef0369670dfc37cc07fc2`; **Apache-2.0**, [model card](https://huggingface.co/facebook/dino-vitb16), [license](../../licenses/upstream/Apache-2.0.txt) | TripoSR image-encoder configuration; no separate DINO pretrained weights downloaded |
| ViTPose | Existing pinned Apache-2.0 model above | CPU landmarks for pose-assisted joint lifting, not a learned specialist 3D rigger |
| einops | 0.7.0, MIT, [original](../../licenses/upstream/creative-models/einops-LICENSE.txt) | Tensor rearrangement |
| OmegaConf | 2.3.0, BSD-3-Clause, [original](../../licenses/upstream/creative-models/omegaconf-LICENSE.txt) | Trusted upstream model configuration |
| ANTLR4 Python runtime | 4.9.3 resolved by OmegaConf, BSD-3-Clause and incorporated terms, [original](../../licenses/upstream/creative-models/ANTLR4-LICENSE.txt) | Configuration parser; preserve installed component notices |
| trimesh | 4.0.5, MIT, [original](../../licenses/upstream/creative-models/trimesh-LICENSE.txt) | Upstream geometry interface dependency |
| imageio | 2.37.0, BSD-2-Clause, [original](../../licenses/upstream/creative-models/imageio-LICENSE.txt) | Upstream image utility dependency |

The [motion catalog](../../art_runtime/motion_catalog.json) pins model files/hashes; the [source record](../../art_runtime/triposr-sources.json) pins original source hashes. Downloaded adapted sources record their original revision, modifications and hashes. Skin weights, gait and face/jaw corrections are procedural. MIT permits use subject to its terms; it does not certify generated character rights. Original drawing model restrictions remain applicable.

## Original notices and attributions

Optional browser testing uses Playwright (Apache-2.0) and a separately installed Chromium with its own notices. These are development/test tools and are not redistributed in Pawzura's EXE ZIP. The `test-browser` extra is optional; keep the tools' installed license files if distributing a test environment.

`licenses/upstream/qtbase`, `licenses/upstream/pyside-setup` and `licenses/upstream/qtsvg` contain unmodified upstream license texts and `qt_attribution.json` files collected at **v6.12.0**. They include the copyright holders and individual terms for Qt's bundled third-party sources (for example FreeType, HarfBuzz, libpng, libjpeg-turbo, PCRE2, double-conversion, zlib, Zstandard, Vulkan headers, md4c, and other selected or optional source components). The collection deliberately also retains notices for upstream components a given binary might not use. File/source mappings are in [licenses/SOURCES.json](../../licenses/SOURCES.json).

Installed wheel/build-tool license files and the exact CPython license are copied unchanged by `scripts/build.py` to the release's `licenses/installed/`. Some Qt wheels list only a commercial-license reference in their dist-info; the selected LGPL/GPL texts are supplied separately from the matching official source repositories in `licenses/upstream/`. The wheel's metadata declares its LGPL/GPL alternatives. No commercial Qt license is asserted for this project.

Model license: [Qwen original license text](../../licenses/upstream/Qwen-LICENSE.txt), [Apache-2.0 text](../../licenses/upstream/Apache-2.0.txt). No model fine-tuning, weight modification or redistribution is performed. Character designs use the model's output plus original application geometry; they are not copies of external sprite assets.

## Qt source and user replacement

This build uses **dynamic** Qt/PySide/Shiboken libraries in a portable folder. Recipients may replace the compatible LGPL libraries and debug/reverse-engineer the application to exercise their rights under LGPL. Pawzura imposes no additional restriction on those activities. Preserve the ZIP build's `_internal` DLL/plugin structure. The optional self-extracting EXE is distributed with corresponding source and rebuild instructions under the LGPLv3 section 4(d)(0) route. See [standalone rebuilding](SINGLE-EXE.md). Releases provide matching Qt Base, Qt SVG and PySide/Shiboken source archives alongside the application source tag.

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
