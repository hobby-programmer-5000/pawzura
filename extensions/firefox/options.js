const api = globalThis.browser || globalThis.chrome;
const installed = !!(api?.storage?.local && api?.runtime?.id);
const $ = selector => document.querySelector(selector);
const EXAMPLE = 'EXAMPLE_ONLY_REPLACE_WITH_YOUR_APP_CONNECTION_CODE';
const browsers = ['chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi', 'arc', 'zen'];
let language = 'en';
let lastStatus = { key: 'not_connected', kind: '' };
function message(key, kind = '') {
  lastStatus = { key, kind };
  $('#status').textContent = PawzuraOptionsText[language][key];
  $('#status').dataset.kind = kind;
}
function translate(value) {
  language = value === 'ko' ? 'ko' : 'en';
  document.documentElement.lang = language;
  document.title = language === 'ko' ? 'Pawzura · 브라우저 연결' : 'Pawzura · Browser connection';
  $('#language').value = language;
  for (const element of document.querySelectorAll('[data-i18n]')) element.textContent = PawzuraOptionsText[language][element.dataset.i18n];
  for (const element of document.querySelectorAll('[data-i18n-placeholder]')) element.placeholder = PawzuraOptionsText[language][element.dataset.i18nPlaceholder];
  message(lastStatus.key, lastStatus.kind);
}
function validate(pairing) {
  if (pairing?.token === EXAMPLE) throw new Error('example_only');
  if (typeof pairing?.token !== 'string' || !/^[A-Za-z0-9_-]{32,256}$/.test(pairing.token)) throw new Error('bad_code');
  if (!Number.isInteger(pairing.port) || pairing.port < 1024 || pairing.port > 65535) throw new Error('bad_port');
  if (!browsers.includes(pairing.browser)) throw new Error('bad_browser');
  return { token: pairing.token, port: pairing.port, browser: pairing.browser };
}
function fill(pairing) {
  $('#browser').value = pairing.browser; $('#port').value = String(pairing.port); $('#token').value = pairing.token;
}
$('#language').addEventListener('change', async () => {
  translate($('#language').value);
  try {
    if (installed) await api.storage.local.set({ language });
    else globalThis.localStorage?.setItem('pawzura-options-language', language);
  } catch (_) { /* Keep language switching usable without preference storage. */ }
});
$('#show-code').addEventListener('change', () => { $('#token').type = $('#show-code').checked ? 'text' : 'password'; });
$('#example').addEventListener('click', () => {
  fill({ browser: 'chrome', port: 47831, token: EXAMPLE });
  $('#token').type = 'text'; $('#show-code').checked = true; message('example_filled');
});
$('#import').addEventListener('click', () => {
  try {
    let raw;
    try { raw = JSON.parse($('#pairing').value); } catch (_) { throw new Error('bad_json'); }
    fill(validate(raw)); $('#pairing').value = ''; message('imported');
  } catch (error) { message(PawzuraOptionsText.en[error.message] ? error.message : 'bad_json', 'error'); }
});
$('#connection-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!installed) { message('file_preview', 'error'); return; }
  $('#save').disabled = true;
  try {
    const pairing = validate({ token: $('#token').value.trim(), port: Number($('#port').value), browser: $('#browser').value });
    message('testing');
    let response;
    try {
      response = await fetch(`http://127.0.0.1:${pairing.port}/evaluate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Pawzura-Token': pairing.token },
        body: JSON.stringify({ browser: pairing.browser, tabs: [] }), signal: AbortSignal.timeout(3000),
      });
    } catch (_) { throw new Error('unavailable'); }
    if (response.status === 401) throw new Error('wrong_code');
    if (!response.ok) throw new Error('bridge_error');
    const state = await response.json();
    if (typeof state.enabled !== 'boolean' || typeof state.preview !== 'boolean') throw new Error('bridge_error');
    try { await api.storage.local.set({ pairing, language }); } catch (_) { throw new Error('storage_error'); }
    message(!state.enabled ? 'connected_off' : state.preview ? 'connected_preview' : 'connected_live');
  } catch (error) { message(PawzuraOptionsText.en[error.message] ? error.message : 'bridge_error', 'error'); }
  finally { $('#save').disabled = !installed; }
});
$('#disconnect').addEventListener('click', async () => {
  if (!installed) return;
  try { await api.storage.local.remove('pairing'); $('#token').value = ''; message('disconnected'); }
  catch (_) { message('storage_error', 'error'); }
});
async function initialize() {
  translate('en');
  if (!installed) {
    $('#preview-warning').hidden = false;
    $('#save').disabled = true; $('#disconnect').disabled = true;
    try { translate(globalThis.localStorage?.getItem('pawzura-options-language')); } catch (_) {}
    return;
  }
  try {
    const saved = await api.storage.local.get(['pairing', 'language']);
    translate(saved.language);
    if (saved.pairing) { fill(validate(saved.pairing)); message('saved'); }
  } catch (_) { message('storage_error', 'error'); }
}
void initialize();
