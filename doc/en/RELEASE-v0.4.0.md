[English](../en/RELEASE-v0.4.0.md) | [한국어](../ko/RELEASE-v0.4.0.md) · [Documentation](../README.md)

# 0.4.0 — directional motion and reusable characters

Pawzura can save generated characters for reuse, delete unwanted versions with optional unused-file cleanup, and prepare experimental directional 3D clips from an approved drawing. Choose walking direction in settings. Existing vector characters and editable 2D motion remain available.

## Use the new controls

- **Settings → General → Walking direction → Left/Right → Save settings** sets the preferred direction. Mixed-DPI monitor crossings and returning from a bite preserve that preference.
- **Settings → Character → Save character… / Saved characters…** names, previews and restores local versions without generating again. Approved artwork and prepared motion are also saved automatically before applying. Source pictures, validated motion and verified preparation caches stay local and outside Git/releases. [Library and backup guide](CHARACTER-LIBRARY.md).
- In **Saved characters…**, select **Delete…** to review the estimated disk space and confirm permanent deletion. Leave **Also delete files no longer in use** checked for unused PNG/motion/recognized finished cache cleanup, or uncheck it to remove only the entry. Current/pending versions cannot be deleted; shared and previous-history references protect their files. Unknown/unfinished caches and model downloads are retained. This is not a global orphan-file sweep.
- In **Create original artwork…**, acknowledge the model terms and choose **Prepare 3D motion · 8 GB · pose-assisted**. Reconstruction, CPU landmark fitting and frame baking run sequentially. The resulting local pack supports side walking, front pauses, turns, waves, hops, cheers and bites without resident model inference. [Exact setup, examples and limitations](3D-MOTION.md).

The 3D path uses MIT TripoSR code/weights and Apache-2.0 ViTPose, plus separately licensed libraries and the original image model terms. It requires the optional prepared image runtime and an NVIDIA CUDA GPU with at least 8 GB VRAM; smaller memory guides still concern image generation/2D motion. No weights or generated characters are shipped in the ZIP. Review [model notices](THIRD-PARTY-NOTICES.md) before downloading.

## Quality and validation scope

The new pose-assisted rig corrects the observed backward torso lean and reuses compatible scenes when only rigging/motion changes. It remains experimental: edges may soften, joints/clothing can distort, feet may slide and inferred side/back views may differ. It is not specialist learned skeleton generation or a guarantee of better animation than the vector character. Keep the original if the result is worse.

Windows 10 source checks include 190 Python regressions, 19 extension tests, three optional geometry checks, localized Qt renders and actual 8 GB test-owned artwork/motion preparation documented in [validation](VALIDATION.md) and the 3D guide. The final packaged artifact must additionally pass frozen smoke, embedded source/version, privacy, license and checksum checks before publication. New Windows 11 hardware/model testing and full user-profile browser E2E are not established by these checks.

## Update

Download the complete **Pawzura-0.4.0-windows-x64.zip**, verify its SHA-256 against **SHA256SUMS-0.4.0.txt**, and extract into a new folder. Quit the old running Pawzura yourself, then open the new `Pawzura/Pawzura.exe`; keep `_internal` beside it. Personal settings and characters stay on your PC. Unsigned builds may show SmartScreen. Browser tab control still needs the separately installed extension; AI generation needs Ollama running and enough available memory. [Getting started](GETTING_STARTED.md).
