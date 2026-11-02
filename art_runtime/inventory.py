"""Keep local installed component notices alongside the optional runtime."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import sys


def main(root):
    root = root.resolve()
    licenses = root / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in sorted(metadata.distributions(), key=lambda value: value.metadata.get("Name", "")):
        name = dist.metadata.get("Name", "unknown")
        license_text = dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See installed notices"
        inventory.append({"name": name, "version": dist.version, "license": license_text})
        # Preserve package-relative paths. Do not copy any settings or model cache.
        for entry in dist.files or []:
            if ".." in Path(entry).parts:
                continue
            if "licens" in str(entry).lower() or Path(entry).name.lower() in ("notice", "copying"):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    target = licenses / name / entry
                    if not target.resolve().is_relative_to(licenses.resolve()):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, licenses / "CPython-LICENSE.txt")
    (root / "DEPENDENCIES.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
