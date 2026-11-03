[English](../en/CHARACTER-LIBRARY.md) | [한국어](../ko/CHARACTER-LIBRARY.md) · [Artwork](CREATIVE-ART.md)

# Save and reuse characters locally

Character generation can take minutes. Pawzura keeps approved drawing pixels and prepared animation so using a saved character does not require Ollama, image generation, reconstruction or rigging again.

## Save and load

- **Automatic:** successfully generated artwork and successfully prepared 3D motion are saved as separate local versions, even before you apply them to the desktop. The completion message confirms the save. A failed/rejected generation is not added. If automatic saving fails, the current character and generated asset files remain; use the manual save button after fixing the local storage problem.
- **Name a version:** open **Settings → Character → Save character…**. In the artwork window the same button saves the approved preview. Enter a name of 1–64 characters. Saving the same settings again preserves its name; manually naming that identical version updates its label rather than making another copy.
- **Restore:** choose **Saved characters…**, select a version and inspect it. Click **Use this character → Save settings** to apply it. Merely previewing or closing the library does not change the desktop. In the artwork window, the library shows artwork versions; the main character page also supports vector designs.
- Changing the drawing, mouth point, editable limb rig or animation pack produces a different saved version. Older approved versions and their pixels/clips remain available. The active character and the 20-item previous-character history are independent of the library.

The selector validates the source image and motion again before applying. Missing/corrupt assets leave the current character unchanged; restore the asset backup instead of regenerating reflexively. The original 2D version remains usable if you do not like a prepared 3D result.

## What is retained

Under `%LOCALAPPDATA%/Pawzura` in normal use:

| Folder | Contents |
| --- | --- |
| `character-library` | Named, bounded `.pawzura-character.json` entries: validated appearance, source/animation hashes and mouth/2D rig settings |
| `artwork` | Approved original PNG pixels |
| `motion` | Validated transparent directional clips with per-frame mouth anchors |
| `motion-jobs` | Verified intermediate reference views, surface mesh, joints/weights and stage metadata |
| `art-runtime` | Separate optional runtime, model downloads, sources and original notices |

Back up **settings plus `character-library`, `artwork`, `motion` and `motion-jobs` together** if you want both restored playback and reusable preparation data. Library JSON alone references the assets; it does not contain them. Copying the runtime/model cache is optional and large; preserve its component terms if redistributing it. Never include these personal folders in a public app distribution. Development reviews with a custom settings path may keep their library next to those temporary settings.

The library stores up to 500 versions. Replacing a character does not automatically remove older saved versions. Use the deletion controls below to manage disk usage.

## Delete an unwanted version

1. Open **Settings → Character → Saved characters…** and select a version.
2. Click **Delete…**. **Also delete files no longer in use** is checked by default. Uncheck it to remove only the library entry and retain all image/motion/cache files.
3. Review the estimated space and file count, then confirm **Delete…**. **Cancel** is the default. Deletion is permanent and does not use the Recycle Bin; back up anything you want to keep.

The applied or pending version cannot be deleted. Choose another character and **Save settings** first. Other saved versions, current/pending characters and the 20-item previous-character history protect the files they share. This means removing a saved version may free little space while its artwork remains in history. Unused source PNGs, motion ZIPs and recognized finished intermediate caches can be cleaned up; model downloads and the runtime stay installed. This is selected-version cleanup, not a scan for all old orphan files.

Pawzura checks references and file identities again after confirmation. If something changes, review and confirm again. Unfinished, unrecognized or unverifiable caches/files are retained. If a file is locked or cleanup partly fails, the message reports removed space and the entry is kept when possible for retry. Close the related preparation and try again; do not manually erase shared folders. Missing artwork disables **Use this character**, but its saved entry can still be removed.

## Reuse intermediate work

Preparation checks stage inputs, source hashes, bounded files and backend fingerprints before reuse. Reconstruction, rigging and baking have separate fingerprints: an authored-motion change can reuse the drawing, scene and compatible rig, while a rigging correction reuses the scene and rebuilds only joints/weights and clips. Changed image/model/reconstruction inputs still invalidate dependent results. Recognized older caches can be adopted only when their pinned stage algorithm and actual output hashes match; unknown/incompatible caches are recomputed. Caching reduces repeated work; it cannot make an individually oversized model fit.

The first posture correction reused the approved picture and verified TripoSR scene. It did not redraw the character or run another GPU reconstruction. A rig fix required CPU pose fitting and frame baking; a motion-only regression verifies that only baking runs. A second saved humanoid is checked separately from that fixture test.

## Local privacy and rights

Descriptions, browser lists, pairing codes, credentials and machine paths are not library metadata. The library contains generated content and custom names, so treat it as private local data. Default storage is outside the repository. `.gitignore` excludes the library, motion/stage/source folders, character-entry suffix and model checkpoints. Release checks also reject these folders and recognizable renamed library JSON. Do not force-add ignored personal data: Git ignore rules are not an access-control boundary.

Saving does not grant rights in a generated image. Original drawing/model/component terms remain applicable; see [notices](THIRD-PARTY-NOTICES.md) and [3D limitations](3D-MOTION.md). No model weights or generated character data are added to Git by this feature.
