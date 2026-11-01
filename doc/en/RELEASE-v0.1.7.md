[English](../en/RELEASE-v0.1.7.md) | [한국어](../ko/RELEASE-v0.1.7.md) · [Documentation](../README.md)

# 0.1.7 preview — describe and customize a character

Character now accepts a free-text English/Korean description (up to 2,000 characters) and offers body/accent/eye colors, ears, eye expression, face markings, accessory, tail and wings. Explicit choices override Qwen output. Apply options works without a model; preview and Save settings apply the result. Previous designs and the default reset remain available.

The designer offers official Hugging Face Qwen2.5 0.5B and 1.5B Q4_K_M models via local Ollama. 1.5B is recommended for descriptions; neither is bundled or silently downloaded by the app. The selected model's download command is shown. Its Apache-2.0 license and provenance are documented. Text descriptions are not saved in settings/history or logged by the app. They are sent only to loopback Ollama.

These are parameter-driven original vector characters. Arbitrary drawings, clothing and hairstyles are not supported. Real model samples missed some requested traits; use manual options for exact requirements. See [examples, supported options and model setup](MODELS.md) and [validation](VALIDATION.md).

The English/Korean browser installation guide and helper now distinguish the extension manager's Developer mode switch from Ctrl+Shift+I Developer Tools. Load the extension folder before opening its connection page.

Quit the old tray app, extract the complete ZIP to a new folder, then run its Pawzura.exe. Existing private local settings remain local; the release carries empty site defaults. Version 0.1.6's overlay protection remains included.
