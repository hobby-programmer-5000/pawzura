from __future__ import annotations

import copy
import json
import re
from pathlib import Path
import sys
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QPlainTextEdit, QTabWidget, QVBoxLayout, QWidget, QInputDialog, QGridLayout, QScrollArea, QFrame, QColorDialog, QLayout,
)
from . import __version__, windows
from .characters import COLORS, DETAIL_MODEL, FEATURES, GPU_MODELS, MAX_PROMPT, MODEL, custom_options, generate_character, models_for_vram, random_character
from .config import BROWSERS, default_character, profile_lists, safe_character
from .pet import CharacterPreview
from .browser_setup import BrowserSetupDialog
from .policy import SiteRuleError, address_rules, normalize_app, site_rule

TEXT = {
    "ko": {
        "subtitle": "작은 발걸음으로 지키는 나만의 집중 시간",
        "general": "일반", "apps": "프로그램", "web": "브라우저", "character": "캐릭터", "about": "정보",
        "guard": "집중 지킴이 켜기", "preview": "미리보기 모드 · 애니메이션만 표시하고 닫지 않기",
        "visible": "바탕화면에 캐릭터 표시", "startup": "Windows 로그인 시 자동 실행", "language": "언어",
        "theme": "화면 테마", "theme_dark": "다크", "theme_light": "라이트 (화이트)",
        "theme_help": "선택하면 바로 미리 봅니다. 다음 실행에도 유지하려면 설정 저장을 누르세요.",
        "advanced": "고급", "advanced_models": "고급 캐릭터 모델 사용",
        "vram_tier": "GPU VRAM 용량 (직접 선택)", "vram_unknown": "CPU / 모름",
        "advanced_help": "2·4·6·8 GB는 모델 선택을 돕는 기준이며 GPU 감지나 실행 보장이 아닙니다. 실제 남은 VRAM과 시스템 RAM이 충분해야 합니다. GPU 지원과 CPU 분산은 Ollama가 결정합니다.",
        "advanced_scope": "큰 모델은 설명 해석을 개선할 수 있지만, 캐릭터는 같은 도형으로 그립니다. 새로운 그림·의상 생성 모델은 아닙니다. 고급 설정은 허용 목록 프로필과 별도로 저장됩니다.",
        "model_memory": "모델 파일 약 {size}. 실행에는 추가 메모리가 필요합니다. Ollama를 실행하고 아래 모델을 먼저 내려받으세요.",
        "model_download": "다운로드 약 {size} · 추가 가용 RAM/VRAM 필요 · Ollama 실행 필수",
        "model_setup": "모델 준비 안내", "copy_model_command": "명령 복사", "command_copied": "복사됨",
        "model_command_copied": "다운로드 명령을 복사했습니다. PowerShell에 붙여넣고 Enter → success 표시까지 대기 → 앱에서 다시 생성하세요.",
        "model_setup_steps": "1. Ollama를 설치하고 실행해 두세요 (ollama.com).\n2. 고급에서 GPU VRAM 기준을 고른 뒤 캐릭터에서 모델을 선택하세요. 시스템 RAM 8GB와 GPU VRAM 8GB는 다릅니다.\n3. 선택 모델의 명령 복사 → Win+X에서 PowerShell/터미널 열기 → 붙여넣기 → Enter.\n4. 다운로드의 success 표시까지 기다리세요. ollama list에 정확한 모델 이름이 있어야 합니다. 다른 이름·양자화는 별도 모델입니다.\n5. 앱에서 Qwen으로 생성 → 미리보기 확인 → 설정 저장. 이미 설치했으면 재다운로드할 필요 없습니다. 앱이 자동 설치하지는 않습니다.",
        "model_setup_limits": "용량은 파일 크기이며 실행 메모리는 더 필요합니다. VRAM 기준은 실행 보장이 아닙니다. CPU/모름은 0.5B 또는 1.5B로 시작하세요. 부족하면 작은 모델로 변경하세요. 프롬프트나 허용 목록은 이 안내에서 변경하지 않습니다.",
        "model_missing_detail": "Ollama가 선택 모델을 찾지 못했거나 지원하지 않습니다:\n{model}\nPowerShell에서 {command}\nsuccess 표시 후 다시 생성하세요. 이미 설치했다면 Ollama를 업데이트하고 정확한 이름을 확인하세요.",
        "model_guide_close": "닫기", "model_selected": "현재 선택: {model}",
        "model_small_memory": "0.5B 약 0.5 GB / 1.5B 약 1.12 GB의 모델 파일과 추가 실행 메모리가 필요합니다. Ollama를 실행해 두세요.",
        "model_missing": "선택한 모델이 없거나 Ollama가 지원하지 않습니다. 표시된 ollama pull 명령을 실행하고 Ollama를 업데이트한 뒤 다시 시도하세요.",
        "model_memory_error": "모델을 실행할 메모리가 부족합니다. 더 작은 모델을 선택하거나 다른 모델·GPU 작업을 종료하고 다시 시도하세요. 기존 캐릭터는 유지됩니다.",
        "model_service_error": "Ollama가 모델 실행에 실패했습니다. Ollama 상태·지원 버전·가용 메모리를 확인하고 다시 시도하세요.",
        "ollama_unavailable": "Ollama에 연결할 수 없거나 생성 시간이 초과되었습니다. Ollama를 실행하고, 느리면 더 작은 모델로 다시 시도하세요.",
        "save": "설정 저장", "close": "트레이로 돌아가기", "saved": "설정을 저장했습니다.",
        "intro": "먼저 미리보기로 허용 목록을 확인하세요.\n프로그램을 제어하며, 사이트 제어도 켜고 확장을 연결한 경우에만 미허용 탭을 닫습니다.",
        "apps_help": "허용할 실행 파일 이름을 한 줄에 하나씩 입력하세요. 경로를 붙여넣으면 파일명만 사용합니다.\nWindows·그래픽/오버레이 보조 창과 이 앱은 항상 보호합니다. 같은 이름의 실행 파일은 모두 허용됩니다.",
        "browse": "실행 파일 추가…", "running": "열려 있는 프로그램 추가…", "startup_scan": "시작프로그램 다시 탐색",
        "browser_help": "브라우저마다 확장을 설치하고 연결해야 합니다. 기본 허용은 새 탭/기본 홈 화면뿐입니다.\n도메인은 사이트 전체를, 경로를 넣은 주소는 해당 구역만 허용합니다. http://와 https:// 모두 입력할 수 있습니다.",
        "browser_on": "이 브라우저의 사이트 허용 목록 적용", "pair": "연결 코드 복사", "extension": "확장 폴더 열기",
        "website_control": "사이트 제어 ON/OFF — 변경 즉시 적용",
        "website_help": "OFF이면 프로그램만 제어하고 브라우저 탭은 건드리지 않습니다. 사이트 제어에는 별도 확장이 필수입니다.",
        "setup": "확장 설치·연결…", "connected": "확장 연결됨", "not_connected": "확장 미연결 — 설치·연결 버튼을 누르세요",
        "website_saved": "사이트 제어를 즉시 저장했습니다. 프로그램 감시 설정은 유지됩니다.",
        "connection_code": "연결 코드", "port": "포트", "startup_list": "시작프로그램",
        "rules": "허용 주소 · 한 줄에 하나 (example.com/* 또는 example.com/section/*)",
        "site_line": "허용 주소 {line}번째 줄: {message}",
        "invalid_url": "도메인 또는 호스트가 포함된 완전한 http://·https:// 주소를 넣으세요.",
        "invalid_port": "포트는 1부터 65535 사이여야 합니다.",
        "invalid_path": "경로에서 .·.. 구역, 역슬래시와 인코딩된 구분자를 제거하세요.",
        "invalid_wildcard": "*는 하위 도메인 앞의 *. 또는 경로 끝의 /*로만 사용하세요.",
        "invalid_subdomain": "하위 도메인을 포함하려면 example.com 같은 도메인을 입력하세요. IP 주소·localhost는 개별 주소로 추가하세요.",
        "add_site": "주소 추가", "include_subdomains": "이 주소의 하위 도메인도 포함",
        "subdomain_help": "console.example.com도 그대로 등록할 수 있습니다. 체크하면 입력한 호스트와 그 아래 하위 도메인을 함께 추가합니다. 예: example.com + *.example.com. 경로·쿼리·HTTP(S)·포트 조건은 유지합니다.",
        "site_added": "목록에 반영했습니다. ‘설정 저장’을 눌러 적용하세요.",
        "profile": "허용 목록 프로필", "profile_new": "다른 이름으로 저장…", "profile_rename": "이름 변경…", "profile_delete": "삭제",
        "profile_name": "프로필 이름 (1–64자)", "profile_error": "중복되지 않는 이름을 입력하세요. 프로필은 최대 32개이며 마지막 프로필은 삭제할 수 없습니다.",
        "profile_help": "프로그램과 브라우저별 사이트 목록을 함께 보관합니다. 선택·편집 후 ‘설정 저장’을 눌러 적용하세요. 감시·미리보기·시작프로그램은 공통 설정입니다.",
        "profile_confirm": "‘{name}’ 프로필을 삭제할까요? 설정 저장을 눌러야 삭제가 적용됩니다.",
        "recover": "캐릭터 화면 복구", "reset_default": "기본 외형으로 초기화",
        "recover_help": "안 보이거나 깨지면 ‘화면 복구’로 현재 외형을 다시 표시하세요. ‘기본 외형’은 설정 저장 후 적용됩니다.",
        "recovered": "캐릭터를 주 모니터로 복구했습니다. 허용 목록은 유지됩니다.",
        "random": "임의 캐릭터", "generate": "Qwen으로 생성", "restore": "이전 캐릭터로 변경",
        "model_help": "Qwen이 외형 설계값을 만들고 앱이 직접 그립니다. 애니메이션 모델은 필요 없습니다.\n모델 선택 옆 ‘명령 복사’와 ‘모델 준비 안내’를 이용하세요. 모델별로 최초 1회 다운로드가 필요합니다.",
        "generating": "로컬 모델로 생성 중…", "generated": "새 캐릭터를 만들었습니다. 설정 저장을 눌러 적용하세요.",
        "description": "원하는 캐릭터 설명 (최대 2,000자 · 선택 입력)",
        "description_help": "색·귀·눈 표정·장식·얼굴 무늬·꼬리·날개를 자세히 적으세요. Qwen이 지원되는 도형 중 가까운 특징을 고릅니다. 임의의 그림·의상·머리카락 생성은 지원하지 않습니다. 설명은 로컬 Ollama로만 보내며 설정에 저장하지 않습니다.",
        "description_example": "민트색 몸, 보라색 포인트, 여우 귀와 꼬리, 파란 눈, 행복한 표정, 주근깨, 리본, 요정 날개가 있는 독창적인 숲속 친구",
        "example": "예시 넣기", "clear_description": "설명 지우기", "custom_options": "직접 고르는 외형 옵션",
        "custom_help": "‘자동’ 또는 빈 색상은 Qwen이 정합니다. 직접 고른 값은 설명과 Qwen 결과보다 우선합니다. ‘옵션 적용’은 모델 없이 현재 외형에 선택값만 반영합니다. 미리보기 확인 후 ‘설정 저장’을 누르세요.",
        "auto": "자동", "apply_custom": "옵션 적용 (모델 불필요)", "choose_color": "색 선택…",
        "custom_error": "옵션을 확인하세요: 색상은 #RRGGBB, 설명은 최대 2,000자입니다.",
        "designer_model": "외형 설계 모델", "model_detail": "Qwen2.5 1.5B · 상세 설명 권장",
        "model_fast": "Qwen2.5 0.5B · 가벼움, 특징을 놓칠 수 있음",
        "credit": "기획·요구사항·관리: hobby-programmer-5000\n구현·문서·검증 지원: ChatGPT (Codex, OpenAI)\n\n앱 코드: MIT · Qt/Python/모델: 각각의 라이선스 적용",
        "status": "감시가 꺼져 있습니다. 캐릭터와 설정만 동작합니다.",
        "demo": "깨물기 애니메이션 미리보기", "pair_help": "코드를 복사했습니다. 확장 설정에서 같은 브라우저와 포트를 선택하고 ‘연결 코드’에 붙여넣은 뒤 ‘연결하고 확인’을 누르세요.",
        "connection_help": "위 ‘확장 설치·연결’을 누르면 도우미가 설치·연결 화면을 엽니다. 마지막 확인창에서 ‘예’를 누르세요.",
        "manual_connection": "수동 연결 — 고급 설정",
        "pair_question": "{browser} 확장을 연결할까요?\n\n설치·연결 도우미 또는 확장에서 연결을 시작했다면 예를 선택하세요.\n{origin}\n\n허용 사이트와 감시 설정은 바뀌지 않습니다.",
        "quit_wait": "캐릭터 생성이 끝난 뒤 종료하세요.", "bridge_error": "브라우저 연결을 시작할 수 없습니다: ",
        "bad_exe": "실행 파일 이름은 .exe로 끝나야 합니다.", "exe_filter": "Windows 실행 파일 (*.exe)",
    },
    "en": {
        "subtitle": "A little companion for a more focused desktop",
        "general": "General", "apps": "Applications", "web": "Browsers", "character": "Character", "about": "About",
        "guard": "Enable focus guardian", "preview": "Preview mode · animate without closing anything",
        "visible": "Show desktop companion", "startup": "Run when I sign in to Windows", "language": "Language",
        "theme": "Theme", "theme_dark": "Dark", "theme_light": "Light (white)",
        "theme_help": "Preview immediately. Save settings to keep your choice for next launch.",
        "advanced": "Advanced", "advanced_models": "Enable advanced character models",
        "vram_tier": "GPU VRAM capacity (manual)", "vram_unknown": "CPU / unknown",
        "advanced_help": "2/4/6/8 GB are model-selection guides, not GPU detection or a guarantee of fit. You need sufficient free VRAM and system RAM. Ollama determines GPU support and CPU offloading.",
        "advanced_scope": "Larger models may interpret descriptions better; the same vector shapes draw the character. They do not generate new artwork or clothing. Advanced preferences are saved separately from allowlist profiles.",
        "model_memory": "About {size} of model files; inference needs extra memory. Keep Ollama running and download the selected model below first.",
        "model_download": "Download ~{size} · extra free RAM/VRAM needed · keep Ollama running",
        "model_setup": "Model setup guide", "copy_model_command": "Copy command", "command_copied": "Copied",
        "model_command_copied": "Download command copied. Paste into PowerShell, press Enter, wait for success, then generate again in the app.",
        "model_setup_steps": "1. Install and start Ollama (ollama.com).\n2. Choose a GPU VRAM guide in Advanced, then a model in Character. 8 GB system RAM is different from 8 GB GPU VRAM.\n3. Copy that model's command, open PowerShell/Terminal from Win+X, paste and press Enter.\n4. Wait for success. ollama list must show the exact model name. Different names/quantizations are separate models.\n5. Generate with Qwen, inspect the preview and Save settings. Already installed models need no new download. The app does not install automatically.",
        "model_setup_limits": "Sizes are downloads; inference needs extra memory. VRAM guides do not guarantee fit. Start with 0.5B or 1.5B for CPU/unknown. Choose a smaller model if memory is insufficient. This guide does not change prompts or allowlists.",
        "model_missing_detail": "Ollama could not find or support the selected model:\n{model}\nRun in PowerShell: {command}\nWait for success, then generate again. If already installed, update Ollama and verify the exact name.",
        "model_guide_close": "Close", "model_selected": "Selected: {model}",
        "model_small_memory": "Model files: about 0.5 GB for 0.5B / 1.12 GB for 1.5B, plus inference memory. Keep Ollama running.",
        "model_missing": "The selected model is missing or unsupported by Ollama. Run the displayed ollama pull command, update Ollama, then try again.",
        "model_memory_error": "Not enough memory to run this model. Choose a smaller model or close other models/GPU tasks, then retry. Your current character is retained.",
        "model_service_error": "Ollama could not run the model. Check Ollama status, supported version and available memory, then retry.",
        "ollama_unavailable": "Ollama is unreachable or generation timed out. Start Ollama; if generation is slow, try a smaller model.",
        "save": "Save settings", "close": "Back to tray", "saved": "Settings saved.",
        "intro": "Check your allowlist in preview mode first.\nApps are controlled; tabs close only when website control is also on and the extension is connected.",
        "apps_help": "Enter one executable filename per line. Pasted paths are reduced to filenames.\nWindows, graphics/overlay helpers and this app are always protected. All files with the same name are allowed.",
        "browse": "Add executable…", "running": "Add open application…", "startup_scan": "Rescan startup apps",
        "browser_help": "Install and pair the extension in each browser. Only built-in new-tab/home pages are allowed initially.\nDomains allow whole sites; a URL path limits access to that section. Both http:// and https:// URLs work.",
        "browser_on": "Apply website allowlist to this browser", "pair": "Copy connection code", "extension": "Open extension folder",
        "website_control": "Website control ON/OFF — applies immediately",
        "website_help": "OFF controls applications only and leaves browser tabs alone. Website control requires the separate extension.",
        "setup": "Install/connect extension…", "connected": "Extension connected", "not_connected": "Extension not connected — use Install/connect",
        "website_saved": "Website control saved immediately. Application guardian settings are unchanged.",
        "connection_code": "Connection code", "port": "Port", "startup_list": "Startup applications",
        "rules": "Allowed addresses · one per line (example.com/* or example.com/section/*)",
        "site_line": "Allowed address, line {line}: {message}",
        "invalid_url": "Enter a domain or a complete http:// or https:// URL including its hostname.",
        "invalid_port": "Enter a port between 1 and 65535.",
        "invalid_path": "Remove dot segments, backslashes and encoded separators from the path.",
        "invalid_wildcard": "Use * only as a subdomain prefix (*.host) or a final /* path suffix.",
        "invalid_subdomain": "Use a domain such as example.com to include subdomains. Add IP addresses and localhost individually.",
        "add_site": "Add address", "include_subdomains": "Include subdomains of this address",
        "subdomain_help": "You can enter console.example.com directly. Check to add the entered host and its subdomains together: example.com + *.example.com. Path, query, HTTP(S) and port constraints are retained.",
        "site_added": "Updated the list. Save settings to apply it.",
        "profile": "Allowlist profile", "profile_new": "Save as…", "profile_rename": "Rename…", "profile_delete": "Delete",
        "profile_name": "Profile name (1–64 characters)", "profile_error": "Use a unique name. Keep 1–32 profiles; the last profile cannot be deleted.",
        "profile_help": "Stores applications and per-browser sites together. Select or edit a profile, then Save settings to apply. Guardian, preview and startup apps are shared.",
        "profile_confirm": "Delete profile ‘{name}’? Save settings to apply the deletion.",
        "recover": "Recover companion on screen", "reset_default": "Reset default appearance",
        "recover_help": "If missing or broken, recover the current appearance on screen. Resetting the default appearance takes effect after Save settings.",
        "recovered": "Companion recovered on the primary monitor. Allowlists are unchanged.",
        "random": "Random character", "generate": "Generate with Qwen", "restore": "Use previous character",
        "model_help": "Qwen designs appearance parameters; the app draws and animates them. No motion model is required.\nUse Copy command and Model setup guide beside the selector. Each model needs its own first download.",
        "generating": "Generating with local model…", "generated": "Character created. Save settings to apply it.",
        "description": "Describe your character (optional · up to 2,000 characters)",
        "description_help": "Describe colors, ears, eye expression, accessory, face markings, tail and wings. Qwen picks the closest supported shapes. Arbitrary artwork, clothing and hairstyles are not supported. The description goes only to local Ollama and is not saved in settings.",
        "description_example": "An original woodland friend with a mint body, purple accents, fox ears and tail, blue eyes, a happy expression, freckles, a bow and fairy wings",
        "example": "Insert example", "clear_description": "Clear description", "custom_options": "Choose appearance options",
        "custom_help": "Auto or blank colors let Qwen choose. Explicit choices override the description and model output. Apply options changes only the selected traits of the current appearance, without a model. Check the preview, then Save settings.",
        "auto": "Auto", "apply_custom": "Apply options (no model needed)", "choose_color": "Choose color…",
        "custom_error": "Check options: colors must be #RRGGBB and the description at most 2,000 characters.",
        "designer_model": "Appearance model", "model_detail": "Qwen2.5 1.5B · recommended for descriptions",
        "model_fast": "Qwen2.5 0.5B · lighter, may miss requested traits",
        "credit": "Product direction, requirements, maintenance: hobby-programmer-5000\nImplementation, documentation, validation assistance: ChatGPT (Codex, OpenAI)\n\nApp code: MIT · Qt, Python and model retain their own licenses",
        "status": "Guardian is off. Only the companion and settings are active.",
        "demo": "Preview bite animation", "pair_help": "Code copied. In extension settings, choose this browser and port, paste into Connection code, then click Connect and test.",
        "connection_help": "Use Install/connect extension above. Its helper opens installation and connection pages; approve the final request in this app.",
        "manual_connection": "Manual connection — advanced",
        "pair_question": "Connect this {browser} extension?\n\nChoose Yes if you started connection in the setup helper or the extension.\n{origin}\n\nAllowlist and guardian settings will stay as configured.",
        "quit_wait": "Wait for character generation to finish before quitting.", "bridge_error": "Browser connection unavailable: ",
        "bad_exe": "Executable names must end with .exe.", "exe_filter": "Windows application (*.exe)",
    },
}

STYLE = """
QWidget { background: #171b2a; color: #e9e8f2; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 13px; }
QDialog { background: #171b2a; }
QLabel#brand { font-size: 30px; font-weight: 700; color: #d2c1ff; }
QLabel#subtitle { color: #a9afc5; font-size: 14px; }
QLabel#status { color: #a8dace; padding: 10px; background: #202d35; border-radius: 8px; }
QTabWidget::pane { border: 1px solid #353b53; border-radius: 12px; background: #1d2234; }
QTabBar::tab { padding: 12px 19px; color: #a9afc5; margin: 0 2px 7px 0; border-radius: 8px; }
QTabBar::tab:selected { background: #363047; color: #e1cfff; }
QTabWidget QWidget { background-color: transparent; }
QPushButton { background: #2c334b; border: 1px solid #414962; border-radius: 8px; padding: 9px 15px; }
QPushButton:hover { background: #3d4563; border-color: #b6a0eb; }
QPushButton:disabled { color: #6d738d; }
QPushButton#primary { background: #c5b0f4; color: #211b32; border: 0; font-weight: 600; }
QPushButton#primary:hover { background: #dac9ff; }
QPlainTextEdit, QLineEdit, QListWidget { background: #131725; border: 1px solid #3c435b; border-radius: 8px; padding: 8px; selection-background-color: #625182; selection-color: #fff; }
QComboBox { background: #242b40; border: 1px solid #414962; border-radius: 7px; padding: 7px; min-width: 125px; }
QComboBox QAbstractItemView { background: #242b40; selection-background-color: #625182; selection-color: #fff; }
QCheckBox { spacing: 10px; padding: 6px 0; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #66708b; border-radius: 5px; background: #151929; }
QCheckBox::indicator:checked { background: #bba2ed; border-color: #d8c6ff; }
QToolTip { background: #303650; color: #fff; border: 0; }
QLabel#setupTitle { font-size: 21px; font-weight: 600; color: #d2c1ff; }
"""

LIGHT_COLORS = {
    "#171b2a": "#fafafe", "#e9e8f2": "#242238", "#d2c1ff": "#634095",
    "#a9afc5": "#55566d", "#a8dace": "#20594d", "#202d35": "#e4f3ed",
    "#353b53": "#d2d5e2", "#1d2234": "#ffffff", "#363047": "#e9ddfa",
    "#e1cfff": "#503477", "#2c334b": "#efedf6", "#414962": "#b9b9cf",
    "#3d4563": "#e2d7f2", "#b6a0eb": "#8060b0", "#6d738d": "#747386",
    "#c5b0f4": "#714a9d", "#211b32": "#ffffff", "#dac9ff": "#5f3d88",
    "#131725": "#ffffff", "#3c435b": "#bfc1d0", "#625182": "#d8c5ef",
    "#242b40": "#ffffff", "#66708b": "#8c8da3", "#151929": "#ffffff",
    "#bba2ed": "#7953a7", "#d8c6ff": "#634095", "#303650": "#f0eaf8",
    "#fff": "#242238",
}


def theme_style(theme):
    return re.sub(r"#[0-9a-fA-F]{3,6}\b", lambda match: LIGHT_COLORS.get(match[0], match[0]), STYLE) if theme == "light" else STYLE


CHARACTER_LABELS = {
    "en": {
        "body": "Body color", "accent": "Accent color", "eye_color": "Eye color", "ears": "Ears",
        "accessory": "Accessory", "eyes": "Eye expression", "markings": "Face markings", "tail": "Tail", "wings": "Wings",
        "rabbit": "Rabbit", "cat": "Cat", "bear": "Bear", "fox": "Fox", "none": "None", "scarf": "Scarf",
        "star": "Star", "leaf": "Leaf", "bow": "Bow", "bell": "Bell", "round": "Round", "sleepy": "Sleepy",
        "happy": "Happy", "freckles": "Freckles", "stripes": "Stripes", "spots": "Spots", "puff": "Puff",
        "fairy": "Fairy", "bat": "Bat",
    },
    "ko": {
        "body": "몸 색상", "accent": "포인트 색상", "eye_color": "눈 색상", "ears": "귀",
        "accessory": "장식", "eyes": "눈 표정", "markings": "얼굴 무늬", "tail": "꼬리", "wings": "날개",
        "rabbit": "토끼", "cat": "고양이", "bear": "곰", "fox": "여우", "none": "없음", "scarf": "목도리",
        "star": "별", "leaf": "나뭇잎", "bow": "리본", "bell": "방울", "round": "동그란 눈", "sleepy": "졸린 눈",
        "happy": "웃는 눈", "freckles": "주근깨", "stripes": "줄무늬", "spots": "반점", "puff": "방울 꼬리",
        "fairy": "요정", "bat": "박쥐",
    },
}


class GenerationWorker(QThread):
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, description="", overrides=None, model=MODEL, parent=None):
        super().__init__(parent)
        self.description = description
        self.overrides = dict(overrides or {})
        self.model = model

    def run(self):
        try:
            self.succeeded.emit(generate_character(self.description, self.overrides, self.model))
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.description = ""


def model_setup_rows():
    return (("CPU", MODEL, "0.49 GB"), ("2 GB / CPU", DETAIL_MODEL, "1.12 GB"),
            *((f"{info[0]} GB", model, info[2]) for model, info in GPU_MODELS.items()))


class ModelSetupDialog(QDialog):
    """Local help only: no model download, inference, or settings mutation."""
    def __init__(self, selected_model, language="en", parent=None):
        super().__init__(parent)
        self.t = TEXT["ko" if language == "ko" else "en"]
        self.setWindowTitle(self.t["model_setup"])
        self.resize(780, 640)
        self.setMinimumSize(650, 520)
        outer = QVBoxLayout(self)
        title = QLabel(self.t["model_setup"])
        title.setObjectName("setupTitle")
        outer.addWidget(title)
        selected = QLabel(self.t["model_selected"].format(model=selected_model))
        selected.setWordWrap(True)
        selected.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(selected)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        steps = QLabel(self.t["model_setup_steps"])
        steps.setWordWrap(True)
        layout.addWidget(steps)
        self.command_fields = {}
        self.copy_buttons = {}
        for tier, model, size in model_setup_rows():
            heading = QLabel(f"{tier} · {model[6:]} · {size}")
            heading.setWordWrap(True)
            layout.addWidget(heading)
            row = QHBoxLayout()
            command = QLineEdit("ollama pull " + model)
            command.setReadOnly(True)
            self.command_fields[model] = command
            row.addWidget(command, 1)
            copy = QPushButton(self.t["copy_model_command"])
            copy.clicked.connect(lambda _, model=model: self.copy_command(model))
            self.copy_buttons[model] = copy
            row.addWidget(copy)
            layout.addLayout(row)
        limits = QLabel(self.t["model_setup_limits"])
        limits.setObjectName("modelSetupLimits")
        limits.setWordWrap(True)
        layout.addWidget(limits)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        close = QPushButton(self.t["model_guide_close"])
        close.clicked.connect(self.accept)
        outer.addWidget(close)

    def copy_command(self, model):
        QApplication.clipboard().setText(self.command_fields[model].text())
        self.copy_buttons[model].setText(self.t["command_copied"])


class SettingsDialog(QDialog):
    applied = Signal()
    language_changed = Signal()
    demo_requested = Signal()
    recovery_requested = Signal()

    def __init__(self, settings, parent=None, connection_check=None):
        super().__init__(parent)
        self.settings = settings
        self.config = settings.snapshot()
        self.t = TEXT.get(self.config["language"], TEXT["en"])
        self.worker = None
        self.connection_check = connection_check or (lambda _: False)
        self.setup_dialog = None
        self.setWindowTitle("Pawzura")
        self.resize(920, 720)
        self.setMinimumSize(820, 640)
        self.preview_theme(self.config.get("theme", "dark"))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(13)
        brand = QLabel("Pawzura / 파우주라" if self.config["language"] == "ko" else "Pawzura")
        brand.setObjectName("brand")
        outer.addWidget(brand)
        subtitle = QLabel(self.t["subtitle"])
        subtitle.setObjectName("subtitle")
        outer.addWidget(subtitle)
        self.build_profiles(outer)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self.build_general()
        self.build_apps()
        self.build_browsers()
        self.build_character()
        self.build_advanced()
        self.build_about()
        self.preview_theme(self.config.get("theme", "dark"))
        self.message = QLabel(self.t["status"] if not self.config["guard_enabled"] else self.t["preview"] if self.config["preview_only"] else self.t["guard"])
        self.message.setObjectName("status")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(self.message)
        footer = QHBoxLayout()
        footer.addWidget(QLabel(f"v{__version__}  ·  Windows companion"))
        footer.addStretch()
        close = QPushButton(self.t["close"])
        close.clicked.connect(self.hide)
        save = QPushButton(self.t["save"])
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        footer.addWidget(close)
        footer.addWidget(save)
        outer.addLayout(footer)
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.refresh_connection)
        self.connection_timer.start(1000)

    def build_profiles(self, outer):
        row = QHBoxLayout()
        row.addWidget(QLabel(self.t["profile"]))
        self.profile_select = QComboBox()
        self.profile_select.addItems(self.config["profiles"])
        self.profile_select.setCurrentText(self.config["active_profile"])
        self.profile_select.currentTextChanged.connect(self.switch_profile)
        row.addWidget(self.profile_select, 1)
        for key, callback in (("profile_new", self.new_profile), ("profile_rename", self.rename_profile), ("profile_delete", self.delete_profile)):
            button = QPushButton(self.t[key])
            button.clicked.connect(callback)
            row.addWidget(button)
        outer.addLayout(row)
        outer.addWidget(self.label(self.t["profile_help"]))

    def store_profile(self):
        self.store_browser()
        apps = sorted({normalize_app(line) for line in self.apps.toPlainText().splitlines() if line.strip()})
        if any(not app.endswith(".exe") for app in apps):
            raise ValueError(self.t["bad_exe"])
        self.config["allowed_apps"] = apps
        self.config["profiles"][self.config["active_profile"]] = profile_lists(self.config)

    def refresh_profiles(self):
        self.profile_select.blockSignals(True)
        self.profile_select.clear()
        self.profile_select.addItems(self.config["profiles"])
        self.profile_select.setCurrentText(self.config["active_profile"])
        self.profile_select.blockSignals(False)

    def load_profile(self, name):
        self.config.update(copy.deepcopy(self.config["profiles"][name]))
        self.config["active_profile"] = name
        self.apps.setPlainText("\n".join(self.config["allowed_apps"]))
        self.load_browser()
        self.refresh_profiles()

    def switch_profile(self, name):
        if not name or name == self.config["active_profile"]:
            return
        try:
            self.store_profile()
            self.load_profile(name)
            self.message.setText(self.t["profile_help"])
        except ValueError as error:
            self.message.setText(str(error))
            self.refresh_profiles()

    def request_profile_name(self, current=""):
        name, ok = QInputDialog.getText(self, "Pawzura", self.t["profile_name"], text=current)
        if not ok:
            return None
        name = name.strip()
        if not name or len(name) > 64 or any(existing.casefold() == name.casefold() for existing in self.config["profiles"] if existing != current):
            raise ValueError(self.t["profile_error"])
        return name

    def new_profile(self):
        try:
            self.store_profile()
            if len(self.config["profiles"]) >= 32:
                raise ValueError(self.t["profile_error"])
            name = self.request_profile_name()
            if name:
                self.config["profiles"][name] = profile_lists(self.config)
                self.load_profile(name)
                self.message.setText(self.t["profile_help"])
        except ValueError as error:
            self.message.setText(str(error))

    def rename_profile(self):
        try:
            self.store_profile()
            current = self.config["active_profile"]
            name = self.request_profile_name(current)
            if name and name != current:
                self.config["profiles"][name] = self.config["profiles"].pop(current)
                self.config["active_profile"] = name
                self.refresh_profiles()
        except ValueError as error:
            self.message.setText(str(error))

    def delete_profile(self):
        if len(self.config["profiles"]) <= 1:
            self.message.setText(self.t["profile_error"])
            return
        name = self.config["active_profile"]
        if QMessageBox.question(self, "Pawzura", self.t["profile_confirm"].format(name=name), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            del self.config["profiles"][name]
            self.load_profile(next(iter(self.config["profiles"])))

    def page(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(13)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, self.t[title])
        return layout

    def label(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    def build_general(self):
        layout = self.page("general")
        layout.addWidget(self.label(self.t["intro"]))
        self.guard = QCheckBox(self.t["guard"])
        self.preview = QCheckBox(self.t["preview"])
        self.visible = QCheckBox(self.t["visible"])
        self.startup = QCheckBox(self.t["startup"])
        for widget, key in ((self.guard, "guard_enabled"), (self.preview, "preview_only"), (self.visible, "pet_visible"), (self.startup, "start_at_login")):
            widget.setChecked(self.config[key])
            layout.addWidget(widget)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("한국어", "ko")
        self.language.setCurrentIndex(self.language.findData(self.config["language"]))
        form.addRow(self.t["language"], self.language)
        self.theme = QComboBox()
        self.theme.addItem(self.t["theme_dark"], "dark")
        self.theme.addItem(self.t["theme_light"], "light")
        self.theme.setCurrentIndex(max(0, self.theme.findData(self.config.get("theme", "dark"))))
        self.theme.currentIndexChanged.connect(lambda: self.preview_theme(self.theme.currentData()))
        form.addRow(self.t["theme"], self.theme)
        layout.insertLayout(1, form)
        self.theme.setToolTip(self.t["theme_help"])
        demo = QPushButton(self.t["demo"])
        demo.clicked.connect(self.demo_requested.emit)
        layout.addWidget(demo, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

    def preview_theme(self, theme):
        light = theme == "light"
        palette = QPalette()
        for role, color in (
            (QPalette.ColorRole.Window, "#fafafe" if light else "#171b2a"),
            (QPalette.ColorRole.Base, "#ffffff" if light else "#131725"),
            (QPalette.ColorRole.Button, "#efedf6" if light else "#2c334b"),
            (QPalette.ColorRole.Text, "#242238" if light else "#e9e8f2"),
            (QPalette.ColorRole.WindowText, "#242238" if light else "#e9e8f2"),
            (QPalette.ColorRole.ButtonText, "#242238" if light else "#e9e8f2"),
            (QPalette.ColorRole.PlaceholderText, "#68667e" if light else "#a9afc5"),
            (QPalette.ColorRole.Highlight, "#714a9d" if light else "#625182"),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)
        self.setStyleSheet(theme_style(theme))
        if hasattr(self, "character_preview"):
            self.character_preview.theme = theme
            self.character_preview.update()

    def build_apps(self):
        layout = self.page("apps")
        layout.addWidget(self.label(self.t["apps_help"]))
        self.apps = QPlainTextEdit("\n".join(self.config["allowed_apps"]))
        layout.addWidget(self.apps, 1)
        buttons = QHBoxLayout()
        browse = QPushButton(self.t["browse"])
        browse.clicked.connect(self.browse_app)
        running = QPushButton(self.t["running"])
        running.clicked.connect(self.add_running)
        scan = QPushButton(self.t["startup_scan"])
        scan.clicked.connect(self.rescan_startup)
        for button in (browse, running, scan):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.startup_label = self.label(self.t["startup_list"] + ": " + ", ".join(self.config["startup_apps"]))
        self.startup_label.setMaximumHeight(65)
        layout.addWidget(self.startup_label)

    def browse_app(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.t["browse"], "", self.t["exe_filter"])
        if filename:
            self.apps.appendPlainText(normalize_app(filename))

    def add_running(self):
        names = sorted({normalize_app(w.executable) for w in windows.list_windows()})
        item, ok = QInputDialog.getItem(self, "Pawzura", self.t["running"], names, 0, False)
        if ok and item:
            self.apps.appendPlainText(item)

    def rescan_startup(self):
        self.config["startup_apps"] = windows.startup_apps()
        self.startup_label.setText(self.t["startup_list"] + ": " + ", ".join(self.config["startup_apps"]))

    def build_browsers(self):
        layout = self.page("web")
        self.website_control = QCheckBox(self.t["website_control"].replace("ON/OFF", "ON" if self.config["browser_control_enabled"] else "OFF"))
        self.website_control.setChecked(self.config["browser_control_enabled"])
        self.website_control.toggled.connect(self.toggle_website_control)
        layout.addWidget(self.website_control)
        layout.addWidget(self.label(self.t["website_help"]))
        row = QHBoxLayout()
        self.browser_select = QComboBox()
        self.browser_select.addItems(BROWSERS)
        self.browser_select.setMaximumWidth(150)
        row.addWidget(self.browser_select)
        self.setup_button = QPushButton(self.t["setup"])
        self.setup_button.setObjectName("primary")
        self.setup_button.clicked.connect(self.open_setup)
        row.addWidget(self.setup_button)
        self.connection_status = self.label(self.t["not_connected"])
        row.addWidget(self.connection_status, 1)
        layout.addLayout(row)
        self.browser_on = QCheckBox(self.t["browser_on"])
        layout.addWidget(self.browser_on)
        add_row = QHBoxLayout()
        self.site_entry = QLineEdit()
        self.site_entry.setPlaceholderText("https://console.example.com")
        self.site_entry.setAccessibleName(self.t["add_site"])
        self.site_entry.returnPressed.connect(self.add_site)
        add_row.addWidget(self.site_entry, 1)
        add = QPushButton(self.t["add_site"])
        add.clicked.connect(self.add_site)
        add_row.addWidget(add)
        layout.addLayout(add_row)
        self.include_subdomains = QCheckBox(self.t["include_subdomains"])
        self.include_subdomains.setToolTip(self.t["subdomain_help"])
        self.include_subdomains.setAccessibleDescription(self.t["subdomain_help"])
        layout.addWidget(self.include_subdomains)
        layout.addWidget(self.label(self.t["rules"]))
        self.sites = QPlainTextEdit()
        self.sites.setMinimumHeight(130)
        self.sites.setPlaceholderText("https://console.example.com\nexample.com/*\n*.example.com\nexample.org/courses/*\nhttp://localhost:3000")
        layout.addWidget(self.sites, 1)
        self.current_browser = BROWSERS[0]
        self.load_browser()
        self.browser_select.currentTextChanged.connect(self.switch_browser)
        layout.addWidget(self.label(self.t["connection_help"]))
        manual = QCheckBox(self.t["manual_connection"])
        layout.addWidget(manual)
        panel = QWidget()
        connection = QFormLayout(panel)
        self.connection_code = QLineEdit(self.config["bridge_token"])
        self.connection_code.setReadOnly(True)
        self.connection_code.setEchoMode(QLineEdit.EchoMode.Password)
        connection.addRow(self.t["connection_code"], self.connection_code)
        connection.addRow(self.t["port"], QLabel(str(self.config["bridge_port"])))
        pair = QPushButton(self.t["pair"])
        pair.clicked.connect(self.copy_pairing)
        connection.addRow(pair)
        panel.setVisible(False)
        manual.toggled.connect(panel.setVisible)
        layout.addWidget(panel)

    def toggle_website_control(self, enabled):
        try:
            self.settings.save({"browser_control_enabled": enabled})
            self.config["browser_control_enabled"] = enabled
            self.website_control.setText(self.t["website_control"].replace("ON/OFF", "ON" if enabled else "OFF"))
            self.applied.emit()
            self.message.setText(self.t["website_saved"])
        except (ValueError, OSError) as error:
            self.website_control.blockSignals(True)
            self.website_control.setChecked(self.settings.snapshot()["browser_control_enabled"])
            self.website_control.blockSignals(False)
            QMessageBox.warning(self, "Pawzura", str(error))

    def refresh_connection(self):
        if self.isVisible():
            self.website_control.setText(self.t["website_control"].replace("ON/OFF", "ON" if self.website_control.isChecked() else "OFF"))
            self.connection_status.setText(self.t["connected"] if self.connection_check(self.current_browser) else self.t["not_connected"])

    def open_setup(self):
        if self.setup_dialog:
            self.setup_dialog.hide()
            self.setup_dialog.deleteLater()
        self.setup_dialog = BrowserSetupDialog(self.current_browser, self.config["bridge_port"], self.config["language"], self.connection_check, self)
        self.setup_dialog.show()
        self.setup_dialog.raise_()

    def store_browser(self):
        rules = []
        for number, line in enumerate(self.sites.toPlainText().splitlines(), 1):
            if not line.strip():
                continue
            try:
                rules.append(site_rule(line))
            except SiteRuleError as error:
                raise ValueError(self.t["site_line"].format(line=number, message=self.t[error.code])) from error
        self.config["browsers"][self.current_browser] = {"enabled": self.browser_on.isChecked(), "allowed_sites": sorted(set(rules))}
        self.sites.setPlainText("\n".join(sorted(set(rules))))

    def add_site(self):
        try:
            additions = address_rules(self.site_entry.text(), self.include_subdomains.isChecked())
        except SiteRuleError as error:
            self.message.setText(self.t[error.code])
            return
        known = set()
        for line in self.sites.toPlainText().splitlines():
            if line.strip():
                try:
                    known.add(site_rule(line))
                except SiteRuleError:
                    pass  # Preserve an invalid unsaved draft for the user's correction.
        for rule in additions:
            if rule not in known:
                self.sites.appendPlainText(rule)
                known.add(rule)
        self.site_entry.clear()
        self.message.setText(self.t["site_added"])

    def load_browser(self):
        entry = self.config["browsers"][self.current_browser]
        self.browser_on.setChecked(entry["enabled"])
        self.sites.setPlainText("\n".join(entry["allowed_sites"]))
        self.site_entry.clear()
        self.include_subdomains.setChecked(False)

    def switch_browser(self, name):
        try:
            self.store_browser()
        except ValueError as error:
            self.message.setText(str(error))
            self.browser_select.blockSignals(True)
            self.browser_select.setCurrentText(self.current_browser)
            self.browser_select.blockSignals(False)
            return
        self.current_browser = name
        self.load_browser()

    def copy_pairing(self):
        config = self.settings.snapshot()
        QApplication.clipboard().setText(config["bridge_token"])
        self.message.setText(self.t["pair_help"])

    def open_extension(self):
        root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        folder = root / "extensions"
        if not folder.exists():
            folder = Path(getattr(sys, "_MEIPASS", root)) / "extensions"
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def build_character(self):
        layout = self.page("character")
        designer = QHBoxLayout()
        self.character_preview = CharacterPreview(self.config["character"])
        self.character_preview.setFixedSize(200, 220)
        designer.addWidget(self.character_preview, 0, Qt.AlignmentFlag.AlignTop)
        prompt = QVBoxLayout()
        designer.addLayout(prompt, 1)
        layout.addLayout(designer)
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel(self.t["designer_model"]))
        self.character_model = QComboBox()
        self.character_model.addItem(self.t["model_detail"], DETAIL_MODEL)
        self.character_model.addItem(self.t["model_fast"], MODEL)
        selected = self.config.get("designer_model", DETAIL_MODEL)
        for model in models_for_vram(self.config["vram_tier"], self.config["advanced_models"])[2:]:
            self.character_model.addItem(GPU_MODELS[model][1], model)
        self.character_model.setCurrentIndex(max(0, self.character_model.findData(selected)))
        model_row.addWidget(self.character_model, 1)
        prompt.addLayout(model_row)
        self.model_command = QLineEdit()
        self.model_command.setReadOnly(True)
        command_row = QHBoxLayout()
        command_row.addWidget(self.model_command, 1)
        self.copy_model_button = QPushButton(self.t["copy_model_command"])
        self.copy_model_button.clicked.connect(self.copy_model_command)
        command_row.addWidget(self.copy_model_button)
        prompt.addLayout(command_row)
        self.model_memory = self.label("")
        prompt.addWidget(self.model_memory)
        setup = QPushButton(self.t["model_setup"])
        setup.clicked.connect(self.show_model_setup)
        prompt.addWidget(setup, alignment=Qt.AlignmentFlag.AlignLeft)
        self.character_model.currentIndexChanged.connect(self.refresh_model_help)
        self.refresh_model_help()
        prompt.addWidget(self.label(self.t["description"]))
        self.character_description = QPlainTextEdit()
        self.character_description.setPlaceholderText(self.t["description_example"])
        self.character_description.setFixedHeight(85)
        prompt.addWidget(self.character_description)
        prompt_actions = QHBoxLayout()
        example = QPushButton(self.t["example"])
        example.clicked.connect(lambda: self.character_description.setPlainText(self.t["description_example"]))
        clear = QPushButton(self.t["clear_description"])
        clear.clicked.connect(self.character_description.clear)
        self.description_count = QLabel(f"0 / {MAX_PROMPT}")
        self.character_description.textChanged.connect(lambda: self.description_count.setText(
            f"{len(self.character_description.toPlainText())} / {MAX_PROMPT}"))
        prompt_actions.addWidget(example)
        prompt_actions.addWidget(clear)
        self.generate_button = QPushButton(self.t["generate"])
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.generate)
        prompt_actions.addWidget(self.generate_button)
        prompt_actions.addWidget(self.description_count)
        prompt.addLayout(prompt_actions)
        layout.addWidget(self.label(self.t["description_help"]))
        row = QHBoxLayout()
        controls = QGridLayout()
        self.random_button = QPushButton(self.t["random"])
        self.random_button.clicked.connect(lambda: self.apply_character(random_character()))
        previous = QPushButton(self.t["restore"])
        self.previous_button = previous
        previous.clicked.connect(self.restore_character)
        controls.addWidget(self.random_button, 0, 0)
        controls.addWidget(previous, 0, 1)
        recover = QPushButton(self.t["recover"])
        recover.clicked.connect(self.recovery_requested.emit)
        controls.addWidget(recover, 1, 0)
        self.reset_button = QPushButton(self.t["reset_default"])
        self.reset_button.clicked.connect(lambda: self.apply_character(default_character()))
        controls.addWidget(self.reset_button, 1, 1)
        for button in (self.random_button, self.generate_button, previous, recover, self.reset_button):
            button.setMinimumHeight(38)
        row.addLayout(controls, 2)
        layout.addLayout(row, 1)
        layout.addWidget(self.label(self.t["custom_options"]))
        layout.addWidget(self.label(self.t["custom_help"]))
        self.custom_panel = QWidget()
        custom = QGridLayout(self.custom_panel)
        custom.setContentsMargins(0, 0, 0, 0)
        labels = CHARACTER_LABELS[self.config["language"] if self.config["language"] == "ko" else "en"]
        self.character_colors, self.character_choices = {}, {}
        for row_number, key in enumerate(COLORS):
            field = QLineEdit()
            field.setPlaceholderText("#RRGGBB · " + self.t["auto"])
            self.character_colors[key] = field
            choose = QPushButton(self.t["choose_color"])
            choose.clicked.connect(lambda _, key=key: self.choose_character_color(key))
            custom.addWidget(QLabel(labels[key]), row_number, 0)
            custom.addWidget(field, row_number, 1)
            custom.addWidget(choose, row_number, 2)
        for number, (key, values) in enumerate(FEATURES.items()):
            field = QComboBox()
            field.addItem(self.t["auto"], None)
            for value in values:
                field.addItem(labels[value], value)
            self.character_choices[key] = field
            row_number, column = len(COLORS) + number // 2, (number % 2) * 2
            custom.addWidget(QLabel(labels[key]), row_number, column)
            custom.addWidget(field, row_number, column + 1)
        layout.addWidget(self.custom_panel)
        self.custom_button = QPushButton(self.t["apply_custom"])
        self.custom_button.clicked.connect(self.apply_custom_options)
        layout.addWidget(self.custom_button)
        layout.addWidget(self.label(self.t["recover_help"]))
        layout.addWidget(self.label(self.t["model_help"]))

    def refresh_model_help(self):
        model = self.character_model.currentData()
        self.model_command.setText("ollama pull " + model)
        size = next(size for _, name, size in model_setup_rows() if name == model)
        self.model_memory.setText(self.t["model_download"].format(size=size))

    def copy_model_command(self):
        QApplication.clipboard().setText(self.model_command.text())
        self.message.setText(self.t["model_command_copied"])

    def show_model_setup(self):
        ModelSetupDialog(self.character_model.currentData(), self.config["language"], self).exec()

    def build_advanced(self):
        layout = self.page("advanced")
        layout.addWidget(self.label(self.t["advanced_scope"]))
        self.advanced_models = QCheckBox(self.t["advanced_models"])
        self.advanced_models.setChecked(self.config["advanced_models"])
        layout.addWidget(self.advanced_models)
        form = QFormLayout()
        self.vram_tier = QComboBox()
        for value in (0, 2, 4, 6, 8):
            self.vram_tier.addItem(self.t["vram_unknown"] if value == 0 else f"{value} GB", value)
        self.vram_tier.setCurrentIndex(self.vram_tier.findData(self.config["vram_tier"]))
        form.addRow(self.t["vram_tier"], self.vram_tier)
        layout.addLayout(form)
        layout.addWidget(self.label(self.t["advanced_help"]))
        setup = QPushButton(self.t["model_setup"])
        setup.clicked.connect(self.show_model_setup)
        layout.addWidget(setup, alignment=Qt.AlignmentFlag.AlignLeft)
        for tier, model in ((2, DETAIL_MODEL), *((info[0], model) for model, info in GPU_MODELS.items())):
            name = "Qwen2.5 1.5B · Q4_K_M" if model == DETAIL_MODEL else GPU_MODELS[model][1]
            layout.addWidget(self.label(f"{tier} GB → {name}"))
        layout.addStretch()
        self.advanced_models.toggled.connect(self.refresh_model_choices)
        self.vram_tier.currentIndexChanged.connect(self.refresh_model_choices)
        self.vram_tier.setEnabled(self.advanced_models.isChecked())

    def refresh_model_choices(self):
        advanced = self.advanced_models.isChecked()
        self.vram_tier.setEnabled(advanced)
        selected = self.character_model.currentData()
        self.character_model.blockSignals(True)
        self.character_model.clear()
        for model in models_for_vram(self.vram_tier.currentData(), advanced):
            label = self.t["model_detail"] if model == DETAIL_MODEL else self.t["model_fast"] if model == MODEL else GPU_MODELS[model][1]
            self.character_model.addItem(label, model)
        self.character_model.setCurrentIndex(max(0, self.character_model.findData(selected)))
        self.character_model.blockSignals(False)
        self.refresh_model_help()

    def choose_character_color(self, key):
        field = self.character_colors[key]
        initial = QColor(field.text().strip() or self.config["character"].get(key, "#34304a"))
        color = QColorDialog.getColor(initial, self, self.t["choose_color"])
        if color.isValid():
            field.setText(color.name())

    def selected_character_options(self):
        options = {key: field.text().strip() for key, field in self.character_colors.items() if field.text().strip()}
        options.update({key: field.currentData() for key, field in self.character_choices.items() if field.currentData() is not None})
        return custom_options(options)

    def apply_custom_options(self):
        try:
            options = self.selected_character_options()
            if options:
                self.apply_character({**self.config["character"], **options, "source": "custom"})
        except ValueError:
            self.message.setText(self.t["custom_error"])

    def apply_character(self, spec):
        spec = safe_character(spec)
        old = self.config["character"]
        self.config["character_history"] = (self.config["character_history"] + [old])[-20:]
        self.config["character"] = spec
        self.character_preview.spec = spec
        self.character_preview.update()
        self.message.setText(self.t["generated"])

    def restore_character(self):
        if self.config["character_history"]:
            spec = self.config["character_history"].pop()
            self.config["character"] = spec
            self.character_preview.spec = spec
            self.character_preview.update()

    def generate(self):
        if self.worker and self.worker.isRunning():
            return
        description = self.character_description.toPlainText()
        try:
            if len(description) > MAX_PROMPT:
                raise ValueError("Description too long")
            options = self.selected_character_options()
        except ValueError:
            self.message.setText(self.t["custom_error"])
            return
        self.generation_controls = (self.generate_button, self.reset_button, self.language, self.random_button,
                                    self.previous_button, self.custom_button, self.custom_panel, self.character_model,
                                    self.advanced_models, self.vram_tier)
        for control in self.generation_controls:
            control.setEnabled(False)
        self.message.setText(self.t["generating"])
        self.worker = GenerationWorker(description, options, self.character_model.currentData(), self)
        self.worker.succeeded.connect(self.apply_character)
        self.worker.failed.connect(self.generation_failed)
        self.worker.finished.connect(self.finish_generation_controls)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: setattr(self, "worker", None))
        self.worker.start()

    def generation_failed(self, error):
        if error == "model_missing":
            model = self.worker.model if self.worker is not None else self.character_model.currentData()
            message = self.t["model_missing_detail"].format(model=model, command="ollama pull " + model)
        else:
            message = "Ollama: " + self.t.get(error, error)
        self.message.setText(message)

    def finish_generation_controls(self):
        for control in self.generation_controls:
            control.setEnabled(True)
        self.vram_tier.setEnabled(self.advanced_models.isChecked())

    def build_about(self):
        layout = self.page("about")
        layout.addWidget(self.label(self.t["credit"]))
        language = "ko" if self.config["language"] == "ko" else "en"
        layout.addWidget(self.label(f"Qwen2.5 0.5B / 1.5B · Qwen3 4B / 8B GGUF · Apache-2.0\nhttps://huggingface.co/Qwen\n\nREADME.md · doc/{language}/MODELS.md\nTHIRD-PARTY-NOTICES.md · CONTRIBUTORS.md"))
        layout.addWidget(self.label("https://github.com/hobby-programmer-5000/pawzura"))
        layout.addStretch()

    def save(self):
        try:
            self.store_profile()
            updates = {"guard_enabled": self.guard.isChecked(), "preview_only": self.preview.isChecked(),
                       "browser_control_enabled": self.website_control.isChecked(),
                       "pet_visible": self.visible.isChecked(), "start_at_login": self.startup.isChecked(),
                       "language": self.language.currentData(), "allowed_apps": self.config["allowed_apps"],
                       "theme": self.theme.currentData(),
                       "advanced_models": self.advanced_models.isChecked(), "vram_tier": self.vram_tier.currentData(),
                       "designer_model": self.character_model.currentData(),
                       "profiles": self.config["profiles"], "active_profile": self.config["active_profile"],
                       "startup_apps": self.config["startup_apps"], "browsers": self.config["browsers"],
                       "character": self.config["character"], "character_history": self.config["character_history"]}
            old_startup = self.settings.snapshot()["start_at_login"]
            if updates["start_at_login"] != old_startup:
                windows.set_startup(updates["start_at_login"])
            try:
                self.settings.save(updates)
            except OSError:
                windows.set_startup(old_startup)
                raise
            self.applied.emit()
            self.message.setText(self.t["saved"])
            if updates["language"] != self.config["language"]:
                self.language_changed.emit()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Pawzura", str(error))

    def closeEvent(self, event):
        self.hide()
        event.ignore()
