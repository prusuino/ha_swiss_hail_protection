# Changelog

## 1.0.0 — 2026-10-08

Initial release.

- Polls the VKF hail-warning service «Hagelschutz – einfach automatisch» (REST interface of `meteo.netitservices.com`) every 120 seconds, the interval the VKF specification requires, for one registered device.
- `binary_sensor.swiss_hail_protection_alarm_<id>` (device class *safety*): `on` while the service signals hail, for a real warning and for a test alarm alike — the zero / non-zero handling the VKF specification advises. Attributes `state_code` and `test_alarm`.
- `sensor.swiss_hail_protection_status_<id>` (enum): `no_hail`, `hail` or `test_alarm`, translated in the frontend. Attribute `state_code`.
- Setup via the UI with the device serial and interface id; the service is polled once to verify them, so a wrong serial shows up in the form instead of as a failed setup. Reauthentication when the service stops recognising the serial, and reconfiguration to change serial or interface id.
- Both entities become unavailable while the service is unreachable or refuses the poll, and come back on the next successful refresh. An undocumented state code is treated as an active warning and logged once.
- The device serial is never logged: a failed request is recorded with its error type or HTTP status and the service's exception name only.
- German, English, French and Italian for the config flow, entity names and states.
