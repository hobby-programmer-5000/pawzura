[English](../en/RELEASE-v0.5.1.md) | [한국어](../ko/RELEASE-v0.5.1.md) · [Documentation](../README.md)

# 0.5.1 — local browser addresses

In **Browsers**, select the browser and allowlist profile you use. To allow a local server, add its full origin, such as `http://127.0.0.1:3000`, and click **Save settings**. HTTP and HTTPS use separate rules. A URL without an explicit port uses port 80 for HTTP or 443 for HTTPS.

For a local app that changes ports, turn off **Include subdomains** and add just `127.0.0.1`. This entry allows all HTTP and HTTPS ports on that exact IP for the selected browser and profile. [Browser allowlist guide](BROWSERS.md#ordinary-websites).

Download **Pawzura-0.5.1-windows-x64.zip** and its SHA-256 checksum from Releases. Quit the previous Pawzura, extract the entire ZIP into a new folder and launch `Pawzura/Pawzura.exe` with `_internal` beside it. The browser extension can stay installed. Test the updated allowlist with preview mode enabled.
