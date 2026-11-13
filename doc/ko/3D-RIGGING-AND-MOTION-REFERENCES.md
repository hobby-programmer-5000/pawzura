[English](../en/3D-RIGGING-AND-MOTION-REFERENCES.md) | [한국어](../ko/3D-RIGGING-AND-MOTION-REFERENCES.md) · [3D 움직임](3D-MOTION.md) · [모델 순차 준비](STAGED-CHARACTER-PIPELINE.md)

# 3D 복원·리깅·스타일화 동작 참고 문헌 및 구현 안내

이 문서는 **VRAM 8GB** 환경에서 Pawzura의 다중 스냅샷 2D→3D 복원, 세밀한 3D 캐릭터 리깅·스키닝, 자연스러운 스타일화 모션을 개선하기 위해 참고한 학술 논문, 오픈소스 저장소, 실무 리깅 사례, 동작·자세 데이터셋을 정리한 참고 문서입니다.

> **중요 경계:** **Pawzura 적용**으로 표시한 기법은 이 저장소의 MIT 코드(`art_runtime/`, `pawzura/`)에 직접 구현된 내용입니다. 비교를 위해 인용한 외부 모델·가중치·데이터셋은 각자의 원본 라이선스를 따르며, [카탈로그](../../art_runtime/catalog.json)와 [고지](THIRD-PARTY-NOTICES.md)에 명시되지 않은 가중치를 앱에 묶거나 자동 다운로드하지 않습니다.

---

## 1. 다중 스냅샷 2D→3D 및 저 VRAM 순차 분할 아키텍처

정면 그림 한 장만으로는 측면·후면 형상과 세부 텍스처가 부족하고, 저해상도 중간 시점만 투영하면 얼굴과 의상 디테일이 흐려집니다. 최신 연구와 오픈소스 구현은 무거운 모델을 동시에 메모리에 올리지 않고 **단계별로 분리·해제하는 순차 파이프라인**으로 수렴하고 있습니다.

| 연구 / 프로젝트 | 핵심 기법 및 단계 분리 포인트 | VRAM 및 라이선스 참고 | Pawzura 반영 여부 |
| --- | --- | --- | --- |
| **TripoSR** (Tochilkin et al., 2024) · [arXiv:2403.02151](https://arxiv.org/abs/2403.02151) | 단일 이미지에서 Triplane NeRF 장면을 바로 생성하는 고속 LRM 트랜스포머 | ~2–6GB 추론; **MIT** | **Pawzura 적용** (다중 고도 24/36 스냅샷 + Z슬라이스 `128³` 메쉬 + 1024px 원본 정면 투영으로 고도화) |
| **MV-Adapter** (Huang et al., ICCV 2025) · [arXiv:2412.03632](https://arxiv.org/abs/2412.03632) | 동결된 **SDXL**에 복제 Self-Attention·병렬 어텐션을 붙여 768px 일관된 멀티뷰 생성 | 어댑터 구조로 기본 SDXL 품질 보존; 어댑터 가중치 라이선스 별도 확인 필요 | 향후 SDXL 어댑터 확장 후보 참고 |
| **CharacterGen** (Peng et al., ACM TOG 2024) · [DOI:10.1145/3658217](https://dl.acm.org/doi/10.1145/3658217) | 임의 자세를 정규 포즈로 정렬하는 멀티뷰 확산 + 성긴 뷰 복원 + **텍스처 역투영** | 캐릭터 특화 다단계 파이프라인 | **개념 적용:** 고해상도 원본·추가 각도 이미지 법선/가시성 가중 역투영 (`project_multiview_colors`) |
| **InstantMesh** (Xu et al., 2024) · [arXiv:2404.07191](https://arxiv.org/abs/2404.07191) | 멀티뷰 확산과 LRM+FlexiCubes 메쉬 추출을 분리해 ~10초 내 메쉬 생성 | `xformers` 기준 ~8GB 구동 가능; **코드 Apache-2.0**, **Zero123++ 가중치는 CC BY-NC 4.0** | 참고용 (비상업 NC 가중치로 기본 MIT 경로 제외) |
| **Zero123++** (Shi et al., 2023) · [arXiv:2310.15110](https://arxiv.org/abs/2310.15110) | 고정 고도 6개 타일 멀티뷰를 한 번에 생성하는 확산 모델 | **코드 Apache-2.0 / 가중치 CC BY-NC 4.0** | 참고용 (NC 제한 명시) |
| **Era3D** (Li et al., 2024) · [arXiv:2405.11616](https://arxiv.org/abs/2405.11616) | 초점거리·고도 추정 + Epipolar 행 단위 어텐션(연산량 12배 절감, 512px) | 기본 실행은 보통 8GB 초과 | 에피폴라 어텐션 구조 참고 |
| **Wonder3D** (Long et al., CVPR 2024) · [IEEE:10657484](https://ieeexplore.ieee.org/document/10657484/) | 멀티뷰 컬러 + 법선 맵 동시 확산 후 법선 융합으로 메쉬 추출 | 에셋당 2–3분 | 법선 기반 표면 융합 참고 |
| **Unique3D** (Wu et al., 2024) · [arXiv:2405.20343](https://arxiv.org/abs/2405.20343) | 멀티뷰 RGB·법선 확산 + 다단계 업스케일 + ISOMER 컬러/형상 통합 복원 | 3단계 분리 구조 | 다단계 업스케일 및 텍스처 융합 참고 |
| **TripoSG** (Li et al., IEEE TPAMI 2025) · [arXiv:2502.06608](https://arxiv.org/abs/2502.06608) | SDF/법선/Eikonal 3D VAE 위에서 Rectified Flow로 3D 형상 직접 생성 | 8GB 초과 권장; **MIT** | 향후 3D 형상 생성 후보 |
| **Hunyuan3D 2.0** (Zhao et al., 2025) · [arXiv:2501.12202](https://arxiv.org/abs/2501.12202) | **Hunyuan3D-DiT**(형상)과 **Hunyuan3D-Paint**(고해상도 UV 텍스처) 완전 분리 | 형상 ~11.5GB / 통합 ~24.5GB; **Community License** | 형상·텍스처 워커 프로세스 분리 설계 참고 |
| **TRELLIS** (Xiang et al., CVPR 2025) · [IEEE:11094803](https://ieeexplore.ieee.org/document/11094803/) | 희소 3D Structured Latent(SLat)에서 가우시안·NeRF·메쉬 선택 디코딩 | 기본 16–24GB (커뮤니티 8GB 양자화); **코어 MIT** | 통합 잠재 표현 분리 참고 |
| **SF3D** (Boss et al., CVPR 2025) · [arXiv:2408.00653](https://arxiv.org/abs/2408.00653) | 빠른 UV 전개 및 조명 제거(Delighting)를 포함한 메쉬 복원 | ~0.3초 순방향 추론 | UV 베이킹 및 조명 제거 참고 |
| **TEXTure / TEXGen** (Richardson et al., 2023; Yu et al., ACM TOG 2024) · [DOI:10.1145/3588432.3591503](https://dl.acm.org/doi/10.1145/3588432.3591503) · [DOI:10.1145/3687909](https://dl.acm.org/doi/10.1145/3687909) | 기존 메쉬 위에서 시점별 깊이 조건부 페인팅 / UV 공간 확산 수행 | 형상 복원과 텍스처 보정 단계 분리 | **개념 적용:** TripoSR 종료 후 별도 워커로 실행하는 선택형 SDXL 측면/후면 저강도 보정(`refine_views`, `strength=0.28`) |
| **MVPainter / MVPaint / SyncMVD** (Shao et al., 2025 · [arXiv:2505.12635](https://arxiv.org/abs/2505.12635); Cheng et al., CVPR 2025 · [arXiv:2411.02336](https://arxiv.org/abs/2411.02336); Liu et al., SIGGRAPH Asia 2024 · [DOI:10.1145/3680528.3687621](https://dl.acm.org/doi/10.1145/3680528.3687621)) | 기하 제어 멀티뷰 확산·텍스처 도메인 동기화·3D 인페인팅 후 UV 공간 아틀라스 베이킹 및 심 스무딩 | 정점 색상 한계와 Janus/이음새 불일치 해소 | **개념 적용:** `bake_texture_atlas`(4-차트 `1280×1280` 원통형 UV 아틀라스) + 3×3 디speckle + 점진적 방향 `refine_views` 순서 |
| **RoCoTex / Paint3D / AlignTex** (Kim et al., 2024 · [arXiv:2409.19989](https://arxiv.org/abs/2409.19989); Zeng et al., CVPR 2024 · [IEEE:10657103](https://ieeexplore.ieee.org/document/10657103/); Zhang et al., ACM TOG 2025 · [DOI:10.1145/3731158](https://dl.acm.org/doi/10.1145/3731158)) | SDXL 방향별 프롬프트 + 조명 제거 2K UV 인페인팅 + 아트워크 정렬 후 텍스처 딜레이션(dilation) | SDXL 일관성 유지 및 UV 경계 블리딩 방지 | **개념 적용:** 방향별 안티-Janus 프롬프트(`±45° → ±90° → 180°`) + 차트별 유클리드 거리 변환(`EDT`) 거터 확장 |
| **DirectUV / NaTex** (Lin et al., 2026 · [arXiv:2609.34651](https://arxiv.org/abs/2609.34651); Lai et al., 2025 · [arXiv:2511.16317](https://arxiv.org/abs/2511.16317)) | 3D 좌표 기반 UV 잠재 확산(seam 일관성) 및 네이티브 3D 포인트 컬러 디퓨전 | UV 불연속성 근본 해소 | 차세대 UV/네이티브 텍스처링 확장 참고 |

### Pawzura의 8GB VRAM 순차 분할 실행 흐름

1. **1단계 (그림 생성):** SDXL 1.0이 1024×1024 정면 캐릭터를 생성하고 프로세스를 종료합니다.
2. **2단계 (다중 고도 TripoSR 스냅샷 + 4-차트 UV 아틀라스):** TripoSR 워커가 `0°`, `+22°`, `-16°` 세 고도에서 **24장 또는 36장 스냅샷(256px)**을 렌더링하고, 8개 Z-슬라이스 단위로 **`128³` 밀도 그리드**를 조회해 삼각형 메쉬를 추출합니다. 이어서 Z-버퍼 가시성·법선 정렬 가중치로 정점 색상을 투영한 뒤, **`1280×1280` 4-차트(`+X/-X/+Y/-Y`) 원통형 UV 아틀라스(`bake_texture_atlas`)**에 1024px 원본 정면 PNG와 추가 각도 PNG를 베이킹하고 `3×3` 이상치 제거와 차트별 EDT 거터 확장을 수행한 뒤 종료합니다.
3. **3단계 (선택형 순차 SDXL 멀티뷰 보정):** `sdxl_multiview` 모드 선택 시, TripoSR 종료 후 캐시된 SDXL 1.0 Img2Img 워커가 CPU 오프로드로 5개 비정면 렌더링을 점진적 순서(`left_3q → right_3q → facing_left → facing_right → back`)와 방향별 안티-Janus 프롬프트로 저강도(`strength=0.28`) 보정하며 UV 아틀라스를 재베이킹하고 종료합니다.
4. **4·5단계 (CPU 팔 분리 리깅 및 UV 2×-SSAA 베이킹):** CPU ViTPose와 메쉬 그래프 지오데식/히트 리깅이 동작하며, 몸통에 융합된 치비 소매를 겨드랑이 아래 대각 절개선으로 분리하고 Z-계층 캡으로 메워(`_detach_and_cap_limbs`) `arm_mobility`를 확보합니다. 이후 2배 슈퍼샘플링(512→256px) UV 이중선형 삼각형 래스터라이저가 투명 PNG 클립을 저장합니다.

---

## 2. 세밀한 3D 캐릭터 리깅 사례와 스키닝·변형 이론

### 실무 3D 리거의 세밀한 관절 설계 (Blender Rigify / Advanced Skeleton / VRM / SD 캐릭터 사례)

실제 3D 아티스트와 리거들은 단순 12개 막대 뼈대 대신 관절 부피 보존과 자연스러운 실루엣을 위해 다음과 같은 세부 본 구조를 공들여 구성합니다:

- **골반·다분절 척추(`pelvis -> spine_lower -> chest -> neck -> head`):** 허리와 흉부를 분리해야 보행 시 골반의 좌우 요(yaw) 회전에 맞서는 상체 역회전(Counter-rotation)이 살아나고, SD 캐릭터의 짧은 몸통이 고무처럼 꺾이는 현상을 막을 수 있습니다.
- **쇄골(`left_clavicle`, `right_clavicle`):** 흉골 끝에서 어깨까지 이어지는 쇄골 본이 없으면 손을 흔들거나 환호(`wave`, `cheer`)할 때 어깨·조끼 부분이 찌그러집니다.
- **위팔·아래팔·손목 분절 + 팔꿈치/무릎 폴 벡터(Pole Vector):** 아래팔이 위팔보다 약간 늦게 따라오는 위상 지연(Overlapping action)을 구현하고, 무릎·팔꿈치가 3D 공간에서 안쪽으로 꺾이지 않도록 전방/외측 폴 벡터로 굽힘 평면을 고정합니다.
- **리버스 풋 롤(`ankle -> ball -> toe`):** 착지 시 뒤꿈치부터 닿고(Heel-strike), 지지 중 발바닥을 바닥에 고정하며, 도약(Push-off) 시 발볼(`ball`)을 지면에 둔 채 발목만 들려 발가락이 자연스럽게 꺾이게 하여 발 미끄러짐과 딱딱한 벽돌 발을 방지합니다.
- **TMJ 턱 관절 피벗과 안면 제어:** 턱 피벗(`tmj_pivot`)을 입술 앞이 아니라 귀 아래 턱관절(TMJ) 깊숙이 배치해 자연스러운 호를 그리며 벌어지게 하고, 곡면 눈꺼풀 덮임·눈썹 움직임·시선(Gaze) 이동을 함께 제어합니다.
- **2차 동적 모션(VRM `VRMSpringBone` / PhysBones):** 머리카락 끝, 귀, 꼬리, 망토 자락 등은 머리·골반에 단단히 붙이지 않고 감쇠 스프링(Stiffness, Drag, Gravity) 체인으로 지연·탄성 흔들림을 부여합니다.

### 자동 리깅·스키닝·변형 핵심 논문

| 논문 / 기법 | 핵심 기여 | Pawzura 반영 여부 |
| --- | --- | --- |
| **Pinocchio** (Baran & Popović, SIGGRAPH 2007) · [DOI:10.1145/1275808.1276467](https://dl.acm.org/doi/10.1145/1275808.1276467) | 정적 메쉬 내부 뼈대 매립 + **Bone-Heat 확산** 가중치 계산의 원조 | **적용** (메쉬 그래프 지오데식 + Screened Laplacian 본 히트 확산) |
| **Bone Glow** (Wareham & Lasenby, 2008) · [DOI:10.1007/978-3-540-70517-8_7](https://link.springer.com/10.1007/978-3-540-70517-8_7) | 각도 가시성 기반 본 히트 개선 | **개념 적용** (오목 주름 페널티 지오데식 시드) |
| **Bounded Biharmonic Weights (BBW)** (Jacobson et al., ACM TOG 2011) · [DOI:10.1145/1964921.1964973](https://dl.acm.org/doi/10.1145/1964921.1964973) | 볼록 경계 제약 라플라시안 에너지 최소화로 부드럽고 국소화된 스킨 가중치 산출 | Screened Poisson 평활화 설계 참고 |
| **Dual Quaternion Skinning (DQS)** (Kavan et al., I3D 2007) · [DOI:10.1145/1230100.1230107](https://dl.acm.org/doi/10.1145/1230100.1230107) | 닫힌 형식의 이중 사원수 블렌딩으로 LBS의 관절 부피 붕괴·사탕 포장지(Candy-wrapper) 현상 제거 | **Pawzura 적용** (반대 반구 정렬 포함 `dual_quaternion_skinning`) |
| **Skeleton Extraction by Mesh Contraction** (Au et al., ACM TOG 2008) · [DOI:10.1145/1399504.1360643](https://dl.acm.org/doi/10.1145/1399504.1360643) | 메쉬 수축을 통한 중심선(Medial axis) 관절 배치 | **개념 적용:** 국소 전·후면 두께 중간점 배치(`lift_medial`) |
| **Pose Space Deformation (PSD)** (Lewis et al., 2000) · [DOI:10.1145/3596711.3596796](https://dl.acm.org/doi/10.1145/3596711.3596796) | 관절 각도 공간에서 보정 형태(Corrective Shape)를 RBF 보간 | 향후 관절 보정 셰이프 후보 |
| **RigNet** (Xu et al., ACM TOG 2020) · [DOI:10.1145/3386569.3392379](https://dl.acm.org/doi/10.1145/3386569.3392379) | 그래프 신경망으로 임의 메쉬의 관절 위치·계층·가중치 동시 예측 | 학술 기준선 |
| **UniRig** (Zhang et al., ACM TOG 2025) · [DOI:10.1145/3730930](https://dl.acm.org/doi/10.1145/3730930) | Skeleton Tree Tokenization 기반 대규모 자기회귀 리깅(Rig-XL); **MIT** (`>=8GB VRAM`, Linux/spconv 중심) | 향후 별도 학습형 오토-리깅 워커 후보 |
| **MagicArticulate** (Song et al., 2025) · [arXiv:2502.12135](https://arxiv.org/abs/2502.12135) | 자기회귀 관절 생성 + **체적 지오데식 거리 사전확률** 기반 스킨 가중치 확산(Articulation-XL) | 지오데식 기반 스키닝 설계 참고 |
| **Make-It-Animatable** (Guo et al., 2024) · [arXiv:2411.18197](https://arxiv.org/abs/2411.18197) | 1초 이내 관절·가중치·휴식 자세 동시 생성 | 참고 |
| **ANEEME / SkelSeg / Variational Mesh Decomposition** (Belen et al., ACM I3D 2017 · [DOI:10.1145/3023368.3036841](https://dl.acm.org/doi/10.1145/3023368.3036841); Noh et al., GI 2019 · [GI:2019-17](http://graphicsinterface.org/proceedings/gi2019/gi2019-17/); Zhang et al., ACM TOG 2012 · [DOI:10.1145/2167076.2167079](https://dl.acm.org/doi/10.1145/2167076.2167079)) | 스캔 메쉬의 융합 팔다리 절개·구멍 메움 및 경계 길이 정규화를 통한 매끄러운 파트 분할 | **Pawzura 적용** (`_detach_and_cap_limbs`: 겨드랑이 아래 대각 절개 + 2패스 인접 삼각형 다수결 경계 스무딩 + 데이터 기반 측복부 의상 분리) |
| **Taubin Boundary Fairing & Unified Mesh Fairing** (Taubin, ICCV 1995 · [IEEE:466848](http://ieeexplore.ieee.org/document/466848/); Li et al., Graphical Models 2004 · [PII:S152407030400013X](https://linkinghub.elsevier.com/retrieve/pii/S152407030400013X); Liepa, Eurographics 2003 · [SGP:2003-200](http://diglib.eg.org/handle/10.2312/SGP.SGP03.200-206)) | 수축 없는 `λ/μ` Taubin 곡선 페어링으로 인접 절단 경계 연속성을 유지한 채 계단형 톱니 제거 및 닫힌 캡 복원 | **Pawzura 적용** (`_detach_and_cap_limbs` · `_cap_cut_boundary`: 몸통/팔 공유 절개 루프 `λ=0.42/μ=-0.44` 동기 평활 + Z-계층 캡) |
| **Silhouette Risk Dilation & Boundary Matting** (Grammatikopoulos et al., 2007 · [CiteSeerX:221.8010](http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.221.8010); Hasinoff et al., 2008 · [CiteSeerX:64.2335](http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.64.2335)) | 멀티뷰 역투영 시 폐색·실루엣 경계 위험 버퍼 확장(erosion+dilation) 및 전경/배경 언믹싱으로 흰색 테두리 halo 제거 | **Pawzura 적용** (`refine_views`: VAE 전 `4px` 전경색 프린지 패딩·`3px` 전경 침식 거리 외삽·halo 스파이크 차단 + `project_multiview_colors` 스침각 무채색 실루엣 halo 억제) |
| **PartUV / OptCuts / Seamless / SCAF** (Wang et al., SIGGRAPH Asia 2025 · [DOI:10.1145/3757377.3763843](https://dl.acm.org/doi/10.1145/3757377.3763843); Li et al., ACM TOG 2018 · [DOI:10.1145/3272127.3275042](https://dl.acm.org/doi/10.1145/3272127.3275042); Liu et al., ACM TOG 2017 · [DOI:10.1145/3130800.3130897](https://dl.acm.org/doi/10.1145/3130800.3130897); Jiang et al., ACM TOG 2017 · [DOI:10.1145/3130800.3130895](https://dl.acm.org/doi/10.1145/3130800.3130895); Yang et al., ACM TOG 2023 · [DOI:10.1145/3618348](https://dl.acm.org/doi/10.1145/3618348)) | AI 복원 메쉬의 비중첩 차트 분할·shelf 빈 패킹·심 경계 블리딩 차단으로 겹침/전단사 붕괴 방지 | **Pawzura 적용** (`bake_texture_atlas` · `_peel_nonoverlapping_subcharts`: 6방향 depth-peel 비중첩 아일랜드 패킹 + `tier-0` 중심 커버 + 박스 한정 EDT 패딩) |
| **HumanRig / HoloPart / SeparateGen / LayerGS / ReEF / GarmentCrafter** (Chu et al., 2024 · [arXiv:2412.02317](https://arxiv.org/abs/2412.02317); Yang et al., 2025 · [arXiv:2504.07943](https://arxiv.org/abs/2504.07943); Chen et al., CVPR 2025 · [arXiv:2412.18608](https://arxiv.org/abs/2412.18608); Li et al., IEEE TVCG 2026 · [IEEE:11342401](https://ieeexplore.ieee.org/document/11342401/); Xu & Dingliana, 2026 · [arXiv:2601.05853](https://arxiv.org/abs/2601.05853); Zhu et al., CVPR 2022 · [IEEE:9879766](https://ieeexplore.ieee.org/document/9879766/); Wang et al., 3DV 2026 · [arXiv:2503.08678](https://arxiv.org/abs/2503.08678)) | 단안 의상/신체 분리, 폐색 소매 내부 기하·소켓 은면 복원 및 정규 자세 리깅 | **Pawzura 부분 적용** (`_detach_and_cap_limbs` · `_cap_cut_boundary`: 원통 소매 체적 보존 + 손목 캡슐 가드 + 안쪽 후퇴 동심 림-링 소켓 캡) |
| **PhysRig** (Zhang et al., ICCV 2025) · [arXiv:2506.20936](https://arxiv.org/abs/2506.20936) | 연속체 역학 기반 미분 가능 탄성 스키닝 | 연조직 부피 보존 참고 |
| **Neural Face Rigging / MANO / NIMBLE** (Qin et al., 2023; Romero et al., 2017; Li et al., 2022) | FACS 얼굴 제어 및 해부학적 손 모델 | 안면·손 세분화 참고 |
| **Neural Emulator for Secondary Motion** (Zheng et al., CVPR 2021) · [IEEE:9577713](https://ieeexplore.ieee.org/document/9577713/) | 물리 시뮬레이션보다 30배 이상 빠른 패치 기반 2차 모션 ODE 근사 | VRM SpringBone 시뮬레이션과 함께 참고 |

---

## 3. 3D 동작·자세 데이터셋, 리타게팅 및 발 미끄러짐 보정

| 자료 / 논문 | 구성 및 포맷 | 라이선스·사용 주의 | Pawzura 활용 |
| --- | --- | --- | --- |
| **AMASS** (Mahmood et al., ICCV 2019) · [IEEE:9009460](https://ieeexplore.ieee.org/document/9009460/) | 15개 모션캡처를 SMPL로 통합한 40시간+ 11,000+ 모션 아카이브 | 구성 데이터셋별 약관 적용 | 표준 인체 모션 사전 데이터 |
| **100STYLE** (Mason et al., PACMCGIT 2022) · [DOI:10.1145/3522618](https://dl.acm.org/doi/10.1145/3522618) | 100가지 감정·성격 스타일 보행·주행·대기 400만+ 프레임 (**BVH** + 로컬 위상) | 공개 연구 데이터셋(재배포 약관 별도 확인) | 스타일화 보행 설계 및 `motion_library.parse_bvh` / `retarget_bvh` 입력 호환 |
| **Bandai Namco Motion Dataset** · [GitHub](https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset) | 전문 배우의 17개 행동·15개 감정 스타일 36,673개 **BVH** 파일 | **CC BY-NC-ND** (비상업·변경금지) | 동작/감정 분류 참고 (상용·MIT 번들링 제외) |
| **HumanML3D / HumanAct12** (Guo, 2022/2024) · [Scholaris:82827](https://ualberta.scholaris.ca/handle/123456789/82827) | 14,616개 모션과 44,970개 텍스트 설명 | 연구 벤치마크 | 텍스트-투-모션 참고 |
| **MMDMC** (Wang et al., 2024) · [arXiv:2407.11266](https://arxiv.org/abs/2407.11266) | MMD 애니메이션 캐릭터와 의상·신체 분리 모션 전이 | 연구 | 치마·머리카락·신체 분리 참고 |
| **RoMo** (Zhang et al., 2026) · [arXiv:2605.26241](https://arxiv.org/abs/2605.26241) | 계층 분류체계와 표준 평가 툴박스를 갖춘 대규모 모션 집합 | 연구 | 참고 |
| **Spacetime Constraints / Skeleton-Aware / R2ET / SAME** (Gleicher 1998; Aberman 2020; Zhang 2023; Lee 2023) | 체형이 다른 뼈대 간 충돌·관통 없는 모션 리타게팅 | 학술 기법 | 팔 외전(abduction) 여유각 및 비율 정규화 반영 |
| **Geometry Scaling Retargeting** (Yang, 2002; Körner et al., 2025) · [GI:48110](https://dl.gi.de/handle/20.500.12116/48110) | 팔다리 길이 비율로 루트·말단 궤적을 스케일링하고 IK 적용 | 비율 적응형 리타게팅 | **Pawzura 적용** (`extract_proportions`, `retarget_bvh`) |
| **Footskate Cleanup** (Kovar et al., SCA 2002; Ikemoto et al., 2006) · [DOI:10.1145/545261.545277](https://dl.acm.org/doi/10.1145/545261.545277) | 지면에 닿은 지지 발 위치를 고정하고 IK로 다리를 맞춰 미끄러짐 제거 | 해석적 보정 알고리즘 | **Pawzura 적용** (`reverse_foot_targets` 지면 고정 + `retarget_bvh(lock_feet=True)`) |

---

## 4. Pawzura 코드베이스에 실제 적용한 개선 내역

- **`art_runtime/three_d.py`:** 기존 수평 8장(192px)과 `96³` 그리드를 **3단 고도 24~36장 스냅샷(256px)**, **8-슬라이스 `128³` Marching Tetrahedra + Taubin 트라이플레인 요철 페어링(`fair_mesh_taubin`)**, **1024px 원본 정면·추가 각도 역투영**, **6방향 depth-peel 비중첩 `1280×1280` UV 아틀라스(`surface.npz` 내 `atlas`/`face_uvs`)**, 선택형 **점진적 방향·안티-Janus 프롬프트 + VAE 전 `4px` 전경색 프린지·`3px` 침식 거리 외삽·halo 스파이크 억제 + UV 일치 가드·저장된 기본 8시점(`view-0..7.png`) 융합 기반 SDXL 보정(`refine_views`)**, **여유 VRAM 부족 시 자동 `sequential_cpu_offload` 폴백 및 CUDA 캐시 해제**, 그리고 **목 잘록점 기반 2패스 `ViTPose` 크롭 및 팔 분리 메타데이터(`detached_limbs`, `arm_mobility`) 저장**으로 확장했습니다.
- **`art_runtime/motion_geometry.py`:** 정점 법선, **체적 보존 Taubin 메쉬 페어링(`fair_mesh_taubin`)**, **적응형 고해상도 3×3 연속 Z-버퍼 가시성(`_visibility_mask`)** 및 `a_sample > 0.94`·스침각 무채색 림 억제·후두부/부츠/바닥 고립 흰 점 정리 기반 멀티뷰 색상 융합(`project_multiview_colors`), **6방향 depth-peel 비중첩 아일랜드 패킹 + 이진 탐색 shelf 배치 + `tier-0` 중심 스플랫 + 서브차트 내부 EDT 거터 패딩 기반 `1280×1280` UV 아틀라스 베이킹(`bake_texture_atlas`, `_peel_nonoverlapping_subcharts`, `_rasterize_subchart_uv`)**, **데이터 기반 측복부 의상·원통형 소매 체적 보존 + 손목 캡슐 가드 + 3패스 다수결 경계 정리 + 수축 없는 Taubin(`λ/μ`) 동기 절개 루프 평활 + 안쪽 후퇴 동심 림-링 수밀 캡 메움(`_detach_and_cap_limbs`, `_cap_cut_boundary`)**, 국소 전·후면 두께 중심 관절 배치(`lift_medial`), **치비 목 경계·측면 팔 윤곽 보정(`_find_neck_pinch`, `_refine_chibi_joints`)**, **22개+ 관절 + `arm_mobility` + 보조 스프링 본(`fit_articulated`)**, **메쉬 그래프 지오데식 본 히트 스키닝(`_geodesic_heat_weights`)**, **듀얼 쿼터니언 스키닝(`dual_quaternion_skinning`)**을 구현했습니다.
- **`art_runtime/motion_library.py`:** 캐릭터 비율 측정에 따른 보폭·무릎 굽힘 자동 스케일링, 골반 이중 주파수 상하 바운스·좌우 체중 이동·흉부 역회전·쇄골 상승·정면 `+X` 힌지 기반 자연스러운 손 흔들기·환호(`wave`, `cheer`)와 위상 지연 팔 스윙·**리버스 풋 롤(`reverse_foot_targets`)**, **감쇠 스프링 본 시뮬레이터(`simulate_spring_chains`)**, 그리고 **BVH 파서 및 IK 리타게터(`parse_bvh`, `retarget_bvh`)**를 추가했습니다.
- **`art_runtime/motion_bake.py` · `scripts/build.py` · `tests/`:** **2× 슈퍼샘플링(512→256px) UV 이중선형 삼각형 래스터라이저(`render_mesh`, `-0.5` 텍셀 중심 정렬)**와 TMJ 턱/눈꺼풀 제어를 적용했고(`triposr-pose-v2`), `scripts/build.py` 배포 스크립트에 `motion_library.py`를 포함해 패키징 누락 방지 검증·실제 PyInstaller `--onedir`/`--onefile` EXE 빌드 및 `--smoke-check`, 라이브 Windows `native_probe.py`, 그리고 오프스크린 Qt `Pet` 클릭·드래그 고정·호버·깨물기 및 가상 mixed-DPI 모니터 경계 E2E 테스트(`test_mixed_dpi_screen_crossing_keeps_logical_size_and_v2_motion`)를 추가했습니다.
