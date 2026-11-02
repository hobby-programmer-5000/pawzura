[English](../en/VALIDATION.md) | [한국어](../ko/VALIDATION.md) · [Documentation](../README.md)

# Validation and known limits

Date: 2026-11-03, Asia/Seoul. Intended support and actual checks are separate.



## 0.2.1 progress reporting

**125 Python tests and 19 extension tests passed locally.** New regressions verify allowlisted/bounded progress events, discarded backend text and extra fields, delivery before final output, bounded result size, safe child error codes, timeout cleanup (including a child that never reads stdin), complete stdin transfer, actual scheduler-length callbacks, English/Korean elapsed and last-report timing, the 60-second notice, indeterminate review stages and terminal timer state. Closing a busy dialog preserves the current stage.

An actual isolated SDXL 8 GB guide run on the existing NVIDIA 8 GB test device reported every drawing step from 0/30 through 30/30, followed by decoding, CPU classification/cutout, vision review and approved storage. SD 1.5's 4 GB configuration on that same device also exercises its 31-step scheduler. This does not certify smaller physical GPUs. Cached runtime setup reported all five trusted installation stages. English/Korean light/dark progress and delayed-report screens were rendered at 680×560 and 820×760; representative views and panel geometry were inspected. No real user prompt/settings or live guardian target was used.

Progress percentages describe their own stage only. Loading/review have no reliable percent/ETA, and a delayed report is not proof of a hang. Timeouts stop waiting; local reviews or installer descendants may still finish, but late progress/results cannot replace the retained character. Model/safety/license and earlier device-coverage limits remain unchanged.

## 0.2.0 creative artwork

**116 Python tests and 19 extension tests passed locally.** New checks cover bounded PNG decode/metadata removal/hash validation, invalid assets and vector fallback, settings/history privacy and restart, procedural poses/bite coordinates/cancellation, explicit per-selection license acknowledgement, local review failure/unsafe/replica/uncertain rejection, Ollama structured-answer compatibility, one bounded download retry and exclusion of personal artwork/runtimes/weights from distribution. Existing native/browser close protections are unchanged.

On Windows 10 x64, main CPython 3.14.7/Qt 6.12.0, an isolated Python 3.12.14/PyTorch 2.7.1+cu118 environment and a **single NVIDIA 8 GB device**, SDXL's 8 GB guide generated two synthetic original descriptions through the full request review → drawing → CPU classifier/cutout → Qwen3-VL review → approved PNG storage flow (about 89 and 88 seconds total). SD 1.5's **4 GB configuration ran on that same 8 GB device**, completing the full flow in about 32 seconds. This is not a separate 4 GB device test. No actual 2/4/6 GB device fit, sequential-offload speed, AMD/Intel support or Windows 11 artwork inference is certified. Model throughput and free memory vary; these timings are examples, not benchmarks/guarantees.

Actual approved images were inspected, rendered at four phase/facing/bite combinations each and restored from disposable settings/history. Requested traits were not all followed, and cutouts retained some background or removed small details; the guide records those limits. Vision mouth estimates were inaccurate, so the preview now accepts a bounded manual mouth click. English/Korean, light/dark, minimum/normal synthetic artwork/setup/error screens were rendered and representative views inspected. Real user prompts, pictures, profiles and guardian targets were not used. A new review model was installed additively for the local test; test image weights/runtime/artifacts remained in an ignored workspace cache.

Observed failures were corrected or bounded: contradictory preflight fields became one verdict; Ollama's complete schema answer in `thinking` is accepted only as whole JSON when content is empty; broad resemblance-based review was replaced by a specific identifiable franchise/unsafe/uncertain decision, while invalid/unavailable checks still reject. This has **not** established exhaustive NSFW, adversarial or copyright detection accuracy. Transient large downloads resumed from cache, with one bounded network retry; the official uv checksum/bootstrap script reached READY and preserved a local package/license inventory. An initial package guard correctly stopped a directory-name collision with public license texts; those texts now use a separate directory.

The 0.2.0 EXE passed smoke rendering/normal exit, embedded version and fourteen compiled app-module comparisons. The packaged external-worker path was checked under Windows bootloader-style inherited DLL search state; it saw CUDA. That probe is not a full interactive frozen-generation E2E test. Detailed user-profile browser E2E and repeatable Windows 11 coverage remain as described below.

## 0.1.10 self-service model setup

**103 Python tests and 19 extension tests passed locally.** New regression checks cover every supported model's exact command and clipboard action, English/Korean all-tier read-only guides, feedback tied to the worker's requested model, and asynchronous missing-model failure retaining the appearance and restoring controls. Opening help/copying does not save settings or trigger generation. The same model list, inference protocol and memory limitations remain in effect.

Synthetic English/Korean character/help/missing-model screens were rendered in light/dark themes at minimum and normal sizes; command visibility, selectable error text, guide scrolling and copy controls were reviewed. The missing-model path was simulated rather than reproduced by changing real user models. No model weights, user settings, allowlists or desktop guardian were changed for validation.

The guide's initial Korean bottom layout overlapped the last command; a scroll-content size constraint and a geometry regression check corrected it. The final 0.1.10 EXE passed smoke rendering/normal exit, embedded version and ten compiled app-module comparisons. Existing GPU inference and browser/device coverage limits remain unchanged.

## 0.1.9 themes and advanced model guides

**99 Python tests and 19 extension tests passed locally.** New checks cover theme preview versus saved/reopened state, legacy/invalid preference migration, opt-in VRAM tiers, model selection persistence and removal after reducing a tier, separation from allowlist profiles, exact model identifiers/schema/non-thinking/unload requests, and actionable failure codes without backend-data echo. Initial restricted-environment runs hit temporary-directory ACL and Node child-process EPERM errors; normal-permission synthetic tests passed. An initial theme test compared differently ordered equivalent default lists; its baseline now uses the existing save normalization.

English/Korean light and dark settings are rendered at 820×640 and 920×720 using synthetic settings. The offscreen renderer first lacked Windows fonts; those captures were invalid and were replaced with font-registered renders. Source model cards, licenses and exact file metadata were checked; original license texts and the public model catalog are included. New Qwen3 weights were not downloaded for device inference: 2/4/6/8 GB tiers are guides, not measured GPU fit, speed or quality claims. Existing 0.5B/1.5B inference evidence and prior device/browser limitations remain unchanged.

The frozen 0.1.9 EXE passed smoke rendering and normal exit; its embedded version and ten app modules matched compiled final source. The first comparison used marshal bytes, which also encode reference/interning layout; code-object comparison confirmed the unmodified bridge matched and was used for all ten modules. No actual user guardian, tabs or settings were used for these checks.

Version 0.1.8 was promoted to a regular GitHub release on 2026-11-02 using the same validated ZIP, SHA-256 `c23a8cf3908e2c10b640f772cc444c57c374e93498288e16b3c54400d86fd47d`. This is a release-status change, not additional device coverage or formal character-rights clearance. The remaining limits below still apply.

## 0.1.8 subdomain address helper

**92 Python tests and 19 extension tests passed locally.** New checks cover exact console-host rules, explicit host-plus-children expansion, nested subdomains, sibling/parent/lookalike exclusion, retained path/query/scheme/port constraints, IDN normalization, IP/localhost feedback, deduplication, save-before-apply behavior and browser selection reset. An actual test-only HTTP bridge accepted the expanded host/subdomain section rules and rejected a lookalike. Existing saved-rule matching semantics were not widened.

English/Korean settings were rendered and reviewed with disposable generic example rules; the affected UI suite passed after compacting the layout. The frozen 0.1.8 EXE passed rendering/normal exit, and all ten embedded app modules matched final source. No real user lists, tabs or monitoring settings were modified. This does not add user-profile browser E2E coverage or another Windows 11 device test beyond the report below.

## Windows 11 maintainer manual report

During the 0.1.7 discussion, the maintainer reported having informally checked the app on Windows 11 and reported no further issue. This records a hands-on user report. The exact app/Windows build, hardware, browser versions and an itemized checklist were not supplied, so no particular feature or browser flow is marked as individually passed on that basis. No identifying device information or personal settings are included.

Windows 11 is therefore no longer listed as entirely awaiting a first user check. Repeatable Windows 11 coverage across configurations and detailed user-profile browser E2E coverage remain unrecorded. The automated and isolated-browser results below have their own stated scope.

## 0.1.7 prompted and manual character design

**87 Python tests and 19 extension tests passed locally.** New checks cover loopback-only prompt delivery without proxies, all nine schema fields, explicit choices overriding model output, rejection before network access for invalid input, incomplete output failures, legacy appearance migration, custom-trait/model persistence, no saved prompt, visible changes for every supported trait, worker input snapshots and failure recovery. One earlier run hit a loopback connection abort in an existing bridge-authentication test; the subsequent complete suite passed.

Actual local inference used the official Qwen2.5 0.5B and 1.5B Q4_K_M weights. Two generic English/Korean examples with 1.5B matched most requested fields but missed eye color and tail type. The smaller model missed more details, particularly in Korean. This is a sample check, not an accuracy benchmark. Explicit options are enforced after inference. A real 1.5B GUI-worker run verified preview/save, the requested eye color/tail, retained model identity, restored controls and absence of the description from disposable saved settings. The 1.5B digest and 1,117,334,278-byte download size are [recorded](../../artifacts/model-provenance-1.5B.json).

English/Korean character screens and synthetic combinations were rendered and reviewed using disposable settings. The Windows EXE passed offscreen rendering/normal exit; all ten embedded app modules match source. Exact illustration generation, arbitrary hair/clothing, reference images and exhaustive GPU/display validation are outside this implementation. See [supported options](MODELS.md).

## 0.1.6 overlay filtering and preview lifetime

**77 Python tests and 19 extension tests passed locally.** Regressions cover ordinary system-menu windows versus overlay/tool/no-activate/click-through/child surfaces, protected graphics/rendering helpers at selection and final close boundaries, one-shot native previews, preview callbacks after mode changes, cached effect windows, stale return heights and cancellation during a hit.

A read-only live-window check found graphics-overlay and embedded-renderer surfaces eligible under the previous inspection rules. Running the previous scheduler against current metadata with all visual/close actions replaced by test functions selected those upper-right targets; preview issued zero close calls. The new live inspection rejected both surfaces. Native checks verified that normal test-owned windows still support normal close requests, and that two safe previews reuse the same effect HWNDs with TOOLWINDOW/NOACTIVATE and without APPWINDOW. The graphics/Explorer process set remained unchanged during that bounded test. Current monitor work-area and shell-taskbar coordinates agreed at inspection.

The reported full flashing/restart sequence was **not** reproduced under a running old guardian: no running Pawzura process was found at inspection. A stable process snapshot and absence of matching recent crash events cannot prove the entire earlier sequence. No driver/Explorer process was terminated or restarted for diagnosis. Raw identities, titles, machine paths and process inventories are not shipped. See [overlay troubleshooting](OVERLAYS-AND-PREVIEW.md).

The 0.1.6 Windows EXE passed offscreen rendering/normal exit and its ten embedded application modules matched final source.

## 0.1.5 guided installation and website switch

**70 Python tests and 19 extension tests passed locally.** Tests cover fixed-file staging without preferences, stable folder updates, token-free setup links, missing-browser feedback, immediate website OFF despite invalid unsaved rule text, retained application monitoring, migration, authenticated status without URL payloads, URL-query preflight while disabled and safe installation pages.

The real isolated Chromium probe confirmed that its installed ID matches the public manifest key and that the helper's direct options link fills browser/port, starts pairing and connects after test-controlled approval. Allowed/options tabs and last-tab window preservation remained passing. English/Korean helper and settings renders were reviewed with disposable defaults and illustrative paths.

The final 0.1.5 Windows EXE passed offscreen rendering and normal exit. All ten embedded app modules matched final source; earlier 0.1.3/0.1.4 release archive checksums were unchanged. Completion status requires the new authenticated status handshake rather than older extension evaluation traffic.

The installed user's Chrome Developer mode toggle and directory-picker clicks were **not** automated/verified; the earlier desktop controller stopped because it could not identify the current URL confidently. The helper's browser-launch calls are unit-tested, while the post-load connection link was tested in isolated Chromium. Firefox/Zen and other browser UI layouts still require separate device testing. No user profile or user list was used for these checks.

## 0.1.4 browser tab indication

**61 Python tests and 18 extension tests passed locally.** Active/background browser events use only a synthetic taskbar-side tab marker in preview and live modes; routing tests assert no foreground-window lookup, native close coordinates or native close call. Preview tests advance time beyond ticket expiry and verify no repeat/close, then verify rearming after allowed navigation/settings apply. A rendering test checks marker bounds and removal on cancellation. Existing allowed-tab, stale-navigation, preview and last-tab window-preservation checks remain passing.

English/Korean marker renders were reviewed. A native Windows probe finished one preview on the lower-screen marker without invoking foreground-window lookup/native closing. The isolated real Chromium probe passed blocked-tab removal, allowed/options-tab protection and last-tab window preservation. The 0.1.4 EXE smoke check passed, its nine embedded app modules matched final source, and checksums confirmed that 419 prior 0.1.3 output files were unchanged. The build used a separate `dist/0.1.4` output folder and disposable settings.

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

- Beyond the Windows 11 manual report above, repeatable checks across Windows 11 configurations, Windows 10 1809 minimum version, ARM64 and Remote Desktop need separate validation.
- Chrome/Edge/Firefox user-profile and packaged-GUI flows, store distribution and permanent signed Firefox packages need separate checks beyond the isolated Chromium probe above.
- Browser APIs do not provide exact tab X positions. Tab animation uses a separate marker near the taskbar, not the browser's real tab X.
- Custom title bars, elevated apps that reject close requests, full-screen/virtual-desktop behavior and all monitor arrangements need further testing.
- Navigation occurs before tab closing. The app fails open if stopped/disconnected and is a focus aid, not a tamper-resistant security tool.

The guardian defaults off with preview on. Model-free drawing and procedural motion remain available without Ollama.
