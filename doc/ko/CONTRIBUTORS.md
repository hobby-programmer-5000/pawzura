[English](../en/CONTRIBUTORS.md) | [한국어](../ko/CONTRIBUTORS.md) · [문서 목록](../README.ko.md)

# Contributors

## hobby-programmer-5000

- 프로젝트 원안과 제품 방향 제시.
- SD 동반자, 다중 모니터 이동, 점프·깨물기·균열과 창 닫기라는 핵심 경험 정의.
- 프로그램·사이트 허용 목록, 기본 허용 앱, 트레이 메뉴, 다국어·자동 실행·캐릭터 변경 요구사항 제시.
- Hugging Face 오픈 모델, Windows 10/11, Python 3.12+, 소스 및 EXE 사용 방식, MIT와 제3자 고지 요구사항 정의.
- GitHub 계정과 private 저장소의 소유·관리, 배포 방향 및 최종 제품 판단.

GitHub: https://github.com/hobby-programmer-5000

- 0.1.1의 읽기 쉬운 양언어 문서와 브라우저 연결 개선 요구사항 제시.

## ChatGPT (Codex, OpenAI)

- 위 요구사항을 바탕으로 네이티브 Windows/Qt 구조와 로컬 브라우저 연결 프로토콜 설계·구현 지원.
- 고유 벡터 SD 도형, 절차적 애니메이션, 모니터 이동, 일반 닫기 요청과 설정 UI 코드 작성.
- Qwen 기반 제한된 JSON 외형 생성, 모델 라이선스 조사, 생성 오류 처리 구현.
- Chromium/Firefox 확장, 허용 목록 검사, URL 재확인과 애니메이션 완료 후 닫기 구현.
- 단위·연결·렌더링 테스트, Windows EXE 빌드 스크립트, 원문 라이선스 수집과 기술 문서 작성 지원.

ChatGPT는 사람인 공동 관리자가 아닌 AI 도구이며 이 작업은 Codex를 통해 수행했습니다. OpenAI의 제품 보증·공식 후원 또는 별도 사람이 수행한 독립 검토를 뜻하지 않습니다. 문서 작성은 검증되지 않은 호환성을 검증 완료로 간주하지 않습니다.

## GitHub 오른쪽 Contributors 표시

README에 두 역할을 직접 표시하고 AI 지원은 실제 [Codex Connector GitHub App](https://github.com/apps/chatgpt-codex-connector)으로 연결했습니다. ChatGPT는 별도의 사람 GitHub 계정이 아닙니다. App bot에 일반 사용자 프로필·hovercard 주소를 적용하면 실패할 수 있으므로 App 링크를 사용합니다.

2026-11-02 확인한 저장소 contributors REST 응답에는 **hobby-programmer-5000**(`User`)와 **chatgpt-codex-connector[bot]**(`Bot`)가 모두 있었습니다. 확인한 AI 구현 커밋도 공개 no-reply 저자 신원을 통해 해당 bot 계정에 연결돼 있었습니다. 이는 기여 기록의 확인이며 모든 GitHub 화면에서 같은 방식으로 표시된다는 뜻은 아닙니다.

제작자의 스크린샷에서는 오른쪽 패널에 사람 계정만 보였습니다. 앞서 단순 집계 지연처럼 설명한 것은 입증되지 않았습니다. 사이드바·hovercard는 GitHub가 관리하므로 프로젝트 Markdown으로 두 번째 항목을 넣거나 App bot 표시를 보장할 수 없습니다. 요청한 기본 사이드바의 두 항목 표시는 아직 해결되지 않았습니다. 이를 위해 이력을 재작성하거나 사람 계정을 꾸미거나 OpenAI 계정 소유권을 주장하지 않습니다.

README와 Git 이력으로 두 역할을 사실대로 표시합니다. [GitHub 기여자 표시 안내](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors), [contributors REST 경로](https://api.github.com/repos/hobby-programmer-5000/pawzura/contributors)(비공개 저장소 권한 필요).
