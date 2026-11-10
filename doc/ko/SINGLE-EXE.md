[English](../en/SINGLE-EXE.md) | [한국어](../ko/SINGLE-EXE.md) · [문서 목록](../README.ko.md)

# Windows 단일 EXE

Releases에서 `Pawzura-<버전>-windows-x64.exe`를 받아 더블 클릭하세요. 시작할 때 포함된 라이브러리·지원 파일을 임시 폴더에 풉니다. 첫 실행은 ZIP 방식보다 오래 걸릴 수 있습니다. 설정과 생성 캐릭터는 기존 사용자 로컬 Pawzura 데이터 폴더에 저장합니다. 서명되지 않아 SmartScreen이 표시될 수 있습니다.

압축을 직접 푸는 **Windows ZIP**도 제공합니다. ZIP 전체를 풀고 `Pawzura/Pawzura.exe`를 실행하세요.

## 캐릭터 하나만 실행

소스·ZIP·단일 EXE는 같은 설정 폴더의 실행 잠금을 공유합니다. 두 번째 실행은 이미 실행 중이라는 안내를 표시하고 종료합니다. 기존 Pawzura 트레이 아이콘으로 설정을 여세요. 폴더 접근·디스크 오류는 저장소 오류로 안내합니다. 프로세스가 비정상 종료되면 운영체제 잠금이 해제되어 이후 실행에서 복구할 수 있습니다.

격리 검사에는 `Pawzura.exe --settings-file <new-folder>/settings.json`을 사용하세요. 전용 폴더를 지정합니다. 같은 디렉터리를 쓰는 인스턴스끼리 실행 잠금을 공유합니다. 검사 중에는 감시를 끄세요.

## 브라우저 확장과 그림

**브라우저 → 확장 설치·연결…**을 사용하세요. 도우미가 포함된 확장을 안정적인 로컬 폴더에 복사한 뒤 브라우저가 불러옵니다. 고급 그림·움직임 준비는 포함된 작업 스크립트를 사용합니다. Ollama, 선택형 그림·3D 실행환경과 모델 가중치는 기존 별도 준비 절차를 따릅니다. [브라우저 안내](BROWSERS.md) · [그림 준비](CREATIVE-ART.md).

앱 실행 중 **정보 → 라이선스 문서 열기**에서 포함된 원본 라이선스를 읽을 수 있습니다.

## 호환 라이브러리로 다시 빌드

Pawzura 자체 코드는 MIT입니다. Qt/PySide/Shiboken은 해당 LGPLv3 선택지로 사용합니다. 단일 EXE는 LGPLv3 제4조 (d)(0)의 소스·재결합 경로를 따릅니다. 대응 앱 소스는 릴리스 태그의 **Source code** 다운로드로 제공하며 빌드 스크립트·요구사항·고지를 포함합니다. 릴리스에는 변경하지 않은 Qt Base·Qt SVG·PySide/Shiboken 6.12.0 원본 소스 압축 파일도 제공합니다.

1. 정확한 릴리스 태그 소스를 받고 일반 CPython 3.14 x64를 설치합니다.
2. 그 체크아웃에서 `setup.ps1`을 실행해 고정 실행환경을 만듭니다.
3. [고지 문서](THIRD-PARTY-NOTICES.md#qt-소스와-교체-권리)에 연결된 원본 소스와 upstream 지침으로 수정한 호환 Qt/PySide/Shiboken을 빌드합니다. Python·Qt ABI와 x64 호환성을 유지해 해당 환경에 설치합니다.
4. 그 환경의 Python으로 `python scripts/build.py --dist-dir dist/custom --onefile`을 실행합니다. 빌드는 그 환경의 라이브러리를 담아 수정본으로 다시 만들 수 있게 합니다.
5. 결과 EXE를 `--smoke-check`로 확인한 뒤 새 설정 디렉터리로 검사합니다.

ZIP의 `_internal`에서도 호환 라이브러리를 교체할 수 있습니다. 재배포 시 원본 고지, 대응 소스 접근과 재빌드 정보를 유지하세요. [LGPLv3 원문](../../licenses/upstream/pyside-setup/LICENSES/LGPL-3.0-only.txt).
