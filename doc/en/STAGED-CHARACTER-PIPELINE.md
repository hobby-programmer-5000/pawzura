[English](../en/STAGED-CHARACTER-PIPELINE.md) | [한국어](../ko/STAGED-CHARACTER-PIPELINE.md) · [Directional animation](DIRECTIONAL-ANIMATION.md) · [3D Rigging & Motion References](3D-RIGGING-AND-MOTION-REFERENCES.md)

# Consistent frames and sequential model preparation

User-directed architecture, recorded 2026-11-03. A first [8 GB pose-assisted connection](3D-MOTION.md) is implemented and checked in the source app. It reuses one approved drawing, derives views/mesh from one shared TripoSR scene, then runs separate CPU pose/weight fitting and frame-baking workers. It does not implement the larger independent-drawing-frame → specialist learned 3D rigger plan below. The existing 0.3.0 release is unchanged; no new EXE is implied. The remaining sections describe the broader target and its constraints.

## Stage order

```mermaid
flowchart LR
    A[Approved reference character] --> B[Consistent drawing frames]
    B --> C[Review and save frame set]
    C --> D[Release drawing worker]
    D --> E[Reconstruct a textured 3D mesh]
    E --> F[Release reconstruction worker]
    F --> G[Predict skeleton and skin weights]
    G --> H[Release rigging worker]
    H --> I[Fit motion and facial controls]
    I --> J[Bake and review transparent clips]
    J --> K[Apply validated pack to Qt companion]
```

**Reconstruction and rigging have different inputs and outputs.** Reconstruction creates mesh geometry/materials from supported image inputs. Rigging takes that mesh and supplies a skeleton plus skinning weights. Rigging alone does not turn 2D pictures into a 3D character. A skeleton alone also does not provide walking, blinking or an opening jaw.

## Consistency comes before quantity

Create and approve one canonical character first. Condition subsequent images on that reference, retaining body proportions, face, colors, clothing and the side of asymmetric accessories. Reusing the same prompt or random seed is not sufficient identity control. A generation backend must demonstrate reference-conditioned consistency before it becomes a product option; no particular new drawing backend is selected by this document.

Use two explicitly separate frame groups:

| Group | Purpose and constraints |
| --- | --- |
| Neutral view set | Front, both three-quarter views, both profiles and back, with the same neutral pose, scale, lighting and complete silhouette. Used for reconstruction only if the chosen backend supports those views. |
| Expression/motion references | Blink, smile, mouth opening, walk/contact poses as needed. May guide later facial controls, retargeting and visual checks; these changing poses are not additional camera views of one static object. |

Do not mix varying limb poses into a static multi-view reconstruction input. Do not merge all views into one reference sheet and feed it to the current single-subject image/app path. Do not reconstruct and rig every frame independently; one shared mesh/rig supplies identity across the animation.

Requested view labels are not measured camera calibration. A multi-view reconstructor requiring camera intrinsics/extrinsics needs actual or validated estimated camera data. A side image generated from text is not automatically a calibrated 90° observation. Hidden surfaces are inferred, and must be reviewed rather than treated as ground truth.

Review each image for identity drift, extra characters/limbs, silhouette continuity, consistent accessories and usable visible hands/feet. Check the view set together. Automatic similarity scores and the existing single-subject checks can miss errors; preserve the last accepted set and regenerate only rejected frames using the same reference. Private descriptions stay session-only, outside settings/logs and cache manifests.

## Model roles and current evidence

| Role | Candidate/evidence | Boundary |
| --- | --- | --- |
| Consistent drawing | Current SD 1.5 / SDXL generate single pictures; their existing licenses still apply | Neither current independent generation nor the added example selector proves multi-view identity preservation. Backend selection remains open. |
| 3D reconstruction | [TripoSR](https://github.com/VAST-AI-Research/TripoSR), [official MIT model](https://huggingface.co/stabilityai/TripoSR); an isolated cached single-image test produced actual novel views | Its official interface is single-image reconstruction, not a multi-view fusion backend. Passing a list of images produces separate scenes, not one fused character. The prior manual QA rig is not automatic rigging. |
| Skeleton and skin weights | [UniRig](https://github.com/VAST-AI-Research/UniRig), [official MIT model card](https://huggingface.co/VAST-AI/UniRig) | Candidate only, not installed/run here. The card requires **more than 8 GB VRAM**; sequential execution alone does not establish an 8 GB configuration. Skeleton and skinning outputs must both be verified. |
| Facial/motion controls | Jaw/eye controls, blend shapes or reviewed corrective assets, plus retargeted motion | Body auto-rigging does not prove these outputs exist. Missing eye/jaw controls must be reported rather than advertised as expressive animation. |

Sources checked 2026-11-03. UniRig's repository describes released skeleton/skinning components, while its model card retains wording about forthcoming components. Pin and inspect the exact checkpoint/configuration before choosing it. Upstream lists Python 3.11 and native/Blender dependencies; Windows compatibility, installed component terms and actual inference memory remain untested. A training memory figure is not an inference requirement. Pawzura's Python 3.12+ GUI remains separate from any independently validated optional worker runtime.

Models and dependencies keep their own licenses. The main app stays MIT. No candidate becomes a supported model, download button or bundled weight merely by appearing in this design.

## What “turn the previous model off” means

For heavy stages, prefer a separate owned worker process. Finish writing and validating its output, wait for that process to exit, and release its pipes/handles before launching the next heavy worker. `del`, garbage collection and a CUDA cache-clear call inside a surviving process are not equivalent to verified worker termination. The current image runner already provides a subprocess boundary that can be extended; the implemented 8 GB controller now uses separate owned workers and verified stage caching, as described in the linked usage guide.

Use one application-wide preparation slot for owned GPU work, not only a sequential loop inside each dialog. A second preparation job must not start while a previous job is still releasing its worker. Carry a job/generation identifier through stage results, and discard results after cancellation or input changes; a late completion cannot revive an old preparation or apply it to a different character.

Unload only models/processes owned by this job. Do not stop the user's Ollama service or unrelated GPU apps. Existing local reviews request `keep_alive: 0`; account for review model use before starting another GPU stage. Shared-service ownership and cleanup must be explicit.

Other applications and Windows retain VRAM, so do not wait for total GPU usage to reach zero. Check the next stage's available headroom and measured requirements. One-at-a-time loading reduces overlapping allocations; it does not make an individually oversized model fit. An exit/cleanup timeout, insufficient headroom or model error stops preparation and retains the previous character. Show the current stage, real progress when available, elapsed time and the next action; do not invent an overall percentage or ETA.

## Saved stage outputs and recovery

| Boundary | Required accepted output |
| --- | --- |
| Drawing complete | Individually validated view/reference images, approved grouping, hashes, bounded dimensions and relevant camera/pose metadata; no private prompt text |
| Reconstruction complete | One bounded mesh/material asset referencing the accepted input hashes; compatible topology/scale and reviewed side/back appearance |
| Rigging complete | Finite joints, acyclic parent hierarchy, valid vertex influence indices and normalized nonnegative skin weights matching that mesh |
| Motion preparation complete | Appropriate gait/contact poses plus actual eye/jaw/expression controls; foot and mouth anchors validated against the rendered character |
| Ready to apply | Transparent directional clips with bounded timing/frame counts, per-frame contact anchors, loop/transition checks and 144-pixel review |

Write each stage to a temporary result and promote it atomically only after validation. Key caches by accepted image/mesh hashes, backend revisions and settings. A changed input invalidates its downstream results. Resume from the last compatible accepted stage after failure; do not unnecessarily repeat the completed drawing stage. The existence of files is not a success signal.

Animate one approved rig, bake lightweight clips and use the existing Qt companion as the final acceptance surface. Walk sideways, plant feet, turn front when stopped, react to cursor/click, and perform jaw-aligned synthetic bites before testing integration. Monitor geometry, cancellation and existing guardian/browser boundaries remain independent requirements. Preview must never become a live close request.

Only apply the new pack after its review and validation succeed. A preparation failure keeps the old character. A 2D fallback must be identified explicitly and cannot count as successful 3D preparation. Ordinary companion playback should not require keeping the drawing, reconstruction or rigging model resident.
