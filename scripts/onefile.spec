"""Build a standalone EXE from the reviewed portable folder's data and DLLs."""
import json
import os
from pathlib import Path
import sys

root = Path(SPECPATH).parent
sys.path.insert(0, str(root))
from pawzura import __version__
from scripts.check_distribution import check_distribution

bundle = Path(os.environ["PAWZURA_BUNDLE_DIR"]).resolve()
check_distribution(bundle)
analysis = Analysis([str(root / "run.py")], pathex=[str(root)])

# Reuse the same normalized MSVC/Qt binaries as the folder build.
analysis.binaries = [
    (name, str(bundle / "_internal" / name), kind)
    for name, source, kind in analysis.binaries
]
# The folder normalization also adds root-level MSVC runtime copies. Preserve
# those copies so both formats expose the same reviewed DLL search locations.
binary_names = {name.casefold() for name, source, kind in analysis.binaries}
for path in (bundle / "_internal").glob("*.dll"):
    if path.name.casefold() not in binary_names:
        analysis.binaries.append((path.name, str(path), "BINARY"))
for name, source, kind in analysis.binaries:
    if not Path(source).is_file():
        raise ValueError(f"Reviewed portable binary missing: {name}")

data = []
metadata = root / "build/onefile-metadata"
metadata.mkdir(parents=True, exist_ok=True)
info = json.loads((bundle / "BUILD-INFO.json").read_text(encoding="utf-8"))
info["mode"] = "onefile/dynamic Qt; source and rebuild instructions provided"
(metadata / "BUILD-INFO.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
for path in sorted(bundle.rglob("*")):
    relative = path.relative_to(bundle)
    if not path.is_file() or relative.parts[0] == "_internal" or path.name == "Pawzura.exe":
        continue
    if path.name == "BUILD-INFO.json":
        path = metadata / path.name
    if relative.as_posix() == "BINARY-MANIFEST.json":
        continue  # The folder EXE is a different artifact.
    data.append((relative.as_posix(), str(path), "DATA"))
analysis.datas += data
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas, [],
    name=f"Pawzura-{__version__}-windows-x64",
    console=False,
    icon=str(root / "build/pawzura.ico"),
    manifest=str(root / "scripts/windows.manifest"),
)
