[English](../en/ARTWORK-MOTION.md) | [한국어](../ko/ARTWORK-MOTION.md) · [Documentation](../README.md)

# Moving artwork hands and feet

Source update: [experimental 8 GB pose-assisted 3D motion](3D-MOTION.md) now connects approved artwork to the actual app. The older release/experiment descriptions below retain their original scope.

Generated artwork can move four separate cutout regions: two arms/hands and two feet. Walking alternates them; waving, hopping and cheering use different poses. This works with existing approved artwork, without generating another picture.

## New artwork

Use [Create original artwork](CREATIVE-ART.md), run Preparation again after upgrading, then generate. Preparation adds a CPU joint helper; generation proposes limb areas automatically. The built-in example asks for a standing character with two visible hands, two booted feet and arms slightly apart from the body. This gives the helper clearer landmarks. Review the moving preview before applying it.

An uncertain estimate does not discard an otherwise approved picture. The completion message tells you when separate hand/foot motion is missing. Use **Edit hand/foot motion…** to configure it. Do not mistake the fallback picture's whole-image sway for articulated motion.

## Add or correct motion on an existing picture

1. Open **Settings → Character → Edit hand/foot motion…**. This button is available when the selected character is artwork. In the artwork creation dialog, the same button edits the approved preview.
2. Optional: click **Prepare CPU motion helper (~350 MB)** once, then **Estimate joints automatically**. Internet is needed for preparation. The helper uses local CPU inference, not Ollama or GPU VRAM; imports/model loading can take several seconds. Stage, elapsed time and time since the last report remain visible. Preparation reuses the isolated image runtime and can also install/update its packages; on a fresh machine it downloads much more than the helper's weights. Manual editing needs no helper download.
3. Select each of the four parts. **Image-left/right means the side of the picture**, not the character's anatomical left/right. The colored outline selects pixels; the circle is the rotation joint.
4. Drag inside an outline to move it, a square corner to resize it, or the circle to move its joint. Drag empty space to replace that part with a rectangle. Keep each region around that limb, clear of the head/torso and other limbs. Put an arm joint near its elbow/top and a foot joint near the top of the boot.
5. Inspect **Walk, Wave, Hop and Cheer** in the live preview. Correct misplaced areas or excessive seams. For difficult artwork, smaller hand regions may look better than including a whole sleeve.
6. Leave **Enable independent hand/foot motion** checked → **Use motion settings** → **Save settings** in the main window. From a new artwork preview, also click **Use this character** before the final main-window save. Cancel keeps the previous selection.

**Reset suggested areas** restores the areas present when this editor opened, or generic starter rectangles if none existed. It does not rerun inference. Uncheck independent motion and save to return to the whole-picture fallback. The original PNG remains intact; changing motion does not redraw it. Character history retains validated motion settings alongside each character. [Recovery and history](PROFILES-AND-RECOVERY.md).

## Interact with the companion

| Action | Result |
| --- | --- |
| Hover over it | Stops walking, faces the cursor and greets with a waving pose/sparkles |
| Left-click | Cycles wave → hop → cheer on successive clicks |
| Wait while it walks | Occasionally pauses to wave |
| Double-click or right-click | Opens settings |

These reactions do not close anything and do not replace a pending guardian action. A guardian bite takes precedence. Screen recovery cancels old reactions and pending animations. Normal walking/interaction uses Qt only: no ongoing image, pose or video inference, and no extra VRAM requirement after setup.

## Helper, privacy and limits

The optional helper is [usyd-community/vitpose-base-simple](https://huggingface.co/usyd-community/vitpose-base-simple), pinned in [the catalog](../../art_runtime/catalog.json), approximately 350 MB, **Apache-2.0**. Its processor uses **SciPy (BSD-3-Clause)**. Original licenses are in [third-party notices](THIRD-PARTY-NOTICES.md). Pawzura remains MIT. Weights are downloaded separately, not bundled in the app.

This is editable **2D cutout animation**. The helper estimates human-style landmarks; animals, tiny/hidden limbs, unusual silhouettes and handheld objects can produce bad areas or no estimate. It cannot invent missing fingers, hidden anatomy or new perspectives. Moving a sleeve can reveal gaps; simple edge blending may leave seams, stretched colors or clipped pixels. Adjust the regions/joints, reduce the region to the hand, or disable the feature if needed. Four valid regions are required to enable this version of the rig. This is not an AI-generated walking video or a fully articulated 3D character.

Only bounded polygon/joint coordinates are saved with the local character. Approved pixels are sent to the local helper through stdin; paths/prompts are not exported. The original image's existing safety checks still apply. See [privacy](PRIVACY.md) and [tested coverage](VALIDATION.md).
