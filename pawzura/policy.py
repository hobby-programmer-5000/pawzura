"""Pure policy: exact executable names, exact web origins, explicit subdomains."""
from pathlib import PureWindowsPath
from urllib.parse import urlsplit

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
    return normalize_app(executable) in {normalize_app(item) for item in allowed}


def site_rule(value: str) -> str:
    value = value.strip()
    wildcard = value.startswith("*.")
    if wildcard:
        value = value[2:]
    if "://" not in value:
        value = "https://" + value
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use an HTTP(S) origin, e.g. https://example.com or *.example.com")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Site rules allow a whole origin; remove paths, queries and fragments")
    host = parsed.hostname.encode("idna").decode("ascii").lower()
    port = parsed.port
    suffix = f":{port}" if port and port != {"https": 443, "http": 80}[parsed.scheme] else ""
    host = f"[{host}]" if ":" in host else host
    return ("*." if wildcard else "") + f"{parsed.scheme}://{host}{suffix}"


def allowed_url(url: str, rules: list[str]) -> bool:
    try:
        # Internal new-tab pages are exact matches, never trust arbitrary internal URLs.
        if url.rstrip("/").split("#", 1)[0].split("?", 1)[0] in INTERNAL_PAGES:
            return True
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return False
        origin = site_rule(f"{parsed.scheme}://{parsed.netloc}")
        normalized = urlsplit(origin)
        for rule in rules:
            if rule.startswith("*."):
                base = urlsplit(rule[2:])
                if (normalized.scheme == base.scheme and normalized.port == base.port
                        and normalized.hostname.endswith("." + base.hostname)):
                    return True
            elif origin == site_rule(rule):
                return True
    except (ValueError, UnicodeError, TypeError):
        return False
    return False
