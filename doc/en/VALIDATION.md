[English](../en/VALIDATION.md) | [한국어](../ko/VALIDATION.md) · [Documentation](../README.md)

# Validation and known limits

Date: 2026-11-02, Asia/Seoul. Intended support and actual checks are separate.

## Rebuilt 0.1.3 profiles, wildcard rules and recovery

**57 Python tests and 18 extension tests passed locally.** New checks cover trailing `/*`, exact host and path boundaries, legacy-list migration, independent profile drafts and persistence, rename/delete, invalid-edit switch rejection, reset without list loss, malformed appearances, whole-character placement, display-change cancellation, actual recovery-window recreation without firing the abandoned close callback, and packaging rejection of profile exports.

Source offscreen rendering passed with all five tabs. English and Korean settings were inspected using disposable defaults; browser input now scrolls instead of compressing into an unreadable line. The isolated real Chromium probe passed automatic pairing, options/allowed-tab protection, blocked-tab removal and preservation of the last-tab browser window. No user settings or browser profile was used. These checks do not reproduce every reported GPU rendering failure.

Instructions: [profiles and recovery](PROFILES-AND-RECOVERY.md), [rebuilt release](RELEASE-v0.1.3.md).

The rebuilt Windows EXE rendered all tabs and exited with code 0. A native Windows probe recreated a distinct companion window, verified that the full window was inside the primary work area, checked visible character pixels and transparent corners across frames, and confirmed that recovery did not execute the pending close callback. It used disposable settings and no real guardian. This is not full GPU/monitor-hotplug coverage.

## 0.1.3 application protection and automatic connection

**42 Python tests and 18 extension tests passed locally.** Regressions cover Codex/ChatGPT executable aliases in old settings, browser exclusion at the native close boundary, TAB marker placement, last-tab replacement, replacement failure, one-time pairing, origin binding, approval, denial and expiration.

A real headless Chromium extension probe passed in an isolated temporary profile: code-free automatic connection, own-options protection, unlisted-tab removal, allowed-tab preservation, and retention of the same browser window ID with a blank tab after the last blocked tab closes. The test acknowledges desktop approval and animation events itself; it does not claim to automate the packaged GUI confirmation. No user profile or user settings were used.

English and Korean automatic-connection screenshots were reviewed. The TAB marker rendered successfully. The 0.1.3 portable EXE built and its offscreen rendering check exited with code 0.

## 0.1.2 URL rule checks

The updated local suite passes **33 Python tests and 14 extension tests**. It covers domains, HTTP/HTTPS URLs, path boundaries, query conditions, Unicode, legacy wildcard entries, malformed paths, localized line numbers and the real HTTP bridge's use of scoped rules. All seven example address formats supplied in the bug report pass validation. Documentation checks cover **33 authored Markdown files and 12 topic language pairs**. This does not imply that login redirects or every linked page on those websites is automatically allowed.

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
- Chrome/Edge/Firefox user-profile and packaged-GUI flows, store distribution and permanent signed Firefox packages need separate checks beyond the isolated Chromium probe above.
- Browser APIs do not provide exact tab X positions. Animation uses a TAB marker below the title bar or a desktop fallback; it never targets the browser window X.
- Custom title bars, elevated apps that reject close requests, full-screen/virtual-desktop behavior and all monitor arrangements need further testing.
- Navigation occurs before tab closing. The app fails open if stopped/disconnected and is a focus aid, not a tamper-resistant security tool.

The guardian defaults off with preview on. Model-free drawing and procedural motion remain available without Ollama.
