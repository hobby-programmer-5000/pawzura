[English](../en/RELEASE-v0.1.4.md) | [한국어](../ko/RELEASE-v0.1.4.md) · [Documentation](../README.md)

# 0.1.4 preview — distinguish tab actions from window closing

The old fallback could put a browser-tab crack near the screen's upper-right corner, making it look like an attempt to close the whole browser. Active/background tabs could also be represented on the current foreground browser rather than their actual window. Those coordinate paths are removed.

- Tab events now bite a separate **Tab preview ×** / **Blocked tab ×** marker near the companion's taskbar. It is explicitly a synthetic marker, not the real browser tab X.
- Preview shows each still-blocked tab/URL once instead of repeating after ticket expiration. It never closes a tab. Navigation or applying settings can rearm preview.
- Real closing remains extension-owned and tab-specific. Known browser windows remain excluded from native app closing; last-tab replacement, URL revalidation and allowed-tab protection are retained.
- Work/leisure profiles, companion recovery, bilingual documentation and local-only settings from 0.1.3 remain available. No user list or connection credential is bundled.

Quit the running app, extract the complete new ZIP into a new folder and run `Pawzura.exe`. Reload the included browser extension. See [browser behavior](BROWSERS.md), [validation](VALIDATION.md) and [privacy](PRIVACY.md). The source stays MIT; bundled components retain their licenses.
