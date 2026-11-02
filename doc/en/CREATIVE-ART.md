[English](../en/CREATIVE-ART.md) | [한국어](../ko/CREATIVE-ART.md) · [Documentation](../README.md)

# Original artwork with a GPU

**Character → Create original artwork…** generates actual pixels instead of selecting the same vector ears, tails and accessories. Use descriptions of original silhouettes, clothing, hair, materials and illustration styles. The lightweight **Generate with Qwen** and manual trait options remain available without the image runtime.

## Before downloading

- Windows 10/11 x64 and a supported **NVIDIA CUDA GPU** are required for this optional implementation. AMD/Intel graphics and CPU-only image generation are not supported. The main app still works without this feature.
- Install and start [Ollama](https://ollama.com/). The image runtime is separate: Windows Ollama is used for **local review**, not for drawing the image.
- Allow **25 GB of disk space**, at least **16 GB system RAM** (32 GB recommended for SDXL), and additional free VRAM. Total capacity is not available memory. Close other GPU/model workloads yourself if needed.
- Downloads can take tens of minutes. The first setup downloads roughly 4 GB of runtime packages, about 3.5 GB of review models and the selected image weights. Installation expands these files and caches may consume more space. Keep the window open until it finishes.
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
4. Preparation downloads the selected image weights, a CPU NSFW classifier, a background-removal model, and these exact local Ollama review models:

   ```powershell
   ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
   ollama pull qwen3-vl:2b
   ```

5. Enter an original description or click **Insert example**. Example: “A tiny glass-and-brass astronomer with a crescent-shaped body, turquoise curly hair, an embroidered navy cape, copper boots and a floating lantern; warm watercolor and ink, friendly expression, full body.” Do not name an existing character, franchise or logo. Do not include restricted content even as a negative instruction.
6. Click **Generate artwork**. The local stages are description verdict → concise English summary when needed → image generation → image classifier/background removal → vision review. A laptop may take many minutes, especially with sequential offload. Wait for the current operation before closing the dialog or quitting.
7. Inspect the preview. Click **Use this character**, then **Save settings** in the main window. This final save applies the companion. Errors retain the previous design; the old result remains selectable after a failed retry.

No private prompt or image goes to a cloud inference service. Setup contacts official package/model hosts; inference uses fixed local files and `127.0.0.1:11434`. Descriptions remain in the dialog for the session and are not written to settings, command arguments or app logs. Ollama is an external service with its own behavior. Approved PNG pixels are stored locally under `%LOCALAPPDATA%\Pawzura\artwork` by content hash; no arbitrary model-supplied file path is accepted. Metadata is removed. Up to 20 design references remain in history; old PNG files are not automatically deleted.


## Follow progress

A progress area stays below the scrolling content during preparation/generation. It shows the current stage, total elapsed time, time in the current stage, and the age of the last progress report. Drawing uses real completed diffusion steps (for example 12/30); this percentage belongs only to that stage, not the entire operation. Scheduler step counts can differ between models. Image decoding, CPU safety checks, background removal and final vision review follow drawing; 30/30 is not final success.

Library/model loading and local review use an indeterminate bar because they do not provide a reliable percentage. Installation reports tool/Python/PyTorch/library/license stages. Model preparation counts completed model groups, not downloaded bytes. No overall ETA is fabricated. If no progress is reported for 60 seconds, the panel says so: loading, CPU offload, network transfer or review may still be running, so this alone does not prove a hang. A new report clears the notice. Closing a busy dialog leaves the stage/counters visible.

Completion/failure freezes the elapsed time and clearly marks Completed/Stopped. Existing review timeouts apply; the image worker wait is limited to 30 minutes, runtime installation and each Ollama pull to 60 minutes. A timeout stops waiting and preserves the previous character; a local review or installer child may still finish in the background. No late progress/output is applied after failure. This update does not add cancellation or bypass content review. Progress contains only fixed stage codes and numeric counters; backend logs, prompts, local paths and pairing data are not displayed or persisted.

## Animation and recovery

Artwork uses whole-image sway, horizontal flip and the existing jump/bite/crack sequence. It is **not an articulated or model-generated walking/blinking sprite rig**. A local vision estimate places the bite marker near the mouth; it can be approximate. Click the mouth in the creation preview to adjust the cross before using the character. The existing native/browser close protections still apply.

Vector appearance options cannot recolor or change an image. Regenerate artwork to edit it; **Random character** or **Reset default appearance** returns to vector design. **Use previous character** restores saved image/vector references. **Recover companion on screen** still recovers position. If a PNG is missing/corrupt, the renderer uses a vector fallback; regenerate or restore a retained image to recover the artwork. Keep the local artwork folder when backing up settings; copying the EXE alone does not copy your designs.

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
