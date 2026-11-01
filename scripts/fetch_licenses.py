"""Fetch upstream license texts and Qt attribution metadata at the exact Qt version.

Run explicitly before building. No source code is downloaded or executed.
The resulting files are committed and distributed alongside the executable.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import io
from pathlib import Path
import tarfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
QT_VERSION = "v6.12.0"


def fetch(url):
    request = Request(url, headers={"User-Agent": "Pawzura-license-collector/0.1"})
    with urlopen(request, timeout=45) as response:
        return response.read()


def main():
    destination = ROOT / "licenses/upstream"
    inventory = []
    for owner, repository in (("qt", "qtbase"), ("pyside", "pyside-setup"), ("qt", "qtsvg")):
        print(f"Collecting {owner}/{repository} at {QT_VERSION}", flush=True)
        url = f"https://api.github.com/repos/{owner}/{repository}/git/trees/{QT_VERSION}?recursive=1"
        tree = json.loads(fetch(url))
        if tree.get("truncated"):
            raise RuntimeError("Incomplete GitHub tree")
        paths = []
        for item in tree["tree"]:
            path = item["path"]
            base = Path(path).name.lower()
            legal = base.startswith(("license", "licence", "copying", "copyright", "notice")) or base == "qt_attribution.json"
            if item["type"] == "blob" and (path.startswith("LICENSES/") or ("3rdparty/" in path and legal)):
                paths.append(path)
        def download(path):
            source = f"https://raw.githubusercontent.com/{owner}/{repository}/{QT_VERSION}/{path}"
            target = destination / repository / path
            content = fetch(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return {"path": str(target.relative_to(ROOT)).replace("\\", "/"), "source": source}
        with ThreadPoolExecutor(max_workers=8) as executor:
            inventory.extend(executor.map(download, paths))
    for name, source in {
        "Apache-2.0.txt": "https://www.apache.org/licenses/LICENSE-2.0.txt",
        "Qwen-LICENSE.txt": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/LICENSE",
        "OpenSSL-LICENSE.txt": "https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.8/LICENSE.txt",
        "libffi-LICENSE.txt": "https://raw.githubusercontent.com/libffi/libffi/v3.4.8/LICENSE",
        "zlib-LICENSE.txt": "https://raw.githubusercontent.com/madler/zlib/v1.3.2/LICENSE",
        "zlib-ng-LICENSE.txt": "https://raw.githubusercontent.com/zlib-ng/zlib-ng/2.2.4/LICENSE.md",
        "XZ-COPYING.txt": "https://raw.githubusercontent.com/tukaani-project/xz/v5.8.1/COPYING",
        "XZ-COPYING-0BSD.txt": "https://raw.githubusercontent.com/tukaani-project/xz/v5.8.1/COPYING.0BSD",
    }.items():
        print(f"Collecting {name}", flush=True)
        target = destination / name
        target.write_bytes(fetch(source))
        inventory.append({"path": str(target.relative_to(ROOT)).replace("\\", "/"), "source": source})
    source = "https://www.bytereef.org/software/mpdecimal/releases/mpdecimal-4.0.0.tar.gz"
    print("Collecting mpdecimal-4.0.0 LICENSE from upstream source archive", flush=True)
    with tarfile.open(fileobj=io.BytesIO(fetch(source)), mode="r:gz") as archive:
        # Read only the root-level license into memory; never unpack or execute contents.
        candidates = [m for m in archive.getmembers() if m.isfile() and len(Path(m.name).parts) == 2
                      and Path(m.name).name.lower() in ("license", "license.txt", "copying", "copyright.txt")]
        if len(candidates) != 1:
            raise RuntimeError("Expected exactly one root-level mpdecimal license")
        member = archive.extractfile(candidates[0])
        if member is None:
            raise RuntimeError("Missing mpdecimal license")
        target = destination / "mpdecimal-LICENSE.txt"
        target.write_bytes(member.read())
        inventory.append({"path": str(target.relative_to(ROOT)).replace("\\", "/"), "source": source, "member": candidates[0].name})
    (ROOT / "licenses/SOURCES.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(inventory)} upstream license/attribution files at {QT_VERSION}")


if __name__ == "__main__":
    main()
