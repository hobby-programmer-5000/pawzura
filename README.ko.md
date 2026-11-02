# Pawzura · 파우주라

[English](README.md) | **한국어**

Windows 작업표시줄 위를 걷고, 선택적으로 켜는 프로그램·사이트 허용 목록으로 집중을 돕는 작은 SD 캐릭터 앱입니다.

Windows 10 (1809+) / Windows 11 · x64 · 소스 실행 Python 3.12–3.15 · MIT

## 바로 시작

1. [Releases](https://github.com/hobby-programmer-5000/pawzura/releases)에서 최신 **Windows ZIP**을 내려받으세요.
2. **ZIP 전체를 압축 해제**하고 `Pawzura` 폴더의 **Pawzura.exe**를 실행하세요. `_internal` 폴더를 함께 두세요. Python·모델 설치는 필요 없습니다.
3. **General → Preview bite animation**으로 체험하세요. 처음에는 **감시 OFF·미리보기 ON**입니다.

앱 기본 언어는 영어입니다. **General → Language → 한국어 → Save settings**로 바꾸세요. 소스로 쓰려면 빌드 대신 **run.bat**를 더블 클릭하세요.

**실행 전 확인:** 서명되지 않은 빌드라 **Windows SmartScreen**이 표시될 수 있습니다. 공식 배포 파일과 체크섬을 확인한 뒤, 제공되는 경우에만 **추가 정보 → 실행**을 선택하세요. [실행 안내](doc/ko/GETTING_STARTED.md).

**AI 설계에는 실행 중인 Ollama와 충분한 가용 RAM·VRAM이 필요합니다.** Qwen 도형: 캐릭터 → **명령 복사** → PowerShell → `success` 대기 → 생성. GPU 그림: **창작 그림 만들기…** → 모델 라이선스 확인 → **실행환경·선택 모델 준비**. [그림 준비](doc/ko/CREATIVE-ART.md) · [Qwen 명령](doc/ko/ADVANCED-MODELS.md). 기본·임의 캐릭터는 모델이 필요 없습니다.

## 브라우저 제어는 선택 기능입니다

**사이트 제어에는 Pawzura 브라우저 확장 설치가 필수입니다.** 프로그램만 제어하려면 **브라우저 → 사이트 제어 OFF**로 두세요. 확장을 설치하지 않아도 됩니다.

사이트를 제어하려면 브라우저 선택 후 **확장 설치·연결…**을 누르세요. 열린 확장 관리 화면의 **개발자 모드**(Chrome: `chrome://extensions` 오른쪽 위 스위치)를 켜고, **압축해제된 확장 프로그램을 로드합니다**에서 복사된 폴더를 선택하세요. **Ctrl+Shift+I로 여는 개발자 도구와 다릅니다.** 설치를 마친 뒤 연결 화면을 여세요. [단계별 사용법과 버튼 위치](doc/ko/BROWSERS.md).

## 주요 기능

- 모니터를 오가며 설정한 그림의 손발을 움직이고 커서·클릭에 반응합니다. [움직임 설정](doc/ko/ARTWORK-MOTION.md).
- 미허용 창을 닫기 전에 점프·깨물기·사라지는 균열을 표시합니다.
- 브라우저 창을 보호하고 미허용 탭만 닫습니다. 확장에서 자동 연결 후 앱에서 승인하면 됩니다.
- 라이트·다크 설정, 가벼운 Qwen 도형 설계와 선택형 GPU [창작 그림 생성](doc/ko/CREATIVE-ART.md)을 제공합니다. 고급 그림 모델은 별도 다운로드와 라이선스 확인이 필요합니다.

## 필요한 안내 찾기

| 할 일 | 문서 |
| --- | --- |
| 실행·한국어 변경·트레이 사용 | [처음 사용하기](doc/ko/GETTING_STARTED.md) |
| Chrome/Edge/Firefox 연결과 입력 예시 | [브라우저 연결](doc/ko/BROWSERS.md) |
| 업무·여가 목록 분리·캐릭터 복구 | [프로필과 복구](doc/ko/PROFILES-AND-RECOVERY.md) |
| GPU 그림 생성과 모델 라이선스 확인 | [창작 그림](doc/ko/CREATIVE-ART.md) |
| 소스 실행·EXE 빌드 | [설정과 빌드](doc/ko/BUILD.md) |
| 테스트 결과·현재 제한 | [검증 기록](doc/ko/VALIDATION.md) |
| 기획자·AI 기여 역할 | [기여자](doc/ko/CONTRIBUTORS.md) |
| 라이브러리·모델 라이선스 | [제3자 고지](doc/ko/THIRD-PARTY-NOTICES.md) |

**브라우저 동작:** 탐색 후 탭을 닫고, 탭 애니메이션은 작업표시줄 근처의 별도 표식에서 보여줍니다.

**검증 현황:** 제작자가 Windows 11에서 직접 사용해 확인했다고 보고했습니다. 수동 확인과 자동 검사의 상세 범위는 [검증 기록과 남은 확인 항목](doc/ko/VALIDATION.md)을 참고하세요.

| 제품 기획·관리 | AI 구현 지원 |
| --- | --- |
| [hobby-programmer-5000](https://github.com/hobby-programmer-5000) | [ChatGPT (Codex)](https://github.com/apps/chatgpt-codex-connector) |

자체 코드 [MIT](LICENSE). [역할과 GitHub 표시 제한](doc/ko/CONTRIBUTORS.md) · [전체 문서](doc/README.ko.md).
