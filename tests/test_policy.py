import unittest
from pawzura.config import defaults
from pawzura.policy import allowed_app, allowed_url, site_rule


class PolicyTests(unittest.TestCase):
    def test_executable_exact_case_insensitive(self):
        config = defaults()
        self.assertTrue(allowed_app(r"C:\Users\Me\Code.EXE", config))
        self.assertFalse(allowed_app("fake-code.exe", config))
        self.assertFalse(allowed_app("code.exe.malware.exe", config))

    def test_startup_snapshot(self):
        config = defaults()
        config["startup_apps"] = ["helper.exe"]
        self.assertTrue(allowed_app("HELPER.EXE", config))

    def test_exact_origin_blocks_lookalikes(self):
        rules = [site_rule("example.com")]
        self.assertTrue(allowed_url("https://example.com/path?q=1", rules))
        for url in ("https://example.com.evil.test", "https://evil-example.com", "https://example.com@evil.test", "http://example.com", "https://sub.example.com", "https://example.com:8443"):
            with self.subTest(url=url):
                self.assertFalse(allowed_url(url, rules))

    def test_explicit_subdomains(self):
        rules = [site_rule("*.example.com")]
        self.assertTrue(allowed_url("https://a.b.example.com/page", rules))
        self.assertTrue(allowed_url("https://a.example.com:443/page", rules))
        self.assertTrue(allowed_url("https://하위.예시.한국/page", [site_rule("*.예시.한국")]))
        self.assertFalse(allowed_url("https://example.com", rules))
        self.assertFalse(allowed_url("http://a.example.com", rules))

    def test_internal_defaults_are_narrow(self):
        for url in ("chrome://newtab/", "edge://newtab", "about:blank", "about:newtab", "about:home"):
            self.assertTrue(allowed_url(url, []), url)
        for url in ("chrome://settings", "file:///secret", "javascript:alert(1)", "https://www.google.com", "about:blank.evil"):
            self.assertFalse(allowed_url(url, []), url)

    def test_idn_and_ports(self):
        self.assertEqual(site_rule("https://EXAMPLE.COM:443/"), "https://example.com")
        self.assertTrue(allowed_url("https://example.com:443/path", ["https://example.com"]))
        self.assertTrue(allowed_url("https://예시.한국/", [site_rule("예시.한국")]))
        self.assertTrue(allowed_url("http://[::1]:8080/", [site_rule("http://[::1]:8080")]))

    def test_bad_rules_and_urls(self):
        for rule in ("", "https://example.com/a", "ftp://example.com", "https://user@example.com", "https://example.com:bad"):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                site_rule(rule)
        self.assertFalse(allowed_url("https://example.com:bad/", []))


if __name__ == "__main__":
    unittest.main()
