[English](../en/RELEASE-v0.8.0.md) | [한국어](../ko/RELEASE-v0.8.0.md)

# 0.8.0

**Hybrid 2.5D/3D rigging advancement, real-time download streaming, and solo character enforcement.**

## Key Changes

1. **Hybrid 2.5D/3D Rigging Advancement**
   - Solved the distortion and uncanny valley of forcing flat 2D anime illustrations into 3D meshes. Based on texture classification (`classify_art_texture`), flat 2D characters now use a **2.5D multiplane parallax cutout engine (4-layer depth planes, spine breathing rhythm, follow-through head sway, curiosity hover tilt, and seamless neck seam overlap)**, while shaded 3D characters continue to use 3D mesh reconstruction.
   - Applied 2.5D elliptical cylinder depth inflation (`inflate_2_5d_mesh`), single-view backside clean-fill pass (`project_multiview_colors`), thickness-aware Taubin smoothing, and ViTPose distal cuff escape.
   - Integrated parametric chibi template mesh generation and 2D landmark morphing.

2. **Real-Time Download Streaming & UI Transparency**
   - Directly streams from local Ollama HTTP API (`/api/pull`) to display per-model downloaded bytes (MB / GB), percentage (%), and granular stages (manifest verification, downloading, checksum verification, completion) in real time.
   - Eliminated false `no progress report` warnings during active downloads and implemented smooth progress bar tracking.
   - Added friendly item names for Hugging Face downloads (SD 1.5/SDXL, Safety Checker, u2netp Cutout, ViTPose).

3. **Solo Character Enforcement & Vision Guard**
   - Injected `solo, 1person, single full-body chibi character only` at the beginning of generation prompts and expanded the negative prompt with `2girls, 2boys, duo, pair, 2characters, multiple people, two people, twins, group, clone, companion` to prevent canvas-filling hallucinations.
   - Enhanced Qwen3-VL vision prompt to detect and reject multiple characters or twins even when tightly touching or identically dressed.

4. **Contributor Roles & AI Attribution**
   - Product Direction & Architecture: `hobby-programmer-5000`
   - AI Rigging Advancement & Engineering: `Antigravity (Google DeepMind)`
   - Initial AI Implementation Assistance: `ChatGPT (Codex, OpenAI)`

Download the Windows standalone EXE or extract the complete ZIP. Close any existing Pawzura instance before updating. [Downloads and setup](SINGLE-EXE.md).
