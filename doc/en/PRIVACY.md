[English](../en/PRIVACY.md) | [한국어](../ko/PRIVACY.md) · [Documentation](../README.md)

# Local settings and distribution privacy

Pawzura stores the user's allowlists and connection code in `%LOCALAPPDATA%/Pawzura/settings.json`. The app reads that local file at startup, so a user's previous entries reappear after an upgrade. This display is not a source-code default or a bundled sample list.

The repository's examples use generic domains. User allowlists, browser profiles and pairing credentials must not be added to source files, screenshots, tests, logs or release archives. Screenshot checks use disposable settings and isolated browser profiles.

From 0.1.7, character descriptions are held in the current settings window and sent only to the separately installed loopback Ollama service. Pawzura does not store descriptions in settings, appearance history or logs. Clear description empties the input; closing settings to the tray retains that window until it is recreated or the app exits. Only validated visual traits and the selected supported model identifier are saved. Review Ollama's own behavior separately.

The 0.1.5 installer helper prepares only six public extension files under `%LOCALAPPDATA%/Pawzura/extensions/`; it does not copy preferences or read/modify browser profiles. Its connection link contains no token. With website control OFF, the new extension checks authenticated status without querying tab URLs. Application monitoring remains independent. Existing connections to older extensions still receive disabled decisions from the desktop app; update both parts for the URL-query preflight.

The build checks the output folder before creating a ZIP and rejects local settings, pairing files, browser profile files and renamed settings exports. Run `python scripts/check_distribution.py PATH_TO_EXTRACTED_RELEASE` to perform the same check. This structural check does not replace reviewing screenshots and other manually added content.

The earlier 0.1.3 release and its tag/assets were withdrawn. At the maintainer's request, [0.1.3 is rebuilt](RELEASE-v0.1.3.md) from a new source commit with new features and a new ZIP/checksum. Re-download the complete archive to replace the withdrawn build. Local user settings are retained; removing a GitHub release does not erase preferences on a user's PC. Existing lists migrate to a local Default profile; new releases do not distribute that profile's contents.

## Optional creative artwork

The [creative artwork mode](CREATIVE-ART.md) installs its separate runtime and model cache only after an explicit Preparation action and model-license acknowledgement. Generated descriptions and images use local inference; only validated PNG pixels, model identity, seed and bounded mouth coordinates are kept for approved designs. Description/vision review failures keep the prior character. Prompts are session-only and never written to settings or command arguments. Ollama remains an external service with its own behavior.

Approved PNGs are personal local data in `%LOCALAPPDATA%/Pawzura/artwork`; settings/history store content hashes rather than arbitrary paths. Back up that folder with settings if desired. The app does not automatically delete unused PNGs. Runtime packages, weights and local license inventory reside under `%LOCALAPPDATA%/Pawzura/art-runtime`; these are not part of a normal EXE update. Distribution checks reject both private directories and model weight files, and build copies only an explicit list of runtime source scripts. Never publish a prepared per-user runtime or artwork folder as an app release.
