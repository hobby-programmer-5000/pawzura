[English](../en/PRIVACY.md) | [한국어](../ko/PRIVACY.md) · [Documentation](../README.md)

# Local settings and distribution privacy

Pawzura stores the user's allowlists and connection code in `%LOCALAPPDATA%/Pawzura/settings.json`. The app reads that local file at startup, so a user's previous entries reappear after an upgrade. This display is not a source-code default or a bundled sample list.

The repository's examples use generic domains. User allowlists, browser profiles and pairing credentials must not be added to source files, screenshots, tests, logs or release archives. Screenshot checks use disposable settings and isolated browser profiles.

The build checks the output folder before creating a ZIP and rejects local settings, pairing files, browser profile files and renamed settings exports. Run `python scripts/check_distribution.py PATH_TO_EXTRACTED_RELEASE` to perform the same check. This structural check does not replace reviewing screenshots and other manually added content.

Release 0.1.3 and its tag/assets were withdrawn. No replacement release is published as part of this privacy change. The source version is an unreleased development version. Local user settings are retained; removing a GitHub release does not erase preferences on a user's PC.
