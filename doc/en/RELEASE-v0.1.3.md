[English](../en/RELEASE-v0.1.3.md) | [한국어](../ko/RELEASE-v0.1.3.md) · [Documentation](../README.md)

# 0.1.3 preview — rebuilt release

This replaces the withdrawn 0.1.3 preview with a new source commit and ZIP/checksum. Re-download the complete ZIP; the version number alone does not identify the withdrawn build. Quit the old app, extract into a new folder and run `Pawzura.exe`. Update/reload the included browser extension. Existing local settings remain on the PC and migrate to **Default**; they are not bundled defaults.

- Accept `example.com/*` for every path on that HTTPS host and `example.com/section/*` for a path section. Plain domains already allow all paths. HTTP and HTTPS stay separate; subdomains need explicit rules.
- Add named application/browser allowlist profiles with copy, rename, delete and saved active selection. See [work/leisure instructions](PROFILES-AND-RECOVERY.md).
- Add immediate tray/Character **Recover companion on screen** and **Reset default appearance → Save settings**. Recover recreates the transparent window without executing an abandoned bite.
- Keep the whole companion above the taskbar, reset after display changes, clear each transparent frame and sanitize malformed saved appearance values.
- Retain Codex/ChatGPT aliases, browser-window protection, last-tab window preservation and code-free connection with desktop approval.
- Reject local settings, profile exports, browser profile files and pairing credentials in packaging. Examples use generic domains only.
- Include English/Korean character rights notices and recorded provenance. Source remains MIT; bundled components retain their own licenses.

No user browser profile or user allowlist is used for build/screenshots. See [privacy](PRIVACY.md), [browser examples](BROWSERS.md) and [actual checks and remaining limits](VALIDATION.md). The app remains a preview; Windows 11 physical-device and all GPU/DPI combinations have not been validated.
