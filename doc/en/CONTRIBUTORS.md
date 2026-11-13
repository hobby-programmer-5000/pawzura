[English](../en/CONTRIBUTORS.md) | [한국어](../ko/CONTRIBUTORS.md) · [Documentation](../README.md)

# Contributors

## hobby-programmer-5000

- Original product idea, overall direction, architecture, and project management.
- Defined the SD companion, multi-display walking, jump/bite/crack experience, app/site allowlists, default apps, tray controls, localization, startup and character settings.
- Required Hugging Face open models, Windows 10/11, Python 3.12+, source/EXE execution, MIT and third-party notices.
- Requested readable bilingual documentation and simpler browser connection workflows.
- **[0.8.0 Update] Subcultural literature & light novel character analysis, and 2D vs 3D texture duality architecture:**
  - Identified the visual distortion and uncanny valley of forcing flat 2D anime illustrations into 3D meshes; proposed the hybrid duality pipeline: 2.5D multiplane parallax cutout for flat 2D characters, and 3D mesh reconstruction for shaded 3D characters.
  - Formulated and approved the 4-phase incremental advancement roadmap (texture classification & inflation → 2.5D parallax → parametric chibi template → landmark morphing).
  - Identified the download perceived hang during multi-gigabyte Ollama model pulls; defined the requirement for live per-model MB/GB bytes and step-by-step progress display.
  - Caught canvas-filling hallucinations (generating 2 characters instead of 1) in SDXL and required strict solo character enforcement.
- Owns and maintains the repository, determines release direction and makes final product/usability decisions.

GitHub: [hobby-programmer-5000](https://github.com/hobby-programmer-5000)

## Antigravity (Google DeepMind)

- **[0.8.0 Addition] 2.5D/3D Rigging advancement, real-time download streaming, and solo generation architecture engineering:**
  - **4-Phase Rigging Engineering**:
    - Phase 1: Texture classifier (`classify_art_texture`: `flat_2d` vs `shaded_3d`), 2.5D elliptical cylinder depth inflation (`inflate_2_5d_mesh`), single-view backside clean-fill pass (`project_multiview_colors`), thickness-aware Taubin smoothing, and ViTPose distal cuff escape algorithm.
    - Phase 2: 2.5D multiplane parallax cutout engine (`representation: "2.5d_parallax"`) with 4 depth layers, spine breathing rhythm, follow-through head sway, curiosity hover tilt, and seamless neck seam overlap.
    - Phase 3 & 4: Modular topology chibi parametric template mesh generator (`generate_parametric_chibi_template`) and ViTPose 2D landmark morphing engine (`morph_chibi_template_to_landmarks`).
  - **Real-Time Download Streaming & UI Transparency**:
    - Built the Ollama REST HTTP streaming integration (`_pull_ollama_model`) parsing live layer bytes, status, and model names with safe CLI fallback.
    - Revamped UI progress reporting (`pawzura/art_ui.py`) with real-time MB/GB formatting, smooth progress bar scaling, and eliminated false 9-minute wait warnings.
    - Added item-level reporting for SD 1.5/SDXL, Safety Checker, Cutout (u2netp), and ViTPose downloads.
  - **Bulletproof Solo Character Generation & Vision Guard**:
    - Enforced `solo, 1person, single full-body chibi character only` leading prompt injection.
    - Expanded negative prompt with `2girls, 2boys, duo, pair, 2characters, multiple people, two people, twins, group, clone, companion`.
    - Enhanced Qwen3-VL vision prompt to detect and reject multiple characters even when touching or identically dressed.
  - **Regression Test Suite (235 tests passed) & Standalone Windows x64 Packaging Verification.**

Antigravity is an advanced agentic AI assistant developed by the Google DeepMind team.

## ChatGPT (Codex, OpenAI)

- Assisted with initial native Windows/Qt architecture, loopback bridge, and implementation based on user requirements.
- Wrote original vector character geometry, procedural motion, monitor handling, normal close requests, and settings UI.
- Implemented bounded Qwen appearance generation, Chromium/Firefox extension logic, exact site policies, and URL revalidation.
- Assisted with tests, source/EXE checks, packaging, upstream license collection, and initial bilingual documentation.

ChatGPT is an AI tool used through Codex, not a human co-maintainer.

## GitHub contributor and bot display

The README and Git commit history provide visible, truthful credit. AI contributions are linked via Git `Co-authored-by` commit metadata. GitHub sidebar and contributor graphs follow GitHub's native aggregation rules. [GitHub contributor troubleshooting](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors).
