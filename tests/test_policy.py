import unittest
from pawzura.config import defaults
from pawzura.policy import allowed_app, allowed_url, site_rule


class PolicyTests(unittest.TestCase):
    def test_trailing_path_wildcards_allow_descendants_with_exact_host(self):
        for rule in ("example.com/*", "https://example.com/*"):
            for path in ("", "/", "/any/depth?x=1#top"):
                self.assertTrue(allowed_url("https://example.com" + path, [rule]))
            for url in ("https://example.com.evil.test/a", "https://sub.example.com/a", "http://example.com/a"):
                self.assertFalse(allowed_url(url, [rule]))
        self.assertTrue(allowed_url("http://example.com/a", ["http://example.com/*"]))
        self.assertTrue(allowed_url("https://sub.example.com/a", ["*.example.com/*"]))
        for path in ("/section", "/section/", "/section/child?x=1"):
            self.assertTrue(allowed_url("https://example.com" + path, ["example.com/section/*"]))
        for path in ("/other", "/section-evil", "/section%2fother"):
            self.assertFalse(allowed_url("https://example.com" + path, ["example.com/section/*"]))
        for rule in ("example.com/sec*", "example.com/*/child", "example.com/sec%2a"):
            with self.assertRaises(ValueError):
                site_rule(rule)

    def test_executable_exact_case_insensitive(self):
        config = defaults()
        self.assertTrue(allowed_app(r"C:\Users\Me\Code.EXE", config))
        self.assertFalse(allowed_app("fake-code.exe", config))
        self.assertFalse(allowed_app("code.exe.malware.exe", config))

    def test_startup_snapshot(self):
        config = defaults()
        config["startup_apps"] = ["helper.exe"]
        self.assertTrue(allowed_app("HELPER.EXE", config))

    def test_codex_display_name_resolves_its_actual_executable(self):
        config = defaults()
        config["allowed_apps"] = ["codex.exe"]
        self.assertTrue(allowed_app(r"C:\Program Files\WindowsApps\OpenAI.Codex_1\app\ChatGPT.exe", config))
        self.assertFalse(allowed_app("fake-chatgpt.exe", config))

    def test_browser_window_is_never_a_native_close_candidate(self):
        config = defaults()
        config["allowed_apps"] = []
        config["startup_apps"] = []
        for name in ("chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "arc.exe"):
            self.assertTrue(allowed_app(name, config), name)

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
        for rule in ("", "http://", "https://", "ftp://example.com", "https://user@example.com", "https://example.com:bad"):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                site_rule(rule)
        self.assertFalse(allowed_url("https://example.com:bad/", []))

    def test_pasted_path_rules_allow_a_section_not_sibling_names(self):
        rules = [site_rule("example.com/my-account")]
        self.assertEqual(rules, ["https://example.com/my-account"])
        for url in ("https://example.com/my-account", "https://example.com/my-account/", "https://example.com/my-account/project?tab=code"):
            self.assertTrue(allowed_url(url, rules), url)
        for url in ("https://example.com/other-account", "https://example.com/my-account-evil", "https://example.com/", "https://example.com/My-account"):
            self.assertFalse(allowed_url(url, rules), url)

    def test_query_rules_accept_extra_keys_but_require_exact_constrained_values(self):
        rule = site_rule("example.com/ko?viewMode=svod")
        self.assertTrue(allowed_url("https://example.com/ko?viewMode=svod&utm_source=test", [rule]))
        for query in ("", "?viewMode=live", "?viewMode=svod&viewMode=live", "?viewMode=svod&viewMode=svod"):
            self.assertFalse(allowed_url("https://example.com/ko" + query, [rule]), query)

    def test_full_http_and_https_addresses(self):
        for scheme in ("http", "https"):
            rule = site_rule(f"{scheme}://example.com/personal/home")
            self.assertTrue(allowed_url(f"{scheme}://example.com/personal/home/classes", [rule]))
        self.assertFalse(allowed_url("http://example.com/personal/home", [site_rule("example.com/personal/home")]))

    def test_wildcards_have_readable_form_and_keep_legacy_compatibility(self):
        self.assertEqual(site_rule("*.example.com/help"), "https://*.example.com/help")
        self.assertEqual(site_rule("*.https://example.com/help"), "https://*.example.com/help")
        self.assertTrue(allowed_url("https://a.example.com/help/topic", ["*.https://example.com/help"]))
        self.assertTrue(allowed_url("http://a.example.com/help", ["http://*.example.com/help"]))
        self.assertFalse(allowed_url("https://example.com/help", ["https://*.example.com/help"]))

    def test_fragment_is_ignored_and_unicode_paths_are_normalized(self):
        self.assertEqual(site_rule("example.com/path#section"), "https://example.com/path")
        self.assertTrue(allowed_url("https://example.com/한글/lesson#top", [site_rule("example.com/한글")]))
        self.assertTrue(allowed_url("https://example.com/%ED%95%9C%EA%B8%80", [site_rule("example.com/한글")]))

    def test_path_scope_rejects_ambiguous_encodings(self):
        for path in ("/a/../b", "/a/%2e%2e/b", "/a%2fb", "/a%5cb", "/a\\b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                site_rule("https://example.com" + path)
        self.assertFalse(allowed_url("https://example.com/allowed/../other", [site_rule("example.com/allowed")]))
        self.assertFalse(allowed_url("https://example.com/allowed%2Fother", [site_rule("example.com/allowed")]))

    def test_one_bad_saved_entry_does_not_hide_later_valid_rules(self):
        self.assertTrue(allowed_url("https://example.com/path", ["https://", "https://example.com/path"]))


if __name__ == "__main__":
    unittest.main()
