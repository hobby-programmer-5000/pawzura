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

4. **Subcultural Literature, Light Novel & Speculative Genre 3D-Rigging Character Examples (+10 Presets, 15 Total) & 4 Bilingual Research Guides**
   - Translated subcultural narrative theory (Hiroki Azuma's database moe-element modularity, Go Ito's *Kyara* semiotics, 70-20-10 visual hierarchy) and 3D rigging constraints (A-pose negative space, cropped jackets exposing hip/leg joints, distinct cuff-to-hand boundaries) into 10 new built-in character presets in `Create original artwork…` ([Creative artwork](CREATIVE-ART.md), [3D motion preparation](3D-MOTION.md)):
     - **Subcultural & Light Novel Archetypes (5):** Status-window shadow hunter (LitRPG), Strategic villainess noble (Otome Isekai), Isekai bookshop artisan (Reincarnation), Banished herbalist supporter (Slow-life), Quiet mastermind scholar (Misunderstanding)
     - **Speculative & Classic Fantasy Archetypes (5):** Cyberpunk netrunner hacker (Cyberpunk), Solarpunk eco-tinker (Solarpunk), Retired adventurer barista (Cozy Fantasy), Night-watch occult detective (Urban Fantasy), Galactic train conductor (Classic Fantasy)
   - Added 4 comprehensive bilingual (Korean/English) research guides to `doc/ko/` and `doc/en/`:
     - [Character design methodology and archetypes](CHARACTER-DESIGN-METHODOLOGY.md)
     - [Literary worldbuilding and character archetypes](LITERARY-WORLDBUILDING-AND-CHARACTERS.md)
     - [Subcultural literature and light novel theory](SUBCULTURAL-LITERATURE-AND-LIGHT-NOVELS.md)
     - [Character design and literature bibliography](CHARACTER-AND-LITERATURE-BIBLIOGRAPHY.md)

5. **Contributor Roles & AI Attribution**
   - Product Direction & Architecture: `hobby-programmer-5000`
   - AI Rigging Advancement & Engineering: `Antigravity (Google DeepMind)`
   - Initial AI Implementation Assistance: `ChatGPT (Codex, OpenAI)`

6. **Full 15-Preset Sandbox Audit & Literature-Backed Side-View / 2.5D Texture Fixes**
   - Added die-cut sticker border stripping (`strip_diecut_sticker_border`), pre-inflation perspective-consistent UV atlas baking with foreground-interior `EDT` extrapolation, pale frontal skin-hue protection (`~is_skin_hue`), silhouette-distance dome crowning (`dome_norm_map`), and Half-Lambert cel-relief shading—eliminating side-view slab flattening (`otter`) and frontal face/costume blotches (`villainess`).
   - Closed the front-to-side visual gap via **`384 px`** equatorial view rendering (`three_d.py`), edge-preserving oblique bilateral denoising (`_bilateral_smooth_rgb`), strict `(min > 0.80) & (sat < 0.08)` background halo gating, `ndot > 0.28` front grazing clamps, central-trunk-proportional inflation with lateral arm attenuation (`motion_geometry.py`), and a `0.87` Half-Lambert side floor with 2× SSAA stylized cel contour outlines (`motion_bake.py`).
   - Fixed `art_review_prompt_invalid` and trait loss on long multi-paragraph (~2,000-char) Korean descriptions via proximity color-to-garment slot extraction and single-line ASCII normalization ([art_policy.py](../../pawzura/art_policy.py)), and eliminated forehead blink flickering via front-shell `lift()`, photometric iris refinement (`_refine_eye_joints`), and single-pass elliptical eyelid blending ([motion_bake.py](../../art_runtime/motion_bake.py)).
   - Verified with **236 Python unit tests**, **26 geometry/pose probe checks**, **123 Markdown doc/link checks**, and **15/15 `rig_3d_ok=True`** sandbox runs (`depth_ratio` `0.273–0.640`). See [3D Rigging References](3D-RIGGING-AND-MOTION-REFERENCES.md) and [Validation Records](VALIDATION.md) for the 31 cited papers and turnaround grids:
     - [Group 1 Original 5 Verification Grid](../../artifacts/sandbox-v0.8.0-group1-original5.png)
     - [Group 2 Subculture & Light-Novel 5 Verification Grid](../../artifacts/sandbox-v0.8.0-group2-subculture5.png)
     - [Group 3 Speculative & Classic Literature 5 Verification Grid](../../artifacts/sandbox-v0.8.0-group3-literature5.png)

Download the Windows standalone EXE or extract the complete ZIP. Close any existing Pawzura instance before updating. [Downloads and setup](SINGLE-EXE.md).
