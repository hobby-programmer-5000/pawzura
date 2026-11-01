[English](../en/RELEASE-v0.1.2.md) | [한국어](../ko/RELEASE-v0.1.2.md) · [Documentation](../README.md)

# Pawzura 0.1.2 preview

Website allowlists now accept pasted paths and query parameters, such as `github.com/my-account` or `example.com/ko?viewMode=svod`. Previously, one such line prevented the whole edited list from saving.

Domains allow a whole site. Paths allow that section and its children; query conditions keep their specified values. HTTPS is assumed if omitted; explicit HTTP and HTTPS URLs are supported separately. Bare scheme prefixes are incomplete, not global allow rules. Fragments are ignored.

The app now reports invalid entries with a line number in English or Korean, displays normalized rules after saving, and retains compatibility with previously saved wildcard rules. Host lookalikes, sibling path prefixes and ambiguous encoded path separators remain blocked.

Download the full ZIP, quit the old desktop app and launch the new Pawzura.exe. The existing 0.1.1 browser extension uses the same protocol. See [browser examples](BROWSERS.md) and [validation](VALIDATION.md). App code remains MIT; bundled components retain their own terms.
