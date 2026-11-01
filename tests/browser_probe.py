"""Opt-in real Chromium test using a fresh profile and a test-only bridge.

Requires playwright in the test environment and a Chromium binary. Never uses
the user's browser profile or their Pawzura settings. Approval/animation events
are acknowledged by the test, not by clicking a real user's confirmation dialog.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pawzura.bridge import Bridge
from pawzura.config import Settings
from pawzura.browser_setup import connection_url, extension_id as expected_extension_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chromium', required=True, type=Path)
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright, expect
    class Page(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'<html><title>Pawzura isolated browser probe</title><h1>Test page</h1></html>'
            self.send_response(200)
            self.send_header('Content-Type','text/html')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self,*args): pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Page)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='browser-probe-',dir=ROOT/'.cache') as temporary:
        settings = Settings(Path(temporary)/'settings.json')
        settings.data['bridge_port'] = 0
        origin = f'http://127.0.0.1:{server.server_port}'
        settings.data['browsers']['chrome'] = {'enabled':True,'allowed_sites':[origin+'/allowed']}
        settings.data.update(guard_enabled=True,preview_only=False,browser_control_enabled=True)
        bridge = Bridge(settings)
        bridge.start()
        stop = threading.Event()
        def acknowledge():
            while not stop.wait(.05):
                try:
                    request = bridge.pairing_events.get_nowait()
                    bridge.approve_pairing(request['request'],True)
                except Empty: pass
                try:
                    event = bridge.events.get_nowait()
                    bridge.complete(event['ticket'])
                except Empty: pass
        threading.Thread(target=acknowledge,daemon=True).start()
        try:
            with sync_playwright() as p:
                extension = ROOT/'extensions/chromium'
                context = p.chromium.launch_persistent_context(
                    str(Path(temporary)/'profile'),executable_path=str(args.chromium),headless=True,
                    ignore_default_args=['--disable-extensions'],
                    args=[f'--disable-extensions-except={extension}',f'--load-extension={extension}'])
                try:
                    worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker',timeout=15000)
                    extension_id = worker.url.split('/')[2]
                    assert extension_id == expected_extension_id(extension / 'manifest.json')
                    options = context.new_page()
                    options.goto(connection_url('chrome',extension,bridge.server.server_port,'en'))
                    expect(options.locator('#status')).to_contain_text('Connected automatically',timeout=15000)
                    assert not options.is_closed(), 'Extension must not close its own options'
                    options.screenshot(path=str(ROOT/'artifacts/connection-automatic-en.png'),full_page=True)
                    options.locator('#language').select_option('ko')
                    expect(options.locator('#status')).to_contain_text('자동 연결됐습니다')
                    options.screenshot(path=str(ROOT/'artifacts/connection-automatic-ko.png'),full_page=True)
                    allowed = context.new_page()
                    allowed.goto(origin+'/allowed')
                    blocked = context.new_page()
                    blocked.goto(origin+'/blocked')
                    blocked.wait_for_event('close',timeout=15000)
                    assert not allowed.is_closed(), 'Allowed tab was closed'
                    assert not options.is_closed(), 'Own extension page was closed'
                    settings.data['guard_enabled'] = False
                    last = context.new_page()
                    last.goto(origin+'/blocked-last')
                    for page in list(context.pages):
                        if page != last: page.close()
                    expected_window = worker.evaluate("async () => (await chrome.tabs.query({})).find(t => t.url.includes('/blocked-last')).windowId")
                    settings.data['guard_enabled'] = True
                    last.wait_for_event('close',timeout=15000)
                    remaining = worker.evaluate("async () => (await chrome.tabs.query({})).map(t => ({url:t.url,windowId:t.windowId}))")
                    assert any(t['url']=='about:blank' and t['windowId']==expected_window for t in remaining), f'Last-tab window was not retained: {remaining}'
                    context.new_page().goto(origin+'/allowed')
                    print('PASS: real Chromium automatic pairing, own-options protection, only blocked tab closed, allowed tab kept, last-tab window retained')
                finally:
                    context.close()
        finally:
            stop.set()
            bridge.stop()
            server.shutdown()
            server.server_close()


if __name__ == '__main__': main()
