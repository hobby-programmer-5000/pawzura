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

Motion settings add only bounded limb polygons/pivots to the existing image/hash/seed record. The optional CPU helper receives approved pixels over local stdin, never a cloud endpoint or arbitrary model-supplied path. It retains no prompt or private screenshot. No texture layers are exported into the release; original local PNGs and settings remain excluded.

Optional 3D preparation additionally stores private source-bound motion packs (`motion`), intermediate views/mesh/joints (`motion-jobs`) and downloaded original/adapted source under `art-runtime/motion-source`. These stay local, contain no prompt or allowlist, and are excluded from distribution together with checkpoint weights. [Locations and recovery](3D-MOTION.md).

Named saved character metadata is private local data under `character-library`; it contains validated appearance/asset hashes and custom names, never prompts or account/profile lists. The folder and `.pawzura-character.json` files are ignored by Git and rejected from release packages, including renamed JSON recognized by its format marker. [Library and backup guide](CHARACTER-LIBRARY.md).

Library deletion reads current character/history references locally to preserve shared files. It does not send or log settings. The temporary `.character-storage.lock` coordinates local storage changes and may contain process/host metadata; it is also ignored by Git and rejected from distribution. Confirmed deletion is permanent, while shared/unverified files and model downloads are retained. See the library guide for the cleanup limits.

Companion pin mode and its last dropped position are also saved only in this local settings file, using bounded logical-pixel coordinates. They are shared across allowlist profiles, are not telemetry, and must not be bundled in examples/releases. Recovery clears the saved position; see [move and pin controls](PROFILES-AND-RECOVERY.md).
