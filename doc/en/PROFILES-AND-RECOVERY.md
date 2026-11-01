[English](../en/PROFILES-AND-RECOVERY.md) | [한국어](../ko/PROFILES-AND-RECOVERY.md) · [Documentation](../README.md)

# Work/leisure profiles and character recovery

## Make separate allowlists

The **Allowlist profile** selector is at the top of settings. Each profile contains its application allowlist and all browsers' site rules and enabled switches together. Browser pairing, language, character, guardian, preview and detected startup apps are shared.

1. Keep **Default**, or use **Rename…** to call it **Work**.
2. In **Applications**, enter the programs for work. In **Browsers**, choose a browser and enter its permitted addresses, for example `example.com/work/*`. Repeat for other browsers.
3. Click **Save settings** to activate and persist these lists.
4. Click **Save as…**, enter **Leisure** and edit its applications and sites, for example `example.org/*`. A new profile begins as a copy of the selected one.
5. Click **Save settings** again.

To switch later, select **Work** or **Leisure**, then **Save settings**. Selecting, renaming or deleting a profile edits the settings draft; the running guardian changes only after saving. Edits to the previous profile stay in the draft when switching. Invalid entries must be corrected before switching or saving. **Delete** asks for confirmation; the last profile cannot be deleted. Names must be unique and 1–64 characters; up to 32 profiles are supported. There is no automatic time schedule or profile import/export in this version.

An upgrade puts the existing live lists into **Default**, retaining them. Existing local entries reappearing after an upgrade do not mean they are bundled examples. Profile data remains in the same [local settings file](PRIVACY.md); it is never included in release packages.

System windows, known browser windows and the app itself remain protected. Detected startup applications are shared exemptions, so they may stay allowed in both profiles. Inspect your lists in **Preview mode** before enabling real closing. Browser changes take effect on the next extension sweep; an already in-flight response cannot be recalled.

## Recover an invisible or broken companion

Right-click Pawzura's tray icon near the clock → **Recover companion on screen**. Check Windows' hidden-icon arrow if the icon is not visible. The same button is available under **Character**.

Recovery is immediate: it cancels the pending bite without closing its target, removes crack windows, recreates the transparent companion window and shows the saved character fully above the primary monitor's taskbar. It preserves allowlists, profiles and the saved appearance. Unsaved appearance edits remain in settings and are not used by this recovery button.

If the appearance itself is wrong, choose **Character → Reset default appearance → Save settings**. This restores the lavender rabbit with a scarf and keeps application/site lists. **Use previous character** instead restores a design from local character history; save to apply it.

Display-add/remove and geometry changes cancel an in-progress jump and return the companion to its primary screen. Every frame clears its transparent drawing surface before rendering. These changes address off-screen placement and stale pixels; they do not establish that every GPU/DPI/Remote Desktop rendering issue is fixed. See [validation limits](VALIDATION.md).
