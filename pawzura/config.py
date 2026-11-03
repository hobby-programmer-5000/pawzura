"""Versioned, atomic local settings. No browser history is persisted."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import threading

DEFAULT_APPS = [
    "spotify.exe", "whatsapp.exe", "code.exe", "docker desktop.exe", "docker.exe",
    "powershell.exe", "pwsh.exe", "windowsterminal.exe", "cmd.exe", "conhost.exe",
    "ollama.exe", "ollama app.exe", "chrome.exe", "msedge.exe", "firefox.exe",
    "brave.exe", "opera.exe", "vivaldi.exe", "arc.exe", "zen.exe",
    "codex.exe", "chatgpt.exe", "claude.exe", "antigravity.exe", "pawzura.exe", "msedgewebview2.exe",
    "python.exe", "pythonw.exe", "py.exe", "explorer.exe", "applicationframehost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe",
    "systemsettings.exe", "taskmgr.exe", "lockapp.exe", "credentialuibroker.exe",
    "securityhealthsystray.exe", "textinputhost.exe", "runtimebroker.exe",
]
BROWSERS = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi", "arc", "zen"]
BROWSER_EXECUTABLES = {
    "chrome.exe": "chrome", "msedge.exe": "edge", "firefox.exe": "firefox",
    "brave.exe": "brave", "opera.exe": "opera", "vivaldi.exe": "vivaldi",
    "arc.exe": "arc", "zen.exe": "zen",
}
# Display/product names may differ from the actual executable in packaged apps.
APP_ALIASES = ({"codex.exe", "chatgpt.exe"},)
# Rendering/driver/session helpers are never application-guardian targets.
PROTECTED_HELPERS = frozenset({
    "nvidia overlay.exe", "nvidia share.exe", "nvidia app.exe", "nvcontainer.exe", "nvdisplay.container.exe",
    "amdow.exe", "radeonsoftware.exe", "amdrsserv.exe", "amdrssrcext.exe",
    "igfxem.exe", "igfxcuiservice.exe", "rtss.exe", "rtsshooksloader.exe", "rtsshooksloader64.exe",
    "gamebar.exe", "gamebarftserver.exe", "gamebarpresencewriter.exe", "msedgewebview2.exe",
})


def expand_app_aliases(apps: list[str]) -> list[str]:
    from pathlib import PureWindowsPath
    names = {PureWindowsPath(name.strip().strip('"')).name.casefold() for name in apps}
    for group in APP_ALIASES:
        if names & group:
            names.update(group)
    return sorted(names)


def data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Pawzura"


def default_character() -> dict:
    from .characters import LEGACY_DETAILS
    return {"seed": 0, "body": "#b8a4ed", "accent": "#f9ce80", "ears": "rabbit", "accessory": "scarf", "source": "random", **LEGACY_DETAILS}


def safe_character(raw) -> dict:
    from .characters import validate_character
    if not isinstance(raw, dict):
        return default_character()
    seed = raw.get("seed", 0)
    seed = seed if isinstance(seed, int) and 0 <= seed < 2**31 else 0
    if raw.get("kind") == "artwork":
        import math
        from .artwork import valid_art_id
        if not valid_art_id(raw.get("art_id")) or raw.get("art_model") not in ("sd15", "sdxl"):
            return default_character()
        coords = [raw.get(key) for key in ("mouth_x", "mouth_y")]
        if not all(type(value) in (int, float) and math.isfinite(value) and .05 <= value <= .95 for value in coords):
            return default_character()
        result = {**default_character(), "kind": "artwork", "source": "artwork", "seed": seed,
                "art_id": raw["art_id"], "art_model": raw["art_model"],
                "mouth_x": coords[0], "mouth_y": coords[1]}
        from .art_rig import safe_rig
        rig = safe_rig(raw.get("rig"))
        if rig is not None:
            result["rig"] = rig
        if valid_art_id(raw.get("animation_id")):
            result["animation_id"] = raw["animation_id"]
        return result
    result = validate_character({**default_character(), **raw}, seed)
    result["source"] = raw.get("source") if raw.get("source") in ("qwen", "custom") else "random"
    if result["source"] == "qwen" or (result["source"] == "custom" and raw.get("model")):
        from .characters import MODEL, MODELS
        model = raw.get("model")
        model = model if isinstance(model, str) and model in MODELS else MODEL
        result.update(model=model, model_card=MODELS[model])
    return result


def profile_lists(data: dict) -> dict:
    """Only allowlists belong to a profile, never credentials or guardian state."""
    return copy.deepcopy({"allowed_apps": data["allowed_apps"], "browsers": data["browsers"]})


def prepare_profiles(data: dict):
    profiles = data.setdefault("profiles", {})
    active = data.setdefault("active_profile", "Default")
    if not isinstance(profiles, dict) or len(profiles) > 32 or not isinstance(active, str):
        raise ValueError("Invalid allowlist profiles")
    for name, profile in profiles.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 64 or not isinstance(profile, dict):
            raise ValueError("Invalid profile name or lists")
        if not isinstance(profile.get("allowed_apps"), list) or not all(isinstance(app, str) for app in profile["allowed_apps"]):
            raise ValueError("Invalid profile applications")
        browsers = profile.get("browsers")
        if not isinstance(browsers, dict):
            raise ValueError("Invalid profile browsers")
        for browser in BROWSERS:
            browsers.setdefault(browser, {"enabled": False, "allowed_sites": []})
            entry = browsers[browser]
            if not isinstance(entry, dict) or not isinstance(entry.get("enabled"), bool) or not isinstance(entry.get("allowed_sites"), list) or not all(isinstance(rule, str) for rule in entry["allowed_sites"]):
                raise ValueError("Invalid profile site rules")
    if not active.strip() or len(active) > 64 or (profiles and active not in profiles):
        raise ValueError("Invalid active profile")
    # The existing live lists are authoritative during migration and ordinary saves.
    profiles[active] = profile_lists(data)


def defaults() -> dict:
    return {
        "version": 1, "language": "en", "theme": "dark", "start_at_login": False,
        "advanced_models": False, "vram_tier": 0,
        "guard_enabled": False, "preview_only": True, "pet_visible": True, "walk_direction": "right",
        "browser_control_enabled": False,
        "allowed_apps": DEFAULT_APPS.copy(), "startup_apps": [],
        "browsers": {name: {"enabled": False, "allowed_sites": []} for name in BROWSERS},
        "bridge_token": secrets.token_urlsafe(32), "bridge_port": 47831,
        "character": default_character(),
        "character_history": [],
        "profiles": {}, "active_profile": "Default",
    }


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = path or data_dir() / "settings.json"
        self.lock = threading.RLock()
        self.data = defaults()
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(saved, dict) or saved.get("version") != 1:
                    raise ValueError("Unsupported settings version")
                self.data.update(saved)
                if not isinstance(self.data["allowed_apps"], list) or not isinstance(self.data["browsers"], dict):
                    raise ValueError("Invalid allowlist")
                for name in BROWSERS:
                    self.data["browsers"].setdefault(name, {"enabled": False, "allowed_sites": []})
                if "browser_control_enabled" not in saved:
                    self.data["browser_control_enabled"] = any(entry.get("enabled", False) for entry in self.data["browsers"].values())
                self.data["allowed_apps"] = expand_app_aliases(self.data["allowed_apps"])
            except (ValueError, TypeError, KeyError) as error:
                # Never silently replace a damaged allowlist and begin closing windows.
                raise ValueError(f"Cannot load {self.path}: {error}") from error
        if self.data.get("theme") not in ("dark", "light"):
            self.data["theme"] = "dark"
        if self.data.get("walk_direction") not in ("left", "right"):
            self.data["walk_direction"] = "right"
        self.data["advanced_models"] = self.data.get("advanced_models") is True
        if type(self.data.get("vram_tier")) is not int or self.data["vram_tier"] not in (0, 2, 4, 6, 8):
            self.data["vram_tier"] = 0
        from .characters import DETAIL_MODEL, models_for_vram
        choices = models_for_vram(self.data["vram_tier"], self.data["advanced_models"])
        selected = self.data.get("designer_model", self.data["character"].get("model") if isinstance(self.data["character"], dict) else None)
        self.data["designer_model"] = selected if selected in choices else DETAIL_MODEL
        self.data["character"] = safe_character(self.data["character"])
        history = self.data.get("character_history", [])
        self.data["character_history"] = [safe_character(item) for item in history[-20:]] if isinstance(history, list) else []
        prepare_profiles(self.data)

    def snapshot(self) -> dict:
        with self.lock:
            return copy.deepcopy(self.data)

    def save(self, updates: dict | None = None):
        from .artwork import asset_root
        if self.path.parent.resolve() == asset_root().parent.resolve():
            from .character_library import storage_lock
            with storage_lock():
                return self._save(updates, validate_changed_artwork=True)
        return self._save(updates)

    def _save(self, updates=None, validate_changed_artwork=False):
        with self.lock:
            candidate = copy.deepcopy(self.data)
            if updates:
                candidate.update(updates)
            if candidate.get("theme") not in ("dark", "light"):
                raise ValueError("Choose dark or light theme")
            if candidate.get("walk_direction") not in ("left", "right"):
                raise ValueError("Choose left or right walking direction")
            from .characters import models_for_vram
            if type(candidate.get("vram_tier")) is not int or candidate["vram_tier"] not in (0, 2, 4, 6, 8) or type(candidate.get("advanced_models")) is not bool:
                raise ValueError("Choose a supported VRAM guide")
            if candidate.get("designer_model") not in models_for_vram(candidate["vram_tier"], candidate["advanced_models"]):
                raise ValueError("Choose a model available for this VRAM guide")
            candidate["allowed_apps"] = expand_app_aliases(candidate["allowed_apps"])
            candidate["character"] = safe_character(candidate["character"])
            if (validate_changed_artwork and candidate["character"].get("kind") == "artwork"
                    and candidate["character"] != self.data["character"]):
                from .character_library import validate_assets
                validate_assets(candidate["character"])
            history = candidate.get("character_history", [])
            candidate["character_history"] = [safe_character(item) for item in history[-20:]] if isinstance(history, list) else []
            prepare_profiles(candidate)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
            self.data = candidate
