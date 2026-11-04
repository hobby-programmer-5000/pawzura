[English](../en/RELEASE-v0.4.1.md) | [한국어](../ko/RELEASE-v0.4.1.md) · [Documentation](../README.md)

# 0.4.1 — browser settings pages and clearer setup

This small update adds a separate **Browsers → Browser settings pages** box. Select a browser to see its known internal settings addresses, including Chrome's `chrome://settings` and Firefox's `about:preferences`. **Allow this browser's settings pages** is ON by default for new and existing settings. Change it per browser/profile and **Save settings**. Settings subpages, search queries and fragments are included; ordinary websites still use the separate site list. [Addresses and usage](BROWSERS.md#browser-settings-pages).

The bridge cancels pending tab-close approvals when it observes an allowlist, profile or monitoring-mode change. Existing new-tab and extension-installation exemptions remain available. The existing extension works with this update; reinstalling it is unnecessary for the settings-page option.

README now highlights starting in preview mode and keeping it enabled until application and controlled-browser allowlists are complete and tested. Disabling preview can lose unsaved work; the risk/liability notice is prominent. The 3D quickstart also identifies the separate preparation button below the picture and the final **Use this character → Save settings** sequence. Optional 3D remains experimental; model/license and visual-quality limits still apply.

## Update and checks

Download **Pawzura-0.4.1-windows-x64.zip** and **SHA256SUMS-0.4.1.txt**. Verify the SHA-256, extract the complete ZIP into a new folder, quit the old app yourself and start `Pawzura/Pawzura.exe` with `_internal` beside it. Personal lists, profiles and characters remain local; upgrading does not enable the guardian or website control. Known settings pages become allowed by default; turn off their checkbox and save if you prefer otherwise. Unsigned builds may trigger SmartScreen.

Source coverage includes 198 Python regressions, 19 extension tests and 16 localized/theme/size browser-page renders with synthetic settings. Release verification additionally checks the exact frozen EXE, embedded source/version, clean defaults, original notices, private-data exclusion, archive integrity and checksum; Windows CI covers Python 3.12/3.14/3.15 before publication. These checks do not establish new Windows 11 hardware/model testing or full user-profile browser E2E. [Validation scope](VALIDATION.md).
