[English](../en/3D-MOTION.md) | [한국어](../ko/3D-MOTION.md) · [Artwork](CREATIVE-ART.md)

# Experimental 8 GB pose-assisted 3D motion

This source implementation connects an approved artwork character to directional clips in the **actual Qt companion**. It is optional and experimental. The existing vector character and [editable 2D cutout motion](ARTWORK-MOTION.md) remain available.

## Use it

**Artwork generation, image-runtime preparation and 3D motion preparation are separate steps.** The top **1. Prepare runtime and selected models** button does not prepare 3D motion for the picture. An existing drawing can be reused.

1. Open **Settings → Character → Create original artwork…**. An existing artwork character opens in the preview; you do not need to draw it again. For a new character, finish image preparation/generation and its local reviews first.
2. Prefer one front-facing, full-body humanoid with two visible arms, separated hands and two clear legs/boots on a plain background. Adjust the original mouth cross before preparing motion. Hidden limbs, animals, props and unusual anatomy may fail.
3. Read the image model's license and the TripoSR/ViTPose terms below. Check the license acknowledgement near the top of this window. **Scroll inside the artwork window, below the picture and “Edit hand/foot motion…”**, then click **Prepare 3D motion · 8 GB · pose-assisted**. It downloads the optional components if needed and runs preparation. If the button is disabled, check that acknowledgement and finish any active job first. The acknowledgement resets when this window opens or the image model changes.
4. Watch the stage, real frame/view counter, elapsed time and time since the last report. Download/reconstruction stages may have no percentage. No overall ETA is promised. **Cancel preparation** stops only this job's owned workers and keeps the current character; completed verified stages can be reused on retry.
5. Use the dropdown below the preparation button to inspect **front idle, left/right walking, turning, wave, hop, cheer and both bites**. Check side/back details, foot motion, eyelids and jaw at small desktop size. Passing file validation does not establish visual quality or rights clearance.
6. Click **Use this character → Save settings** in the main window. Preparation alone does not replace the desktop character. It walks sideways, turns to front when paused/hovered and uses its own mouth coordinates during a bite. Existing click reactions and guardian safety boundaries are retained.
7. To undo it, reopen this artwork window, click **Return to original 2D artwork → Use this character → Save settings**. The source PNG and its earlier 2D rig remain intact. Edit the 2D joint regions only after returning to 2D. Changing the original mouth then requires preparing the derived motion again.

## A contrasting full-body example

Choose **Cloud mechanic → Insert example** in the artwork window. Its ivory curls, saffron vest, plum trousers and turquoise boots contrast with the earlier turquoise-haired character. Keep hands empty and away from the torso; a tool or long coat can hide the joints. This is a test design, not a guarantee of prompt compliance or successful rigging.

> One original chibi cloud-station mechanic, full-body front view, standing upright in the center. Oversized rounded head, short fluffy ivory curls, dark expressive eyes, lavender eyebrows and a small clearly visible smiling mouth. A saffron cropped vest over a cream long-sleeved shirt, muted plum trousers and two chunky turquoise ankle boots. Two arms slightly away from the torso, both elbows and wrists visible, empty open hands separated from the vest. Two distinct legs with a clear gap between the boots; visible knees and ankles. One small mint hexagonal fabric patch stitched at the center of the chest, no logo. Friendly clean painted illustration with simple rounded volumes and readable facial features. The whole figure including hair, hands and soles fits inside the image with generous white margins. Plain white background. Only one character, no held tools, hat, bag, floating objects, pedestal, text or additional views.

Generate and inspect this new drawing before preparing its motion. Review left/right profiles for identity and clothing consistency, both arm/leg cycles, front idle/eyelids, click reactions and both mouth anchors. A passed content review can still have bad anatomy. Rejected output must not be applied. Set actual wandering under **Settings → General → Walking direction → Left/Right → Save settings**; the preview dropdown does not change that global preference. [Direction details](GETTING_STARTED.md).

## What runs, and when

| Stage | Actual implementation |
| --- | --- |
| Approved drawing | Existing SD 1.5/SDXL flow and content reviews, or a previously approved local PNG |
| Views and mesh | One **TripoSR** learned scene produces eight consistent camera views and a reconstructed surface; its owned CUDA worker exits |
| Joints and skin | A separate **CPU ViTPose** worker predicts 17 human landmarks; Pawzura lifts them into the surface and computes 12-bone skin weights; the worker exits |
| Motions and face | A separate CPU worker applies authored gait, eyelid/jaw/smile corrections and bakes 437 transparent 256 px frames across 12 clips; the worker exits |
| Playback | Source-bound, checksum-validated PNG pack, cached Qt image playback; no resident inference model |

This uses a shared single-image reconstruction to preserve view identity. It does **not** fuse independently generated drawing frames, perform learned video generation, or invoke UniRig/a specialist learned 3D skeleton-and-skinning model. The body rig is **pose-assisted**; facial controls and motion are procedural. The larger staged design remains in [the architecture guide](STAGED-CHARACTER-PIPELINE.md).

Only one owned preparation runs at a time in the app. Workers launch without a shell and on Windows are assigned to a kill-on-close process job before starting; cancellation waits for their exit. If release cannot be verified, restart Pawzura before another preparation. The user's Ollama service and unrelated GPU apps are not stopped.

## Hardware, downloads and licenses

- This path currently requires an **NVIDIA CUDA GPU with at least 8 GB VRAM**, plus an already prepared isolated Python 3.12 image runtime. Other 2/4/6 GB guides still concern image generation/2D motion; they do not enable this 3D path.
- Allow approximately **1.7 GB additional TripoSR weights**, the existing ~350 MB CPU pose weights if missing, small source/library downloads and extra disk for local stages/frames. The main [image-runtime requirements](CREATIVE-ART.md) still apply. Capacity is not free memory; close other large workloads yourself.
- [TripoSR code](https://github.com/VAST-AI-Research/TripoSR) and [weights](https://huggingface.co/stabilityai/TripoSR): **MIT**. [DINO ViT-B/16](https://huggingface.co/facebook/dino-vitb16) configuration: **Apache-2.0**; its separate pretrained weights are not downloaded. The TripoSR checkpoint already contains its trained components.
- [ViTPose base simple](https://huggingface.co/usyd-community/vitpose-base-simple): **Apache-2.0**. Pinned source revisions, model hashes and dependency terms are in the [motion catalog](../../art_runtime/motion_catalog.json), [source record](../../art_runtime/triposr-sources.json) and [notices](THIRD-PARTY-NOTICES.md). App MIT does not replace these terms or the original drawing model's OpenRAIL terms.

Original upstream source is retained locally. Two unused optional imports are deferred in a separate adapted copy so this route can use its own surface extraction without compiling torchmcubes. No generated executable code is accepted. No model weights are bundled in source or EXE distributions.

## Recovery and local files

Stage caches are keyed by source-image hash, backend revision and relevant mouth settings. Actual files, sizes and hashes are checked before reuse. A changed source/backend invalidates dependent results; changing the mouth invalidates rigging and baking. Failure/cancellation keeps the prior character. Retry preparation to resume compatible completed stages.

Local folders beneath `%LOCALAPPDATA%/Pawzura`: `artwork` (source PNG), `motion` (validated ZIP packs), `motion-jobs` (stage data), and `art-runtime` (isolated runtime, downloaded models, original/adapted sources and their notices). Back up the source and motion folders with settings if needed. Prompts, allowlists and browser data are not part of a pack. Do not publish these personal folders; distribution checks reject them, renamed motion packs and model checkpoints. See [privacy](PRIVACY.md).

Missing/corrupt motion falls back to the original 2D image and the artwork window explains how to prepare again. This fallback does not count as successful 3D preparation. Ordinary character recovery still cancels stale actions.

## Tested result and remaining limits

2026-11-03 source check on Windows 10, RTX 2070 Max-Q **8 GiB**, ~32 GiB RAM; main CPython 3.14.7/Qt 6.12, separate CPython 3.12.14/PyTorch 2.7.1 CUDA 11.8 worker. One previously approved original QA drawing completed actual reconstruction → automatic pose/weights → 437 frames in **197.26 seconds** with cached model files. TripoSR peak PyTorch-allocated memory was **1936.12 MiB**; this excludes driver/display/other applications and is not a minimum-VRAM guarantee or fresh-download timing.

The native source app subsequently reused verified stages through its artwork dialog, saved/applied the pack and walked **116 px** at the current monitor work-area floor. Front pause, clip mouth alignment, one synthetic bite callback, cancelled action suppression and eight English/Korean dark/light normal/minimum widget renders were checked. Native targeting/closing was blocked in this test. This was not a fresh diffusion generation, real blocked-app close, user-input E2E, packaged EXE, multi-monitor or Windows 11 validation of the new path.


Additional source check on the same 8 GiB machine: the built-in **Cloud mechanic** example produced a new SDXL image and passed the existing content reviews in **184.52 s**. Its pose-assisted preparation then produced 437 frames in **160.44 s**. The visible mouth was manually marked at normalized `(0.49, 0.375)` because the vision estimate was too low; body joints and weights were automatic. The native source app's saved direction setting moved this new character **100 px left and 101 px right** at the work-area floor, restored the chosen direction after a target-facing synthetic bite, and preserved left walking after recovery/reopening settings. These are test-owned widget actions, not OS-input E2E. The drawing missed some requested colors and retained small white background pieces; the reconstructed face/edges softened and some limb seams remained. File/content passes do not make those quality defects a pass.

Quality remains uneven: point-rendered edges can look rough, wrists/clothes can distort, feet can slide, and inferred side/back details may differ from the drawing. Wave amplitude and facial corrections may be subtle or misplaced. Pose confidence does not prove correct 3D anatomy. This is a usable experimental connection, **not a guarantee of better-looking animation than the vector character**. Inspect each result; keep the original if it is worse.

A later boundary run found repeated native tool-window resizing when entering the 125% left monitor. Fixed logical size, explicit destination-screen assignment and handling the native resize event corrected it. The new artwork then passed size/floor and preferred-direction checks across that real boundary; a separate model-free probe passed 238 samples over both 100%/125% directions. Other arrangements and Windows 11 still need separate checks. [Repeat the probe](GETTING_STARTED.md).

[Save and reuse characters locally](CHARACTER-LIBRARY.md): approved drawing/motion versions are retained automatically; load saved pixels/clips without running a model. Intermediate preparation is reused by stage fingerprint.

## Posture correction and retained versions

The original humanoid fit derived torso pivots before depth regularization but limb pivots afterwards. That mixed coordinate basis exaggerated the inferred trunk angle (about −17° in the cloud-mechanic sample). Pivots now use the same regularized joints. A bounded upper-body correction targets a neutral 2° forward trunk lean, at most 20° from its fitted rest angle; head/shoulder transforms remain connected and leg lengths/contact targets are preserved. This is an authored posture correction, not a new learned motion model or a guarantee of anatomically natural walking. Foot sliding, soft edges and imperfect skinning remain possible.

Existing PNGs and verified scenes were reused for two saved humanoids; only CPU rigging/baking ran. Older motion packs remain available in the [local library](CHARACTER-LIBRARY.md). To update an older saved character, open its artwork window and prepare motion again, then review and apply the new version. Do not regenerate the drawing just to rebuild its motion. The saved library can load both old and corrected clips without inference.
