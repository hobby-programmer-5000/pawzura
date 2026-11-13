"""Build a replaceable-DLL portable folder, its notices and a distributable ZIP."""
import hashlib
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main(dist_dir: Path | None = None, onefile: bool = False):
    dist_dir = (dist_dir or ROOT / "dist").resolve()
    if sys.platform != "win32":
        raise SystemExit("Build Windows executables on Windows")
    if not (ROOT / "licenses/SOURCES.json").exists():
        raise SystemExit("First run: python scripts/fetch_licenses.py")
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
    from pawzura.characters import random_character
    from pawzura.pet import draw_character
    app = QGuiApplication([])
    icon = ROOT / "build/pawzura.ico"
    icon.parent.mkdir(exist_ok=True)
    pixmap = QPixmap(144, 146)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    draw_character(painter, random_character(212))
    painter.end()
    if not pixmap.save(str(icon), "ICO"):
        raise RuntimeError("Cannot save application icon")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
               "--name", "Pawzura", "--icon", str(icon), "--manifest", str(ROOT / "scripts/windows.manifest"),
               "--specpath", str(ROOT / "build"), "--distpath", str(dist_dir),
               "--workpath", str(ROOT / "build/pyinstaller"), str(ROOT / "run.py")]
    import PySide6
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([sys.base_prefix, str(Path(PySide6.__file__).parent),
                                          str(Path(os.environ["WINDIR"]) / "System32"), os.environ["WINDIR"]])
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    output = dist_dir / "Pawzura"
    # Python, Shiboken and Qt wheels can carry different MSVC versions. Windows loads
    # a DLL basename once, so an older copy can break a newer Qt despite correct paths.
    # Unify unmodified redistributable files to the newest shipped version everywhere.
    import pefile
    runtimes = {}
    for binary in (output / "_internal").rglob("*.dll"):
        if binary.name.lower().startswith(("msvcp140", "vcruntime140", "concrt140")):
            pe = pefile.PE(str(binary), fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
            fixed = pe.VS_FIXEDFILEINFO[0]
            version = (fixed.FileVersionMS, fixed.FileVersionLS)
            pe.close()
            runtimes.setdefault(binary.name.lower(), []).append((version, binary))
    for name, candidates in runtimes.items():
        _, newest = max(candidates, key=lambda item: item[0])
        content = newest.read_bytes()
        for destination in {output / "_internal" / name, *(p for _, p in candidates)}:
            destination.write_bytes(content)
    for name in ("README.md", "README.ko.md", "AGENTS.md", "AGENTS.ko.md", "LICENSE", "LICENSE.ko.md", "CHARACTER-POLICY.md", "CHARACTER-POLICY.ko.md", "THIRD-PARTY-NOTICES.md", "THIRD-PARTY-NOTICES.ko.md", "CONTRIBUTORS.md", "CONTRIBUTORS.ko.md"):
        shutil.copy2(ROOT / name, output / name)
    for name in ("doc", "extensions", "licenses"):
        shutil.copytree(ROOT / name, output / name, dirs_exist_ok=True)
    runtime = output / "art_runtime"
    runtime.mkdir(exist_ok=True)
    for name in ("catalog.json", "requirements.txt", "setup.ps1", "runner.py", "inventory.py", "pose.py",
                 "three_d.py", "motion_geometry.py", "motion_library.py", "motion_bake.py", "motion_catalog.json", "triposr-sources.json", "motion_cache_legacy.json"):
        shutil.copy2(ROOT / "art_runtime" / name, runtime / name)
    # Only reviewed model evidence is shipped, never an arbitrary artifact folder.
    (output / "artifacts").mkdir(exist_ok=True)
    for name in ("model-provenance.json", "model-provenance-1.5B.json", "model-catalog.json", "qwen-character.json", "browser-setup-en.png", "browser-setup-ko.png", "character-custom-en.png", "character-custom-ko.png", "subdomain-rules-en.png", "subdomain-rules-ko.png"):
        shutil.copy2(ROOT / "artifacts" / name, output / "artifacts" / name)
    # Keep the bundled README's staged-demo links usable. Only public assets,
    # never renderer working frames, profiles or diagnostics, may be copied.
    demo = output / "artifacts/demo"
    demo.mkdir(exist_ok=True)
    for name in ("pawzura-demo-en.gif", "pawzura-demo-en.mp4", "pawzura-demo-ko.gif", "pawzura-demo-ko.mp4", "manifest.json", "NOTICE.md"):
        shutil.copy2(ROOT / "artifacts/demo" / name, demo / name)
    bundled = output / "licenses/installed"
    bundled.mkdir(parents=True, exist_ok=True)
    dependencies = []
    for distribution_name in ("PySide6-Essentials", "shiboken6", "PyInstaller", "altgraph", "packaging", "pefile", "pywin32-ctypes", "pyinstaller-hooks-contrib", "setuptools"):
        dist = metadata.distribution(distribution_name)
        dependencies.append({"name": dist.metadata["Name"], "version": dist.version, "license": dist.metadata.get("License-Expression") or dist.metadata.get("License")})
        for entry in dist.files or []:
            if "licens" in str(entry).lower() or Path(entry).name.lower() in ("copying", "notice"):
                source = Path(dist.locate_file(entry))
                if source.is_file():
                    destination = bundled / distribution_name / Path(entry)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.exists():
        raise RuntimeError("CPython LICENSE.txt is required for redistribution; use standard CPython")
    shutil.copy2(python_license, bundled / "CPython-LICENSE.txt")
    build_info = {"python": sys.version, "dependencies": dependencies, "qt": "6.12.0", "mode": "onedir/dynamic Qt", "modified_upstream": False, "msvc_runtime_unified": True}
    (output / "BUILD-INFO.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8")
    # Record every shipped binary for auditing notices against a particular artifact.
    binaries = {str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in output.rglob("*") if p.suffix.lower() in (".exe", ".dll", ".pyd")}
    (output / "BINARY-MANIFEST.json").write_text(json.dumps(binaries, indent=2) + "\n", encoding="utf-8")
    from pawzura import __version__
    from check_distribution import check_distribution
    check_distribution(output)
    archive = shutil.make_archive(str(dist_dir / f"Pawzura-{__version__}-windows-x64"), "zip", output.parent, output.name)
    print(f"Built: {output / 'Pawzura.exe'}\nArchive: {archive}")
    if onefile:
        environment["PAWZURA_BUNDLE_DIR"] = str(output)
        subprocess.run([
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--distpath", str(dist_dir), "--workpath", str(ROOT / "build/onefile"),
            str(ROOT / "scripts/onefile.spec"),
        ], cwd=ROOT, env=environment, check=True)
        print(f"Standalone: {dist_dir / f'Pawzura-{__version__}-windows-x64.exe'}")


if __name__ == "__main__":
    # Running a script by path adds scripts/, not the repository root.
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, help="Separate output directory for preserving earlier builds")
    parser.add_argument("--onefile", action="store_true", help="Also build a standalone self-extracting EXE")
    options = parser.parse_args()
    main(options.dist_dir, options.onefile)
