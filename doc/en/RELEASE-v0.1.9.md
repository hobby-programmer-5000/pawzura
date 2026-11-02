[English](../en/RELEASE-v0.1.9.md) | [한국어](../ko/RELEASE-v0.1.9.md) · [Documentation](../README.md)

# 0.1.9 — light theme and advanced local designers

Choose **General → Theme → Light (white) → Save settings** for a white settings window; Dark remains the default. Theme selection previews immediately and persists on save, including the character preview and extension setup helper. The browser extension's own page keeps its separate appearance.

The new **Advanced** tab enables manual **2/4/6/8 GB VRAM guides**. Character retains Qwen2.5 0.5B/1.5B and adds official Apache-2.0 Qwen3 4B Q4_K_M (4 GB guide), 4B Q8_0 (6 GB) and 8B Q4_K_M (8 GB). These interpret descriptions into the same existing vector traits. No image-generation model, GPU detection, automatic large-model selection or silent weight download is added. See [setup, memory and licenses](ADVANCED-MODELS.md).

**AI design needs Ollama running, the selected model downloaded, and sufficient free RAM/VRAM.** Installed VRAM and model file sizes do not guarantee fit; GPU/CPU placement is handled by Ollama. Requests retain bounded JSON validation; advanced models use non-thinking mode and unload after the request. Missing models, unavailable Ollama and memory errors give actionable English/Korean feedback and retain the current character.

The README highlights possible SmartScreen warnings, the extension required for browser tab control, and model prerequisites. Quit the previous tray app, extract the entire ZIP and run its **Pawzura.exe**. Settings migrate locally; no personal allowlists or model weights are bundled. The existing extension needs no new permissions for these desktop changes.

The [validation record](VALIDATION.md) distinguishes automated/render/frozen-artifact checks from actual hardware inference. New Qwen3 variants were not downloaded for device benchmarking; 2/4/6/8 GB are guides, not certified minimums. All earlier browser and device coverage limits remain applicable.
