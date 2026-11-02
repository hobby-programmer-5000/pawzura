[English](../en/THIRD-PARTY-NOTICES.md) | [한국어](../ko/THIRD-PARTY-NOTICES.md) · [문서 목록](../README.ko.md)

# 제3자 라이선스 고지

Pawzura 자체 앱·확장·지원 스크립트 코드는 [MIT](../../LICENSE)입니다. 언어·런타임·라이브러리·빌드 도구·선택 모델은 **각자의 라이선스**를 유지합니다. 이 한국어 설명은 동봉한 원문 라이선스를 대체하지 않습니다.

## 구성요소와 배포

| 구성요소 | 버전/출처 | 라이선스 | 포함 방식 |
| --- | --- | --- | --- |
| CPython | 빌드 인터프리터, 기준 3.14.7. 소스 대상 3.12–3.15 | PSF v2와 포함 고지 | DLL·표준 라이브러리. 빌드 원문 LICENSE를 licenses/installed/CPython-LICENSE.txt에 복사 |
| PySide6 Essentials | 6.12.0 | 제공되는 선택지 중 LGPL-3.0-only 사용 | QtCore/Gui/Widgets 바인딩과 필요한 DLL을 동적으로 로드 |
| Shiboken6 | 6.12.0 | 제공되는 선택지 중 LGPL-3.0-only 사용 | 동적 바인딩 런타임 |
| Qt Base Core/Gui/Widgets/Network와 플러그인 | 6.12.0 | LGPL-3.0-only 및 해당 upstream 예외·개별 제3자 조건 | PyInstaller가 선택한 동적 DLL/플러그인 |
| Qt SVG·이미지 플러그인 | 패키징 훅에서 선택될 경우 | LGPL-3.0-only 및 포함 고지 | 실제 파일은 BINARY-MANIFEST.json에 기록 |
| Microsoft VC runtime/UCRT | Python·Qt 배포 원본 | Microsoft Distributable Code 조건 | 수정하지 않은 DLL. Python Windows 빌드 조건 참고 |
| OpenSSL | 기준 빌드 3.5.8 | Apache-2.0 | libssl/libcrypto DLL과 원문 고지 |
| libffi | CPython에 동봉된 버전 | MIT | libffi-8.dll과 원문 고지 |
| zlib·liblzma/XZ·mpdecimal·bzip2·Zstandard·Unicode | 선택된 CPython 빌드에 포함된 버전 | 각각 zlib·0BSD/공개 도메인 조건·BSD-2-Clause·bzip2·BSD/GPL 선택지·Unicode 조건 | Python 원문과 추가 원문 고지 |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later 및 bootloader 예외 | EXE 실행부. 예외에 따라 앱 자체 라이선스 사용 가능 |
| PyInstaller hooks contrib | 기준 2026.9, BUILD-INFO.json 확인 | 파일에 따라 Apache-2.0/GPL-2.0-or-later | 빌드 도구 |
| altgraph | 기준 0.17.5 | MIT | 빌드 의존성 |
| packaging | 기준 26.3 | Apache-2.0 또는 BSD-2-Clause | 빌드 도구 및 선택된 런타임 파일 |
| pefile | 기준 2024.8.26 | MIT | 빌드 의존성 |
| pywin32-ctypes | 기준 0.2.3 | BSD-3-Clause | 빌드 의존성 |
| setuptools | 기준 84.2.1 | MIT와 vendored 의존성 조건 | 빌드 도구 및 원문 고지 수집 |
| Qwen2.5-0.5B-Instruct / 공식 GGUF | Q4_K_M, Qwen Team / Alibaba Cloud | Apache-2.0 | 선택 다운로드. EXE·저장소에 가중치 없음 |
| Qwen2.5-1.5B-Instruct / 공식 GGUF | Q4_K_M, Qwen Team / Alibaba Cloud; [공식 출처](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) | Apache-2.0 | 상세 설명용 선택 모델. EXE·저장소에 가중치 없음. 원문은 `licenses/upstream/Qwen-1.5B-LICENSE.txt` |
| Qwen3 4B / 공식 GGUF | Q4_K_M·Q8_0; [공식 출처](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | Apache-2.0 | 고급 선택 모델. 가중치 미포함. 원문: `licenses/upstream/Qwen3-4B-LICENSE.txt` |
| Qwen3 8B / 공식 GGUF | Q4_K_M; [공식 출처](https://huggingface.co/Qwen/Qwen3-8B-GGUF) | Apache-2.0 | 고급 선택 모델. 가중치 미포함. 원문: `licenses/upstream/Qwen3-8B-LICENSE.txt` |
| Ollama | 사용자 별도 설치 | 본체 MIT, 포함 구성요소는 개별 조건 | 앱에서 재배포하지 않음 |

CPython 표준 바이너리 확장의 구성은 버전과 import 그래프에 따라 다릅니다. OpenSSL·zlib·bzip2·liblzma·libffi·mpdecimal·Zstandard·Unicode 등이 포함될 수 있으며, 실제 바이너리와 해시는 배포의 BINARY-MANIFEST.json으로 확인하세요. 해당 빌드의 Python Windows 라이선스 원문을 변경 없이 보존합니다. Windows 시스템 DLL은 운영체제의 구성요소입니다.


## 선택형 창작 그림 실행환경과 모델

배포 ZIP은 검토한 설치·작업 스크립트와 고정 [카탈로그](../../art_runtime/catalog.json)만 포함합니다. **가중치·Python 3.12·uv·PyTorch·CUDA 바이너리는 포함하지 않으며** 사용자가 준비를 명시적으로 실행해야 별도 로컬 환경에 설치합니다. 앱의 MIT가 다운로드한 구성요소를 재라이선스하지 않습니다. 고급 모델 사용 전 원본 조건을 확인해야 하며 UI는 기준을 바꿀 때마다 다시 확인받습니다. 모델 라이선스가 생성물의 타인 권리를 검증하는 것은 아닙니다.

| 선택 구성요소 | 조건·출처 | 역할 |
| --- | --- | --- |
| SD 1.5 유지보수 가중치 저장소 | [CreativeML OpenRAIL-M](../../licenses/upstream/creative-models/SD15-LICENSE.txt) · [카드](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) | 2/4 GB 그림 생성. 제한된 공개 가중치이며 OSI 승인 오픈소스가 아님 |
| SDXL base 1.0 | [CreativeML Open RAIL++-M](../../licenses/upstream/creative-models/SDXL-LICENSE.txt) · [카드](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 6/8 GB 그림 생성, 별도 이용 제한 |
| Qwen3-VL 2B Instruct / Ollama `qwen3-vl:2b` | Apache-2.0 · [공식 모델](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) · [Ollama 패키지](https://ollama.com/library/qwen3-vl:2b) | 로컬 그림 검사. 위의 Qwen2.5 1.5B는 설명 검사 |
| Falconsai/nsfw_image_detection | Apache-2.0 · [모델 카드](https://huggingface.co/Falconsai/nsfw_image_detection) · [원문](../../licenses/upstream/Apache-2.0.txt) | CPU ViT 분류기, 완벽한 안전 보장 아님 |
| U2NetP ONNX | Apache-2.0 · [미러](https://huggingface.co/edgetools/u2netp) · [원본 U-2-Net 라이선스](../../licenses/upstream/creative-models/U2Net-LICENSE.txt) | CPU 배경 제거 |
| ViTPose base simple | Apache-2.0 · [모델 카드](https://huggingface.co/usyd-community/vitpose-base-simple) · [원문](../../licenses/upstream/creative-models/ViTPose-LICENSE.txt) | 선택형 CPU 손발 관절 추정. revision 고정, 가중치 미동봉 |
| SciPy 1.16.3 | BSD-3-Clause·포함 고지 · [원문](../../licenses/upstream/creative-models/SciPy-LICENSE.txt) | 선택형 자세 모델 전후 처리. 설치 wheel의 포함 의존성 고지 유지 |
| uv 0.13.6 | MIT OR Apache-2.0 · [MIT](../../licenses/upstream/creative-models/uv-LICENSE-MIT.txt) · [Apache](../../licenses/upstream/creative-models/uv-LICENSE-APACHE.txt) | 공식 파일 체크섬 검증 후 환경 준비 |
| 별도 CPython 3.12.14 | PSF·포함 고지 · [python-build-standalone](https://github.com/astral-sh/python-build-standalone) | 격리된 그림 인터프리터, 원본 배포의 고지 유지 |
| PyTorch 2.7.1 CUDA 11.8 | BSD-3-Clause·포함 고지 · [원문](https://github.com/pytorch/pytorch/blob/v2.7.1/LICENSE) | 추론. 내려받는 NVIDIA CUDA·cuDNN은 [CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html) 등 자체 독점 조건 적용 |
| Diffusers 0.35.2, Transformers 4.57.1, Accelerate 1.11.0, Safetensors 0.6.2, Hugging Face Hub 0.36.0 | Apache-2.0, 개별 저작권·고지는 설치 패키지에 유지 | safetensors 전용 로컬 파이프라인, 원격/사용자 정의 모델 코드 실행 없음 |
| Pillow 12.0.0 | HPND/Pillow 조건·포함 고지 · [원문](https://github.com/python-pillow/Pillow/blob/12.0.0/LICENSE) | 픽셀·PNG |
| NumPy 2.2.6 | BSD-3-Clause·포함 고지 · [원문](https://github.com/numpy/numpy/blob/v2.2.6/LICENSE.txt) | 마스크 처리 |
| ONNX Runtime 1.23.2 | MIT·타사 고지 · [원문](https://github.com/microsoft/onnxruntime/blob/v1.23.2/LICENSE) | CPU 배경 제거 |

간접 패키지로 requests/urllib3/certifi, tokenizers, filelock, fsspec, Jinja2/MarkupSafe, SymPy/mpmath, networkx, packaging, PyYAML, regex, tqdm, psutil, protobuf, coloredlogs/humanfriendly, flatbuffers, typing-extensions, setuptools 등이 설치될 수 있습니다. 각 라이선스·메타데이터를 설치 환경에 유지하며 앱 ZIP에 포함하거나 재라이선스하지 않습니다. 준비 과정에서 로컬 `DEPENDENCIES.json` 목록과 사용 가능한 라이선스·NOTICE 원문을 `art-runtime/licenses/`에 보존합니다. 모델 snapshot과 라이브러리 버전은 별개입니다. 준비된 실행환경을 직접 재배포한다면 모든 개별 조건을 유지해야 하며 가벼운 앱 EXE의 고지만으로 충분한 전체 고지 목록이 되지 않습니다.

## 원문 보관

선택적 브라우저 검사에는 Playwright(Apache-2.0)와 개별 고지가 적용되는 별도 Chromium을 사용합니다. 개발·검사 도구이며 Pawzura EXE ZIP에 재배포하지 않습니다. `test-browser` 추가 의존성은 선택 사항이고 검사 환경 자체를 배포한다면 설치된 도구의 라이선스 원문도 유지해야 합니다.

[licenses/SOURCES.json](../../licenses/SOURCES.json)에 파일별 공식 출처를 기록합니다. `licenses/upstream/qtbase`, `pyside-setup`, `qtsvg`의 v6.12.0 원문과 qt_attribution.json에는 FreeType, HarfBuzz, PNG/JPEG, PCRE2, double-conversion, zlib, Zstandard, Vulkan, md4c 등 Qt의 포함·선택 구성요소 고지가 있습니다. 실제 사용하지 않는 upstream 구성요소의 고지도 넓게 보존합니다.

설치된 휠·빌드 도구 고지는 배포의 `licenses/installed`로 복사합니다. 일부 휠 dist-info에는 상용 라이선스 참조만 있지만 메타데이터는 LGPL/GPL 선택지를 명시하므로, 같은 공식 소스 버전의 LGPL/GPL 원문을 별도로 제공합니다. 이 프로젝트가 상용 Qt 라이선스를 보유한다고 주장하지 않습니다.

[Qwen 원문](../../licenses/upstream/Qwen-LICENSE.txt)과 [Apache-2.0](../../licenses/upstream/Apache-2.0.txt)을 보관합니다. 모델을 학습·수정·재배포하지 않습니다. 캐릭터는 모델 출력과 자체 도형을 사용하며 외부 스프라이트를 복사하지 않습니다.

## Qt 소스와 교체 권리

Qt/PySide/Shiboken은 포터블 폴더에서 **동적**으로 사용합니다. 수령자는 LGPL 권리 행사를 위해 호환 라이브러리를 교체하거나 앱을 디버깅·역공학할 수 있으며, Pawzura가 이를 추가 제한하지 않습니다. `_internal`의 DLL/플러그인 구조를 유지하세요. 단일 self-extracting EXE를 기본 배포로 사용하지 않습니다.

수정하지 않은 대응 소스와 빌드 안내:

- [Qt Base 6.12.0](https://github.com/qt/qtbase/tree/v6.12.0)
- [Qt SVG 6.12.0](https://github.com/qt/qtsvg/tree/v6.12.0)
- [PySide/Shiboken 6.12.0](https://github.com/pyside/pyside-setup/tree/v6.12.0)
- [Qt for Python 빌드](https://doc.qt.io/qtforpython-6/building_from_source/index.html)
- [Qt LGPL 의무 안내](https://www.qt.io/development/open-source-lgpl-obligations)
- [PyInstaller 예외](https://pyinstaller.org/en/stable/license.html)
- [CPython 3.14.7](https://github.com/python/cpython/tree/v3.14.7)
- [Ollama](https://github.com/ollama/ollama)

바이너리를 변경해 재배포하면 실제 버전의 고지·구성 목록·대응 소스 제공과 교체 권리를 보존해야 합니다. MIT 자체 코드를 private로 관리하더라도 배포하는 LGPL 구성요소의 의무는 유지됩니다. 상위 프로젝트의 라이선스 원문은 정확성을 위해 번역·수정하지 않습니다.
