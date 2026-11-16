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

4. **서브컬처 문학·라이트노벨·사변문학 기반 2.5D/3D 리깅 최적화 캐릭터 예시 10종 추가 (총 15종) 및 학술 연구 문서 4종 수록**
   - 아즈마 히로키의 데이터베이스 소비론(모듈형 모에 요소), 이토 고의 캐라(Kyara) 기호학, 70-20-10 시각 위계, 그리고 3D 리깅 가동성(A-포즈 팔다리 네거티브 스페이스·소매 단차·골반/무릎 노출형 짧은 상의)을 결합한 10종의 장르별 프리셋을 `창작 그림 만들기` 예시 선택기에 탑재했습니다 ([창작 그림 만들기](CREATIVE-ART.md), [3D 움직임 준비](3D-MOTION.md)):
     - **서브컬처·라이트노벨 5종:** 상태창 그림자 헌터(헌터물·LitRPG), 전략가 악역 영애(로맨스 판타지), 이세계 책공방 장인(이세계 전생물), 추방된 만능 약초사(추방·슬로우라이프), 착각계 흑막 마도학도(착각계)
     - **현대 사변·고전 환상문학 5종:** 사이버펑크 넷러너 해커(사이버펑크), 솔라펑크 태양광 수리공(솔라펑크), 은퇴 모험가 카페 바리스타(코지 판타지), 야경 오컬트 탐정(어번 판타지), 은하철도 별빛 차장(고전 환상문학)
   - 한·영 양방향 학술·이론 심층 가이드 문서 4종을 `doc/ko/` 및 `doc/en/`에 정식 수록했습니다:
     - [캐릭터 디자인 방법론과 원형 가이드](CHARACTER-DESIGN-METHODOLOGY.md)
     - [문학 장르·세계관 구축과 캐릭터 원형](LITERARY-WORLDBUILDING-AND-CHARACTERS.md)
     - [서브컬처 문학·라이트노벨 이론과 서사 구조](SUBCULTURAL-LITERATURE-AND-LIGHT-NOVELS.md)
     - [캐릭터 디자인·문학·서브컬처 통합 참고문헌](CHARACTER-AND-LITERATURE-BIBLIOGRAPHY.md)

5. **기여자 및 협력 명시**
   - 제품 기획 및 총괄 관리: `hobby-programmer-5000`
   - AI 리깅 고도화 및 엔지니어링: `Antigravity (Google DeepMind)`
   - AI 초기 구현 지원: `ChatGPT (Codex, OpenAI)`

6. **전수 15종 샌드박스 검증 및 학술 기반 측면·질감 복원 보완**
   - 외곽 다이컷 스티커 테두리 제거(`strip_diecut_sticker_border`), 2.5D 팽창 전 다중 뷰 원근 아틀라스 베이킹 + 내부 `EDT` 외삽, 창백한 정면 피부 림 보호(`~is_skin_hue`), 실루엣 돔 크라우닝(`dome_norm_map`), Half-Lambert 셀 릴리프 셰이딩을 반영해 `otter`·`villainess` 등 측면 평면화 및 얼굴·의상 2.5D 질감 왜곡을 해결했습니다.
   - 2,000자 급 다문단 한국어 창작 설명에서 `Qwen2.5-1.5B`가 줄바꿈·항목 헤더로 `art_review_prompt_invalid` 오류를 내거나 의상 특징을 놓치던 문제를 근접 색상-부위 슬롯 추출 및 단일행 ASCII 정규화([art_policy.py](../../pawzura/art_policy.py))로 보완했습니다.
   - Python 단위 테스트 **236개**, 지오메트리 프로브 **23개**, 한/영 문서 링크 점검 **123개**, 15종 전체 샌드박스 3D 리깅(`rig_3d_ok=True`, 측면 깊이비 `0.300~0.661`)을 모두 통과했습니다. 상세 논문 25편과 검증 그리드는 [3D 참고 문헌](3D-RIGGING-AND-MOTION-REFERENCES.md) 및 [검증 기록](VALIDATION.md)에서 확인할 수 있습니다:
     - [그룹 1 기본 5종 검증 그리드](../../artifacts/sandbox-v0.8.0-group1-original5.png)
     - [그룹 2 서브컬처·라노벨 5종 검증 그리드](../../artifacts/sandbox-v0.8.0-group2-subculture5.png)
     - [그룹 3 사변·고전문학 5종 검증 그리드](../../artifacts/sandbox-v0.8.0-group3-literature5.png)

Windows 단일 EXE를 내려받거나 Windows ZIP 전체를 압축 해제하세요. 업데이트 전에 기존 Pawzura를 종료하세요. [다운로드와 사용법](SINGLE-EXE.md).
