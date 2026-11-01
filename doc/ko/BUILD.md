[English](../en/BUILD.md) | [한국어](../ko/BUILD.md) · [문서 목록](../README.ko.md)

# 소스 실행과 EXE 빌드

Windows에서 저장소 폴더를 열고 명령을 실행하세요. 일반 CPython 3.12–3.15를 지원 대상으로 하며 고정한 Qt는 3.16 이상을 지원하지 않습니다. 로컬에서는 Conda와 Qt DLL 충돌이 재현됐습니다.

## 빌드 없이 소스 실행

`run.bat`를 더블 클릭하세요. 처음에는 `setup.ps1`이 `.venv-standard`를 만들고 Qt를 설치합니다. `uv`가 있으면 관리형 CPython 3.14, 없으면 `py -3.14`를 사용합니다.

기존 Python 3.12 설치를 직접 지정하려면 다음과 같이 실행하세요.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Python C:\Python312\python.exe
.\.venv-standard\Scripts\python.exe -m pawzura --settings
```

`--tray`는 로그인 시 조용히 트레이로 시작합니다. `--settings`와 기본 실행은 설정 창을 엽니다. 자동 실행은 현재 사용자의 Run 키에서 Pawzura 항목만 사용하며 일반 설정에서 해제할 수 있습니다.

## 빌드

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

결과는 `dist/Pawzura/Pawzura.exe`, `dist/Pawzura-<version>-windows-x64.zip`입니다. 개발 빌드는 게시된 릴리스가 아닙니다. Qt DLL을 교체할 수 있는 포터블 폴더이므로 **전체 폴더**를 배포하세요. Ollama와 모델 가중치는 포함하지 않습니다. ZIP 생성 전에 [개인정보 배포 검사](PRIVACY.md)를 수행합니다.

빌드는 양쪽 언어의 문서와 제3자 라이선스 원문을 복사합니다. `BUILD-INFO.json`에 Python·의존성 버전, `BINARY-MANIFEST.json`에 EXE/DLL/PYD의 SHA-256을 기록합니다. DLL 탐색 순서에 따른 충돌을 피하도록 동봉된 Microsoft 런타임 중 가장 최신인 원본 파일을 일관되게 사용합니다.

Qt를 변경하면 `scripts/fetch_licenses.py`의 버전도 맞추고 원문 고지를 다시 수집하세요.

```powershell
.\.venv-standard\Scripts\python.exe scripts/fetch_licenses.py
```

## 검사

```powershell
.\.venv-standard\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-standard\Scripts\python.exe -m pawzura --smoke-check --capture artifacts/settings.png
node --test tests/*.test.cjs
.\.venv-standard\Scripts\python.exe scripts/check_docs.py
```

별도 실행하는 `python tests/native_probe.py`는 자신이 만든 테스트 창만 열고 닫습니다. 일반 검사는 사용자 앱을 닫거나 자동 실행 레지스트리를 변경하지 않습니다.

공유 확장 파일을 고치면 `python scripts/sync_extensions.py`로 Firefox를 동기화하세요. GitHub Actions는 Python 3.12·3.14·3.15를 검사합니다. 별도 Build 작업은 수동 실행입니다. 실제 결과는 [검증 기록](VALIDATION.md)에 있습니다.

선택적 실제 브라우저 검사: `test-browser` 추가 의존성(Playwright)을 설치한 뒤 `python tests/browser_probe.py --chromium C:\path\to\chrome.exe`를 실행하세요. 압축 해제 확장 로딩을 지원하는 Chromium을 사용하세요. 새 임시 프로필과 테스트용 브리지만 사용하며 승인·애니메이션 이벤트는 테스트가 직접 처리합니다. 사용자 설정을 변경하지 않고 Playwright를 EXE에 포함하지 않습니다.
