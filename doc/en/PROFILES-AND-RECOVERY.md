[English](../en/PROFILES-AND-RECOVERY.md) | [한국어](../ko/PROFILES-AND-RECOVERY.md) · [Documentation](../README.md)

# Work/leisure profiles and character recovery

## Make separate allowlists

The **Allowlist profile** selector is at the top of settings. Each profile contains its application allowlist and all browsers' site rules, enabled switches and [internal settings-page choices](BROWSERS.md#browser-settings-pages) together. Browser pairing, language, character, guardian, preview and detected startup apps are shared.

The global **Website control** switch (0.1.5+) is also shared. Turn it OFF for apps-only use without changing lists or pausing application monitoring; it applies immediately.

1. Keep **Default**, or use **Rename…** to call it **Work**.
2. In **Applications**, enter the programs for work. In **Browsers**, choose a browser and enter its permitted addresses, for example `example.com/work/*`. Repeat for other browsers.
3. Click **Save settings** to activate and persist these lists.
4. Click **Save as…**, enter **Leisure** and edit its applications and sites, for example `example.org/*`. A new profile begins as a copy of the selected one.
5. Click **Save settings** again.

To switch later, select **Work** or **Leisure**, then **Save settings**. Selecting, renaming or deleting a profile edits the settings draft; the running guardian changes only after saving. Edits to the previous profile stay in the draft when switching. Invalid entries must be corrected before switching or saving. **Delete** asks for confirmation; the last profile cannot be deleted. Names must be unique and 1–64 characters; up to 32 profiles are supported. There is no automatic time schedule or profile import/export in this version.

An upgrade puts the existing live lists into **Default**, retaining them. Existing local entries reappearing after an upgrade do not mean they are bundled examples. Profile data remains in the same [local settings file](PRIVACY.md); it is never included in release packages.

System windows, known browser windows and the app itself remain protected. Detected startup applications are shared exemptions, so they may stay allowed in both profiles. Inspect your lists in **Preview mode** before enabling real closing. Browser changes take effect on the next extension sweep; an already in-flight response cannot be recalled.

## Move the companion out of your way

Right-click the companion (or double-click it) → **General → Pin companion at its current position → Save settings**. It stops roaming at its current resting position. Clear that checkbox and save to resume walking above the taskbar in the selected direction.

You can also **hold the left mouse button on the companion, drag it, then release**. A drop immediately pins the companion and saves that location locally; no extra Save click is needed. A short click still cycles wave/hop/cheer. Dragging uses a movement threshold so small pointer movements remain clicks. The whole companion is kept inside the nearest monitor's available work area; extended displays and negative origins use Qt logical coordinates.

Pinning does not disable the guardian or website control. A bite can temporarily leave the pinned position and returns there afterward. Starting a drag cancels the current bite and pending browser approvals; it cannot undo a close that already happened. New guardian actions wait until the mouse is released. Hide the companion or pause the guardian from the tray when needed.

Pin mode and its position are shared across allowlist profiles and restored on restart. They are private local settings, never release defaults. If saving a drop fails, a notification asks you to check folder write access/free disk space; the current on-screen drop remains, but persistence is not guaranteed. Recovery clears the saved location, preserves pin mode and places the companion above the primary taskbar. Display changes also cancel gestures/actions and rehome it. Saved positions are fitted to the current work areas, rather than assuming the same monitor arrangement is still present.

These controls are available in **0.5.0 EXE and source builds**. Users of 0.4.1 should upgrade the complete portable folder; see [the update guide](RELEASE-v0.5.0.md).

## Recover an invisible or broken companion

Right-click Pawzura's tray icon near the clock → **Recover companion on screen**. Check Windows' hidden-icon arrow if the icon is not visible. The same button is available under **Character**.

Recovery is immediate: it cancels the pending bite without closing its target, removes crack windows, recreates the transparent companion window and shows the saved character fully above the primary monitor's taskbar. It preserves allowlists, profiles and the saved appearance. Unsaved appearance edits remain in settings and are not used by this recovery button.

If the appearance itself is wrong, choose **Character → Reset default appearance → Save settings**. This restores the lavender rabbit with a scarf and keeps application/site lists. **Use previous character** instead restores a design from local character history; save to apply it.

Display-add/remove and geometry changes cancel an in-progress jump and return the companion to its primary screen. Every frame clears its transparent drawing surface before rendering. These changes address off-screen placement and stale pixels; they do not establish that every GPU/DPI/Remote Desktop rendering issue is fixed. See [validation limits](VALIDATION.md).
