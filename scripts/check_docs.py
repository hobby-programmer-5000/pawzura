"""Check authored Markdown language pairs and repository-local links, without network."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent


def check():
    errors = []
    english = {p.name for p in (ROOT / "doc/en").glob("*.md")}
    korean = {p.name for p in (ROOT / "doc/ko").glob("*.md")}
    if english != korean:
        errors.append(f"Unpaired topic guides: {english ^ korean}")
    roots = ("README", "CONTRIBUTORS", "THIRD-PARTY-NOTICES", "CHARACTER-POLICY")
    for name in roots:
        for suffix in (".md", ".ko.md"):
            if not (ROOT / (name + suffix)).exists():
                errors.append(f"Missing {name + suffix}")
    files = [*(ROOT / "doc").rglob("*.md"), *(ROOT / (name + suffix) for name in roots for suffix in (".md", ".ko.md")), ROOT / "LICENSE.ko.md"]
    for path in files:
        content = path.read_text(encoding="utf-8")
        # Ignore fenced code so samples are not mistaken for Markdown links.
        content = re.sub(r"```.*?```", "", content, flags=re.S)
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            link = link.strip("<>")
            if urlsplit(link).scheme or link.startswith("#"):
                continue
            destination = (path.parent / unquote(link.split("#", 1)[0])).resolve()
            if not destination.is_relative_to(ROOT) or not destination.exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {link}")
        if path.parent.name in ("en", "ko") and f"../{'ko' if path.parent.name == 'en' else 'en'}/{path.name}" not in content:
            errors.append(f"Missing language switch: {path.relative_to(ROOT)}")
    for name in ("README.md", "README.ko.md"):
        if len((ROOT / name).read_text(encoding="utf-8").splitlines()) > 55:
            errors.append(f"{name} is too long for the short introduction")
    return errors, len(files), len(english)


if __name__ == "__main__":
    errors, count, pairs = check()
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"PASS: {count} Markdown files, {pairs} topic language pairs, local links and README length")
