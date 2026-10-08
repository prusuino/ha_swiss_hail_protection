# Changelog

## 1.1.0 — 2026-10-08

- **New: a second source, the MeteoSwiss hail radar.** When adding the integration you now choose between the VKF hail-warning signal (registered device, as before) and the open-data hail radar products of MeteoSwiss — probability of hail (POH) and maximum expected severe hail size (MESHS) on the 1 km Swiss radar composite, published every five minutes. The radar source needs no registration: you enter a location (your home by default), a radius (default 10 km, up to 50 km) and an alarm threshold (default 80 % probability of hail), and the alarm switches on while any cell within the radius reaches the threshold. Nothing about the location leaves your instance — one file covers all of Switzerland, and the evaluation runs locally.
- **Same alarm for both sources:** `binary_sensor.swiss_hail_protection_alarm_<id>` and `sensor.swiss_hail_protection_status_<id>` exist for every entry, so an automation does not care where the signal comes from, and both sources can run side by side as separate entries. The binary sensor carries a `source` attribute.
- New for MeteoSwiss entries: `sensor.swiss_hail_protection_probability_<id>` (highest POH within the radius, %, with `poh_home`, `hail_cells` and `nearest_hail_km` as attributes), `sensor.swiss_hail_protection_hail_size_<id>` (largest MESHS within the radius, mm) and the diagnostic `sensor.swiss_hail_protection_radar_time_<id>` (nominal time of the product). The status sensor gains the value `off_season` for October to March, when MeteoSwiss does not compute the products.
- The radar files are decoded with `pyfive`, a pure-Python HDF5 reader (new requirement, installed automatically together with NumPy); no HDF5 system library is needed. The newest available product is fetched by name; if MeteoSwiss ever changes the file-name pattern, the integration discovers the current one from the day's STAC listing.
- Reconfigure now covers both sources (serial and interface id, or location, radius and threshold). Reauthentication remains a VKF-only step.
- The integration's name is now *Swiss Hail Protection (VKF / MeteoSwiss)*. Entries created with 1.0.0 are treated as VKF entries; nothing to do on upgrade.

## 1.0.0 — 2026-10-08

Initial release.

- Polls the VKF hail-warning service «Hagelschutz – einfach automatisch» (REST interface of `meteo.netitservices.com`) every 120 seconds, the interval the VKF specification requires, for one registered device.
- `binary_sensor.swiss_hail_protection_alarm_<id>` (device class *safety*): `on` while the service signals hail, for a real warning and for a test alarm alike — the zero / non-zero handling the VKF specification advises. Attributes `state_code` and `test_alarm`.
- `sensor.swiss_hail_protection_status_<id>` (enum): `no_hail`, `hail` or `test_alarm`, translated in the frontend. Attribute `state_code`.
- Setup via the UI with the device serial and interface id; the service is polled once to verify them, so a wrong serial shows up in the form instead of as a failed setup. Reauthentication when the service stops recognising the serial, and reconfiguration to change serial or interface id.
- Both entities become unavailable while the service is unreachable or refuses the poll, and come back on the next successful refresh. An undocumented state code is treated as an active warning and logged once.
- The device serial is never logged: a failed request is recorded with its error type or HTTP status and the service's exception name only.
- German, English, French and Italian for the config flow, entity names and states.
