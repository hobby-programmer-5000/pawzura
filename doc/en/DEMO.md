[English](../en/DEMO.md) | [한국어](../ko/DEMO.md) · [Documentation](../README.md)

# README interaction demo

[English MP4](../../artifacts/demo/pawzura-demo-en.mp4) · [Korean MP4](../../artifacts/demo/pawzura-demo-ko.mp4). Each silent clip lasts 16 seconds; the README uses a looping GIF preview.

The windows, taskbar, sites and browser tabs are original, fictional scene elements. The character uses Pawzura's existing `Pet.bite`, `Pet.tick`, `draw_character`, crack effect and separate tab marker. At the bite callback, only an in-memory scene flag changes. The fictional app disappears first; then one fictional tab disappears while the allowed tab and its browser remain. This illustrates the interaction; it is not a recording of native window closure or browser-extension integration.

The renderer forces Qt's **offscreen** platform and verifies it before rendering. It never starts the guardian or bridge, calls native window closing, connects a browser, reads a user profile, captures a desktop, or changes startup/settings. The video focuses on the app's functions; this guide records how its demo window and scene were made. The demonstration does not change app defaults: guardian OFF, preview ON, website control OFF.

## Reproduce on Windows

Use the existing standard CPython project environment with PySide6 and an independently installed FFmpeg on PATH. The system Segoe UI and Malgun Gothic fonts must be readable. A missing font stops rendering instead of accepting missing glyphs. No model or media-generation service is used.

Choose **new** frame and output paths; the renderer and the commands below refuse to overwrite files. For Korean, replace `en` with `ko` in all paths and the language argument.

```powershell
.\.venv-standard\Scripts\python.exe scripts/render_demo.py --language en --output .cache/demo-en
ffmpeg -nostdin -n -framerate 24 -i .cache/demo-en/frame-%04d.png -an -c:v libx264 -crf 19 -pix_fmt yuv420p -movflags +faststart demo-en.mp4
ffmpeg -nostdin -n -framerate 24 -i .cache/demo-en/frame-%04d.png -filter_complex "fps=12,scale=896:560:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" -loop 0 demo-en.gif
```

`render.json` records 384 frames at 1120×700, two mock close callbacks and the surviving allowed tab. The MP4 is 24 fps; the GIF is 896×560 at approximately 12 fps. The committed [manifest](../../artifacts/demo/manifest.json) records exact output hashes, component versions and sources. The [media notice](../../artifacts/demo/NOTICE.md) records rights and attribution. Only the six explicitly listed public demo files are copied into future app builds; working frames and diagnostics remain ignored.

## Rights and verification

The original scene, captions, script and existing default character retain the repository's MIT terms; no new noncommercial designation is introduced. Product direction belongs to the maintainer; code, composition and validation were assisted by ChatGPT (Codex). No third-party site, logo, music, model output or font file is bundled. Windows fonts are rendered to pixels only, consistent with [Microsoft's font output FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq). FFmpeg 9.0.2 was used as a separate development encoder; this installed build reports GPL-3.0-or-later and is not redistributed. See [FFmpeg licensing](https://ffmpeg.org/legal.html); its terms remain separate from the original scene.

Both languages' jump/bite, mock closures, marker and end frames were inspected. Complete MP4/GIF decoding and stream metadata were checked. This staged media does not expand native/browser, Windows 11, GPU or optional-model compatibility claims. For actual integration coverage, see [Validation](VALIDATION.md).
