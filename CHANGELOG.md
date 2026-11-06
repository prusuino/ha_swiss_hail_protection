# Changelog

## 1.3.1 — 2026-11-06

- Fixed: the manifest now declares the dependency on Home Assistant's `http` component, which serves the dashboard strategy file. Nothing changes at runtime (`http` is always loaded); it is what Home Assistant's manifest validation (hassfest) requires.

## 1.3.0 — 2026-11-06

- **New: triggers and conditions in the automation editor** (Home Assistant 2026.10 / 2026.11 or newer). *Hail alarm started*, *Hail alarm cleared* and *VKF test alarm started* appear in the trigger list, *Hail alarm is active* and *Hail alarm is not active* in the condition list, in all four languages. Each targets the integration's own entities, so a device or area target never picks up an unrelated safety sensor; the usual *for* and behaviour options apply. On older versions nothing changes: the entries are simply not offered.
- **New: a blueprint, *raise blinds on hail alarm*.** One-click import from the README: raises the selected covers when the alarm starts, stores their positions in a snapshot scene and restores them once the alarm has been over for a configurable hold time (default 15 minutes); a returning alarm does not overwrite the snapshot. Two action fields take your own steps for the alarm and the all-clear.
- **New: a dashboard strategy.** The integration now serves `/swiss_hail_protection_files/swiss-hail-protection-dashboard.js`, a recipe Home Assistant renders in the browser: one section per config entry with the alarm and the status, and for a MeteoSwiss radar entry the probability of hail, the hail size, the radar time and a six-hour history of the probability — generated live from your config entries, nothing is written into your dashboard configuration. Register the file once as a Lovelace resource (JavaScript module), then pick *Swiss Hail Protection* under **Settings → Dashboards → + Add dashboard**, or fill a single view of your own dashboard with `custom:swiss-hail-protection`; `title` and `max_columns` can be set under `strategy:`. The README has the details.

## 1.2.0 — 2026-11-05

- **Changed: a publication gap at MeteoSwiss no longer fails the setup.** When MeteoSwiss has published no hail product for the last 20 minutes while Home Assistant starts (it happened for several hours on 5 November), the MeteoSwiss entry used to end up as *failed to set up* and be retried. It now loads, its values are unavailable as before, a warning names the gap, and the alarm resumes with the next product. A service that cannot be reached at all is still retried the usual way.
- **Changed: the radar time sensor stays readable during a gap.** All other values of a MeteoSwiss entry go unavailable while no current product exists; the diagnostic `radar_time` sensor keeps the time of the newest product, so its age shows how long the gap is.
- **Changed: the product file names found to work are remembered.** MeteoSwiss renamed the files again on 3 and 4 November (`rl` → `tl` → `vl`); the discovery from the day's catalog entry caught it, but every start began with the stale built-in names, four misses and a catalog request. The names that worked are now kept with the config entry and used from the next start; the built-in names remain the fallback for a fresh entry.
- **Fixed: the catalog lookup was on the edge of its timeout.** The STAC catalog regularly takes about 30 seconds to answer, which was exactly the request timeout; the lookup now allows 90 seconds, and when today's catalog entry does not exist yet (right after midnight UTC) yesterday's is consulted instead of reporting a connection error.
- No changes for VKF entries, to entity ids or to the alarm logic.

## 1.1.2 — 2026-10-29

- **Privacy: the VKF device serial no longer appears in the entry title and the device name.** The serial is the service's only credential, but the title and device name were *Hail Protection VKF <serial>*, so it showed up on the integration and device pages and in any log line or diagnostics file that names the entry. Both are now just *Hail Protection VKF* (in the Home Assistant language); existing entries are renamed on the first start after the update, a device name you set yourself is kept.
- The serial field in the setup, reauthentication and reconfiguration forms is masked, and the stored serial is no longer pre-filled when you reconfigure an entry — enter it again (only the interface id is pre-filled).
- The radius check now matches the error text and the documentation: 1 to 50 km.
- Verified against a live VKF registration, including the VKF function test with a test alarm from the portal.

## 1.1.1 — 2026-10-24

- **Fix: MeteoSwiss setup failed with "The data service could not be reached"** (#1). Two causes: MeteoSwiss renamed the hail product files (suffix `vl` → `rl`, e.g. `bzc…rl.845.h5`), and the data server reports a missing file with HTTP 403 rather than 404, which the integration took for a connection problem — so the built-in file-name discovery never got a chance to run. Missing files are now recognised by either status, and the default names are the current ones; the discovery from the STAC listing remains as the fallback for the next rename. Existing MeteoSwiss entries recover on their own after the update.

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
