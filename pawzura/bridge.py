"""Authenticated loopback bridge. Browser extension owns its tabs; no arbitrary close API."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import json
from queue import Empty, Queue
import re
import secrets
import threading
import time

from .policy import allowed_url


class Bridge:
    def __init__(self, settings):
        self.settings = settings
        self.events = Queue(maxsize=32)
        self.lock = threading.Lock()
        self.tickets = {}
        self.preview_seen = {}
        self.policy = None
        self.peers = {}
        self.pairing_events = Queue(maxsize=4)
        self.pairings = {}
        self.server = None

    def _expire_pairings(self):
        now = time.monotonic()
        self.pairings = {key: value for key, value in self.pairings.items() if now - value["created"] < 60}

    def pairing_request(self, data, origin):
        if not re.fullmatch(r"(?:chrome-extension|moz-extension)://[a-zA-Z0-9-]+", origin):
            raise PermissionError("Extension origin required")
        browser = data.get("browser")
        if browser not in self.settings.snapshot()["browsers"]:
            raise ValueError("Unknown browser")
        with self.lock:
            self._expire_pairings()
            for key, request in self.pairings.items():
                if request["browser"] == browser and request["origin"] == origin:
                    return {"request": key, "state": "pending"}
            if len(self.pairings) >= 4 or self.pairing_events.full():
                raise ValueError("Too many pairing requests")
            key = secrets.token_urlsafe(32)
            self.pairings[key] = {"origin": origin, "browser": browser, "created": time.monotonic(), "state": "pending"}
            self.pairing_events.put_nowait({"request": key, "browser": browser, "origin": origin})
            return {"request": key, "state": "pending"}

    def approve_pairing(self, key, allowed):
        with self.lock:
            self._expire_pairings()
            if key in self.pairings:
                self.pairings[key]["state"] = "approved" if allowed else "denied"

    def pairing_result(self, data, origin):
        with self.lock:
            self._expire_pairings()
            key = data.get("request")
            if not isinstance(key, str) or key not in self.pairings:
                return {"state": "expired"}
            pending = self.pairings[key]
            if pending["origin"] != origin:
                raise PermissionError("Origin mismatch")
            state = pending["state"]
            result = {"state": state}
            if state == "approved":
                config = self.settings.snapshot()
                result["pairing"] = {"token": config["bridge_token"], "port": self.server.server_port,
                                     "browser": pending["browser"]}
            if state != "pending":
                del self.pairings[key]  # one-time delivery, never an open token-discovery API
            return result

    def complete(self, ticket: str):
        with self.lock:
            if ticket in self.tickets:
                self.tickets[ticket]["ready"] = True

    def is_connected(self, browser: str) -> bool:
        with self.lock:
            return time.monotonic() - self.peers.get(browser, float("-inf")) < 5

    def status(self, data: dict) -> dict:
        config = self.settings.snapshot()
        browser = data.get("browser")
        if browser not in config["browsers"]:
            raise ValueError("Unknown browser")
        with self.lock:
            self.peers[browser] = time.monotonic()
            self._sync_policy_locked(config)
        return {"enabled": bool(config["guard_enabled"] and config.get("browser_control_enabled", False) and config["browsers"][browser]["enabled"]), "preview": config["preview_only"]}

    def invalidate_tickets(self):
        with self.lock:
            self._invalidate_tickets_locked()

    def _invalidate_tickets_locked(self):
        self.tickets.clear()
        self.preview_seen.clear()
        while True:
            try:
                self.events.get_nowait()
            except Empty:
                break

    def _sync_policy_locked(self, config):
        policy = json.dumps([config["guard_enabled"], config.get("browser_control_enabled", False),
                             config["preview_only"], config.get("active_profile"), config["browsers"]], sort_keys=True)
        if self.policy != policy:
            self._invalidate_tickets_locked()
            self.policy = policy

    def evaluate(self, data: dict) -> dict:
        config = self.settings.snapshot()
        browser = data.get("browser")
        if browser not in config["browsers"]:
            raise ValueError("Unknown browser")
        tabs = data.get("tabs", [])
        if not isinstance(tabs, list) or len(tabs) > 200:
            raise ValueError("Invalid tabs")
        now = time.monotonic()
        with self.lock:
            self._sync_policy_locked(config)
            # Setup completion requires the new status handshake, not an older
            # extension's URL-evaluation traffic from a different installation.
            self.tickets = {k: v for k, v in self.tickets.items() if now - v["created"] < 20}
            enabled = config["guard_enabled"] and config.get("browser_control_enabled", False) and config["browsers"][browser]["enabled"]
            preview = config["preview_only"]
            decisions = []
            seen = self.preview_seen.get(browser, set())
            blocked = set()
            for tab in tabs:
                if not isinstance(tab, dict) or not isinstance(tab.get("id"), int) or not isinstance(tab.get("url"), str):
                    continue
                url = tab["url"][:8192]
                browser_rules = config["browsers"][browser]
                allowed = not enabled or allowed_url(url, browser_rules["allowed_sites"], browser=browser,
                                                    allow_settings=browser_rules.get("allow_settings_pages", True))
                entry = {"id": tab["id"], "url": url, "allowed": allowed, "close": False}
                if not allowed:
                    policy = json.dumps([config.get("active_profile"), config["preview_only"], config["browsers"][browser]], sort_keys=True)
                    key = f"{policy}:{browser}:{tab['id']}:{url}"
                    fingerprint = hashlib.sha256(key.encode()).digest()
                    blocked.add(fingerprint)
                    ticket = next((k for k, v in self.tickets.items() if v["key"] == key), None)
                    if preview:
                        # A preview is a single demonstration, not a repeating close attempt.
                        if ticket and fingerprint not in seen:
                            del self.tickets[ticket]
                        ticket = None
                    if (not preview or fingerprint not in seen) and not ticket and not self.events.full() and len(self.tickets) < 256:
                        ticket = secrets.token_hex(12)
                        self.tickets[ticket] = {"key": key, "created": now, "ready": False}
                        self.events.put_nowait({"ticket": ticket, "browser": browser,
                                               "active": bool(tab.get("active")), "preview": preview})
                    if ticket:
                        entry["close"] = not preview and self.tickets[ticket]["ready"]
                        if preview:
                            seen.add(fingerprint)
                decisions.append(entry)
            self.preview_seen[browser] = seen & blocked if preview else set()
            return {"enabled": enabled, "preview": preview, "decisions": decisions}

    def start(self):
        bridge = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass  # URLs and tokens must not land in logs.

            def send_json(self, status, payload):
                body = json.dumps(payload).encode()
                self.send_response(status)
                origin = self.headers.get("Origin", "")
                if origin.startswith(("chrome-extension://", "moz-extension://")):
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_OPTIONS(self):
                self.send_response(204)
                origin = self.headers.get("Origin", "")
                if origin.startswith(("chrome-extension://", "moz-extension://")):
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Pawzura-Token")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.end_headers()

            def do_POST(self):
                try:
                    config = bridge.settings.snapshot()
                    host = self.headers.get("Host", "")
                    if host != f"127.0.0.1:{bridge.server.server_port}":
                        self.send_json(403, {"error": "Invalid host"})
                        return
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 256_000:
                        self.send_json(413, {"error": "Payload too large"})
                        return
                    if self.path in ("/pair/request", "/pair/result"):
                        origin = self.headers.get("Origin", "")
                        data = json.loads(self.rfile.read(length))
                        if not isinstance(data, dict):
                            raise ValueError("Invalid object")
                        result = (bridge.pairing_request(data, origin) if self.path == "/pair/request"
                                  else bridge.pairing_result(data, origin))
                        self.send_json(200, result)
                        return
                    # Drain only the bounded body before rejecting authentication.
                    # Closing with unread upload bytes can reset the Windows TCP
                    # connection before the client receives its 401 response.
                    payload = self.rfile.read(length)
                    token = self.headers.get("X-Pawzura-Token", "")
                    if not hmac.compare_digest(token.encode(), config["bridge_token"].encode()):
                        self.send_json(401, {"error": "Pairing required"})
                        return
                    if self.path not in ("/evaluate", "/status"):
                        self.send_json(404, {"error": "Unknown endpoint"})
                        return
                    data = json.loads(payload)
                    if not isinstance(data, dict):
                        raise ValueError("Invalid object")
                    self.send_json(200, bridge.status(data) if self.path == "/status" else bridge.evaluate(data))
                except PermissionError:
                    self.send_json(403, {"error": "Pairing origin rejected"})
                except (ValueError, TypeError, KeyError):
                    self.send_json(400, {"error": "Invalid request"})
                except (ConnectionError, OSError):
                    pass

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            def get_request(self):
                sock, address = super().get_request()
                sock.settimeout(3)
                return sock, address

        self.server = Server(("127.0.0.1", self.settings.snapshot()["bridge_port"]), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True, name="browser-bridge").start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
