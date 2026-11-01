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


def expand_app_aliases(apps: list[str]) -> list[str]:
    from pathlib import PureWindowsPath
    names = {PureWindowsPath(name.strip().strip('"')).name.casefold() for name in apps}
    for group in APP_ALIASES:
        if names & group:
            names.update(group)
    return sorted(names)


def data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "Pawzura"


def defaults() -> dict:
    return {
        "version": 1, "language": "en", "start_at_login": False,
        "guard_enabled": False, "preview_only": True, "pet_visible": True,
        "allowed_apps": DEFAULT_APPS.copy(), "startup_apps": [],
        "browsers": {name: {"enabled": False, "allowed_sites": []} for name in BROWSERS},
        "bridge_token": secrets.token_urlsafe(32), "bridge_port": 47831,
        "character": {"seed": secrets.randbits(31), "body": "#b8a4ed", "accent": "#f9ce80", "ears": "rabbit", "accessory": "scarf", "source": "random"},
        "character_history": [],
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
                self.data["allowed_apps"] = expand_app_aliases(self.data["allowed_apps"])
            except (ValueError, TypeError, KeyError) as error:
                # Never silently replace a damaged allowlist and begin closing windows.
                raise ValueError(f"Cannot load {self.path}: {error}") from error

    def snapshot(self) -> dict:
        with self.lock:
            return copy.deepcopy(self.data)

    def save(self, updates: dict | None = None):
        with self.lock:
            candidate = copy.deepcopy(self.data)
            if updates:
                candidate.update(updates)
            candidate["allowed_apps"] = expand_app_aliases(candidate["allowed_apps"])
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, self.path)
            self.data = candidate
