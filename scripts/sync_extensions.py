import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent / "extensions"
source = root / "chromium"
target = root / "firefox"
target.mkdir(exist_ok=True)
for name in ("background.js", "options.html", "options.js", "options-i18n.js", "options.css"):
    shutil.copy2(source / name, target / name)
manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
manifest.pop("key", None)  # Chromium-only public ID key; Firefox assigns its own UUID.
manifest.pop("options_page", None)
manifest["options_ui"] = {"page": "options.html", "open_in_tab": True}
manifest["background"] = {"scripts": ["background.js"]}
manifest["browser_specific_settings"] = {"gecko": {"id": "focus-bridge@pawzura.local", "strict_min_version": "128.0", "data_collection_permissions": {"required": ["browsingActivity"]}}}
(target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Firefox extension synchronized")
