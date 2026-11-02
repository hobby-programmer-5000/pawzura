[English](../en/RELEASE-v0.1.8.md) | [한국어](../ko/RELEASE-v0.1.8.md) · [Documentation](../README.md)

# 0.1.8 preview — easier subdomain rules

Browsers now has an Add address input and an explicit Include subdomains checkbox, off by default. Enter console.example.com to permit that host, or enter example.com with the checkbox on to add both example.com and *.example.com. The generated entries remain visible in the list and require Save settings. Existing rules, monitoring switches and private local settings are retained.

The helper keeps path, query, scheme and port constraints. Entering console.example.com does not infer its parent or sibling sites. Lookalike hosts remain excluded; IP/localhost entries are added individually. The browser extension and authenticated bridge use the existing rule format, without new permissions or an automatic allow-all rule. See [examples](BROWSERS.md) and [validation](VALIDATION.md).

Quit the previous tray app, extract the complete new ZIP and run its Pawzura.exe. The ZIP includes clean defaults and bilingual guides, including the recently added small-app development rules. No model or browser extension needs an additional permission for this UI change.
