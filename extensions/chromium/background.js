/* Original Pawzura bridge; no page scripts, history storage or external services. */
const api = globalThis.browser || chrome;
let busy = false;

async function sweep() {
  if (busy) return;
  busy = true;
  try {
    const { pairing } = await api.storage.local.get("pairing");
    if (!pairing) return;
    const tabs = await api.tabs.query({});
    const ownRoot = api.runtime.getURL?.('');
    const candidates = tabs.filter(t => !ownRoot || !(t.pendingUrl || t.url || '').startsWith(ownRoot));
    const response = await fetch(`http://127.0.0.1:${pairing.port}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Pawzura-Token": pairing.token },
      body: JSON.stringify({ browser: pairing.browser, tabs: candidates.slice(0, 200).map(t => ({ id: t.id, url: t.pendingUrl || t.url || "about:blank", active: t.active })) }),
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) throw new Error(`Bridge: ${response.status}`);
    const result = await response.json();
    await api.action.setBadgeText({ text: result.enabled ? (result.preview ? "PRE" : "ON") : "" });
    if (!result.enabled || result.preview) return;
    for (const decision of result.decisions) {
      if (!decision.close || decision.allowed) continue;
      try {
        const current = await api.tabs.get(decision.id);
        // Never close a tab which navigated to another URL after the app's decision.
        if ((current.pendingUrl || current.url) !== decision.url) continue;
        const siblings = await api.tabs.query({ windowId: current.windowId });
        if (siblings.length === 1) {
          // Removing a window's last tab closes the entire window in many browsers.
          // If a replacement cannot be created, leave the existing tab untouched.
          await api.tabs.create({ windowId: current.windowId, url: 'about:blank', active: false });
        }
        const checked = await api.tabs.get(decision.id);
        if ((checked.pendingUrl || checked.url) === decision.url) await api.tabs.remove(decision.id);
      } catch (_) { /* The user may have already closed the tab. */ }
    }
  } catch (_) {
    // App absent / invalid token / request failed: fail open and expose disconnected status.
    await api.action.setBadgeText({ text: "OFF" }).catch(() => {});
  } finally {
    busy = false;
  }
}

api.tabs.onUpdated.addListener(() => { void sweep(); });
api.tabs.onActivated.addListener(() => { void sweep(); });
api.runtime.onStartup.addListener(() => { void sweep(); });
api.runtime.onInstalled.addListener(() => {
  api.alarms.create("pawzura-sweep", { periodInMinutes: 0.5 });
  void sweep();
});
api.alarms.onAlarm.addListener(() => { void sweep(); });
api.action.onClicked.addListener(() => { void api.runtime.openOptionsPage(); });
api.storage.onChanged.addListener(() => { void sweep(); });
// Tab API calls keep an active Chromium worker awake while paired. Alarms restore it after suspension.
setInterval(() => { void sweep(); }, 1000);
void sweep();
