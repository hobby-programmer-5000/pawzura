# Pawzura 0.1.0 preview

Windows SD desktop companion with original vector characters, taskbar-area walking, multi-display traversal, jump/bite/fading-crack animation and an opt-in focus guardian.

Download **Pawzura-0.1.0-windows-x64.zip**, extract the complete folder and run **Pawzura/Pawzura.exe**. Keep `_internal`, `licenses` and the notices alongside it. Python is not required for the portable executable. Source execution and build instructions are in README.

The guardian starts **OFF**, with preview mode **ON**. Review allowed executables and sites before enabling real closing. Normal window close requests preserve applications' save prompts; no process force-killing is used. Browser monitoring requires installing and pairing the included extension in each browser.

Optional Hugging Face character designer: Qwen2.5-0.5B-Instruct-GGUF Q4_K_M via a separately installed Ollama. Original procedural rendering and animation also work without the model.

Validation: 20 Python checks, 6 extension checks, controlled native-window close probe, actual local Qwen generation, source and frozen EXE rendering/normal-exit smoke checks on Windows 10 / CPython 3.14.7. See docs/VALIDATION.md for precise scope.

Preview limitations: Windows 11 and actual browser-extension E2E still need separate device/browser validation. The extension closes tabs after navigation, rather than blocking network requests. Exact tab X coordinates are not exposed by browser APIs, so the visual bite uses the browser window's close area or a desktop fallback. Firefox permanent installation needs Mozilla signing. This is a focus aid with fail-open behavior, not a security boundary.

Original app code: MIT. Runtime/library/model terms and original texts are in THIRD-PARTY-NOTICES.md and licenses/. Product direction: hobby-programmer-5000. Implementation and documentation assistance: ChatGPT via Codex; details in CONTRIBUTORS.md.
