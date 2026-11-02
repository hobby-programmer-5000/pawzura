[English](../en/RELEASE-v0.1.10.md) | [한국어](../ko/RELEASE-v0.1.10.md) · [Documentation](../README.md)

# 0.1.10 — model setup without guesswork

**Character → Copy command** now sits beside the selected model, with its download size and a **Model setup guide** button. Paste into PowerShell, press Enter, wait for `success`, then generate again. Model errors identify the exact requested model and full download command. A similarly named installed model or another quantization does not substitute for it.

The guide is also available in Advanced. It lists copyable commands for CPU/unknown 0.5B, 2 GB/CPU 1.5B, 4 GB Qwen3 4B Q4_K_M, 6 GB Qwen3 4B Q8_0 and 8 GB Qwen3 8B Q4_K_M, with sizes and start/download/retry steps. It explains system RAM versus GPU VRAM and preserves all existing memory/device limitations. Opening the guide or copying a command does not install a model, start inference or save settings.

The English/Korean README and [complete setup guide](ADVANCED-MODELS.md) include every model's exact command, `ollama list` verification and recovery for missing commands/models or a different Ollama host. Model inference, licenses, browser/native closing and private settings remain unchanged. Quit the old tray app, extract the whole ZIP and run **Pawzura.exe**. Existing browser extensions need no new permissions. See [validation](VALIDATION.md).
