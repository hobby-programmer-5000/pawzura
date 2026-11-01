[English](../en/VALIDATION.md) | [한국어](../ko/VALIDATION.md) · [Documentation](../README.md)

# Validation and known limits

Date: 2026-11-02, Asia/Seoul. Intended support and actual checks are separate.

## Baseline 0.1.0 results

- Local Windows 10 22H2 build 19045 x64, standard CPython 3.14.7, PySide/Shiboken 6.12.0 and PyInstaller 6.22.3.
- Detected three screens: 1920×1080 landscape, a negative-X display at logical 1536×864, and 1080×1920 portrait. This is not full validation of every DPI/hotplug/taskbar arrangement.
- 20 Python checks and 6 extension tests passed, covering executable/site policies, bridge authentication, preview/pause/navigation changes, settings, bounded generation and animation timing.
- A controlled native probe passed enumeration, actual PID identification, DPI mapping, WM_CLOSE and stale-handle rejection. It closed only a window created by the test.
- Real local Qwen generation passed through Ollama 0.32.14. Five Qt settings tabs and frozen EXE rendering/normal-exit smoke checks passed.
- [Baseline GitHub CI](https://github.com/hobby-programmer-5000/pawzura/actions/runs/41338706235) passed Python 3.12, 3.14 and 3.15, Node checks and Firefox synchronization.

## 0.1.1 changes to verify

Local checks passed: **23 Python tests**, **14 extension/connection-form tests**, and **31 authored Markdown files with 11 topic language pairs and valid local links**. These cover English defaults, saved Korean choice, language-refresh notification, plain-code copying, form validation, rejected samples, old JSON import, connection-state messages and file-preview behavior. Commands are in [the build guide](BUILD.md).

The actual file-preview page was captured in an isolated headless Chrome profile and visually reviewed. The 0.1.1 portable EXE built successfully and its offscreen smoke-check exited with code 0. These checks do not claim real user-profile extension installation or site-closing E2E.

## Environment fixes retained

Conda caused Qt DLL import failures; source setup recommends standard CPython. The build unifies unmodified MSVC runtime copies to avoid mixed-version loading. Offscreen rendering explicitly loads system fonts without redistributing them. Smoke-check deletes Qt widgets before application shutdown. Native tests use the actual GUI child PID, since a venv launcher may have a different PID.

The Windows automation helper's screenshot capture timed out in baseline testing. App-owned Qt rendering captures were used instead; a complete tray-click-to-exit UI automation run was not claimed.

## Remaining limits

- Windows 11 physical devices, Windows 10 1809 minimum version, ARM64 and Remote Desktop need separate validation.
- Real browser extension installation/navigation/closing E2E, store distribution and permanent signed Firefox packages need separate checks. HTTP bridge and extension API tests do not replace that work.
- Browser APIs do not provide exact tab X positions. Animation uses the browser window's close area or a desktop fallback; the extension closes the revalidated tab itself.
- Custom title bars, elevated apps that reject close requests, full-screen/virtual-desktop behavior and all monitor arrangements need further testing.
- Navigation occurs before tab closing. The app fails open if stopped/disconnected and is a focus aid, not a tamper-resistant security tool.

The guardian defaults off with preview on. Model-free drawing and procedural motion remain available without Ollama.
