const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function run({ decision, currentUrl = 'https://unlisted.example', enabled = true, preview = false, offline = false }) {
  const removed = [], badges = [];
  const listener = { addListener() {} };
  const api = {
    storage: { local: { get: async () => ({ pairing: { token: 'x'.repeat(43), port: 47831, browser: 'chrome' } }) }, onChanged: listener },
    tabs: { query: async () => [{ id: 7, url: currentUrl, active: true }], get: async () => ({ id: 7, url: currentUrl }), remove: async id => removed.push(id), onUpdated: listener, onActivated: listener },
    action: { setBadgeText: async value => badges.push(value.text), onClicked: listener },
    runtime: { onStartup: listener, onInstalled: listener },
    alarms: { create() {}, onAlarm: listener },
  };
  const context = vm.createContext({ chrome: api, AbortSignal, setInterval() {}, fetch: async () => {
    if (offline) throw new Error('App stopped');
    return { ok: true, json: async () => ({ enabled, preview, decisions: [decision] }) };
  } });
  vm.runInContext(fs.readFileSync('extensions/chromium/background.js', 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  return { removed, badges };
}

const close = { id: 7, url: 'https://unlisted.example', close: true, allowed: false };
test('close only after explicit app decision', async () => {
  assert.deepEqual((await run({ decision: close })).removed, [7]);
  assert.deepEqual((await run({ decision: { ...close, close: false } })).removed, []);
});
test('navigation invalidates stale close', async () => {
  assert.deepEqual((await run({ decision: close, currentUrl: 'https://allowed.example' })).removed, []);
});
test('preview never closes', async () => {
  assert.deepEqual((await run({ decision: close, preview: true })).removed, []);
});
test('disabled guardian never closes', async () => {
  assert.deepEqual((await run({ decision: close, enabled: false })).removed, []);
});
test('allowed tab never closes', async () => {
  assert.deepEqual((await run({ decision: { ...close, allowed: true } })).removed, []);
});
test('missing app fails open and shows OFF', async () => {
  const result = await run({ decision: close, offline: true });
  assert.deepEqual(result.removed, []);
  assert.deepEqual(result.badges, ['OFF']);
});
