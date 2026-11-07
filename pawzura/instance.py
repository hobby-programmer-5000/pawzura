"""One long-lived application lock for each settings directory."""
from pathlib import Path

from PySide6.QtCore import QLockFile


class AlreadyRunningError(Exception):
    pass


def acquire_instance_lock(settings_file: Path) -> QLockFile:
    folder = settings_file.resolve().parent
    folder.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(folder / "instance.lock"))
    lock.setStaleLockTime(0)
    if lock.tryLock(0):
        return lock
    if lock.error() == QLockFile.LockError.LockFailedError:
        raise AlreadyRunningError()
    raise OSError("Cannot create the application lock. Check folder write access and free disk space.")
