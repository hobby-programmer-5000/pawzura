[English](../en/ADVANCED-MODELS.md) | [한국어](../ko/ADVANCED-MODELS.md) · [Documentation](../README.md)

# Advanced models and memory

**Keep Ollama running, download the selected model first, and leave sufficient free system RAM and GPU VRAM.** Opening Pawzura, using random/manual appearances and animating the pet require no model. These models interpret descriptions into the existing vector traits; they do not create new illustrations, clothing or hairstyles. Larger models or higher precision may help interpretation but do not guarantee a prettier result or perfect prompt adherence.

## Choose a model

1. Open **Advanced → Enable advanced character models**.
2. Choose your GPU's VRAM capacity: **2, 4, 6 or 8 GB**. If unknown, retain **CPU / unknown** and the basic models.
3. Open **Character → Appearance model** and select an available model. Enabling Advanced does not automatically select a larger model.
4. Beside the model selector, click **Copy command**. Open **PowerShell** (right-click Start → Windows PowerShell or Terminal), paste and press Enter. Wait for `success`, then return to Pawzura. The read-only command and download size follow your current selection, including unsaved changes. **Model setup guide** is available in Character and Advanced and lists all five commands.
5. Keep Ollama running, generate, inspect the preview and **Save settings**. Model choice and advanced preferences persist separately from work/leisure allowlists. Reducing the VRAM guide removes larger choices and selects 1.5B if necessary; the current character remains unchanged.

| Manual VRAM guide | Suggested model | Approx. weight download | License |
| --- | --- | --- | --- |
| CPU / unknown | Qwen2.5 0.5B or 1.5B Instruct · Q4_K_M | 0.49 / 1.12 GB | Apache-2.0 |
| 2 GB | Qwen2.5 1.5B Instruct · Q4_K_M | 1.12 GB | Apache-2.0 |
| 4 GB | Qwen3 4B · Q4_K_M | 2.50 GB | Apache-2.0 |
| 6 GB | Qwen3 4B · Q8_0 (higher precision, same parameter count) | 4.28 GB | Apache-2.0 |
| 8 GB | Qwen3 8B · Q4_K_M | 5.03 GB | Apache-2.0 |

## Exact download commands for every guide

Run only the command for the model you selected. Each model is a separate download; choosing a VRAM tier does not install it. Already installed models do not need to be downloaded again.

### CPU / unknown: lighter 0.5B (about 0.49 GB)

```powershell
ollama pull hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M
```

### 2 GB / CPU: 1.5B (about 1.12 GB)

```powershell
ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
```

### 4 GB: Qwen3 4B Q4_K_M (about 2.50 GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

### 6 GB: Qwen3 4B Q8_0 (about 4.28 GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q8_0
```

### 8 GB: Qwen3 8B Q4_K_M (about 5.03 GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
```

After `success`, `ollama list` must show the **exact identifier**, including the `hf.co/…` name and quantization suffix. A similarly named model, a different quantization or a GGUF downloaded into another folder is not automatically the model Pawzura requests. Return to **Generate with Qwen**, inspect the result, then **Save settings**. If PowerShell says `ollama` is not recognized, install/start Ollama and reopen PowerShell. Downloads require network access and disk space, separately from inference memory.

## Capacity versus free memory

**8 GB system RAM is not 8 GB GPU VRAM.** Use the GPU's dedicated VRAM capacity for Advanced. Choose CPU / unknown if unsure; do not choose 8 GB just because Windows reports 8 GB RAM.

These tiers are conservative selection guides, **not measured minimum VRAM requirements or device-validation claims**. Installed capacity differs from free VRAM. Weight file size excludes inference buffers, context/KV cache, display/driver allocations and other workloads. CPU offloading also needs system RAM and can be much slower. Integrated/shared memory is not equivalent to dedicated GPU VRAM. The app does not detect hardware, reserve memory or force GPU execution. Ollama's GPU support depends on the GPU, driver and backend; see its [GPU documentation](https://docs.ollama.com/gpu).

Use `ollama ps` to check actual loaded size and CPU/GPU placement. Start small, close other heavy GPU workloads and choose a smaller model if memory is insufficient. A GPU is optional when system RAM and CPU performance suffice. Advanced requests use a 4,096-token context, non-thinking JSON generation, a 180-second timeout and unload the used model afterward (`keep_alive: 0`); other models are not stopped. A timeout or load failure preserves the current character. See [Ollama memory/placement guidance](https://docs.ollama.com/faq) and [thinking controls](https://docs.ollama.com/capabilities/thinking).

## Models and licenses

Exact supported additional identifiers:

```text
hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
hf.co/Qwen/Qwen3-4B-GGUF:Q8_0
hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
```

Official sources: [Qwen3 4B files](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/main), [Qwen3 8B files](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/main), [Hugging Face Ollama integration](https://huggingface.co/docs/hub/en/ollama). Recorded revisions, exact byte counts and upstream SHA-256 values are in the [model catalog](../../artifacts/model-catalog.json). Unmodified license texts: [4B](../../licenses/upstream/Qwen3-4B-LICENSE.txt), [8B](../../licenses/upstream/Qwen3-8B-LICENSE.txt); [notices](THIRD-PARTY-NOTICES.md). No fine-tuning or weight redistribution occurs.

## If generation fails

- **Cannot connect / timeout:** start or update Ollama. Use the displayed pull command and try a smaller model if CPU generation exceeds the timeout.
- **Model missing / unsupported:** the app now shows the requested identifier and full pull command in the error. Use **Copy command** next to that selected model, wait for `success`, and generate again. If already installed, verify the exact name and update Ollama for Qwen3 support. Pawzura uses `127.0.0.1:11434`; a CLI pointing to another Ollama host or a different account can have a different model library. The app does not substitute another model silently.
- **Not enough memory:** choose a smaller model or free RAM/VRAM; the tier is guidance rather than a memory check.
- **Trait missed:** use the manual color/trait options to enforce it. All output still goes through the existing bounded validator.

The added identifiers, schema requests, memory/error handling and saved settings are covered by automated tests. This does **not** establish real inference speed, accuracy or fit on every 2/4/6/8 GB GPU. New variants were not downloaded for device inference testing. Earlier 0.5B/1.5B local inference evidence remains in [validation](VALIDATION.md).
