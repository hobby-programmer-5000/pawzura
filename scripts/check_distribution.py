"""Reject local preferences, browser profiles and repository internals in a release."""
import json
from pathlib import Path
import sys

PRIVATE_FILES = {"settings.json", "settings.tmp", "pairing.json", "instance.lock",
                 "preferences", "secure preferences", "local state", "cookies", "history"}
PRIVATE_DIRS = {".git", ".cache", ".venv", ".venv-standard", "artwork", "art-runtime"}


def check_distribution(folder: Path):
    if not folder.is_dir():
        raise ValueError("Distribution folder does not exist")
    problems = []
    for path in folder.rglob("*"):
        relative = path.relative_to(folder)
        if any(part.casefold() in PRIVATE_DIRS for part in relative.parts):
            problems.append(str(relative))
            continue
        if not path.is_file():
            continue
        if path.name.casefold() in PRIVATE_FILES:
            problems.append(str(relative))
            continue
        if path.suffix.casefold() in (".safetensors", ".gguf", ".onnx"):
            problems.append(str(relative))
            continue
        if path.suffix.casefold() == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and ("bridge_token" in data or "active_profile" in data or "profiles" in data or {"browsers", "allowed_apps"} <= data.keys()):
                    problems.append(str(relative))
            except (UnicodeError, ValueError):
                pass
    if problems:
        # Filenames only; never repeat settings contents or credentials in CI logs.
        raise ValueError("Local/private files cannot be distributed: " + ", ".join(problems))
    return True


if __name__ == "__main__":
    check_distribution(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/Pawzura"))
    print("PASS: no local settings or browser profiles in distribution")
