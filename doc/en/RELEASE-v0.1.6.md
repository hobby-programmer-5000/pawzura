[English](../en/RELEASE-v0.1.6.md) | [한국어](../ko/RELEASE-v0.1.6.md) · [Documentation](../README.md)

# 0.1.6 preview — protect graphics overlays and stop repeat previews

- Exclude tool/no-activate/click-through/child windows and windows without system menus from application targeting.
- Protect common graphics overlay/driver helpers and WebView2 hosts even when absent from editable app lists. The final native close boundary also rejects them.
- Show each native application preview once until its identity changes or settings are reapplied. A preview callback cannot turn into a real close after a mode change.
- Reuse companion-owned crack/tab-marker windows with non-activating tool styles, reducing effect-window churn.
- Return jumps to the current desktop floor and preserve recovered coordinates when a hit is cancelled.
- Keep the 0.1.5 extension helper, global website switch, work/leisure profiles and local settings. No personal lists or raw diagnostic inventories are bundled.

Quit the old app from its tray before running the full new ZIP. Existing website settings stay local; the extension protocol and fixed ID are unchanged. See [overlay troubleshooting](OVERLAYS-AND-PREVIEW.md) and [actual validation](VALIDATION.md). The reported full flicker sequence was not reproduced under a running old guardian; no historical process-restart claim is made. Code remains MIT and dependencies retain their licenses.
