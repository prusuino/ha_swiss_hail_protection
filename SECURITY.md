# Security Policy

## Supported Versions

Only the latest release is supported. Please update to the latest version before reporting an issue.

## Reporting a Vulnerability

This integration reads one value from the VKF hail-warning service over HTTPS. It has no write access to any external system and does not use the service's error-report endpoint.

**What it sends:** with every refresh (every 120 seconds) and once during setup, reauthentication or reconfiguration, the configured device serial (`deviceId`, in the URL path) and interface id (`hwtypeId`, as a query parameter) go to `https://meteo.netitservices.com/api/v1/devices/<deviceId>/poll` over TLS. Nothing else leaves your instance — no coordinates, no account data, no cookies.

**The device serial is the only credential.** The VKF service has no password or token: whoever knows a registered serial and its interface id can read that device's hail state (nothing more — the interface is read-only). Treat the serial accordingly: it is stored in Home Assistant's `.storage` with the other config entries, it is shown only in the config form you fill in yourself, and it is never written to the log — a failed request is logged with its error type or HTTP status and the service's exception name, not with the URL.

If you believe you have found a security issue (for example in how the response is parsed or how entities are exposed), please report it privately via [GitHub Security Advisories](../../security/advisories/new) rather than opening a public issue.

For anything that is not security-sensitive (bugs, feature requests), please use the regular [Issues](../../issues) tab instead.
