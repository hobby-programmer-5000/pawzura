"""Opt-in desktop integration test. Closes ONLY a window created by this script.

Run on an unlocked Windows desktop: python tests/native_probe.py
"""
from pathlib import Path
import subprocess
import json
import os
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def child():
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLabel
    app = QApplication([])
    window = QLabel("Temporary Pawzura integration probe. No user data.")
    window.setWindowTitle("Pawzura Native Close Probe")
    window.resize(420, 180)
    window.show()
    print(json.dumps({"pid": os.getpid()}), flush=True)
    QTimer.singleShot(15000, app.quit)
    return app.exec()


def parent():
    from pawzura.windows import inspect_window, list_windows, close_window, physical_to_logical
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--child"], stdout=subprocess.PIPE, text=True)
    child_pid = json.loads(process.stdout.readline())["pid"]
    target = None
    for _ in range(50):
        target = next((w for w in list_windows() if w.pid == child_pid and w.title == "Pawzura Native Close Probe"), None)
        if target:
            break
        time.sleep(0.1)
    assert target is not None, "Native test window was not inspectable"
    point = physical_to_logical(*target.close_point, app.screens())
    assert all(isinstance(n, (float, int)) for n in point)
    assert inspect_window(target.hwnd).pid == child_pid
    assert close_window(target), "WM_CLOSE could not be posted"
    assert process.wait(timeout=5) == 0, "Native child failed to close cleanly"
    assert not close_window(target), "Stale handle must not close another window"
    print("PASS: native enumeration, PID identity, DPI mapping, WM_CLOSE, stale-handle rejection")


if __name__ == "__main__":
    raise SystemExit(child() if "--child" in sys.argv else parent())
