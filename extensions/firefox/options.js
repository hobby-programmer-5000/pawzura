const api = globalThis.browser || chrome;
const status = document.querySelector("#status");
document.querySelector("#save").addEventListener("click", async () => {
  try {
    const pairing = JSON.parse(document.querySelector("#pairing").value);
    if (typeof pairing.token !== "string" || pairing.token.length < 32 || pairing.token.length > 256 || !/^[A-Za-z0-9_-]+$/.test(pairing.token)) throw new Error("Invalid token");
    if (!Number.isInteger(pairing.port) || pairing.port < 1024 || pairing.port > 65535) throw new Error("Invalid port");
    if (!["chrome", "edge", "firefox", "brave", "opera", "vivaldi", "arc", "zen"].includes(pairing.browser)) throw new Error("Invalid browser");
    await api.storage.local.set({ pairing: { token: pairing.token, port: pairing.port, browser: pairing.browser } });
    document.querySelector("#pairing").value = "";
    status.textContent = "연결 정보를 저장했습니다. / Paired. Enable this browser and guardian in the desktop app.";
  } catch (error) { status.textContent = error.message; }
});
document.querySelector("#disconnect").addEventListener("click", async () => {
  await api.storage.local.remove("pairing");
  status.textContent = "연결 해제됨 / Disconnected";
});
api.storage.local.get("pairing").then(({ pairing }) => {
  status.textContent = pairing ? `Paired: ${pairing.browser} · 127.0.0.1:${pairing.port}` : "연결되지 않음 / Not paired";
});
