"""Explicit setup and original-artwork flow, independent of vector trait controls."""
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPainter, QColor, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget, QLayout)
from .art_client import TIERS, catalog, generate_artwork, prepare_artwork, source_dir
from .characters import GenerationError, MAX_PROMPT
from .config import default_character, safe_character
from .pet import CharacterPreview

TEXT = {
    "en": {
        "title": "Creative artwork · optional GPU mode",
        "intro": "Generate an actual image with a different silhouette, hair, clothes and materials. This is separate from the Qwen trait designer. NVIDIA CUDA is required; capacity is a guide, not a guarantee.",
        "tier": "GPU VRAM guide",
        "license": "Model: {repo}\n{license} · image download {download}, plus ~3.5 GB review models and ~4 GB runtime. Allow 25 GB disk space; system RAM 16 GB minimum / 32 GB recommended for SDXL.\n{size} px · CPU offload: {offload}. 2/6 GB guides are especially slow. Other running models also use VRAM.",
        "read": 'Before using this advanced model, read its <a href="{url}">original license and use restrictions</a>. App code is MIT; model weights are not MIT or OSI-approved open source. No weights are bundled. Commercial use remains subject to the model license; this is not legal clearance for an output.',
        "agree": "I have reviewed the selected model's license and will request only original, family-friendly characters.",
        "prepare": "1. Prepare runtime and selected models (large download)",
        "setup": "Install/start Ollama first. Preparation installs an isolated Python 3.12/CUDA runtime and downloads the selected image model, CPU safety/cutout models, Qwen2.5 1.5B and Qwen3-VL 2B. Internet is needed for setup; descriptions and images stay local. No administrator rights or global PATH change needed. Retry Preparation after a failed download.",
        "prompt": "2. Describe an original character (required, at most 2,000 characters)",
        "example": "An original tiny glass-and-brass astronomer with a crescent-shaped body, turquoise curly hair, a navy embroidered cape, oversized copper boots and a floating lantern. Warm watercolor and ink, friendly expression, complete body visible.",
        "sample": "Insert example", "generate": "Generate artwork", "use": "Use this character", "close": "Close", "guide": "Open detailed setup/license guide",
        "limits": "NSFW and recognizable character/logo replication requests are prohibited. Local prompt review, an image classifier and vision review must all pass. Checks can miss content or reject safe requests; they do not guarantee copyright clearance. Inspect the result before using or publishing it. Motion is whole-image sway/flip/jump, not AI-generated limb animation. Trait options cannot edit this bitmap; regenerate to change it.",
        "ready": "Ready. Enter an original description and generate. Review may take several minutes; SDXL generation can take much longer on a laptop.",
        "done": "Artwork passed local checks. Inspect it, then Use this character → Save settings in the main window.",
        "mouth": "Click the mouth in the preview to adjust the bite point (cross). The automatic estimate can be inaccurate.",
        "art_installing": "Preparing isolated image runtime… first setup can take tens of minutes.",
        "art_downloading": "Downloading selected image, safety and cutout models… keep this window open.",
        "art_review_models": "Downloading local Ollama review models… keep Ollama running.",
        "art_reviewing": "Reviewing your description locally…",
        "art_drawing": "Drawing artwork locally… keep this window open. CPU offload may be slow.",
        "art_checking": "Reviewing image content locally before saving or displaying it…",
        "busy": "Wait for the current operation to finish before closing. Your current character is retained.",
        "art_description_required": "Enter a description of 1–2,000 characters.",
        "art_prompt_blocked": "The description was rejected by the originality/content check. Use a generic original design without existing characters, logos or sexual/violent details. Avoid restricted terms even in negative instructions.",
        "art_policy_unavailable": "The local review failed or returned invalid data. Keep Ollama running and run Preparation to install both review models. No unchecked artwork was applied.",
        "art_output_blocked": "The image did not pass local safety/originality review. Try a clearer original, family-friendly design. Your previous character is retained.",
        "art_not_prepared": "Run Preparation first. The optional image runtime is missing.",
        "art_download_failed": "A model download failed after a bounded retry. Check internet and disk space, then run Preparation again; completed files are reused. No character was replaced.",
        "art_gpu_required": "A supported NVIDIA CUDA GPU is required for this optional mode. Update its driver or use the lightweight trait designer.",
        "art_cutout_failed": "The character could not be separated from its background. Request one full-body character on a plain white background and retry.",
        "art_runtime_failed": "Image runtime/setup failed or timed out. Check your connection, disk space, NVIDIA driver and Ollama installation, then retry Preparation. Use the smaller 2/4 GB guide if needed; see the Creative artwork guide for diagnosis.",
        "model_memory_error": "Not enough memory. Close other GPU workloads or choose a lower guide. SDXL also needs substantial system RAM. Your previous character is retained.",
    },
    "ko": {
        "title": "창작 그림 · 선택형 GPU 모드",
        "intro": "실루엣·머리카락·의상·재질이 다른 실제 그림을 생성합니다. Qwen 도형 설계와는 별도입니다. NVIDIA CUDA GPU가 필요하며 VRAM 기준은 실행 보장이 아닙니다.",
        "tier": "GPU VRAM 기준",
        "license": "모델: {repo}\n{license} · 그림 모델 {download}, 별도 검사용 약 3.5 GB, 실행환경 약 4 GB 다운로드. 디스크 25 GB 여유 권장. 시스템 RAM 최소 16 GB / SDXL은 32 GB 권장.\n{size} px · CPU 분산: {offload}. 2/6 GB 기준은 특히 느립니다. 다른 모델이 점유한 VRAM도 고려하세요.",
        "read": '고급 모델 사용 전 <a href="{url}">원본 라이선스와 이용 제한</a>을 확인하세요. 앱 코드는 MIT이며 모델은 MIT·OSI 승인 오픈소스가 아닙니다. 가중치는 배포본에 포함하지 않습니다. 상업적 이용도 모델의 조건을 따라야 하며 결과물의 권리 확보를 보증하지 않습니다.',
        "agree": "선택한 모델의 라이선스를 확인했으며 독창적이고 전연령에 적합한 캐릭터만 요청하겠습니다.",
        "prepare": "1. 실행환경·선택 모델 준비 (대용량 다운로드)",
        "setup": "먼저 Ollama를 설치하고 실행하세요. 준비 버튼은 격리된 Python 3.12/CUDA 환경, 선택 그림 모델, CPU 안전 검사·배경 제거 모델, Qwen2.5 1.5B·Qwen3-VL 2B를 설치합니다. 설치에는 인터넷이 필요하며 설명·그림은 로컬에서 처리합니다. 관리자 권한이나 전역 PATH 변경은 필요 없습니다. 다운로드 실패 시 준비를 다시 누르세요.",
        "prompt": "2. 독창적인 캐릭터 설명 (필수 · 최대 2,000자)",
        "example": "초승달 모양의 몸을 가진 유리와 황동 재질의 작은 천문학자. 청록색 곱슬머리, 자수가 놓인 남색 망토, 커다란 구리 부츠와 공중에 떠 있는 등불. 따뜻한 수채화와 잉크 표현, 친근한 표정, 전신이 보이는 독창적인 캐릭터.",
        "sample": "예시 넣기", "generate": "그림 생성", "use": "이 캐릭터 사용", "close": "닫기", "guide": "자세한 설치·라이선스 안내 열기",
        "limits": "NSFW 및 식별 가능한 기존 캐릭터·로고 복제 요청은 금지합니다. 로컬 요청 검사·이미지 분류·비전 검사를 모두 통과해야 합니다. 검사 누락이나 정상 요청의 오차단이 있을 수 있으며 저작권 검증을 보장하지 않습니다. 사용·공개 전에 직접 확인하세요. 움직임은 그림 전체의 흔들림·반전·점프이며 AI 팔다리 애니메이션은 아닙니다. 도형 옵션으로 이 그림을 편집할 수 없으며 바꾸려면 다시 생성하세요.",
        "ready": "준비됐습니다. 설명을 입력하고 생성하세요. 검사는 수 분, 노트북의 SDXL 그림 생성은 훨씬 오래 걸릴 수 있습니다.",
        "done": "로컬 검사를 통과했습니다. 결과 확인 → 이 캐릭터 사용 → 본창의 설정 저장을 누르세요.",
        "mouth": "미리보기의 입을 클릭하면 깨물기 위치(십자)를 조정합니다. 자동 추정에는 오차가 있을 수 있습니다.",
        "art_installing": "격리된 그림 실행환경 준비 중… 최초 설치는 수십 분 걸릴 수 있습니다.",
        "art_downloading": "선택한 그림·안전 검사·배경 제거 모델 다운로드 중… 창을 열어 두세요.",
        "art_review_models": "Ollama 검사용 모델 다운로드 중… Ollama를 실행해 두세요.",
        "art_reviewing": "로컬에서 설명 검사 중…",
        "art_drawing": "로컬에서 그림 생성 중… 창을 열어 두세요. CPU 분산 시 오래 걸릴 수 있습니다.",
        "art_checking": "저장·표시 전에 로컬에서 그림 내용 검사 중…",
        "busy": "현재 작업이 끝난 뒤 닫으세요. 기존 캐릭터는 유지됩니다.",
        "art_description_required": "1~2,000자의 설명을 입력하세요.",
        "art_prompt_blocked": "독창성·콘텐츠 검사에서 설명을 거부했습니다. 기존 캐릭터·로고·선정적이거나 잔혹한 묘사 없이 독창적인 설정을 적으세요. 금지 표현은 부정 지시에도 쓰지 마세요.",
        "art_policy_unavailable": "로컬 검사가 실패했거나 잘못된 응답입니다. Ollama를 실행하고 준비 버튼으로 검사용 모델을 설치하세요. 검사하지 않은 그림은 적용하지 않습니다.",
        "art_output_blocked": "그림이 안전성·독창성 검사를 통과하지 못했습니다. 전연령에 적합한 독창적인 묘사로 다시 시도하세요. 기존 캐릭터는 유지됩니다.",
        "art_not_prepared": "선택형 그림 실행환경이 없습니다. 먼저 준비 버튼을 누르세요.",
        "art_download_failed": "한 차례 재개 후에도 모델 다운로드가 실패했습니다. 인터넷·디스크 여유를 확인하고 준비를 다시 누르세요. 완료한 파일은 재사용하며 기존 캐릭터는 유지됩니다.",
        "art_gpu_required": "이 모드는 지원되는 NVIDIA CUDA GPU가 필요합니다. 드라이버를 업데이트하거나 가벼운 도형 설계를 이용하세요.",
        "art_cutout_failed": "배경과 캐릭터를 분리하지 못했습니다. 흰색 단색 배경에 전신 캐릭터 하나만 요청해서 다시 시도하세요.",
        "art_runtime_failed": "그림 실행·설치 실패 또는 시간 초과입니다. 네트워크·디스크·NVIDIA 드라이버·Ollama 설치를 확인하고 준비를 다시 누르세요. 필요하면 2/4 GB 기준을 사용하고 창작 그림 안내의 진단 절차를 확인하세요.",
        "model_memory_error": "메모리가 부족합니다. 다른 GPU 작업을 종료하거나 낮은 기준을 선택하세요. SDXL은 시스템 RAM도 많이 필요합니다. 기존 캐릭터는 유지됩니다.",
    },
}


class ArtworkWorker(QThread):
    progress = Signal(str)
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


class BitePreview(CharacterPreview):
    mouth_changed = Signal(float, float)

    def mousePressEvent(self, event):
        if self.spec.get("kind") != "artwork" or event.button() != Qt.MouseButton.LeftButton:
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
        if self.spec.get("kind") == "artwork":
            scale = min(self.width() / 180, self.height() / 180)
            x = (self.width() - 144 * scale) / 2 + self.spec["mouth_x"] * 144 * scale
            y = (self.height() - 144 * scale) / 2 + self.spec["mouth_y"] * 144 * scale
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#de4389"), 2))
            painter.drawLine(round(x - 5), round(y), round(x + 5), round(y))
            painter.drawLine(round(x), round(y - 5), round(x), round(y + 5))


class ArtworkDialog(QDialog):
    chosen = Signal(dict)

    def __init__(self, language="en", tier=8, parent=None):
        super().__init__(parent)
        self.t = TEXT.get(language, TEXT["en"])
        self.language = "ko" if language == "ko" else "en"
        self.worker = None
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
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText(self.t["example"])
        self.description.setFixedHeight(100)
        layout.addWidget(self.description)
        row = QHBoxLayout()
        sample = QPushButton(self.t["sample"])
        sample.clicked.connect(lambda: self.description.setPlainText(self.t["example"]))
        row.addWidget(sample)
        self.generate = QPushButton(self.t["generate"])
        self.generate.setObjectName("primary")
        self.generate.clicked.connect(lambda: self.start(True))
        row.addWidget(self.generate)
        layout.addLayout(row)
        self.preview = BitePreview(default_character())
        self.preview.mouth_changed.connect(self.adjust_mouth)
        layout.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.label(self.t["mouth"]))
        layout.addWidget(self.label(self.t["limits"]))
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
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
        for control in (self.tier, self.agree, self.description):
            control.setEnabled(not busy)
        self.preview.setEnabled(not busy)
        self.use.setEnabled(not busy and self.result_spec is not None)

    def start(self, generate):
        if self.worker is not None or not self.agree.isChecked():
            return
        description = self.description.toPlainText() if generate else None
        if generate and (not description.strip() or len(description) > MAX_PROMPT):
            self.status.setText(self.t["art_description_required"])
            return
        self.worker = ArtworkWorker(self.tier.currentData(), description, self)
        if self.parent():
            self.parent().worker = self.worker  # App's quit/language-change guard.
        self.worker.progress.connect(lambda code: self.status.setText(self.t[code]))
        self.worker.succeeded.connect(self.succeeded)
        self.worker.failed.connect(lambda code: self.status.setText(self.t.get(code, self.t["art_runtime_failed"])))
        self.worker.finished.connect(self.finished_work)
        self.controls()
        self.worker.start()

    def succeeded(self, result):
        if result.get("ready"):
            self.status.setText(self.t["ready"])
        else:
            self.result_spec = result
            self.preview.spec = safe_character(result)
            self.preview.timer.stop()
            self.preview.phase = 0
            self.preview.update()
            self.status.setText(self.t["done"])

    def adjust_mouth(self, x, y):
        if self.result_spec is not None and self.worker is None:
            self.result_spec.update(mouth_x=x, mouth_y=y)

    def finished_work(self):
        self.worker.deleteLater()
        self.worker = None
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
