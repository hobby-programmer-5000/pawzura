[English](../en/RELEASE-v0.2.0.md) | [한국어](../ko/RELEASE-v0.2.0.md) · [Documentation](../README.md)

# 0.2.0 — original artwork, beyond preset traits

**Character → Create original artwork…** is a separate optional image-generation workflow. Describe an original silhouette, hairstyle, clothes and materials; SD 1.5/SDXL draw pixels rather than choose the vector designer's existing traits. The lightweight Qwen/manual vector mode remains available, with larger Qwen variants clearly labeled as same-shape trait interpreters.

1. Install/start Ollama. Open the new artwork dialog and select a 2/4/6/8 GB NVIDIA CUDA guide.
2. **Read the selected model's original license**, then check the acknowledgement. App code remains MIT; image weights use separate, restricted OpenRAIL terms and are not bundled or represented as OSI-approved open source.
3. Click **Prepare runtime and selected models**. Expect large downloads and extra disk/RAM use. The isolated Python 3.12 image environment is separate from the main app's Python and supports portable EXE users too.
4. Describe your original character, generate and inspect the result. Local prompt/classifier/vision reviews must pass. Click the mouth in the preview to adjust the bite point.
5. **Use this character → Save settings**. Approved PNGs survive restart/history, use whole-image sway/flip/jump/bite motion, and fall back safely if missing/corrupt. Vector options cannot edit a bitmap.

See [Creative artwork](CREATIVE-ART.md) for exact model roles/licenses, memory guides, steps and troubleshooting. No cloud inference is used. Descriptions are session-only; personal settings, artwork, runtimes and weights are excluded from distribution.

**Limits:** NVIDIA only; memory tiers are guides, not fit guarantees. More VRAM does not ensure prettier results. Prompt following and background removal are imperfect; this is not articulated AI walking/blinking animation. Local safety/originality checks can miss content or reject safe requests and are not legal clearance. Inspect outputs before use/publication. Full GPU/device and user-profile browser E2E coverage remain limited; see [validation](VALIDATION.md).
