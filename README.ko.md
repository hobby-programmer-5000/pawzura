# Pawzura · 파우주라

[English](README.md) | **한국어**

Windows 작업표시줄 위를 걷고, 선택적으로 켜는 프로그램·사이트 허용 목록으로 집중을 돕는 작은 SD 캐릭터 앱입니다.

Windows 10 (1809+) / Windows 11 · x64 · 소스 실행 Python 3.12–3.15 · MIT

## 바로 시작

1. [Releases](https://github.com/hobby-programmer-5000/pawzura/releases)에서 최신 **Windows ZIP**을 내려받으세요.
2. **ZIP 전체를 압축 해제**하고 `Pawzura` 폴더의 **Pawzura.exe**를 실행하세요. `_internal` 폴더를 함께 두세요. Python·모델 설치는 필요 없습니다.
3. **General → Preview bite animation**으로 체험하세요. 처음에는 **감시 OFF·미리보기 ON**입니다.

앱 기본 언어는 영어입니다. **General → Language → 한국어 → Save settings**로 바꾸세요. 소스로 쓰려면 빌드 대신 **run.bat**를 더블 클릭하세요.

## 주요 기능

- 바꿀 수 있는 고유 캐릭터가 연결된 모니터 사이를 산책합니다.
- 미허용 창을 닫기 전에 점프·깨물기·사라지는 균열을 표시합니다.
- 브라우저 창을 보호하고 미허용 탭만 닫습니다. 확장에서 자동 연결 후 앱에서 승인하면 됩니다.
- 선택적으로 Ollama와 Hugging Face Qwen을 사용해 캐릭터 외형을 설계합니다.

## 필요한 안내 찾기

| 할 일 | 문서 |
| --- | --- |
| 실행·한국어 변경·트레이 사용 | [처음 사용하기](doc/ko/GETTING_STARTED.md) |
| Chrome/Edge/Firefox 연결과 입력 예시 | [브라우저 연결](doc/ko/BROWSERS.md) |
| Qwen 캐릭터 생성 | [모델과 캐릭터](doc/ko/MODELS.md) |
| 소스 실행·EXE 빌드 | [설정과 빌드](doc/ko/BUILD.md) |
| 테스트 결과·현재 제한 | [검증 기록](doc/ko/VALIDATION.md) |
| 기획자·AI 기여 역할 | [기여자](doc/ko/CONTRIBUTORS.md) |
| 라이브러리·모델 라이선스 | [제3자 고지](doc/ko/THIRD-PARTY-NOTICES.md) |

**Preview 제한:** 탐색 후 탭을 닫고, 탭 X 위치는 추정 표시입니다. Windows 11 실기기와 실제 브라우저 전체 동작 검증은 남아 있습니다. 상세 범위는 검증 기록을 참고하세요.

자체 코드 [MIT](LICENSE). 기획: [hobby-programmer-5000](https://github.com/hobby-programmer-5000). 구현 지원: ChatGPT via Codex. [전체 문서](doc/README.ko.md).
