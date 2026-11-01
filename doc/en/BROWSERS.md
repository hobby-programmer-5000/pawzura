[English](../en/BROWSERS.md) | [한국어](../ko/BROWSERS.md) · [Documentation](../README.md)

# Connect a browser

## Install the extension first

For **Chrome**, open `chrome://extensions`. For **Edge**, open `edge://extensions`. Turn on **Developer mode**, choose **Load unpacked**, then select the extracted `Pawzura/extensions/chromium` folder. Select the folder containing `manifest.json`, not `options.html`.

In the extension's **Details** page, choose **Extension options**. You can also click the Pawzura extension icon. This is the page that can actually connect to the desktop app.

**If you opened `file:///.../options.html`:** that is a preview, with a visible explanation and disabled connection buttons. Install the extension using the steps above, then open Extension options. The local preview still supports language switching and the sample.

Brave/Opera/Vivaldi use the Chromium extension folder, subject to each browser's extension support. For Firefox, open `about:debugging#/runtime/this-firefox` → **Load Temporary Add-on** → `extensions/firefox/manifest.json`. Temporary installation disappears after restart; permanent Firefox distribution requires Mozilla signing. Zen compatibility needs separate validation.

## Connect automatically — no code entry

1. Start **Pawzura 0.1.3 or newer** and keep it running.
2. Open the installed extension's options, select your browser, and click **Connect automatically**. Keep port **47831** unless the app uses another port.
3. In the desktop app's confirmation, choose **Yes**. Connection information is exchanged and saved automatically.

The extension is still needed once: its browser permission is what lets it read URLs and close individual tabs. The desktop app never sends native close requests to browser windows, even if a browser was removed from the application list. No browser password or account login is needed for pairing. Allowed sites and guardian settings do not change when you connect.

**Upgrade both parts:** quit the old app, extract the new ZIP, and reload the extension from `extensions/chromium` in the browser's extension manager (or reload Firefox's temporary add-on). If the folder changed, load the new folder. Close old options tabs and reopen options. Existing saved connections remain valid.

The extension's Language menu offers English and 한국어 independently from the desktop app.

<details>
<summary>Advanced manual connection and old JSON examples</summary>

Automatic connection is recommended. For an older app or troubleshooting, enable **Manual connection — advanced** in the desktop Browsers tab to access Copy connection code and the port. In extension options, expand its own manual connection section, paste the code, and click Connect and test. The sample below is illustrative and cannot connect.

### Concrete example

| Field | Example | What you should enter |
| --- | --- | --- |
| Browser | Chrome | The browser where you installed this extension |
| Port | 47831 | The number shown in Pawzura → Browsers |
| Connection code | EXAMPLE_ONLY_REPLACE_WITH_YOUR_APP_CONNECTION_CODE | Your real code from Copy connection code |

The example code **cannot connect**. It is labelled as a sample and rejected by the Connect button. The **Fill example fields** button demonstrates where values belong without saving a connection.

### Already copied JSON from 0.1.0?

Expand **See an example / import old JSON**. Paste the complete copied text into the import box, then click **Use these details**. This fills the three fields; it does not connect until you click **Connect and test**.

```json
{
  "browser": "chrome",
  "port": 47831,
  "token": "EXAMPLE_ONLY_REPLACE_WITH_YOUR_APP_CONNECTION_CODE"
}
```

`browser` is the Browser field, `port` is Port, and `token` is Connection code. In 0.1.1 the app copies just the code, so paste it into the main Connection code field. No braces or quotation marks are needed there.


</details>

## Add allowed sites and enable monitoring

1. In desktop **Browsers**, select the connected browser. Enter sites, one per line, for example `https://example.com`.
2. Check **Apply website allowlist to this browser** and click **Save settings**.
3. In **General**, check **Enable focus guardian**, leave preview on, and save. Verify the behavior before turning preview off.

Only built-in new-tab/home pages and explicit blank-page URLs are initially allowed. Custom startup URLs are **not** detected automatically: add them yourself. Install the extension before enabling site monitoring, since internal settings pages are not default-allowed pages.

| Rule | Allows | Does not allow |
| --- | --- | --- |
| `https://example.com` | Every path on that HTTPS origin | Subdomains, HTTP, non-default ports |
| `example.com/*` | Every HTTPS path, query and fragment on that host, including `/` | Subdomains, HTTP, lookalike hosts |
| `example.com/section/*` | `/section` and its children | `/section-other` or other sections |
| `github.com/my-account` | HTTPS `/my-account` and its child paths | Other accounts or `/my-account-other` |
| `https://example.com/personal/home` | That path and its child paths | Other sections of the site |
| `example.com/ko?viewMode=svod` | HTTPS `/ko` and children with `viewMode=svod` | Missing/different `viewMode` values |
| `*.example.com` | HTTPS subdomains such as `help.example.com` | The root `example.com` |
| `http://localhost:3000` | That exact HTTP origin | A different port |

You can paste a domain, a URL path, or a URL with query parameters. Without a scheme, HTTPS is assumed; explicit `http://` and `https://` URLs both work and remain separate. **A bare `http://` or `https://` is incomplete and is not a rule that allows every site.**

A domain without a path allows the whole site. A path allows that section and children on slash boundaries: `/home` does not allow `/home-other`. Query values in the rule must match; extra keys such as tracking parameters are allowed, but extra values for a constrained key are rejected. `#fragment` parts are ignored and cannot restrict SPA hash routes. Internationalized names, Unicode paths and default ports are normalized. Dot segments, backslashes and encoded path separators are rejected for path-scoped rules.

`example.com` and `www.example.com` remain different hosts. If a site redirects to another host or a login site, add that address explicitly if you want to allow it. A rule such as `github.com/my-account` does not permit GitHub's login page. Hostnames still match exactly, so `example.com.evil.test` is not allowed.

Before 0.1.2, paths or queries caused the whole edited list to fail validation. Version 0.1.2 accepts them and identifies the line of any remaining error in the selected language. Saving shows the normalized addresses, including the assumed `https://`.

## Connection messages and troubleshooting

| Message | Next step |
| --- | --- |
| File preview | Install the extension, then open Extension options |
| Code rejected | Copy the current code from the app again |
| Cannot reach Pawzura | Start the desktop app and check the port |
| Connected, guardian off | Enable the browser setting and overall guardian in the app |
| Connected, preview | Keep preview for testing; turn it off to close tabs |

The badge shows ON for real monitoring, PRE for preview and OFF for a connection failure. A blank badge means monitoring is disabled. Disconnecting removes pairing; closing the desktop app stops tab closing.

## Technical behavior and limits

A final `/*` is accepted in 0.1.3 and normalized to the equivalent domain/path rule after saving. `/section/*` includes `/section` itself. Other path patterns such as `/section*` or `/*/item` are rejected. Query constraints after `/*` still apply. Use [profiles](PROFILES-AND-RECOVERY.md) for separate work/leisure lists.

The extension checks up to 200 open tabs per sweep. Each unlisted URL gets an animation ticket; the URL is checked again before closing the tab. A suspended Chromium worker can take about 30 seconds to resume through its alarm. Version 0.1.4 uses a separate synthetic **Tab preview ×** / **Blocked tab ×** marker near the taskbar for both active and background tabs. It does not infer a native window's X from a browser tab ID, use the foreground window's controls, or fall back to the screen's upper-right corner. This marker is not the real browser tab X. Its own extension options pages are excluded from monitoring. Before closing the last blocked tab in a window, the extension creates an about:blank replacement in that same window. If that fails, it leaves the tab open. Other tabs are not closed.

Preview mode never closes tabs. A still-blocked tab/URL is demonstrated once rather than repeating when its animation ticket expires. Navigation, closing/reopening the tab or applying settings can rearm the demonstration. Browser IDs, URLs and preview fingerprints stay in memory; they are not added to logs or settings. Real tab removal is performed only by the extension after an acknowledged decision, with guardian/browser checks enabled and preview off. The native guardian excludes known browser windows in both preview and live modes.

Navigation happens **before** tab closing; this is not a network firewall. Removing the extension or closing the app stops enforcement. Incognito tabs require separate browser permission. Permanent store distribution and real-browser E2E testing remain separate work; see [validation](VALIDATION.md).

The bridge binds only to `127.0.0.1`, checks its private code and Host, limits requests and does not log URLs. In-memory URL tickets expire after 20 seconds. Only extension origins receive CORS responses. URLs never go to the character model. The app is a focus aid, not a security boundary.

References: [Chrome tabs API](https://developer.chrome.com/docs/extensions/reference/api/tabs), [Firefox signing](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/).

Automatic pairing requests accept only extension origins, expire after 60 seconds and disclose a credential only after explicit desktop approval. The one-time result is bound to the requesting origin and cannot be redeemed again. Ordinary website origins are rejected. Manual token-based pairing remains an advanced fallback.
