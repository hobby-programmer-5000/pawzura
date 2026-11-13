[English](../en/RELEASE-v0.8.0.md) | [한국어](../ko/RELEASE-v0.8.0.md)

# 0.8.0

**2.5D/3D 하이브리드 리깅 고도화, 실시간 다운로드 스트리밍 및 단일 캐릭터 보호가 적용되었습니다.**

## 주요 변경 사항

1. **2.5D/3D 하이브리드 리깅 고도화**
   - 2D 애니메이션 질감(평면 캐릭터)을 무리하게 3D화할 때 발생하는 왜곡을 해결하기 위해, 질감 분석(`classify_art_texture`)에 따라 완전 평면 캐릭터는 **2.5D 멀티플레인 패럴랙스 컷아웃(4-layer depth planes, 척추 호흡 주기, 시선 팔로우스루 헤드 스웨이, 호기심 호버 틸트, 목 접합부 심리스 오버랩)**으로 표현하고, 음영 3D 마스코트는 3D 메시 복원으로 표현하는 하이브리드 파이프라인을 구축했습니다.
   - 2.5D 타원형 깊이 팽창(`inflate_2_5d_mesh`), 단일 시점 후면 클린필 패스(`project_multiview_colors`), 두께 보존 Taubin 스무딩 및 ViTPose 원위부 커프 탈출 알고리즘을 적용했습니다.
   - 파라메트릭 치비 템플릿 메시 생성기 및 2D 관절 랜드마크 모핑 엔진을 탑재했습니다.

2. **실시간 다운로드 진행 스트리밍 & UI 투명성 개편**
   - 로컬 Ollama HTTP 스트리밍 API(`/api/pull`)와 직접 연동하여 모델별 실시간 다운로드 용량(MB / GB), 진행률(%), 세부 단계(매니페스트 확인, 다운로드, 체크섬 검증, 완료)를 실시간 표시합니다.
   - 장시간 모델 다운로드 중 발생하던 `진행 보고 없이 대기 중` 허위 경고를 제거하고 부드러운 진행 바 갱신을 지원합니다.
   - SD 1.5/SDXL, Safety Checker, u2netp Cutout, ViTPose 등 Hugging Face 모델도 항목별 이름과 단계가 명확하게 표시됩니다.

3. **복수 인물 생성 원천 차단 & 비전 검사 강화**
   - 캔버스 여백으로 인해 2명(쌍둥이/동반자)이 생성되는 현상을 방지하도록 프롬프트 맨 앞에 `solo, 1person, single full-body chibi character only`를 최우선 주입하고, 부정 프롬프트에 `2girls, 2boys, duo, pair, 2characters, multiple people, two people, twins, group, clone, companion`을 대폭 보강했습니다.
   - Qwen3-VL 비전 검사기 프롬프트를 강화하여 밀착된 쌍둥이나 복수 인물 얼굴이 감지되면 즉시 다중 인물로 판정하여 제외합니다.

4. **기여자 및 협력 명시**
   - 제품 기획 및 총괄 관리: `hobby-programmer-5000`
   - AI 리깅 고도화 및 엔지니어링: `Antigravity (Google DeepMind)`
   - AI 초기 구현 지원: `ChatGPT (Codex, OpenAI)`

Windows 단일 EXE를 내려받거나 Windows ZIP 전체를 압축 해제하세요. 업데이트 전에 기존 Pawzura를 종료하세요. [다운로드와 사용법](SINGLE-EXE.md).
