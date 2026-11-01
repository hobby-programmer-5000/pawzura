const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function setup({ installed = true, response = { enabled: false, preview: true }, status = 200, offline = false, saved = {}, pairingState = 'approved', query = '' } = {}) {
  const ids = ['auto-connect','language', 'status', 'browser', 'port', 'token', 'show-code', 'example', 'import', 'pairing', 'connection-form', 'save', 'disconnect', 'preview-warning'];
  const elements = Object.fromEntries(ids.map(id => [id, { value: '', textContent: '', dataset: {}, hidden: id === 'preview-warning', disabled: false, type: 'password', handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; } }]));
  elements.browser.value = 'chrome'; elements.port.value = '47831';
  const storage = { ...saved }, requests = [];
  const api = { runtime: { id: 'test-extension' }, storage: { local: {
    get: async () => ({ ...storage }),
    set: async data => Object.assign(storage, data),
    remove: async name => delete storage[name],
  } } };
  const document = { documentElement: {}, title: '', querySelector: s => elements[s.slice(1)], querySelectorAll: () => [] };
  const context = vm.createContext({ document, AbortSignal, setTimeout, Date, URLSearchParams, location: {search:query}, chrome: installed ? api : undefined, localStorage: { getItem: () => null, setItem() {} }, fetch: async (url, options) => {
    requests.push({ url, options });
    if (offline) throw new Error('offline');
    const body = url.endsWith('/pair/request') ? {request:'test-challenge',state:'pending'} :
      url.endsWith('/pair/result') ? {state:pairingState,pairing:{browser:'chrome',port:47831,token}} : response;
    return { ok: status === 200, status, json: async () => body };
  } });
  vm.runInContext(fs.readFileSync('extensions/chromium/options-i18n.js', 'utf8'), context);
  vm.runInContext(fs.readFileSync('extensions/chromium/options.js', 'utf8'), context);
  await new Promise(r => setImmediate(r));
  return { elements, storage, requests, context, fire: async (id, event = 'click') => elements[id].handlers[event]({ preventDefault() {} }) };
}
const token = 'real_app_code_abcdefghijklmnopqrstuvwxyz123456';
test('file preview is usable and cannot connect', async () => {
  const ui = await setup({ installed: false });
  assert.equal(ui.elements['preview-warning'].hidden, false);
  assert.equal(ui.elements.save.disabled, true);
  assert.equal(ui.elements.disconnect.disabled, true);
  await ui.fire('example');
  assert.equal(ui.elements.browser.value, 'chrome');
  assert.match(ui.elements.token.value, /EXAMPLE_ONLY/);
});
test('English is default and Korean switching updates state messages', async () => {
  const ui = await setup();
  assert.equal(ui.elements.language.value, 'en');
  ui.elements.language.value = 'ko'; await ui.fire('language', 'change');
  assert.equal(ui.storage.language, 'ko');
  assert.match(ui.elements.status.textContent, /연결/);
});
test('examples are never saved or sent to the app', async () => {
  const ui = await setup(); await ui.fire('example'); await ui.fire('connection-form', 'submit');
  assert.equal(ui.requests.length, 0); assert.equal(ui.storage.pairing, undefined);
  assert.match(ui.elements.status.textContent, /example/);
});
test('legacy JSON fills fields without saving or connecting', async () => {
  const ui = await setup(); ui.elements.pairing.value = JSON.stringify({ browser: 'edge', port: 47831, token });
  await ui.fire('import');
  assert.equal(ui.elements.browser.value, 'edge'); assert.equal(ui.elements.token.value, token);
  assert.equal(ui.requests.length, 0); assert.equal(ui.storage.pairing, undefined);
});
test('successful check sends no tabs and saves pairing', async () => {
  const ui = await setup(); ui.elements.token.value = token; await ui.fire('connection-form', 'submit');
  assert.equal(ui.storage.pairing.token, token);
  assert.deepEqual(JSON.parse(ui.requests[0].options.body), {browser:'chrome'});
  assert.equal(ui.requests[0].url, 'http://127.0.0.1:47831/status');
  assert.match(ui.elements.status.textContent, /Website control is off/);
});
test('rejected code and unreachable app do not overwrite saved pairing', async () => {
  for (const options of [{ status: 401 }, { offline: true }]) {
    const ui = await setup({ ...options, saved: { pairing: { browser: 'chrome', port: 47831, token } } });
    ui.elements.token.value = token + 'new'; await ui.fire('connection-form', 'submit');
    assert.equal(ui.storage.pairing.token, token); assert.equal(ui.elements.status.dataset.kind, 'error');
  }
});
test('translation keys match all HTML labels', async () => {
  const ui = await setup();
  const texts = ui.context.PawzuraOptionsText;
  assert.deepEqual(Object.keys(texts.en).sort(), Object.keys(texts.ko).sort());
  const html = fs.readFileSync('extensions/chromium/options.html', 'utf8');
  for (const match of html.matchAll(/data-i18n(?:-placeholder)?="([^"]+)"/g)) {
    assert.equal(typeof texts.en[match[1]], 'string', match[1]);
    assert.equal(typeof texts.ko[match[1]], 'string', match[1]);
  }
});
test('bad JSON and invalid port have actionable errors', async () => {
  const ui = await setup(); ui.elements.pairing.value = '{broken'; await ui.fire('import');
  assert.match(ui.elements.status.textContent, /JSON/);
  ui.elements.token.value = token; ui.elements.port.value = '99999'; await ui.fire('connection-form', 'submit');
  assert.match(ui.elements.status.textContent, /port/); assert.equal(ui.requests.length, 0);
});
test('automatic pairing saves approved credentials without a code field', async () => {
  const ui=await setup();
  assert.equal(ui.elements.token.value,'');
  await ui.fire('auto-connect');
  assert.equal(ui.storage.pairing.token,token);
  assert.match(ui.elements.status.textContent,/Connected automatically/);
  assert.deepEqual(ui.requests.map(r=>new URL(r.url).pathname),['/pair/request','/pair/result','/status']);
});
test('denied or expired automatic pairing does not save credentials', async () => {
  for(const pairingState of ['denied','expired']) {
    const ui=await setup({pairingState}); await ui.fire('auto-connect');
    assert.equal(ui.storage.pairing,undefined);
    assert.equal(ui.elements.status.dataset.kind,'error');
  }
});

test('desktop setup link prefills safe fields and requests approval without a code', async () => {
  const ui = await setup({query:'?browser=chrome&port=47831&lang=ko&setup=1'});
  assert.equal(ui.elements.language.value,'ko');
  assert.equal(ui.storage.pairing.token,token);
  assert.deepEqual(ui.requests.map(r=>new URL(r.url).pathname),['/pair/request','/pair/result','/status']);
  const preview = await setup({installed:false, query:'?setup=1'});
  assert.equal(preview.requests.length,0);
});
