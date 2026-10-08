# Security Policy

## Supported Versions

Only the latest release is supported. Please update to the latest version before reporting an issue.

## Reporting a Vulnerability

This integration only reads from two Swiss data services over HTTPS. It has no write access to any external system and does not use the VKF error-report endpoint.

**VKF source — what it sends:** with every refresh (every 120 seconds) and once during setup, reauthentication or reconfiguration, the configured device serial (`deviceId`, in the URL path) and interface id (`hwtypeId`, as a query parameter) go to `https://meteo.netitservices.com/api/v1/devices/<deviceId>/poll` over TLS. Nothing else leaves your instance — no coordinates, no account data, no cookies.

**The device serial is the only credential** of the VKF service. There is no password or token: whoever knows a registered serial and its interface id can read that device's hail state (nothing more — the interface is read-only). Treat the serial accordingly: it is stored in Home Assistant's `.storage` with the other config entries, it is shown only in the config form you fill in yourself, and it is never written to the log — a failed request is logged with its error type or HTTP status and the service's exception name, not with the URL.

**MeteoSwiss source — what it sends:** every five minutes (and once during setup or reconfiguration) the integration downloads the newest hail radar products from `https://data.geo.admin.ch/ch.meteoschweiz.ogd-radar-hail/<day>/<file>` over TLS, and, only if the file names stop matching the built-in pattern, reads the day's listing from `https://data.geo.admin.ch/api/stac/v1/`. The file names contain the product and the time, nothing else. Your coordinates, radius and threshold never leave your instance: one file covers all of Switzerland, and the evaluation around your location runs on your own machine. No credentials are involved.

**Decoding downloaded files:** the radar files are parsed with [pyfive](https://github.com/jjhelmus/pyfive), a pure-Python HDF5 reader, in a worker thread. A file that does not decode to the expected 640 × 710 grid is rejected and the entities go unavailable; nothing from the file is executed or written to disk.

If you believe you have found a security issue (for example in how a response is parsed or how entities are exposed), please report it privately via [GitHub Security Advisories](../../security/advisories/new) rather than opening a public issue.

For anything that is not security-sensitive (bugs, feature requests), please use the regular [Issues](../../issues) tab instead.
