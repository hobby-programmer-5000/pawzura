"""Explicit setup and original-artwork flow, independent of vector trait controls."""
import time
import threading
from PySide6.QtCore import QThread, Signal, Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget, QLayout, QProgressBar, QSizePolicy)
from .art_client import TIERS, catalog, generate_artwork, prepare_artwork, source_dir
from .characters import GenerationError, MAX_PROMPT
from .art_policy import review_error_info
from .config import default_character, safe_character
from .pet import CharacterPreview

TEXT = {
    "en": {
        "title": "Creative artwork · optional GPU mode",
        "motion_cleanup_failed": "Worker release could not be verified. Restart Pawzura before preparing another model. Your previous character is retained.",
        "motion_missing": "The saved 3D motion pack is missing or corrupt; the original 2D artwork is shown. Prepare motion again or return to the original.",
        "motion_mouth": "3D frames contain their own mouth anchors. To adjust the original bite point, return to 2D, click the mouth, then prepare again.",
        "motion_3d": "Prepare 3D motion · 8 GB · pose-assisted",
        "motion_help": "Experimental: first use downloads ~1.7 GB of MIT TripoSR weights and small runtime libraries. One shared 3D reconstruction provides consistent views, then a separate CPU ViTPose stage estimates humanoid joints and computed skin weights. This is pose-assisted rigging, not UniRig; unusual anatomy may fail. Each worker exits before the next. Inspect the views, limbs, face and bite before using the result.",
        "motion_view": "Preview motion", "motion_original": "Return to original 2D artwork",
        "motion_cancel": "Cancel preparation", "motion_stopping": "Stopping this preparation worker… your previous character is retained.",
        "motion_done": "Pose-assisted 3D clips prepared. Inspect each preview, then Use this character → Save settings. Facial corrections are procedural; quality is not guaranteed.",
        "motion_downloading": "Preparing pinned 3D/pose models · {completed}/{total}",
        "motion_reconstructing": "Reconstructing one 3D scene locally…",
        "motion_views": "Rendering consistent reference views · {completed}/{total}",
        "motion_rigging": "Previous GPU worker exited. Estimating joints and skin weights on CPU…",
        "motion_baking": "Rig worker exited. Baking transparent motion frames · {completed}/{total}",
        "motion_validating": "Checking source identity, frame checksums and mouth anchors…",
        "motion_cached": "Reusing a verified completed stage…",
        "motion_gpu_required": "This experimental path requires an NVIDIA CUDA GPU with at least 8 GB VRAM. The prior character is retained.",
        "motion_not_prepared": "The optional 3D runtime/source is missing or corrupt. Run preparation again; verified stages and your character are retained.",
        "motion_download_failed": "A pinned model/source download failed verification. Check internet/disk space and retry preparation. No character was replaced.",
        "motion_reconstruction_failed": "A usable 3D scene could not be reconstructed. Try a clear single full-body character with separated limbs.",
        "motion_pose_uncertain": "Humanoid joints or skin weights could not be fitted reliably. Use the original 2D artwork or try a clearer front-facing design. This path does not support arbitrary anatomy.",
        "motion_runtime_failed": "3D preparation failed. Your previous character is retained. Check available memory/runtime setup and retry; verified stages are reused.",
        "motion_source_missing": "The approved source image is missing or changed. Restore it or generate a new character.",
        "art_model_busy": "Another model preparation is still running or releasing its worker. Wait for it to finish, then retry.",
        "art_cancelled": "Preparation cancelled. Your previous character and verified stages are retained.",
        "intro": "Generate an actual image with a different silhouette, hair, clothes and materials. This is separate from the Qwen trait designer. NVIDIA CUDA is required; capacity is a guide, not a guarantee.",
        "tier": "GPU VRAM guide",
        "license": "Model: {repo}\n{license} · image download {download}, plus ~3.9 GB review/motion models and ~4 GB runtime. Allow 25 GB disk space; system RAM 16 GB minimum / 32 GB recommended for SDXL.\n{size} px · CPU offload: {offload}. 2/6 GB guides are especially slow. Other running models also use VRAM.",
        "read": 'Before using this advanced model, read its <a href="{url}">original license and use restrictions</a>. App code is MIT; model weights are not MIT or OSI-approved open source. No weights are bundled. Commercial use remains subject to the model license; this is not legal clearance for an output.',
        "agree": "I have reviewed the selected model's license and will request only original, family-friendly characters.",
        "prepare": "1. Prepare runtime and selected models (large download)",
        "setup": "Install/start Ollama first. Preparation installs an isolated Python 3.12/CUDA runtime and downloads the selected image model, CPU safety/cutout/joint models, Qwen2.5 1.5B and Qwen3-VL 2B. Internet is needed for setup; descriptions and images stay local. No administrator rights or global PATH change needed. Retry Preparation after a failed download.",
        "prompt": "2. Describe an original character (required, at most 2,000 characters)",
        "example": "Original chibi astronomer, front view, full body standing, both hands clearly visible beside the hips, two separate copper boots. Short turquoise hair, cream shirt, navy vest, crescent brooch. Friendly watercolor illustration, white background.",
        "examples": "Motion-friendly drawing examples",
        "example_astronomer": "Chibi astronomer",
        "example_courier": "Woodland courier",
        "example_gardener": "Clockwork gardener",
        "example_mechanic": "Cloud mechanic",
        "mechanic_prompt": 'One original chibi cloud-station mechanic, full-body front view, standing upright in the center. Oversized rounded head, short fluffy ivory curls, dark expressive eyes, lavender eyebrows and a small clearly visible smiling mouth. A saffron cropped vest over a cream long-sleeved shirt, muted plum trousers and two chunky turquoise ankle boots. Two arms slightly away from the torso, both elbows and wrists visible, empty open hands separated from the vest. Two distinct legs with a clear gap between the boots; visible knees and ankles. One small mint hexagonal fabric patch stitched at the center of the chest, no logo. Friendly clean painted illustration with simple rounded volumes and readable facial features. The whole figure including hair, hands and soles fits inside the image with generous white margins. Plain white background. Only one character, no held tools, hat, bag, floating objects, pedestal, text or additional views.',
        "courier_prompt": "Original chibi woodland courier, front view, entire body visible with space around it. Two arms relaxed beside the body, both hands visible and separated from the jacket. Two separate short legs and clearly visible boots. Apricot jacket, teal trousers, small leaf-shaped collar pin, short chestnut hair, expressive eyes and a small friendly mouth. Clean soft illustration, plain white background.",
        "gardener_prompt": "Original chibi clockwork gardener, front view, complete body standing upright. Two separate arms and hands beside the torso, two distinct legs and boots. Rounded brass face with visible eyes and a small expressive mouth, moss-green overalls, cream sleeves, short copper hair, a tiny flower-shaped pocket decoration. Friendly painted illustration with a clear silhouette and plain white background.",
        "example_help": "Choose an example, then Insert example. Visible, separated hands and feet help 2D motion and experimental pose-assisted 3D preparation. You can edit the text; generated results vary.",
        "sample": "Insert example", "generate": "Generate artwork", "use": "Use this character", "close": "Close", "guide": "Open detailed setup/license guide",
        "limits": "NSFW and recognizable character/logo replication requests are prohibited. Local prompt review, an image classifier and vision review must all pass. Checks can miss content or reject safe requests; they do not guarantee copyright clearance. Inspect the result before using or publishing it. The 2D editor moves cutout limbs. Optional pose-assisted 3D preparation below infers hidden geometry; inspect its directional clips. Neither route is learned AI video. Trait options cannot repaint this bitmap.",
        "ready": "Ready. Enter an original description and generate. Review may take several minutes; SDXL generation can take much longer on a laptop.",
        "done": "Artwork passed local checks. Inspect it, then Use this character → Save settings in the main window.",
        "mouth": "Click the mouth in the preview to adjust the bite point (cross). The automatic estimate can be inaccurate.",
        "motion": "Edit hand/foot motion…",
        "done_no_motion": "Artwork passed content checks. A reliable limb rig was not found. Open Edit hand/foot motion to prepare the helper or adjust the four areas manually before applying.",
        "art_rigging": "Estimating editable hand/foot motion on the CPU…",
        "art_pose_downloading": "Downloading the CPU joint-estimation model…",
        "art_pose_unavailable": "The CPU motion helper is unavailable or uncertain. Prepare it in the motion editor or adjust the limb areas manually.",
        "art_installing": "Preparing isolated image runtime… first setup can take tens of minutes.",
        "art_downloading": "Downloading selected image, safety and cutout models… keep this window open.",
        "art_review_models": "Downloading local Ollama review models… keep Ollama running.",
        "art_reviewing": "Reviewing your description locally…",
        "art_summarizing": "Summarizing the approved visual description in English…",
        "art_drawing": "Drawing artwork locally… keep this window open. CPU offload may be slow.",
        "art_loading": "Loading image libraries and model weights…",
        "art_sampling": "Drawing image · step {completed}/{total}",
        "art_decoding": "Decoding the image…",
        "art_scanning": "Checking image safety on the CPU…",
        "art_cutting": "Removing the background on the CPU…",
        "progress_download": "Downloading model groups · {completed}/{total} complete",
        "progress_review_download": "Downloading Ollama review models · {completed}/{total} complete",
        "art_runtime_tool": "Preparing the runtime bootstrap tool…",
        "art_runtime_python": "Preparing isolated Python…",
        "art_runtime_torch": "Downloading/installing PyTorch and CUDA…",
        "art_runtime_packages": "Downloading/installing image libraries…",
        "art_runtime_notices": "Recording installed library licenses…",
        "progress_time": "Elapsed {elapsed} · this stage {stage} · last progress report {quiet} ago",
        "progress_wait": "Still waiting; no progress report for {quiet}. Loading, CPU offload or review can be slow. This alone does not confirm a hang; remaining time is unknown.",
        "progress_complete": "Completed", "progress_stopped": "Stopped",
        "art_timed_out": "Stopped waiting after the time limit. Your previous character is retained. A local review or installer child may still finish in the background. Check Ollama, memory and your connection before retrying.",
        "art_checking": "Reviewing image content locally before saving or displaying it…",
        "busy": "Wait for the current operation to finish before closing. Your current character is retained.",
        "art_description_required": "Enter a description of 1–2,000 characters.",
        "art_prompt_blocked": "The description was rejected by the originality/content check. Use a generic original design without existing characters, logos or sexual/violent details. Avoid restricted terms even in negative instructions.",
        "art_policy_unavailable": "The local review failed or returned invalid data. Keep Ollama running and run Preparation to install both review models. No unchecked artwork was applied.",
        "review_prompt": "Description review", "review_image": "Image review",
        "review_missing": "This exact review model is missing. Run Preparation, or run {command} in PowerShell and wait for success. Your previous character is retained.",
        "review_unreachable": "Cannot reach local Ollama. Start Ollama and retry. Reinstalling the image runtime is unnecessary for a connection failure.",
        "review_timeout": "Ollama did not complete this review in time. Wait for other model work to finish, free memory or shorten the description, then retry. Your previous character is retained.",
        "review_memory": "Ollama reported insufficient memory for this review model. Close other model/GPU workloads and retry. Image-model VRAM selection does not change the review model.",
        "review_service": "Ollama rejected this review request. Update Ollama and check the named model with ollama list, then retry. No unchecked artwork was applied.",
        "review_invalid": "The review returned an invalid structured answer. Retry with the core visual features; update Ollama if it repeats. Do not edit JSON. Your previous character is retained.",
        "review_incomplete": "The review response was cut short before completion. Retry with a shorter description containing the main visual features. This is a response-limit error, not proof that a model is missing. Your previous character is retained.",
        "art_output_blocked": "The image did not pass local safety/originality review. Try a clearer original, family-friendly design. Your previous character is retained.",
        "art_multiple_characters": "The picture appears to contain multiple figures or large separate shapes. It was not applied. Request one centered full-body character standing alone on white, then generate again. Your previous character is retained.",
        "art_not_prepared": "Run Preparation first. The optional image runtime is missing.",
        "art_download_failed": "A model download failed after a bounded retry. Check internet and disk space, then run Preparation again; completed files are reused. No character was replaced.",
        "art_gpu_required": "A supported NVIDIA CUDA GPU is required for this optional mode. Update its driver or use the lightweight trait designer.",
        "art_cutout_failed": "The character could not be separated from its background. Request one full-body character on a plain white background and retry.",
        "art_runtime_failed": "Image runtime/setup failed or timed out. Check your connection, disk space, NVIDIA driver and Ollama installation, then retry Preparation. Use the smaller 2/4 GB guide if needed; see the Creative artwork guide for diagnosis.",
        "model_memory_error": "Not enough memory. Close other GPU workloads or choose a lower guide. SDXL also needs substantial system RAM. Your previous character is retained.",
    },
    "ko": {
        "title": "창작 그림 · 선택형 GPU 모드",
        "motion_cleanup_failed": "실행 프로세스 종료를 확인하지 못했습니다. 다른 모델을 준비하기 전에 Pawzura를 다시 시작하세요. 이전 캐릭터는 유지됩니다.",
        "motion_missing": "저장한 3D 동작 파일이 없거나 손상되어 원본 2D 그림을 표시합니다. 동작을 다시 준비하거나 원본으로 돌아가세요.",
        "motion_mouth": "3D 프레임에는 자체 입 좌표가 있습니다. 원본 깨물기 위치는 2D로 돌아가 입을 클릭한 뒤 다시 준비해 변경하세요.",
        "motion_3d": "3D 움직임 준비 · 8GB · 포즈 추정 보조",
        "motion_help": "실험 기능: 처음 사용할 때 MIT TripoSR 가중치 약 1.7GB와 작은 실행 라이브러리를 받습니다. 하나의 3D 복원 결과에서 일관된 시점을 만들고, 별도 CPU ViTPose 단계에서 사람형 관절과 스킨 가중치를 계산합니다. UniRig가 아닌 포즈 추정 보조 리깅이며 특이한 신체는 실패할 수 있습니다. 각 작업 프로세스를 종료한 뒤 다음 단계를 시작합니다. 시점·팔다리·얼굴·깨물기를 확인한 뒤 사용하세요.",
        "motion_view": "움직임 미리보기", "motion_original": "원래 2D 그림으로 돌아가기",
        "motion_cancel": "준비 취소", "motion_stopping": "이 준비 작업을 종료하고 있습니다… 이전 캐릭터는 유지됩니다.",
        "motion_done": "포즈 추정 보조 3D 클립을 준비했습니다. 각 미리보기 확인 → 이 캐릭터 사용 → 설정 저장을 누르세요. 표정은 절차적 보정이며 품질을 보장하지 않습니다.",
        "motion_downloading": "고정된 3D·포즈 모델 준비 · {completed}/{total}",
        "motion_reconstructing": "로컬에서 하나의 3D 장면을 복원하고 있습니다…",
        "motion_views": "일관된 참고 시점 렌더링 · {completed}/{total}",
        "motion_rigging": "이전 GPU 작업을 종료했습니다. CPU에서 관절·스킨 가중치를 추정합니다…",
        "motion_baking": "리깅 작업을 종료했습니다. 투명 동작 프레임 저장 · {completed}/{total}",
        "motion_validating": "원본 일치·프레임 체크섬·입 접촉점을 검사하고 있습니다…",
        "motion_cached": "검증한 완료 단계를 재사용하고 있습니다…",
        "motion_gpu_required": "이 실험 경로는 VRAM 8GB 이상 NVIDIA CUDA GPU가 필요합니다. 이전 캐릭터는 유지됩니다.",
        "motion_not_prepared": "선택형 3D 실행환경·소스가 없거나 손상됐습니다. 준비를 다시 실행하세요. 검증한 단계와 기존 캐릭터는 유지됩니다.",
        "motion_download_failed": "고정 모델·소스 다운로드 검증에 실패했습니다. 인터넷·디스크를 확인하고 다시 준비하세요. 캐릭터는 교체하지 않았습니다.",
        "motion_reconstruction_failed": "사용할 3D 장면을 복원하지 못했습니다. 손발이 분리된 명확한 전신 캐릭터 하나로 다시 시도하세요.",
        "motion_pose_uncertain": "사람형 관절·스킨 가중치를 확실하게 맞추지 못했습니다. 원래 2D 그림을 사용하거나 더 명확한 정면 디자인으로 시도하세요. 임의의 신체 구조를 지원하는 경로는 아닙니다.",
        "motion_runtime_failed": "3D 준비에 실패했습니다. 이전 캐릭터는 유지됩니다. 가용 메모리·실행환경을 확인해 재시도하면 검증한 단계는 재사용합니다.",
        "motion_source_missing": "승인한 원본 그림이 없거나 변경됐습니다. 복구하거나 캐릭터를 다시 생성하세요.",
        "art_model_busy": "다른 모델 준비가 실행 중이거나 작업을 정리하고 있습니다. 완료된 뒤 다시 시도하세요.",
        "art_cancelled": "준비를 취소했습니다. 이전 캐릭터와 검증한 단계는 유지됩니다.",
        "intro": "실루엣·머리카락·의상·재질이 다른 실제 그림을 생성합니다. Qwen 도형 설계와는 별도입니다. NVIDIA CUDA GPU가 필요하며 VRAM 기준은 실행 보장이 아닙니다.",
        "tier": "GPU VRAM 기준",
        "license": "모델: {repo}\n{license} · 그림 모델 {download}, 별도 검사·움직임용 약 3.9 GB, 실행환경 약 4 GB 다운로드. 디스크 25 GB 여유 권장. 시스템 RAM 최소 16 GB / SDXL은 32 GB 권장.\n{size} px · CPU 분산: {offload}. 2/6 GB 기준은 특히 느립니다. 다른 모델이 점유한 VRAM도 고려하세요.",
        "read": '고급 모델 사용 전 <a href="{url}">원본 라이선스와 이용 제한</a>을 확인하세요. 앱 코드는 MIT이며 모델은 MIT·OSI 승인 오픈소스가 아닙니다. 가중치는 배포본에 포함하지 않습니다. 상업적 이용도 모델의 조건을 따라야 하며 결과물의 권리 확보를 보증하지 않습니다.',
        "agree": "선택한 모델의 라이선스를 확인했으며 독창적이고 전연령에 적합한 캐릭터만 요청하겠습니다.",
        "prepare": "1. 실행환경·선택 모델 준비 (대용량 다운로드)",
        "setup": "먼저 Ollama를 설치하고 실행하세요. 준비 버튼은 격리된 Python 3.12/CUDA 환경, 선택 그림 모델, CPU 안전 검사·배경 제거·관절 추정 모델, Qwen2.5 1.5B·Qwen3-VL 2B를 설치합니다. 설치에는 인터넷이 필요하며 설명·그림은 로컬에서 처리합니다. 관리자 권한이나 전역 PATH 변경은 필요 없습니다. 다운로드 실패 시 준비를 다시 누르세요.",
        "prompt": "2. 독창적인 캐릭터 설명 (필수 · 최대 2,000자)",
        "example": "독창적인 작은 SD 천문학자. 정면에 가까운 서 있는 전신, 양손은 엉덩이 옆에서 뚜렷하게 보이고 구리 부츠를 신은 양발은 떨어진 자세. 짧은 청록색 머리, 크림색 셔츠, 남색 조끼, 초승달 브로치. 친근한 수채화 표현, 흰색 배경.",
        "examples": "움직임에 적합한 그림 예시",
        "example_astronomer": "작은 SD 천문학자",
        "example_courier": "숲속 배달부",
        "example_gardener": "태엽 정원사",
        "example_mechanic": "구름 정비사",
        "mechanic_prompt": '독창적인 작은 SD 구름 정거장 정비사 한 명. 정면을 향해 화면 중앙에 똑바로 서 있는 전신. 크고 둥근 머리, 짧고 풍성한 상아색 곱슬머리, 표정이 잘 보이는 짙은 눈, 연보라 눈썹, 작고 선명한 웃는 입. 크림색 긴팔 셔츠 위 짧은 샛노란 조끼, 차분한 자주색 바지, 두툼한 청록색 발목 부츠 두 짝. 두 팔은 몸통에서 조금 떨어뜨리고 팔꿈치·손목이 보이며 빈 손바닥은 조끼와 겹치지 않는다. 두 다리가 구분되고 부츠 사이에 틈이 있으며 무릎·발목이 보인다. 가슴 중앙에는 작은 민트색 육각형 천 패치 하나, 로고 없음. 단순하고 둥근 부피감과 읽기 쉬운 얼굴을 가진 친근하고 깔끔한 채색 일러스트. 머리·손·신발 밑창까지 전신이 화면 안에 들어오며 주변에 충분한 흰 여백. 단순한 흰색 배경. 캐릭터 한 명만, 손에 든 도구·모자·가방·떠다니는 소품·받침대·글자·다른 시점 없음.',
        "courier_prompt": "독창적인 작은 SD 숲속 배달부. 정면을 향한 전신과 몸 주변 여백. 두 팔은 몸 옆에 편안하게 두고 양손은 재킷과 떨어져 뚜렷하게 보이게 한다. 짧은 두 다리와 부츠도 각각 분리되어 보인다. 살구색 재킷, 청록색 바지, 작은 나뭇잎 모양 옷깃 핀, 짧은 밤색 머리, 표정이 잘 보이는 눈과 작고 친근한 입. 깔끔하고 부드러운 그림, 단순한 흰색 배경.",
        "gardener_prompt": "독창적인 작은 SD 태엽 정원사. 정면을 향해 똑바로 서 있는 전신. 두 팔과 손은 몸통 옆에 각각 떨어져 있고 두 다리와 부츠가 뚜렷하게 구분된다. 눈과 작고 표정 있는 입이 보이는 둥근 황동색 얼굴, 이끼색 멜빵바지, 크림색 소매, 짧은 구릿빛 머리, 주머니의 작은 꽃 모양 장식. 실루엣이 명확한 친근한 채색 그림, 단순한 흰색 배경.",
        "example_help": "예시 선택 후 ‘예시 넣기’를 누르세요. 손발이 가려지지 않고 떨어져 있으면 2D 움직임과 실험용 포즈 추정 보조 3D 준비에 도움이 됩니다. 설명은 자유롭게 고칠 수 있으며 생성 결과는 달라질 수 있습니다.",
        "sample": "예시 넣기", "generate": "그림 생성", "use": "이 캐릭터 사용", "close": "닫기", "guide": "자세한 설치·라이선스 안내 열기",
        "limits": "NSFW 및 식별 가능한 기존 캐릭터·로고 복제 요청은 금지합니다. 로컬 요청 검사·이미지 분류·비전 검사를 모두 통과해야 합니다. 검사 누락이나 정상 요청의 오차단이 있을 수 있으며 저작권 검증을 보장하지 않습니다. 사용·공개 전에 직접 확인하세요. 2D 편집기는 손발 그림 조각을 움직입니다. 아래 선택형 포즈 추정 보조 3D 준비는 가려진 형상을 추정하므로 방향별 클립을 확인하세요. 두 방식 모두 학습된 AI 영상은 아니며 도형 옵션으로 그림을 다시 칠할 수는 없습니다.",
        "ready": "준비됐습니다. 설명을 입력하고 생성하세요. 검사는 수 분, 노트북의 SDXL 그림 생성은 훨씬 오래 걸릴 수 있습니다.",
        "done": "로컬 검사를 통과했습니다. 결과 확인 → 이 캐릭터 사용 → 본창의 설정 저장을 누르세요.",
        "mouth": "미리보기의 입을 클릭하면 깨물기 위치(십자)를 조정합니다. 자동 추정에는 오차가 있을 수 있습니다.",
        "motion": "그림 손발 움직임 설정…",
        "done_no_motion": "그림 검사는 통과했지만 손발 영역을 확실히 추정하지 못했습니다. 손발 움직임 설정에서 도우미를 준비하거나 네 영역을 직접 조정한 뒤 사용하세요.",
        "art_rigging": "CPU에서 조정 가능한 손발 움직임 추정 중…",
        "art_pose_downloading": "CPU 관절 추정 모델 다운로드 중…",
        "art_pose_unavailable": "CPU 움직임 도우미가 없거나 추정이 불확실합니다. 움직임 설정에서 준비하거나 손발 영역을 직접 조정하세요.",
        "art_installing": "격리된 그림 실행환경 준비 중… 최초 설치는 수십 분 걸릴 수 있습니다.",
        "art_downloading": "선택한 그림·안전 검사·배경 제거 모델 다운로드 중… 창을 열어 두세요.",
        "art_review_models": "Ollama 검사용 모델 다운로드 중… Ollama를 실행해 두세요.",
        "art_reviewing": "로컬에서 설명 검사 중…",
        "art_summarizing": "승인된 외형 설명을 영어로 요약 중…",
        "art_drawing": "로컬에서 그림 생성 중… 창을 열어 두세요. CPU 분산 시 오래 걸릴 수 있습니다.",
        "art_loading": "그림 라이브러리·모델 가중치 불러오는 중…",
        "art_sampling": "그림 생성 · {completed}/{total}단계",
        "art_decoding": "이미지로 변환 중…",
        "art_scanning": "CPU에서 그림 안전성 검사 중…",
        "art_cutting": "CPU에서 배경 제거 중…",
        "progress_download": "모델 그룹 다운로드 · {completed}/{total}개 완료",
        "progress_review_download": "Ollama 검사 모델 다운로드 · {completed}/{total}개 완료",
        "art_runtime_tool": "실행환경 준비 도구 설치 중…",
        "art_runtime_python": "격리된 Python 준비 중…",
        "art_runtime_torch": "PyTorch·CUDA 다운로드·설치 중…",
        "art_runtime_packages": "그림 라이브러리 다운로드·설치 중…",
        "art_runtime_notices": "설치한 라이브러리 라이선스 기록 중…",
        "progress_time": "전체 {elapsed} · 현재 단계 {stage} · 마지막 진행 보고 {quiet} 전",
        "progress_wait": "진행 보고 없이 {quiet}째 대기 중입니다. 로딩·CPU 분산·검사가 오래 걸릴 수 있어 이것만으로 멈춤을 확정할 수는 없습니다. 남은 시간은 알 수 없습니다.",
        "progress_complete": "완료", "progress_stopped": "중단됨",
        "art_timed_out": "제한 시간을 초과해 대기를 중단했습니다. 기존 캐릭터는 유지됩니다. 로컬 검사·설치의 하위 작업은 백그라운드에서 끝날 수 있습니다. 재시도 전 Ollama·메모리·네트워크를 확인하세요.",
        "art_checking": "저장·표시 전에 로컬에서 그림 내용 검사 중…",
        "busy": "현재 작업이 끝난 뒤 닫으세요. 기존 캐릭터는 유지됩니다.",
        "art_description_required": "1~2,000자의 설명을 입력하세요.",
        "art_prompt_blocked": "독창성·콘텐츠 검사에서 설명을 거부했습니다. 기존 캐릭터·로고·선정적이거나 잔혹한 묘사 없이 독창적인 설정을 적으세요. 금지 표현은 부정 지시에도 쓰지 마세요.",
        "art_policy_unavailable": "로컬 검사가 실패했거나 잘못된 응답입니다. Ollama를 실행하고 준비 버튼으로 검사용 모델을 설치하세요. 검사하지 않은 그림은 적용하지 않습니다.",
        "review_prompt": "설명 검사", "review_image": "그림 검사",
        "review_missing": "이 정확한 검사 모델이 없습니다. 준비 버튼을 누르거나 PowerShell에서 {command} 실행 후 success까지 기다리세요. 기존 캐릭터는 유지됩니다.",
        "review_unreachable": "로컬 Ollama에 연결할 수 없습니다. Ollama를 실행하고 다시 시도하세요. 연결 오류 때문에 그림 실행환경을 재설치할 필요는 없습니다.",
        "review_timeout": "Ollama가 제한 시간 안에 검사를 끝내지 못했습니다. 다른 모델 작업이 끝나길 기다리거나 메모리를 확보하고 설명을 줄여 재시도하세요. 기존 캐릭터는 유지됩니다.",
        "review_memory": "Ollama가 검사 모델의 메모리 부족을 보고했습니다. 다른 모델·GPU 작업을 종료하고 다시 시도하세요. 그림 모델의 VRAM 선택이 검사 모델을 바꾸지는 않습니다.",
        "review_service": "Ollama가 검사 요청을 처리하지 못했습니다. Ollama를 업데이트하고 ollama list에서 표시된 모델의 정확한 이름을 확인한 뒤 재시도하세요. 미검사 그림은 적용하지 않습니다.",
        "review_invalid": "검사 모델의 구조화된 응답이 잘못됐습니다. 핵심 외형 특징으로 다시 시도하고 반복되면 Ollama를 업데이트하세요. JSON을 직접 수정할 필요는 없습니다. 기존 캐릭터는 유지됩니다.",
        "review_incomplete": "검사 응답이 끝나기 전에 잘렸습니다. 주요 외형 특징을 남겨 설명을 줄이고 다시 시도하세요. 응답 한도 오류이며 모델이 없다는 뜻은 아닙니다. 기존 캐릭터는 유지됩니다.",
        "art_output_blocked": "그림이 안전성·독창성 검사를 통과하지 못했습니다. 전연령에 적합한 독창적인 묘사로 다시 시도하세요. 기존 캐릭터는 유지됩니다.",
        "art_multiple_characters": "그림이 여러 인물 또는 큰 분리 영역을 포함한 것으로 판정되어 적용하지 않았습니다. 흰 배경 중앙에 전신 캐릭터 한 명만 서 있도록 요청해 다시 생성하세요. 이전 캐릭터는 유지됩니다.",
        "art_not_prepared": "선택형 그림 실행환경이 없습니다. 먼저 준비 버튼을 누르세요.",
        "art_download_failed": "한 차례 재개 후에도 모델 다운로드가 실패했습니다. 인터넷·디스크 여유를 확인하고 준비를 다시 누르세요. 완료한 파일은 재사용하며 기존 캐릭터는 유지됩니다.",
        "art_gpu_required": "이 모드는 지원되는 NVIDIA CUDA GPU가 필요합니다. 드라이버를 업데이트하거나 가벼운 도형 설계를 이용하세요.",
        "art_cutout_failed": "배경과 캐릭터를 분리하지 못했습니다. 흰색 단색 배경에 전신 캐릭터 하나만 요청해서 다시 시도하세요.",
        "art_runtime_failed": "그림 실행·설치 실패 또는 시간 초과입니다. 네트워크·디스크·NVIDIA 드라이버·Ollama 설치를 확인하고 준비를 다시 누르세요. 필요하면 2/4 GB 기준을 사용하고 창작 그림 안내의 진단 절차를 확인하세요.",
        "model_memory_error": "메모리가 부족합니다. 다른 GPU 작업을 종료하거나 낮은 기준을 선택하세요. SDXL은 시스템 RAM도 많이 필요합니다. 기존 캐릭터는 유지됩니다.",
    },
}


class ArtworkWorker(QThread):
    progress = Signal(object)
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, tier, description=None, parent=None):
        super().__init__(parent)
        self.tier, self.description = tier, description

    def run(self):
        try:
            if self.description is None:
                prepare_artwork(self.tier, self.progress.emit)
                result = {"ready": True}
            else:
                result = generate_artwork(self.description, self.tier, self.progress.emit)
            self.succeeded.emit(result)
        except Exception as error:
            self.failed.emit(str(error) if isinstance(error, GenerationError) else "art_runtime_failed")
        finally:
            self.description = None


class MotionWorker(QThread):
    progress = Signal(object)
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = safe_character(spec)
        self.cancel_event = threading.Event()

    def run(self):
        from .motion_client import prepare_animation
        try:
            result = prepare_animation(self.spec, self.progress.emit, self.cancel_event)
            if self.cancel_event.is_set():
                raise GenerationError("art_cancelled")
            self.succeeded.emit(result)
        except Exception as error:
            self.failed.emit(str(error) if isinstance(error, GenerationError) else "motion_runtime_failed")


class BitePreview(CharacterPreview):
    mouth_changed = Signal(float, float)

    def mousePressEvent(self, event):
        if self.spec.get("kind") != "artwork" or self.spec.get("animation_id") or event.button() != Qt.MouseButton.LeftButton:
            return
        scale = min(self.width() / 180, self.height() / 180)
        x = (event.position().x() - (self.width() - 144 * scale) / 2) / (144 * scale)
        y = (event.position().y() - (self.height() - 144 * scale) / 2) / (144 * scale)
        if .05 <= x <= .95 and .05 <= y <= .95:
            self.spec = {**self.spec, "mouth_x": x, "mouth_y": y}
            self.mouth_changed.emit(x, y)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.spec.get("kind") == "artwork" and not self.spec.get("animation_id"):
            scale = min(self.width() / 180, self.height() / 180)
            x = (self.width() - 144 * scale) / 2 + self.spec["mouth_x"] * 144 * scale
            y = (self.height() - 144 * scale) / 2 + self.spec["mouth_y"] * 144 * scale
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#de4389"), 2))
            painter.drawLine(round(x - 5), round(y), round(x + 5), round(y))
            painter.drawLine(round(x), round(y - 5), round(x), round(y + 5))


class ArtworkDialog(QDialog):
    chosen = Signal(dict)

    def __init__(self, language="en", tier=8, parent=None, initial_spec=None):
        super().__init__(parent)
        self.t = TEXT.get(language, TEXT["en"])
        self.language = "ko" if language == "ko" else "en"
        self.worker = None
        from .character_library import root as library_root
        self.library_root = getattr(parent, "library_root", library_root())
        self.result_spec = None
        self.setWindowTitle(self.t["title"])
        self.resize(820, 760)
        self.setMinimumSize(680, 560)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        for text in (self.t["intro"], self.t["tier"]):
            layout.addWidget(self.label(text))
        self.tier = QComboBox()
        for value in TIERS:
            self.tier.addItem(f"{value} GB · {'SD 1.5' if value <= 4 else 'SDXL 1.0'}", value)
        self.tier.setCurrentIndex(max(0, self.tier.findData(tier)))
        layout.addWidget(self.tier)
        self.model_info = self.label("")
        layout.addWidget(self.model_info)
        self.license_info = self.label("")
        self.license_info.setOpenExternalLinks(True)
        layout.addWidget(self.license_info)
        self.agree = QCheckBox(self.t["agree"])
        layout.addWidget(self.agree)
        layout.addWidget(self.label(self.t["setup"]))
        guide = QPushButton(self.t["guide"])
        guide.clicked.connect(self.open_guide)
        layout.addWidget(guide)
        self.prepare = QPushButton(self.t["prepare"])
        self.prepare.clicked.connect(lambda: self.start(False))
        layout.addWidget(self.prepare)
        layout.addWidget(self.label(self.t["prompt"]))
        layout.addWidget(self.label(self.t["examples"]))
        self.example_choice = QComboBox()
        for label, key in (("example_astronomer", "example"),
                           ("example_courier", "courier_prompt"),
                           ("example_gardener", "gardener_prompt"),
                           ("example_mechanic", "mechanic_prompt")):
            self.example_choice.addItem(self.t[label], key)
        example_row = QHBoxLayout()
        example_row.addWidget(self.example_choice, 1)
        self.sample = QPushButton(self.t["sample"])
        self.sample.clicked.connect(self.insert_example)
        example_row.addWidget(self.sample)
        layout.addLayout(example_row)
        layout.addWidget(self.label(self.t["example_help"]))
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText(self.t["example"])
        self.description.setFixedHeight(100)
        layout.addWidget(self.description)
        row = QHBoxLayout()
        self.generate = QPushButton(self.t["generate"])
        self.generate.setObjectName("primary")
        self.generate.clicked.connect(lambda: self.start(True))
        row.addWidget(self.generate)
        layout.addLayout(row)
        self.preview = BitePreview(default_character())
        self.preview.mouth_changed.connect(self.adjust_mouth)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        from .library_ui import TEXT as LIBRARY_TEXT
        lt = LIBRARY_TEXT[self.language]
        library_row = QHBoxLayout()
        self.save_character_button = QPushButton(lt["save"])
        self.save_character_button.clicked.connect(self.save_character_locally)
        self.library_button = QPushButton(lt["open"])
        self.library_button.clicked.connect(self.open_character_library)
        library_row.addWidget(self.save_character_button)
        library_row.addWidget(self.library_button)
        layout.addLayout(library_row)
        self.mouth_note = self.label(self.t["mouth"])
        layout.addWidget(self.mouth_note)
        self.motion_button = QPushButton(self.t["motion"])
        self.motion_button.clicked.connect(self.open_motion)
        layout.addWidget(self.motion_button)
        layout.addWidget(self.label(self.t["motion_help"]))
        self.motion_3d = QPushButton(self.t["motion_3d"])
        self.motion_3d.clicked.connect(self.start_motion)
        layout.addWidget(self.motion_3d)
        self.motion_view = QComboBox()
        for en, ko, clip in (("Front idle", "정면 대기", "idle_front"), ("Walk right", "오른쪽 걷기", "walk_right"),
                             ("Walk left", "왼쪽 걷기", "walk_left"), ("Turn right", "오른쪽 돌기", "turn_right"),
                             ("Wave", "손 흔들기", "wave"), ("Hop", "뛰기", "hop"), ("Cheer", "응원", "cheer"),
                             ("Bite right", "오른쪽 깨물기", "bite_right"), ("Bite left", "왼쪽 깨물기", "bite_left")):
            self.motion_view.addItem(ko if self.language == "ko" else en, clip)
        self.motion_view.setAccessibleName(self.t["motion_view"])
        self.motion_view.currentIndexChanged.connect(self.preview_motion)
        layout.addWidget(self.motion_view)
        self.motion_original = QPushButton(self.t["motion_original"])
        self.motion_original.clicked.connect(self.restore_original)
        layout.addWidget(self.motion_original)
        layout.addWidget(self.label(self.t["limits"]))
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.progress_panel = QWidget()
        self.progress_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        progress_layout = QVBoxLayout(self.progress_panel)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)
        self.stage_label = self.label("")
        self.progress_bar = QProgressBar()
        self.timing_label = self.label("")
        self.wait_label = self.label("")
        for control in (self.stage_label, self.progress_bar, self.timing_label, self.wait_label):
            progress_layout.addWidget(control)
        outer.addWidget(self.progress_panel)
        self.progress_panel.hide()
        self.cancel_motion = QPushButton(self.t["motion_cancel"])
        self.cancel_motion.clicked.connect(self.cancel_preparation)
        self.cancel_motion.hide()
        outer.addWidget(self.cancel_motion)
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.update_timing)
        self.started_at = self.stage_started_at = self.last_report_at = None
        self.current_stage = None
        self.status = self.label("")
        outer.addWidget(self.status)
        footer = QHBoxLayout()
        self.use = QPushButton(self.t["use"])
        self.use.setEnabled(False)
        self.use.clicked.connect(self.choose)
        footer.addWidget(self.use)
        close = QPushButton(self.t["close"])
        close.clicked.connect(self.reject)
        footer.addWidget(close)
        outer.addLayout(footer)
        self.tier.currentIndexChanged.connect(self.refresh)
        self.agree.toggled.connect(self.controls)
        self.refresh()
        if isinstance(initial_spec, dict) and initial_spec.get("kind") == "artwork":
            self.result_spec = safe_character(initial_spec)
            self.preview.spec = self.result_spec
            self.preview_motion()
            self.controls()

    @staticmethod
    def label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        return label

    def open_guide(self):
        path = source_dir().parent / "doc" / self.language / "CREATIVE-ART.md"
        url = QUrl.fromLocalFile(str(path)) if path.is_file() else QUrl(
            "https://github.com/hobby-programmer-5000/pawzura/blob/codex/pawzura/doc/" + self.language + "/CREATIVE-ART.md")
        QDesktopServices.openUrl(url)

    def refresh(self):
        name, size, offload = TIERS[self.tier.currentData()]
        model = catalog()[name]
        self.model_info.setText(self.t["license"].format(**model, size=size, offload=offload))
        self.license_info.setText(self.t["read"].format(url=model["license_url"]))
        self.agree.setChecked(False)
        self.controls()

    def controls(self):
        busy = self.worker is not None
        self.prepare.setEnabled(not busy and self.agree.isChecked())
        self.generate.setEnabled(not busy and self.agree.isChecked())
        for control in (self.tier, self.agree, self.description, self.example_choice, self.sample):
            control.setEnabled(not busy)
        self.preview.setEnabled(not busy)
        self.save_character_button.setEnabled(not busy and self.result_spec is not None)
        self.library_button.setEnabled(not busy)
        self.use.setEnabled(not busy and self.result_spec is not None)
        self.motion_button.setEnabled(not busy and self.result_spec is not None and not self.result_spec.get("animation_id"))
        self.motion_3d.setEnabled(not busy and self.result_spec is not None and self.agree.isChecked())
        animated = bool(self.result_spec and self.result_spec.get("animation_id"))
        from .motion_pack import load_pack
        valid = bool(animated and load_pack(self.result_spec["animation_id"], self.result_spec["art_id"]))
        self.mouth_note.setText(self.t["motion_mouth"] if valid else self.t["motion_missing"] if animated else self.t["mouth"])
        self.motion_view.setEnabled(not busy and valid)
        self.motion_original.setEnabled(not busy and animated)

    def save_character_locally(self):
        if self.worker is not None or self.result_spec is None:
            return
        from .library_ui import save_named
        message = save_named(self.result_spec, self.language, self, self.library_root)
        if message:
            self.status.setText(message)

    def library_references(self):
        parent = self.parent()
        refs = parent.library_references() if parent is not None and hasattr(parent, "library_references") else {"active": [], "history": []}
        return {"active": [*refs["active"], *([self.result_spec] if self.result_spec else [])],
                "history": refs["history"], "busy": self.worker is not None or refs.get("busy", False)}

    def open_character_library(self):
        if self.worker is not None:
            return
        from .library_ui import LibraryDialog
        dialog = LibraryDialog(self.language, self.preview.theme, self, self.library_root, artwork_only=True, current_spec=self.result_spec, reference_provider=self.library_references)
        dialog.chosen.connect(self.library_chosen)
        dialog.exec()
        dialog.preview.timer.stop()
        dialog.deleteLater()

    def library_chosen(self, spec):
        self.result_spec = safe_character(spec)
        self.preview.spec = self.result_spec
        self.preview.pose = "walk"
        self.preview.phase = 0
        self.preview.timer.start(40)
        self.preview.update()
        self.controls()

    def auto_save_character(self):
        from .character_library import try_save
        from .library_ui import TEXT as LIBRARY_TEXT
        if self.result_spec is not None:
            saved = try_save(self.result_spec, self.library_root)
            self.status.setText(self.status.text() + "\n" + LIBRARY_TEXT[self.language]["auto_saved" if saved else "auto_failed"])

    def start_motion(self):
        if self.worker is not None or self.result_spec is None or not self.agree.isChecked():
            return
        self.started_at = self.stage_started_at = self.last_report_at = time.monotonic()
        self.current_stage = None
        self.progress_panel.show()
        self.wait_label.clear()
        self.status.clear()
        self.progress_timer.start()
        self.set_progress("motion_reconstructing")
        self.worker = MotionWorker(self.result_spec, self)
        if self.parent():
            self.parent().worker = self.worker
        self.worker.progress.connect(self.set_progress)
        self.worker.succeeded.connect(self.motion_succeeded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished_work)
        self.cancel_motion.show()
        self.cancel_motion.setEnabled(True)
        self.controls()
        self.worker.start()

    def cancel_preparation(self):
        if isinstance(self.worker, MotionWorker):
            self.worker.cancel_event.set()
            self.cancel_motion.setEnabled(False)
            self.status.setText(self.t["motion_stopping"])

    def motion_succeeded(self, spec):
        if not isinstance(self.worker, MotionWorker) or self.worker.cancel_event.is_set():
            return
        if self.result_spec is None or spec.get("art_id") != self.result_spec["art_id"]:
            return
        self.result_spec = safe_character(spec)
        self.preview.spec = self.result_spec
        self.preview_motion()
        self.stop_progress(True)
        self.status.setText(self.t["motion_done"])
        self.auto_save_character()

    def preview_motion(self):
        if self.result_spec and self.result_spec.get("animation_id"):
            self.preview.pose = self.motion_view.currentData()
            self.preview.phase = 0
            self.preview.timer.start(40)
            self.preview.update()

    def restore_original(self):
        if self.worker is None and self.result_spec:
            self.result_spec = {key: value for key, value in self.result_spec.items() if key != "animation_id"}
            self.preview.spec = self.result_spec
            self.preview.pose = "walk"
            self.preview.update()
            self.controls()

    def insert_example(self):
        if self.worker is None:
            self.description.setPlainText(self.t[self.example_choice.currentData()])

    def start(self, generate):
        if self.worker is not None or not self.agree.isChecked():
            return
        description = self.description.toPlainText() if generate else None
        if generate and (not description.strip() or len(description) > MAX_PROMPT):
            self.status.setText(self.t["art_description_required"])
            return
        self.started_at = self.stage_started_at = self.last_report_at = time.monotonic()
        self.current_stage = None
        self.progress_panel.show()
        self.wait_label.clear()
        self.status.clear()
        self.progress_timer.start()
        self.set_progress("art_reviewing" if generate else "art_installing")
        self.worker = ArtworkWorker(self.tier.currentData(), description, self)
        if self.parent():
            self.parent().worker = self.worker  # App's quit/language-change guard.
        self.worker.progress.connect(self.set_progress)
        self.worker.succeeded.connect(self.succeeded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished_work)
        self.controls()
        self.worker.start()

    @staticmethod
    def duration(seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"

    def set_progress(self, event):
        if self.started_at is None or not self.progress_timer.isActive():
            return
        event = {"stage": event} if isinstance(event, str) else event
        stage = event.get("stage")
        if stage not in self.t:
            return
        now = time.monotonic()
        if stage != self.current_stage:
            self.stage_started_at = now
            self.current_stage = stage
        self.last_report_at = now
        if "completed" in event:
            completed, total = event["completed"], event["total"]
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(completed)
            self.progress_bar.setFormat("%p%")
            key = {"art_downloading": "progress_download", "art_review_models": "progress_review_download"}.get(stage, stage)
            self.stage_label.setText(self.t[key].format(completed=completed, total=total))
        else:
            self.progress_bar.setRange(0, 0)
            self.stage_label.setText(self.t[stage])
        self.update_timing()

    def update_timing(self):
        if self.started_at is None:
            return
        now = time.monotonic()
        quiet = self.duration(now - self.last_report_at)
        self.timing_label.setText(self.t["progress_time"].format(
            elapsed=self.duration(now - self.started_at), stage=self.duration(now - self.stage_started_at), quiet=quiet))
        self.wait_label.setText(self.t["progress_wait"].format(quiet=quiet)
                                if self.progress_timer.isActive() and now - self.last_report_at >= 60 else "")

    def stop_progress(self, success):
        self.update_timing()
        self.progress_timer.stop()
        self.wait_label.clear()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if success else 0)
        self.progress_bar.setFormat(self.t["progress_complete" if success else "progress_stopped"])

    def failed(self, code):
        self.stop_progress(False)
        info = review_error_info(code)
        if info is not None:
            stage, reason, model = info
            self.status.setText(self.t["review_" + stage] + " · " + model + "\n" +
                                self.t["review_" + reason].format(command="ollama pull " + model))
        else:
            self.status.setText(self.t.get(code, self.t["art_runtime_failed"]))

    def succeeded(self, result):
        self.stop_progress(True)
        if result.get("ready"):
            self.status.setText(self.t["ready"])
        else:
            self.result_spec = result
            self.preview.spec = safe_character(result)
            self.preview.pose = "walk"
            if self.preview.spec.get("rig"):
                self.preview.timer.start(40)
            else:
                self.preview.timer.stop()
            self.preview.phase = 0
            self.preview.update()
            self.status.setText(self.t["done"] if self.preview.spec.get("rig") else self.t["done_no_motion"])
            self.auto_save_character()

    def open_motion(self):
        if self.worker is not None or self.result_spec is None or self.result_spec.get("animation_id"):
            return
        from .motion_ui import MotionDialog
        dialog = MotionDialog(self.result_spec, self.language, self.preview.theme, self, self.parent())
        dialog.chosen.connect(self.motion_chosen)
        dialog.exec()
        dialog.preview.timer.stop()
        dialog.deleteLater()

    def motion_chosen(self, spec):
        self.result_spec = safe_character(spec)
        self.preview.spec = self.result_spec
        if self.result_spec.get("rig"):
            self.preview.timer.start(40)
        else:
            self.preview.timer.stop()
        self.preview.update()

    def adjust_mouth(self, x, y):
        if self.result_spec is not None and self.worker is None:
            self.result_spec.update(mouth_x=x, mouth_y=y)

    def finished_work(self):
        self.worker.deleteLater()
        self.worker = None
        self.cancel_motion.hide()
        if self.parent():
            self.parent().worker = None
        self.controls()

    def choose(self):
        if self.result_spec is not None and self.worker is None:
            self.chosen.emit(self.result_spec)
            self.accept()

    def reject(self):
        if self.worker is not None:
            self.status.setText(self.t["busy"])
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker is not None:
            self.status.setText(self.t["busy"])
            event.ignore()
        else:
            super().closeEvent(event)
