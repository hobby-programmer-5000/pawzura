[English](../en/CONTRIBUTORS.md) | [한국어](../ko/CONTRIBUTORS.md) · [문서 목록](../README.ko.md)

# Contributors

## hobby-programmer-5000

- 프로젝트 원안과 제품 방향 제시 및 총괄 관리.
- SD 동반자, 다중 모니터 이동, 점프·깨물기·균열과 창 닫기라는 핵심 경험 정의.
- 프로그램·사이트 허용 목록, 기본 허용 앱, 트레이 메뉴, 다국어·자동 실행·캐릭터 변경 요구사항 제시.
- Hugging Face 오픈 모델, Windows 10/11, Python 3.12+, 소스 및 EXE 사용 방식, MIT와 제3자 고지 요구사항 정의.
- 0.1.1의 읽기 쉬운 양언어 문서와 브라우저 연결 개선 요구사항 제시.
- **[0.8.0 갱신] 서브컬처 라노벨 캐릭터 조형론 분석 및 2D vs 3D 질감 기반 하이브리드 리깅 아키텍처 수립:**
  - 2D 애니메이션 질감(평면 캐릭터)을 무리하게 3D화할 때 발생하는 왜곡/찌그러짐을 정확히 지적하고, 질감 특성에 따라 완전 2D는 2.5D(멀티플레인 패럴랙스 컷아웃), 음영 3D는 3D 메시 복원으로 이원화하는 하이브리드 파이프라인 제안.
  - 4단계 순차 고도화(텍스처 분류 및 팽창 → 2.5D 패럴랙스 → 파라메트릭 치비 템플릿 → 랜드마크 모핑) 로드맵 채택 및 승인.
  - 대용량 모델 다운로드 시 체감 프리징 현상 발견 및 실시간 단계별 모델명·용량(MB/GB) 투명 표시 요구.
  - SDXL 이미지 생성 시 캔버스 여백 채움으로 인한 복수 인물(2명) 발생 버그 포착 및 단일 인물(Solo) 원천 차단 요구.
- GitHub 계정과 저장소의 소유·관리, 배포 방향 및 최종 제품 판단.

GitHub: https://github.com/hobby-programmer-5000

## Antigravity (Google DeepMind)

- **[0.8.0 추가] 2.5D/3D 리깅 고도화, 실시간 다운로드 파이프라인 및 복수 인물 방지 아키텍처 엔지니어링:**
  - **4단계 리깅 고도화 구현**:
    - Phase 1: 텍스처 분류기(`classify_art_texture`: `flat_2d` vs `shaded_3d`), 2.5D 타원형 깊이 팽창(`inflate_2_5d_mesh`), 단일 시점 후면 클린필 패스(`project_multiview_colors`), 두께 보존 Taubin 스무딩, ViTPose 원위부 커프 탈출 알고리즘 구현.
    - Phase 2: 2.5D 멀티플레인 패럴랙스 컷아웃 엔진(`representation: "2.5d_parallax"`) 구현 (4개 깊이 평면, 척추 호흡 주기, 시선 팔로우스루 헤드 스웨이, 호기심 호버 틸트, 목 접합부 심리스 오버랩).
    - Phase 3 & 4: 모듈형 토폴로지 치비 파라메트릭 템플릿 메시 생성기(`generate_parametric_chibi_template`) 및 ViTPose 2D 랜드마크 기반 모핑 엔진(`morph_chibi_template_to_landmarks`) 구현.
  - **실시간 다운로드 스트리밍 & UI 투명성 개편**:
    - Ollama REST HTTP 스트리밍 API(`/api/pull`) 연동 엔진(`_pull_ollama_model`) 구현: 레이어 바이트(`bytes_completed`, `bytes_total`), 상태(`status`), 모델명(`model_name`) 실시간 수신 및 CLI 폴백 지원.
    - UI 실시간 MB/GB 용량 표시, 부드러운 진행 바 갱신, 허위 9분 대기 경고 제거(`pawzura/art_ui.py`).
    - SD 1.5/SDXL, Safety, Cutout, ViTPose 다운로드 항목별 실시간 라벨링.
  - **복수 인물 생성 원천 차단 및 비전 필터링 고도화**:
    - 프롬프트 선두에 `solo, 1person, single full-body chibi character only` 강제 주입.
    - 네거티브 프롬프트에 `2girls, 2boys, duo, pair, 2characters, multiple people, two people, twins, group, clone, companion` 보강.
    - Qwen3-VL 비전 검사기 프롬프트 강화: 밀착된 쌍둥이나 복수 인물 얼굴/머리 2개 이상 감지 시 즉시 거부하도록 개선.
  - **전체 단위 테스트(235개 전체 통과) 및 x64 단일 실행 파일(EXE) 무설치 패키징 검증.**

Antigravity는 Google DeepMind가 개발한 첨단 에이전트 인공지능 도구입니다.

## ChatGPT (Codex, OpenAI)

- 위 요구사항을 바탕으로 네이티브 Windows/Qt 구조와 로컬 브라우저 연결 프로토콜 초기 설계·구현 지원.
- 고유 벡터 SD 도형, 절차적 애니메이션, 모니터 이동, 일반 닫기 요청과 설정 UI 코드 작성.
- Qwen 기반 제한된 JSON 외형 생성, 모델 라이선스 조사, 생성 오류 처리 구현.
- Chromium/Firefox 확장, 허용 목록 검사, URL 재확인과 애니메이션 완료 후 닫기 구현.
- 단위·연결·렌더링 테스트, Windows EXE 빌드 스크립트, 원문 라이선스 수집과 기술 문서 작성 지원.

ChatGPT는 사람인 공동 관리자가 아닌 AI 도구이며 이 초기 작업은 Codex를 통해 수행했습니다.

## GitHub 기여자 및 봇 표시

README와 Git 이력으로 역할을 사실대로 표시합니다. Git 커밋 이력에 `Co-authored-by`를 통해 Antigravity와 Codex의 기여를 명시합니다. 사이드바와 기여자 패널 표시는 GitHub의 자체 집계 기준을 따릅니다. [GitHub 기여자 표시 안내](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors).
