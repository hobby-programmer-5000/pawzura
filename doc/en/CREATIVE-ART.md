[English](../en/CREATIVE-ART.md) | [한국어](../ko/CREATIVE-ART.md) · [Documentation](../README.md)

# Original artwork with a GPU

Source update: [experimental 8 GB pose-assisted 3D motion](3D-MOTION.md) now connects approved artwork to the actual app. The older release/experiment descriptions below retain their original scope.

**Character → Create original artwork…** generates actual pixels instead of selecting the same vector ears, tails and accessories. Use descriptions of original silhouettes, clothing, hair, materials and illustration styles. The lightweight **Generate with Qwen** and manual trait options remain available without the image runtime.

## Before downloading

- Windows 10/11 x64 and a supported **NVIDIA CUDA GPU** are required for this optional implementation. AMD/Intel graphics and CPU-only image generation are not supported. The main app still works without this feature.
- Install and start [Ollama](https://ollama.com/). The image runtime is separate: Windows Ollama is used for **local review**, not for drawing the image.
- Allow **25 GB of disk space**, at least **16 GB system RAM** (32 GB recommended for SDXL), and additional free VRAM. Total capacity is not available memory. Close other GPU/model workloads yourself if needed.
- Downloads can take tens of minutes. The first setup downloads roughly 4 GB of runtime packages, about 3.9 GB of review/motion models and the selected image weights. Installation expands these files and caches may consume more space. Keep the window open until it finishes.
- **Check the selected advanced model's original license before use.** Pawzura code is MIT; SD 1.5 and SDXL weights use different, restricted OpenRAIL licenses, not MIT/Apache or OSI-approved open-source terms. The app does not bundle or relicense weights. The optional installer also downloads third-party runtime packages, including NVIDIA components with their own terms. See [notices](THIRD-PARTY-NOTICES.md).

## Select a memory guide

These are conservative starting configurations, **not a guarantee of fit or quality**. Hardware, free memory, driver and system RAM affect success. A higher tier changes the image model/resolution, rather than applying the vector designer's fixed trait list.

| GPU VRAM guide | Image model | Resolution | CPU offload | Image weights | Original terms |
| --- | --- | --- | --- | --- | --- |
| 2 GB | [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5) | 384 × 384 | Sequential, very slow | ~2.3 GB | [CreativeML OpenRAIL-M](https://github.com/CompVis/stable-diffusion/blob/main/LICENSE) |
| 4 GB | SD 1.5 | 512 × 512 | Model | ~2.3 GB | Same SD 1.5 terms |
| 6 GB | [SDXL base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | 768 × 768 | Sequential, very slow | ~7 GB | [CreativeML Open RAIL++-M](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/LICENSE.md) |
| 8 GB | SDXL base 1.0 | 1024 × 1024 | Model | ~7 GB | Same SDXL terms |

The image model generates a single illustration. There is no preset list of body shapes, clothing or hairstyles, but prompt following, anatomy and background removal remain imperfect. More VRAM does not guarantee a prettier design. Long descriptions can lose later details in the text encoder; put distinctive features first and keep them concise.

## Prepare and generate

1. Open **Character → Create original artwork…** (also available in **Advanced**).
2. Choose your VRAM guide. Open the model's original license link and read its restrictions. Check the acknowledgement for that selection. Changing the guide clears it. The acknowledgement is session-only.
3. Click **1. Prepare runtime and selected models**. This explicitly installs an isolated Python 3.12.14 environment and pinned CUDA image packages under `%LOCALAPPDATA%\Pawzura\art-runtime`. It does not change global Python, PATH, administrator permissions or persistent PowerShell execution policy. Runtime bootstrapping uses a checksum-verified official uv download. Preparation is resumable; run it again after a failed download or when changing image families.
4. Preparation downloads the selected image weights, a CPU NSFW classifier, a background-removal model, an Apache-2.0 ViTPose joint helper, and these exact local Ollama review models:

   ```powershell
   ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
   ollama pull qwen3-vl:2b
   ```

5. Enter an original description, or select **Motion-friendly drawing examples → Chibi astronomer / Woodland courier / Clockwork gardener**, then click **Insert example**. Selecting a name alone preserves your current text; Insert example replaces it. The examples request a front-facing full body with visible, separated hands and feet on white, making the current motion setup easier. The selector and insert button are disabled while generation is running. You can edit the inserted description before generating. Do not name an existing character, franchise or logo. Do not include restricted content even as a negative instruction.
6. Click **Generate artwork**. The local stages are description verdict → concise English summary when needed → image generation → image classifier/background removal → optional joint suggestions → composition/vision review. Generation asks for one centered figure and discourages reference sheets and repeated views. A transparent-silhouette check rejects substantial separate upright figures; the vision response must also explicitly identify a single character. A laptop may take many minutes, especially with sequential offload. Wait for the current operation before closing the dialog or quitting.
7. Inspect the preview. Click **Use this character**, then **Save settings** in the main window. This final save applies the companion. Errors retain the previous design; the old result remains selectable after a failed retry.

No private prompt or image goes to a cloud inference service. Setup contacts official package/model hosts; inference uses fixed local files and `127.0.0.1:11434`. Descriptions remain in the dialog for the session and are not written to settings, command arguments or app logs. Ollama is an external service with its own behavior. Approved PNG pixels are stored locally under `%LOCALAPPDATA%\Pawzura\artwork` by content hash; no arbitrary model-supplied file path is accepted. Metadata is removed. Up to 20 design references remain in history; old PNG files are not automatically deleted.


## Follow progress

A progress area stays below the scrolling content during preparation/generation. It shows the current stage, total elapsed time, time in the current stage, and the age of the last progress report. Drawing uses real completed diffusion steps (for example 12/30); this percentage belongs only to that stage, not the entire operation. Scheduler step counts can differ between models. Image decoding, CPU safety checks, background removal and final vision review follow drawing; 30/30 is not final success.

Library/model loading and local review use an indeterminate bar because they do not provide a reliable percentage. Installation reports tool/Python/PyTorch/library/license stages. Model preparation counts completed model groups, not downloaded bytes. No overall ETA is fabricated. If no progress is reported for 60 seconds, the panel says so: loading, CPU offload, network transfer or review may still be running, so this alone does not prove a hang. A new report clears the notice. Closing a busy dialog leaves the stage/counters visible.

Completion/failure freezes the elapsed time and clearly marks Completed/Stopped. Existing review timeouts apply; the image worker wait is limited to 30 minutes, runtime installation and each Ollama pull to 60 minutes. A timeout stops waiting and preserves the previous character; a local review or installer child may still finish in the background. No late progress/output is applied after failure. This update does not add cancellation or bypass content review. Progress contains only fixed stage codes and numeric counters; backend logs, prompts, local paths and pairing data are not displayed or persisted.


## Animation and recovery

New humanoid artwork receives editable hand/forearm and foot cutout suggestions from the local CPU joint helper. The app moves these original pixels independently during walking, waving and cheering; it does not generate a 3D rig or AI video. Hover pauses walking and greets, clicks cycle wave/hop/cheer, and idle greetings occur occasionally. Double-click/right-click still opens settings. These visual reactions never close an app/tab or replace a guardian bite.

To check an example in the app, wait for all generation/review stages to finish, inspect the picture and motion areas, then **Use this character → Save settings**. Keep **guardian off** and **website control off** while checking appearance. The companion should walk along the current monitor's available work-area floor; hover/click to check reactions. The existing settings animation preview can show a bite without closing a real window. Recovery cancels the animation and returns the companion to the current floor. Results vary: a successful picture or joint estimate does not establish natural limb motion.

If generation produces a sheet with small extra figures or several views, the whole sheet must not be used as one pet. The composition error asks you to request one centered full-body character standing alone on white, then generate again. Rejected output is not stored/applied; the previous result remains selectable. The silhouette heuristic can reject large detached accessories and can miss touching/connected figures; the local vision model can also miscount. Inspect the entire picture even after checks pass. These checks are quality aids, not proof of a correct rig or a single subject in every case.

The separate [directional-animation research demo](DIRECTIONAL-ANIMATION.md) uses a manually fitted 3D character and procedural facial controls. It is **not connected to this generation/app path**. These drawing examples do not activate side-view turns, profile expressions or that demo's animated jaw. Verify the app's current 2D behavior separately rather than treating the research preview as a shipped feature.

For existing pictures, open **Character → Edit hand/foot motion…**. Prepare the optional helper once, click **Estimate joints automatically**, inspect the four colored areas and joints, then **Use motion settings → Save settings**. No image regeneration is needed. Manual area/joint editing also works without the helper. New artwork has the same editor in its creation dialog. [Full motion guide](ARTWORK-MOTION.md).

Animals, hidden limbs and unusual clothing may need manual corrections. Revealed sleeve/cape areas use simple edge blending and can show seams; no missing anatomy is reconstructed. If estimation is unavailable, the creation dialog explicitly points to motion setup rather than claiming articulated motion. Unconfigured/disabled rigs retain the prior whole-image fallback. Mouth coordinates remain separately adjustable. The source PNG stays unchanged; rig geometry is kept with settings/history.

Vector appearance options cannot recolor an image. Regenerate to repaint it; Random/default returns to vector design. History restores retained image/rig references, and Recover companion on screen cancels current visual actions and recovers position. A missing/corrupt source image uses the existing vector fallback. Back up the artwork folder with settings.

## Content and rights

NSFW content and identifiable existing character/logo replication requests are prohibited. The app uses a lexical request filter, local Qwen description review, a separate CPU NSFW classifier and local Qwen3-VL image review. Unavailable/invalid reviews reject the operation instead of applying unchecked output. Checks can miss content and can reject safe artwork; this is **not copyright clearance or a perfect safety filter**. Inspect every output before using/sharing it. Model licenses do not guarantee exclusive rights, trademark clearance, or freedom from third-party rights in generated images. Keep the applicable terms if redistributing models; Pawzura's MIT does not replace them.

## When something fails

| Symptom | Next step |
| --- | --- |
| Preparation/generation buttons disabled | Read the license and check the acknowledgement for the selected guide. |
| Runtime missing/setup failed | Check internet, 25 GB free disk, current NVIDIA driver and Ollama installation. Retry Preparation; downloads reuse the cache. |
| Review model missing | The error names the description/image stage and exact model. Run Preparation or its displayed `ollama pull` command. |
| Review response cut short | This is a response-limit failure, not a missing-model diagnosis. Update Pawzura to 0.2.2+; it separates verdict from summarization. If it repeats, keep the main visual features and shorten the description. |
| Ollama unreachable / review timeout | Start Ollama or wait for other local model work/free memory, then retry. Reinstalling the image environment does not fix a disconnected service. |
| Review memory / service / invalid answer | Follow the specific named-model message. Free memory for a memory error; update Ollama/check its exact model name for service errors. Invalid/incomplete JSON is rejected; users do not need to edit JSON. |
| CUDA unavailable | Update the NVIDIA driver. This mode does not support AMD/Intel/CPU. Continue with the vector designer if incompatible. |
| Out of memory | Close other GPU workloads; switch from 8/6 GB to 4/2 GB and prepare SD 1.5. Free system RAM too. Do not assume an 8 GB RAM laptop has 8 GB VRAM. |
| Cutout failed/parts missing | Request one full-body character, a clear silhouette and plain white background; simplify floating accessories and retry. |
| Safe request rejected | Avoid existing identities, logos, sexual/violent details and restricted terms in negative instructions; describe an original design more clearly. The app does not bypass failed review. |
| Need local runtime diagnosis | In PowerShell, run the command below from the extracted Pawzura/source folder. `cuda: true` confirms only runtime visibility, not enough free memory. No prompt is involved. |

```powershell
& "$env:LOCALAPPDATA\Pawzura\art-runtime\venv\Scripts\python.exe" art_runtime\runner.py check --tier 8 --cache "$env:LOCALAPPDATA\Pawzura\art-runtime\models"
```

Pinned model revisions are recorded in [the catalog](../../art_runtime/catalog.json). The optional runtime keeps package license files in its environment. See [validation](VALIDATION.md) for tested environments and remaining GPU coverage; do not infer 2/4/6 GB device testing from an 8 GB result.

Description review now returns only a small verdict over the full input. Approved non-ASCII/long input is summarized separately into bounded English (at most 512 characters, compacted to 55 words); short usable ASCII descriptions remain unchanged. Common Korean color translations are hints, not appearance restrictions. Small-model summaries can still omit/alter details; concise English is useful when exact wording matters. The 8,192-token text-review context and 1,024-token summary budget need inference memory. Any failed verdict/summary/image review retains the old character rather than bypassing checks.

[Save and reuse characters locally](CHARACTER-LIBRARY.md): approved drawing/motion versions are retained automatically; load saved pixels/clips without running a model. Intermediate preparation is reused by stage fingerprint.
