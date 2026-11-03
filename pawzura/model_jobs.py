"""One owned model-preparation job at a time inside this app process."""
from contextlib import contextmanager
import threading
from functools import wraps
from .characters import GenerationError

_SLOT = threading.RLock()
_QUARANTINED = False


def quarantine():
    global _QUARANTINED
    _QUARANTINED = True


@contextmanager
def model_job():
    if _QUARANTINED:
        raise GenerationError("motion_cleanup_failed")
    if not _SLOT.acquire(blocking=False):
        raise GenerationError("art_model_busy")
    try:
        yield
    finally:
        _SLOT.release()


def serialized(function):
    @wraps(function)
    def call(*args, **kwargs):
        with model_job():
            return function(*args, **kwargs)
    return call
