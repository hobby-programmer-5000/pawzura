[English](../en/PRIVACY.md) | [한국어](../ko/PRIVACY.md) · [Documentation](../README.md)

# Local settings and distribution privacy

Pawzura stores the user's allowlists and connection code in `%LOCALAPPDATA%/Pawzura/settings.json`. The app reads that local file at startup, so a user's previous entries reappear after an upgrade. This display is not a source-code default or a bundled sample list.

The repository's examples use generic domains. User allowlists, browser profiles and pairing credentials must not be added to source files, screenshots, tests, logs or release archives. Screenshot checks use disposable settings and isolated browser profiles.

The 0.1.5 installer helper prepares only six public extension files under `%LOCALAPPDATA%/Pawzura/extensions/`; it does not copy preferences or read/modify browser profiles. Its connection link contains no token. With website control OFF, the new extension checks authenticated status without querying tab URLs. Application monitoring remains independent. Existing connections to older extensions still receive disabled decisions from the desktop app; update both parts for the URL-query preflight.

The build checks the output folder before creating a ZIP and rejects local settings, pairing files, browser profile files and renamed settings exports. Run `python scripts/check_distribution.py PATH_TO_EXTRACTED_RELEASE` to perform the same check. This structural check does not replace reviewing screenshots and other manually added content.

The earlier 0.1.3 release and its tag/assets were withdrawn. At the maintainer's request, [0.1.3 is rebuilt](RELEASE-v0.1.3.md) from a new source commit with new features and a new ZIP/checksum. Re-download the complete archive to replace the withdrawn build. Local user settings are retained; removing a GitHub release does not erase preferences on a user's PC. Existing lists migrate to a local Default profile; new releases do not distribute that profile's contents.
