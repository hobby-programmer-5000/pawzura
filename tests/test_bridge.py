import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import time
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request
from pawzura.bridge import Bridge
from pawzura.config import Settings


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.directory.name) / "settings.json")
        self.settings.data["bridge_port"] = 0
        self.bridge = Bridge(self.settings)
        self.bridge.start()
        self.url = f"http://127.0.0.1:{self.bridge.server.server_port}/evaluate"

    def tearDown(self):
        self.bridge.stop()
        self.directory.cleanup()

    def send(self, token=None, url="https://unlisted.example"):
        request = Request(self.url, json.dumps({"browser": "chrome", "tabs": [{"id": 1, "url": url, "active": True}]}).encode(),
                          {"X-Pawzura-Token": token if token is not None else self.settings.data["bridge_token"], "Content-Type": "application/json"})
        with build_opener(ProxyHandler({})).open(request, timeout=2) as response:
            return json.load(response)

    def enable(self, preview=False):
        self.settings.data["guard_enabled"] = True
        self.settings.data["browser_control_enabled"] = True
        self.settings.data["preview_only"] = preview
        self.settings.data["browsers"]["chrome"]["enabled"] = True

    def test_rejects_bad_token(self):
        with self.assertRaises(HTTPError) as raised:
            self.send("wrong-token")
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

    def test_disabled_never_closes(self):
        result = self.send()
        self.assertTrue(result["decisions"][0]["allowed"])
        self.assertTrue(self.bridge.events.empty())

    def test_master_switch_overrides_ready_ticket_without_pausing_app_guardian(self):
        self.enable()
        self.send()
        self.bridge.complete(self.bridge.events.get_nowait()["ticket"])
        self.settings.save({"browser_control_enabled": False})
        result = self.send()
        self.assertFalse(result["enabled"])
        self.assertTrue(result["decisions"][0]["allowed"])
        self.assertFalse(result["decisions"][0]["close"])
        self.assertTrue(self.settings.snapshot()["guard_enabled"])

    def test_authenticated_status_uses_no_tabs_or_events(self):
        self.enable()
        self.bridge.evaluate({"browser":"chrome","tabs":[]})
        self.assertFalse(self.bridge.is_connected("chrome"))
        request = Request(self.url.removesuffix("/evaluate") + "/status", json.dumps({"browser":"chrome"}).encode(), {"X-Pawzura-Token":self.settings.data["bridge_token"]})
        with build_opener(ProxyHandler({})).open(request, timeout=2) as response:
            result = json.load(response)
        self.assertTrue(result["enabled"])
        self.assertTrue(self.bridge.is_connected("chrome"))
        self.assertTrue(self.bridge.events.empty())
        self.assertEqual(self.bridge.tickets, {})

    def test_close_waits_for_bite(self):
        self.enable()
        self.assertFalse(self.send()["decisions"][0]["close"])
        event = self.bridge.events.get_nowait()
        self.bridge.complete(event["ticket"])
        self.assertTrue(self.send()["decisions"][0]["close"])

    def test_profile_switch_requires_new_animation_and_can_allow_existing_tab(self):
        self.enable()
        self.send()
        event = self.bridge.events.get_nowait()
        self.bridge.complete(event["ticket"])
        self.settings.data["active_profile"] = "Leisure"
        self.assertFalse(self.send()["decisions"][0]["close"])
        self.settings.data["browsers"]["chrome"]["allowed_sites"] = ["https://unlisted.example/*"]
        self.assertTrue(self.send()["decisions"][0]["allowed"])
        self.bridge.invalidate_tickets()
        self.assertTrue(self.bridge.events.empty())
        self.assertEqual(self.bridge.tickets, {})

    def test_preview_never_closes(self):
        self.enable(preview=True)
        self.send()
        event = self.bridge.events.get_nowait()
        self.bridge.complete(event["ticket"])
        self.assertFalse(self.send()["decisions"][0]["close"])

    def test_preview_does_not_repeat_when_ticket_expires(self):
        self.enable(preview=True)
        self.send()
        event = self.bridge.events.get_nowait()
        self.bridge.complete(event["ticket"])
        with patch("pawzura.bridge.time.monotonic", return_value=time.monotonic()+60):
            self.assertFalse(self.send()["decisions"][0]["close"])
        self.assertTrue(self.bridge.events.empty())
        self.assertNotIn(event["ticket"], self.bridge.tickets)

    def test_preview_rearms_after_allowed_navigation_or_settings_apply(self):
        self.enable(preview=True)
        self.settings.data["browsers"]["chrome"]["allowed_sites"] = ["example.com/*"]
        self.send()
        self.bridge.events.get_nowait()
        self.send(url="https://example.com/allowed")
        self.assertTrue(self.bridge.events.empty())
        self.send()
        self.assertFalse(self.bridge.events.empty())
        self.bridge.invalidate_tickets()
        self.send()
        self.assertFalse(self.bridge.events.empty())

    def test_pause_cancels_ready_close(self):
        self.enable()
        self.send()
        self.bridge.complete(self.bridge.events.get_nowait()["ticket"])
        self.settings.data["guard_enabled"] = False
        self.assertFalse(self.send()["decisions"][0]["close"])

    def test_navigation_does_not_reuse_close(self):
        self.enable()
        self.send()
        self.bridge.complete(self.bridge.events.get_nowait()["ticket"])
        result = self.send(url="https://other.example")
        self.assertFalse(result["decisions"][0]["close"])

    def test_live_allowlist_change_cancels_close(self):
        self.enable()
        self.send()
        self.bridge.complete(self.bridge.events.get_nowait()["ticket"])
        self.settings.data["browsers"]["chrome"]["allowed_sites"] = ["https://unlisted.example"]
        result = self.send()["decisions"][0]
        self.assertTrue(result["allowed"])
        self.assertFalse(result["close"])

    def test_scoped_url_rule_is_used_by_http_bridge(self):
        self.enable()
        self.settings.data["browsers"]["chrome"]["allowed_sites"] = ["https://example.com/library?view=video"]
        permitted = self.send(url="https://example.com/library/lesson?view=video&utm=test")["decisions"][0]
        self.assertTrue(permitted["allowed"])
        self.assertTrue(self.bridge.events.empty())
        denied = self.send(url="https://example.com/other?view=video")["decisions"][0]
        self.assertFalse(denied["allowed"])
        self.assertFalse(denied["close"])

    def test_subdomain_address_rules_flow_through_bridge(self):
        from pawzura.policy import address_rules
        self.enable()
        self.settings.data["browsers"]["chrome"]["allowed_sites"] = address_rules("example.com/team/*", True)
        for host in ("example.com", "console.example.com", "a.console.example.com"):
            self.assertTrue(self.send(url=f"https://{host}/team/project")["decisions"][0]["allowed"])
        self.assertTrue(self.bridge.events.empty())
        self.assertFalse(self.send(url="https://example.com.evil.test/team")["decisions"][0]["allowed"])

    def pair_post(self, path, data, origin="chrome-extension://testextension"):
        request = Request(self.url.removesuffix("/evaluate") + path, json.dumps(data).encode(),
                          {"Content-Type":"application/json", "Origin":origin})
        with build_opener(ProxyHandler({})).open(request, timeout=2) as response:
            return json.load(response)

    def test_automatic_pairing_requires_desktop_approval_and_is_one_time(self):
        start = self.pair_post("/pair/request", {"browser":"chrome"})
        pending = self.pair_post("/pair/result", {"request":start["request"]})
        self.assertEqual(pending, {"state":"pending"})
        self.assertNotIn("pairing", pending)
        event = self.bridge.pairing_events.get_nowait()
        self.bridge.approve_pairing(event["request"], True)
        approved = self.pair_post("/pair/result", {"request":start["request"]})
        self.assertEqual(approved["pairing"]["token"],self.settings.data["bridge_token"])
        self.assertEqual(self.pair_post("/pair/result", {"request":start["request"]}), {"state":"expired"})

    def test_pairing_denies_web_origins_and_cross_extension_redemption(self):
        for origin in ("https://evil.test", "null", ""):
            with self.assertRaises(HTTPError) as rejected:
                self.pair_post("/pair/request", {"browser":"chrome"},origin)
            self.assertEqual(rejected.exception.code,403)
            rejected.exception.close()
        request = self.pair_post("/pair/request", {"browser":"chrome"})
        self.bridge.approve_pairing(request["request"],True)
        with self.assertRaises(HTTPError) as rejected:
            self.pair_post("/pair/result", {"request":request["request"]}, "chrome-extension://otherextension")
        self.assertEqual(rejected.exception.code,403)
        rejected.exception.close()

    def test_pairing_denial_and_expiry_do_not_disclose_token(self):
        request = self.pair_post("/pair/request", {"browser":"chrome"})
        self.bridge.approve_pairing(request["request"],False)
        self.assertEqual(self.pair_post("/pair/result", {"request":request["request"]}), {"state":"denied"})
        request = self.pair_post("/pair/request", {"browser":"chrome"})
        self.bridge.pairings[request["request"]]["created"] -= 61
        self.assertEqual(self.pair_post("/pair/result", {"request":request["request"]}), {"state":"expired"})


if __name__ == "__main__":
    unittest.main()
