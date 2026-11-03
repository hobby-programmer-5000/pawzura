[English](../en/ANIMATION-EXPERIMENT.md) | [한국어](../ko/ANIMATION-EXPERIMENT.md) · [Research survey](ANIMATION-RESEARCH.md)

# Single-image animation experiment

**2026-11-03, Asia/Seoul.** Local prototype results against Pawzura source `f8bb0bf81b84a2478f4425ffaa42a9b98f63d58b`; not an app integration or release. The earlier [survey](ANIMATION-RESEARCH.md) is followed here by actual mesh and facial inference tests. One-to-All received a resource preflight only, not video inference.

## Environment and input

- Windows 10 x64 build 19045; NVIDIA RTX 2070 Max-Q, 8 GiB VRAM; about 32 GiB system RAM.
- Separate Python 3.12.14 experiment environment, PyTorch 2.7.1+cu118, NumPy 1.26.4, SciPy 1.16.3, Pillow 12.0.0. Existing CUDA packages were reused read-only; main app dependencies/settings were not changed.
- One original, previously approved agent-generated SDXL QA illustration, not a user's picture or prompt. The 0.3.0 input PNG hash was checked before processing. Body comparison resolution: 256×256, with an additional 144-pixel display preview.
- No user's guardian, browser profile, saved character or GPU process was controlled. Timings are observations under desktop workloads, not isolated-device performance guarantees.

## Results

| Test | Observed result | Resource/time scope |
| --- | --- | --- |
| Current 0.3.0 cutouts | 48 walking/waving frames exported as baseline | 0.85 s for the instrumented Qt export, including PNG writes |
| Official ARAP solver + experimental mesh renderer | 72 CPU frames; same wrist/ankle paths for the walking/waving comparison. Additional stronger joint-path experiment | 22.09 s in the measured 72-frame run; solver mean 14.06 ms/frame plus Python rasterizer 279.72 ms/frame. Actual process peak working set 83.64 MiB |
| Corrected stronger arm motion | 24 further frames after fixing mirrored-arm phase; elbow vertical-motion correlation −0.941 | 6.77 s, actual process peak working set 83.11 MiB. This uses different pose paths, so it is not a matched-motion quality comparison |
| THA3 `separable_half` | **72 actual neural frames:** blink, smile and head/gaze controls, 24 each | 512×512 inference, 256×256 aligned copies. Measured run 9.25 s including model warm start and frame writes; mean inference 36.54 ms/frame, p95 47.00 ms; warm start 1.98 s |
| THA3 small-model GPU/RAM | Runs on this 8 GiB device | PyTorch peak allocated **219.43 MiB**, reserved **324 MiB**; actual process peak working set **801.95 MiB**. CUDA context, other apps and driver memory are not included in the PyTorch counters |
| THA3 `standard_half` quality comparison | **72 further neural frames**, same input and controls; selected for the final hybrid preview | 11.78 s including warm start/writes; mean inference **43.18 ms/frame**, p95 62.45 ms, warm start 4.02 s. Allocated/reserved VRAM **475.94/564 MiB**; actual process RAM peak **956.61 MiB** |
| One-to-All 1.3B default all-GPU path | **Preflight failed; full generation NOT RUN** | Its UMT5 encoder has 5,680,910,336 parameters: 10.582 GiB at 16-bit before generator/VAE/activations. This exceeds total 8 GiB, not merely free memory. No deliberate GPU OOM was induced |

THA3's input was fitted to the author's frontal 512×512 RGBA layout. Testing this one correctly placed SD illustration does not establish arbitrary-character success. This is facial neural rendering plus geometric body motion, **not** a successful full-body video-diffusion test.

## Visual findings

The blink and happy-expression frames visibly change the eyes and mouth; head/gaze controls also produce new frames. On this input the standard model's closed-eye/smile lines look clearer than the small variant, while skin-tone patches remain. Both were retained for comparison. A temporary face-region composite demonstrates how these frames could accompany a walking mesh. At 144 pixels the expression remains visible, but facial softening and skin-tone patches need further work. The current composite is not a final blending method.

The connected mesh avoids treating each limb as a detached patch. It still bends a single texture: strong poses can stretch sleeves or distort outlines, and it cannot paint hidden anatomy. Added arm/knee trajectories matter as much as switching the renderer; a mesh with the old endpoint paths can still look restrained.

Initial triangle-by-triangle rasterization left visible holes/jagged edges. A supersampled pixel-center rasterizer, silhouette margin and fixed head constraints reduced those artifacts. Rest-pose geometry max error was 0.0114 px, and thresholded alpha-mask intersection-over-union was 0.9826. Those numerical checks do not prove good animation; representative pose/face contact sheets were also inspected.

An initial stronger-motion curve raised mirrored arms together. The corrected experimental curve alternates their vertical movement; the correlation assertion guards that specific mistake. The released app has not received this change.

## Output and validation boundaries

Local ignored experiment output contains English/Korean HTML previews, animated walking/waving comparisons, a clearly labeled stronger-motion comparison, 144-pixel previews, expression close-ups, transparent PNG frames, source/weight hashes, scripts and resource receipts. These QA artifacts and model files are not bundled in Pawzura or committed with this document.

Each GIF was reopened and verified to contain 24 frames. Cached preview timing is 40 ms/frame (25 FPS), not a real-time inference benchmark or a reproduction of the app's full idle/event timing. Model output was checked for finite values; source hashes, rest-pose geometry/alpha coverage and phase behavior were checked. The same-path body comparisons are separate from the stronger-motion comparison. English/Korean reports were rendered with isolated headless Chrome profiles and inspected; an initial English capture had missing glyphs, resolved with explicit fonts, fixed device scale and a longer capture budget. Selector/pause interactions were not driven, so no complete browser UI E2E claim is made.

An early RAM monitor observed the small venv launcher instead of the real inference process, yielding invalid 7.89 MiB readings. Those readings are excluded above. The final measurements query OS peak counters **inside the actual child process**. Earlier failed/rough outputs remain in local evidence.

## Provenance and licenses

| Component | Tested source | Terms |
| --- | --- | --- |
| [Meta Animated Drawings](https://github.com/facebookresearch/AnimatedDrawings) ARAP solver | `b859684857519c7424da51a0b0862fbd1fd258f4` | MIT; only the solver was used, with a custom test mesh/rasterizer, not the upstream full application |
| [Talking Head Anime 3](https://github.com/pkhungurn/talking-head-anime-3-demo), Pramook Khungurn | `8946939ec7b417f443d7b0e3fcd97384313fcdb8` | Code MIT; model weights CC BY 4.0. Five files each for `separable_half` and `standard_half`, fetched from the author's linked archive |
| [HF THA3 mirror](https://huggingface.co/OktayAlpk/talking-head-anime-3) | `cd1db3407b5542434724b5732cca34c9d9f68a39` | All ten author's archive weight hashes matched this mirror's pinned SHA-256 metadata; this is a community mirror, not an author-owned model account |
| [One-to-All](https://github.com/ssj9596/One-to-All-Animation) preflight source | `b3c9d886c93c43e767b995e93968708ee2d410cb` | No generator weights downloaded/run; survey's dependency/usage-scope caveats remain |
| [Wan base model](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers) encoder configuration | `0fad780a534b6463e45facd96134c9f345acfa5b` | Configuration used to instantiate the encoder on the meta device and count parameters, without allocating its weights |

No new model is added to the supported app list. Before any integration, retain original licenses/attribution, validate the complete dependency stack, and keep the existing character/content/guardian boundaries.

## Decision supported by this test

**Scope update:** the later requirement for side-facing travel and volumetric turning is evaluated separately in [Directional walking and depth](DIRECTIONAL-ANIMATION.md). The frontal tests below do not satisfy it; the later static 3D views do not yet establish walking either.

**A cached mesh-plus-facial-frame path is worth a product prototype.** The test demonstrates real expression generation within this GPU's capacity and a CPU body-animation preparation path. It also demonstrates why the default One-to-All script is not an 8 GiB recipe.

Next work would be better automatic face fitting/blending, less distorted full-body motion, event/clip transitions, cache playback and failure/cancellation handling. Separately, CPU/quantized text encoding and generator/VAE offload could make One-to-All worth another experiment; this test does not establish that result. App integration and a new EXE were not part of this experiment.
