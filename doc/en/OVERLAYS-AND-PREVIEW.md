[English](../en/OVERLAYS-AND-PREVIEW.md) | [한국어](../ko/OVERLAYS-AND-PREVIEW.md) · [Documentation](../README.md)

# Overlay targeting, repeated previews and walking height

## What changed in 0.1.6

Earlier window inspection accepted visible, unowned, titled windows even when they were full-screen transparent overlay hosts or embedded child surfaces. A graphics overlay without a native close button could therefore receive a guessed upper-right bite point. Hiding the overlay's content does not necessarily remove its host window from enumeration.

The guardian now rejects child, tool, no-activate and click-through windows and requires a system menu. Known graphics/overlay/session helpers and WebView2 rendering hosts are protected independently of editable allowlists, including at the final native close boundary. This protects helper surfaces even with older saved app lists. Some custom/frameless applications without a system menu are intentionally left alone; the focus aid prioritizes avoiding system/overlay interference.

Native application previews are now shown once for a still-open target identity rather than every cooldown. A new window/title or applying settings can rearm preview. A callback created in preview cannot later send a close request even if preview is switched off before it runs.

Crack/tab-marker windows are reused and owned by the companion. They remain non-activating tool windows and do not request taskbar buttons. This reduces window creation/destruction during effects; it does not prove that every compositor/GPU flicker is eliminated.

Jump completion recomputes the current desktop floor instead of restoring a stale launch height. Cancellation during a hit cannot overwrite the recovered position afterwards. Walking still uses the monitor work area; display configuration and auto-hide behavior need device-specific checks.

## If you see repeated biting or flashing

1. Use the tray's **Pause guardian** first. **Hide companion** suppresses its display; **Quit** stops the app. Closing settings only returns to the tray.
2. Quit the old build and use the complete 0.1.6+ ZIP. Do not terminate graphics-driver or Explorer processes to diagnose this symptom.
3. Use **Recover companion on screen** if the character is misplaced. Try preview before enabling actual close requests again.
4. If a problem remains, record the app version, preview state, affected process **filename** and whether it continues with Pawzura fully quit. Avoid screenshots containing private site lists or document titles.

A flashing taskbar, a hidden/recreated overlay window and a restarted process are different observations. Process IDs/start times, window lifetime and crash events must be checked separately. A short stable observation cannot establish what happened earlier, and an animation near a corner is not proof of a process termination. See [the measured validation scope](VALIDATION.md).

The diagnostic work uses read-only window/process metadata and safe test-owned windows. User window titles, site lists, machine paths and raw process inventories are not included in the release or this guide.

Technical references: [Microsoft extended window styles](https://learn.microsoft.com/en-us/windows/win32/winmsg/extended-window-styles), [GetWindowLongPtrW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowlongptrw), [taskbar window behavior](https://learn.microsoft.com/en-us/windows/win32/shell/taskbar).
