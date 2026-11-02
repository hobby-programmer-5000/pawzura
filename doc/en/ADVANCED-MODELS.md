[English](../en/ADVANCED-MODELS.md) | [한국어](../ko/ADVANCED-MODELS.md) · [Documentation](../README.md)

# Advanced models and memory

**Keep Ollama running, download the selected model first, and leave sufficient free system RAM and GPU VRAM.** Opening Pawzura, using random/manual appearances and animating the pet require no model. These models interpret descriptions into the existing vector traits; they do not create new illustrations, clothing or hairstyles. Larger models or higher precision may help interpretation but do not guarantee a prettier result or perfect prompt adherence.

## Choose a model

1. Open **Advanced → Enable advanced character models**.
2. Choose your GPU's VRAM capacity: **2, 4, 6 or 8 GB**. If unknown, retain **CPU / unknown** and the basic models.
3. Open **Character → Appearance model** and select an available model. Enabling Advanced does not automatically select a larger model.
4. Run the exact `ollama pull …` command shown below the character options, once per model. Downloads are separate from Pawzura; no weights are bundled or silently downloaded.
5. Keep Ollama running, generate, inspect the preview and **Save settings**. Model choice and advanced preferences persist separately from work/leisure allowlists. Reducing the VRAM guide removes larger choices and selects 1.5B if necessary; the current character remains unchanged.

| Manual VRAM guide | Suggested model | Approx. weight download | License |
| --- | --- | --- | --- |
| CPU / unknown | Qwen2.5 0.5B or 1.5B Instruct · Q4_K_M | 0.49 / 1.12 GB | Apache-2.0 |
| 2 GB | Qwen2.5 1.5B Instruct · Q4_K_M | 1.12 GB | Apache-2.0 |
| 4 GB | Qwen3 4B · Q4_K_M | 2.50 GB | Apache-2.0 |
| 6 GB | Qwen3 4B · Q8_0 (higher precision, same parameter count) | 4.28 GB | Apache-2.0 |
| 8 GB | Qwen3 8B · Q4_K_M | 5.03 GB | Apache-2.0 |

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
- **Model missing / unsupported:** download that exact identifier and update Ollama for Qwen3 support. The app does not substitute another model silently.
- **Not enough memory:** choose a smaller model or free RAM/VRAM; the tier is guidance rather than a memory check.
- **Trait missed:** use the manual color/trait options to enforce it. All output still goes through the existing bounded validator.

The added identifiers, schema requests, memory/error handling and saved settings are covered by automated tests. This does **not** establish real inference speed, accuracy or fit on every 2/4/6/8 GB GPU. New variants were not downloaded for device inference testing. Earlier 0.5B/1.5B local inference evidence remains in [validation](VALIDATION.md).
