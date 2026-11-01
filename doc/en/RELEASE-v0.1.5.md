[English](../en/RELEASE-v0.1.5.md) | [한국어](../ko/RELEASE-v0.1.5.md) · [Documentation](../README.md)

# 0.1.5 preview — guided extension installation

- Add **Browsers → Install/connect extension…**. The helper prepares only public extension files in a stable local folder, copies its path, opens the chosen browser's extension manager and shows the remaining browser clicks.
- On Chromium browsers, **Open connection and request pairing** opens the installed options page with browser, port and language filled in and starts the approval request. The user still chooses Yes in Pawzura. No code or JSON copying is needed.
- Add a global **Website control ON/OFF** in settings and the tray. It applies immediately and preserves application monitoring and saved site lists. New installations default to OFF; migration retains an existing website-control choice. The new extension checks status before reading tab URLs and skips URL queries while disabled.
- Show recent extension connection status. Installation/pairing never turns website control on automatically.
- Keep bilingual installation instructions in the app and emphasize the extension requirement in both READMEs. A button missing until Developer mode is enabled is explicitly explained.
- Use a fixed public Chromium development ID and stable app-data extension folder. Older copies under other IDs should be removed before loading this one; site lists remain local. Firefox has its own options-page declaration and a temporary-install workflow, with fewer automated steps than Chromium.

Quit the old app and extract the complete new ZIP into a new folder. Open the new EXE, then use its helper. Browser-side installation approval is still required; this is not silent or store-based installation. No enterprise policy or browser profile is edited. No private settings or connection credentials are included in the archive.

See [the short installation walkthrough](BROWSERS.md), [privacy](PRIVACY.md) and [validation scope](VALIDATION.md). Original code remains MIT and bundled dependencies retain their own licenses.
