[English](../en/RELEASE-v0.5.0.md) | [한국어](../ko/RELEASE-v0.5.0.md) · [Documentation](../README.md)

# 0.5.0 — pin and drag the companion

The companion can stay out of your working area:

- Right-click it → **General → Pin companion at its current position → Save settings** to stop roaming.
- Hold the **left mouse button**, drag and release to move it. Dropping immediately pins and saves that location locally. Short clicks retain wave/hop/cheer reactions; right-click/double-click still opens settings.
- Clear the pin checkbox and save to resume walking above the taskbar in your selected direction. Pin state and position are shared across allowlist profiles and restored on restart.

Pinning leaves guardian and website-control settings intact. A bite temporarily moves away and returns to the pinned location. Starting a drag cancels the current bite and pending browser approvals; new actions wait until release. It cannot undo an already completed close. Lost mouse capture and display changes clear the gesture safely. Saved/drop positions fit inside current monitor work areas, including negative origins. **Recover companion on screen** clears the saved location, keeps pin mode and rehomes the pet above the primary taskbar. [Usage and save-failure guidance](PROFILES-AND-RECOVERY.md#move-the-companion-out-of-your-way).

## Code and official artwork

App code and earlier MIT permissions remain MIT. The new [official artwork policy](ASSET-LICENSING.md) selects CC BY-NC-SA 4.0 only for future explicitly designated official assets. **The current register is empty.** Existing default/random/Qwen vector characters, example prompts and independent user outputs are not automatically made noncommercial. Third-party models/libraries retain their own terms. No new artwork, model or dependency is added by this update.

## Update and verification

Download **Pawzura-0.5.0-windows-x64.zip** and **SHA256SUMS-0.5.0.txt**. Verify the checksum, extract the complete ZIP into a new folder, quit the old Pawzura and run `Pawzura/Pawzura.exe` with `_internal` beside it. SmartScreen may appear for the unsigned build. Do not copy only the EXE.

Personal lists, pairing data, character assets and positions stay local and are excluded from the package. Fresh settings use English, guardian OFF, preview ON, website control OFF and pin OFF. Existing preferences are retained. Start in preview and complete/test allowlists before enabling real closing; unsaved work can be lost.

Source verification covers 211 Python and 19 extension tests, eight English/Korean theme/size renders and synthetic Qt drag tests on three connected monitors at 100%/125% scale. The user also reported confirming the feature without an itemized test report. Release checks cover the final EXE's embedded source/version, smoke rendering, clean defaults, notices/privacy, ZIP inventory and checksums; Windows CI covers Python 3.12/3.14/3.15. These checks do not establish physical hand-drag testing on every configuration, new Windows 11 GPU/model testing or user-profile browser E2E. Optional 3D remains experimental. [Validation limits](VALIDATION.md).
