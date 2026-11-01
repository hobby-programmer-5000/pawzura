[English](../en/RELEASE-v0.1.3.md) | [한국어](../ko/RELEASE-v0.1.3.md) · [Documentation](../README.md)

# Pawzura 0.1.3 preview

- Codex executable aliases now work with old allowlists: allowing codex.exe also protects ChatGPT.exe.
- Known browser windows are excluded from native program closing at candidate and final close boundaries.
- Browser animations use a TAB marker below the title bar, not the window X.
- Closing the last blocked tab creates about:blank in the same window first. Failure to create it leaves the tab untouched. The extension's own options pages are protected.
- Connect automatically in the extension, then approve in the desktop app. No code entry is needed. Requests expire after one minute and credentials are delivered once to the requesting extension origin.

Quit the old app, extract the full ZIP, run the new Pawzura.exe and reload the updated extension from extensions/chromium (or the Firefox add-on). Existing connection details and settings are retained. Extension installation is still required once to grant access to tab URLs and tab operations.

Validation: 42 Python checks, 18 extension checks and a real isolated Chromium probe for automatic connection, allowed/blocked tabs and same-window last-tab preservation. See [setup](BROWSERS.md) and [scope](VALIDATION.md). Original code remains MIT; component licenses remain unchanged.
