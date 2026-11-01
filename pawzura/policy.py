"""Exact hosts with optional path sections and query constraints."""
from collections import Counter
from pathlib import PureWindowsPath
import re
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from .config import BROWSER_EXECUTABLES, expand_app_aliases

INTERNAL_PAGES = {
    "about:blank", "about:newtab", "about:home", "about:privatebrowsing",
    "chrome://newtab", "chrome://new-tab-page", "chrome://welcome",
    "edge://newtab", "edge://welcome", "brave://newtab", "vivaldi://newtab",
    "opera://startpage", "chrome-search://local-ntp/local-ntp.html",
}


def normalize_app(value: str) -> str:
    return PureWindowsPath(value.strip().strip('"')).name.casefold()


def allowed_app(executable: str, config: dict) -> bool:
    allowed = config["allowed_apps"] + config.get("startup_apps", [])
    # Browser windows are NEVER controlled by the native app guardian.
    return is_browser(executable) or normalize_app(executable) in expand_app_aliases(allowed)


def is_browser(executable: str) -> bool:
    return normalize_app(executable) in BROWSER_EXECUTABLES


class SiteRuleError(ValueError):
    def __init__(self, code="invalid_url"):
        self.code = code
        super().__init__({
            "invalid_url": "Enter a domain or a complete HTTP(S) URL, including its hostname.",
            "invalid_port": "Enter a valid port between 1 and 65535.",
            "invalid_path": "Use a path without dot segments, backslashes or encoded separators.",
            "invalid_wildcard": "Use * only as a subdomain prefix or a final /* path suffix.",
        }[code])


def _split(value: str, allow_wildcard=False):
    if not isinstance(value, str) or not value.strip() or re.search(r"[\x00-\x20\x7f]", value.strip()):
        raise SiteRuleError()
    value = value.strip()
    # Accept the 0.1.0/0.1.1 serialized wildcard form as well as normal URLs.
    if value.startswith(("*.https://", "*.http://")):
        value = value[2:].replace("://", "://*.", 1)
    if "://" not in value:
        value = "https://" + value
    if "\\" in value or re.search(r"%(?![0-9a-fA-F]{2})", value):
        raise SiteRuleError()
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise SiteRuleError()
        wildcard = allow_wildcard and parsed.hostname.startswith("*.")
        host = parsed.hostname[2:] if wildcard else parsed.hostname
        if "*" in host or "%" in host:
            raise SiteRuleError()
        host = host.encode("idna").decode("ascii").lower()
        # DNS labels or an IPv6 literal; reject malformed host syntax early.
        if ":" not in host and any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", part) for part in host.split(".")):
            raise SiteRuleError()
        try:
            port = parsed.port
        except ValueError as error:
            raise SiteRuleError("invalid_port") from error
        if port == 0:
            raise SiteRuleError("invalid_port")
        port = None if port == {"https": 443, "http": 80}[parsed.scheme] else port
        return parsed, host, port, wildcard
    except (UnicodeError, ValueError) as error:
        if isinstance(error, SiteRuleError):
            raise
        raise SiteRuleError() from error


def _path(path: str) -> str:
    if re.search(r"%(?:2f|5c)", path, re.I):
        raise SiteRuleError("invalid_path")
    decoded = unquote(path, errors="strict")
    if "\\" in decoded or any(part in (".", "..") for part in decoded.split("/")) or re.search(r"[\x00-\x1f\x7f]", decoded):
        raise SiteRuleError("invalid_path")
    return quote(decoded, safe="/:@!$&'()*+,;=-._~").rstrip("/")


def site_rule(value: str) -> str:
    parsed, host, port, wildcard = _split(value, allow_wildcard=True)
    suffix = f":{port}" if port is not None else ""
    host = f"[{host}]" if ":" in host else host
    authority = ("*." if wildcard else "") + host + suffix
    try:
        path = parsed.path[:-2] if parsed.path.endswith("/*") else parsed.path
        if "*" in unquote(path):
            raise SiteRuleError("invalid_wildcard")
        path = _path(path)
        query = urlencode(parse_qsl(parsed.query, keep_blank_values=True, errors="strict"))
    except (UnicodeError, ValueError) as error:
        if isinstance(error, SiteRuleError):
            raise
        raise SiteRuleError() from error
    # Fragments are browser-side navigation, not part of the server URL policy.
    return urlunsplit((parsed.scheme, authority, path, query, ""))


def allowed_url(url: str, rules: list[str]) -> bool:
    try:
        # Internal new-tab pages are exact matches, never trust arbitrary internal URLs.
        if url.rstrip("/").split("#", 1)[0].split("?", 1)[0] in INTERNAL_PAGES:
            return True
        parsed, host, port, _ = _split(url)
        for rule in rules:
            try:
                base, base_host, base_port, wildcard = _split(site_rule(rule), allow_wildcard=True)
                if parsed.scheme != base.scheme or port != base_port:
                    continue
                if not (host.endswith("." + base_host) if wildcard else host == base_host):
                    continue
                if base.path:
                    path = _path(parsed.path)
                    if path != base.path and not path.startswith(base.path + "/"):
                        continue
                required = parse_qsl(base.query, keep_blank_values=True)
                actual = parse_qsl(parsed.query, keep_blank_values=True)
                if any(Counter(v for k, v in actual if k == key) != Counter(v for k, v in required if k == key)
                       for key in {k for k, _ in required}):
                    continue
                return True
            except (ValueError, UnicodeError, TypeError):
                # One damaged saved entry must not invalidate other valid rules.
                continue
    except (ValueError, UnicodeError, TypeError):
        return False
    return False
