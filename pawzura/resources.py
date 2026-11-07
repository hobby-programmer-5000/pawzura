"""Locate shipped data in source, folder builds and self-extracting builds."""
from pathlib import Path
import sys


def resource_path(name: str) -> Path:
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent / name
    extracted = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / name
    if extracted.exists():
        return extracted
    return Path(sys.executable).parent / name
