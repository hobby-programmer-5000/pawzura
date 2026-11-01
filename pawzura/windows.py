"""64-bit-safe Win32 window inspection and polite close requests via ctypes."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"


@dataclass(frozen=True)
class Window:
    hwnd: int
    pid: int
    executable: str
    title: str
    rect: tuple[int, int, int, int]
    close_point: tuple[int, int]


if IS_WINDOWS:
    user = C.WinDLL("user32", use_last_error=True)
    kernel = C.WinDLL("kernel32", use_last_error=True)
    dwm = C.WinDLL("dwmapi")
    user.GetForegroundWindow.restype = W.HWND
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.IsWindow.argtypes = [W.HWND]
    user.GetWindowTextLengthW.argtypes = [W.HWND]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    user.GetWindowRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.GetWindow.argtypes = [W.HWND, W.UINT]
    user.GetWindow.restype = W.HWND
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    kernel.OpenProcess.restype = W.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    dwm.DwmGetWindowAttribute.argtypes = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]
    CALLBACK = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [CALLBACK, W.LPARAM]
    user.IsIconic.argtypes = [W.HWND]


def inspect_window(hwnd: int) -> Window | None:
    if not IS_WINDOWS or not user.IsWindow(hwnd) or not user.IsWindowVisible(hwnd) or user.IsIconic(hwnd):
        return None
    if user.GetWindow(hwnd, 4):  # GW_OWNER: never act on modal or owned tool windows
        return None
    pid = W.DWORD()
    user.GetWindowThreadProcessId(hwnd, C.byref(pid))
    if pid.value == os.getpid():
        return None
    length = user.GetWindowTextLengthW(hwnd)
    if length < 1:
        return None
    title = C.create_unicode_buffer(length + 1)
    user.GetWindowTextW(hwnd, title, length + 1)
    process = kernel.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not process:
        return None
    try:
        buf, size = C.create_unicode_buffer(32768), W.DWORD(32768)
        if not kernel.QueryFullProcessImageNameW(process, 0, buf, C.byref(size)):
            return None
        executable = buf.value
    finally:
        kernel.CloseHandle(process)
    # Protect Windows components regardless of user edits to the allowlist.
    windows_root = os.path.normcase(os.environ.get("WINDIR", r"C:\Windows")) + os.sep
    if os.path.normcase(executable).startswith(windows_root):
        return None
    cloaked = W.DWORD()
    if dwm.DwmGetWindowAttribute(hwnd, 14, C.byref(cloaked), C.sizeof(cloaked)) == 0 and cloaked.value:
        return None
    rect = W.RECT()
    if not user.GetWindowRect(hwnd, C.byref(rect)) or rect.right - rect.left < 80 or rect.bottom - rect.top < 50:
        return None
    buttons = W.RECT()
    x, y = rect.right - 24, rect.top + 18
    if dwm.DwmGetWindowAttribute(hwnd, 5, C.byref(buttons), C.sizeof(buttons)) == 0 and buttons.right > buttons.left:
        x = rect.left + buttons.right - (buttons.right - buttons.left) // 6
        y = rect.top + (buttons.top + buttons.bottom) // 2
    return Window(int(hwnd), pid.value, executable, title.value,
                  (rect.left, rect.top, rect.right, rect.bottom), (x, y))


def list_windows() -> list[Window]:
    if not IS_WINDOWS:
        return []
    result = []
    @CALLBACK
    def visit(hwnd, _):
        window = inspect_window(hwnd)
        if window:
            result.append(window)
        return True
    user.EnumWindows(visit, 0)
    return result


def foreground_window() -> Window | None:
    return inspect_window(user.GetForegroundWindow()) if IS_WINDOWS else None


def close_window(target: Window) -> bool:
    current = inspect_window(target.hwnd)
    if not current or (current.pid, current.executable, current.title) != (target.pid, target.executable, target.title):
        return False
    return bool(user.PostMessageW(target.hwnd, 0x0010, 0, 0))  # WM_CLOSE; no terminate/kill


def startup_apps() -> list[str]:
    if not IS_WINDOWS:
        return []
    import winreg
    names = set()
    # Resolve Run entries and Startup folder .lnk targets without executing the entries.
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for subkey in (r"Software\Microsoft\Windows\CurrentVersion\Run", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"):
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for index in range(winreg.QueryInfoKey(key)[1]):
                        _, command, _ = winreg.EnumValue(key, index)
                        command = os.path.expandvars(str(command)).strip()
                        import re
                        match = re.match(r'^"([^"]+\.exe)"|^(.+?\.exe)(?:\s|$)', command, re.I)
                        if match:
                            names.add(Path(match.group(1) or match.group(2)).name.casefold())
            except OSError:
                pass
    script = r"""$ws = New-Object -ComObject WScript.Shell
$dirs = @([Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('CommonStartup'))
$names = foreach ($dir in $dirs) {
  Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Extension -eq '.lnk') { [IO.Path]::GetFileName($ws.CreateShortcut($_.FullName).TargetPath) }
    elseif ($_.Extension -eq '.exe') { $_.Name }
  }
}
ConvertTo-Json -InputObject @($names)
"""
    try:
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                capture_output=True, timeout=12, creationflags=subprocess.CREATE_NO_WINDOW)
        # Windows PowerShell redirected output uses the system OEM encoding.
        output = json.loads(result.stdout.decode("utf-8-sig", errors="replace") or "[]")
        names.update(str(item).casefold() for item in output if item and str(item).lower().endswith(".exe"))
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return sorted(names - {"pawzura.exe"})


def set_startup(enabled: bool):
    if not IS_WINDOWS:
        return
    import winreg
    if getattr(sys, "frozen", False):
        command = subprocess.list2cmdline([sys.executable, "--tray"])
    else:
        python = Path(sys.executable)
        windowless = python.with_name("pythonw.exe")
        command = subprocess.list2cmdline([str(windowless if windowless.exists() else python), str(Path(__file__).resolve().parent.parent / "run.py"), "--tray"])
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            winreg.SetValueEx(key, "Pawzura", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "Pawzura")
            except FileNotFoundError:
                pass


def physical_to_logical(x: int, y: int, screens):
    """Map each monitor independently; negative origins and mixed DPI are supported."""
    if not IS_WINDOWS:
        return x, y
    class MONITORINFOEX(C.Structure):
        _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD), ("szDevice", W.WCHAR * 32)]
    user.MonitorFromPoint.argtypes = [W.POINT, W.DWORD]
    user.MonitorFromPoint.restype = W.HANDLE
    user.GetMonitorInfoW.argtypes = [W.HANDLE, C.c_void_p]
    monitor = user.MonitorFromPoint(W.POINT(x, y), 2)
    info = MONITORINFOEX()
    info.cbSize = C.sizeof(info)
    if user.GetMonitorInfoW(monitor, C.byref(info)):
        for screen in screens:
            geometry = screen.geometry()
            if (screen.name().casefold() == info.szDevice.casefold()
                    or (geometry.x(), geometry.y()) == (info.rcMonitor.left, info.rcMonitor.top)):
                g = screen.geometry()
                return (g.x() + (x - info.rcMonitor.left) * g.width() / (info.rcMonitor.right - info.rcMonitor.left),
                        g.y() + (y - info.rcMonitor.top) * g.height() / (info.rcMonitor.bottom - info.rcMonitor.top))
    return x, y
