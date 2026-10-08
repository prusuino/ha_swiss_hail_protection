# Swiss Hail Protection (VKF)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
<a href="https://www.buymeacoffee.com/prusuino"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="20"></a>

![Swiss Hail Protection](readme_header.png)

A Home Assistant custom integration that brings the hail-warning signal of **«Hagelschutz – einfach automatisch»**, the hail-protection system of the Swiss cantonal building insurers (VKF / AEAI / AICAA), into Home Assistant — so your blinds can be raised before the hail arrives, by your own automations.

## Background

Hail is the single most expensive natural hazard for buildings in Switzerland, and most of the damage is to blinds and shutters. The cantonal building insurers therefore run **«Hagelschutz – einfach automatisch»**, developed with SRF Meteo: a nowcast predicts hail cells for every registered building, and a warning signal tells the building to raise its blinds in time. When the danger has passed, the signal is cleared and the blinds may return to their previous position.

Traditionally the signal reaches the building through a **VKF signal box**, a small device with a relay that the blind controller is wired to. Building control systems that can talk HTTP do not need the box: the VKF documents a **REST interface** that delivers the same signal, and that is what this integration polls.

The integration does one thing: it asks the service every 120 seconds — the interval the VKF specification requires, and the cadence of the signal box — whether a hail warning is active, and exposes the answer. What the house does with it is entirely up to your automations.

## Getting access: the device serial and interface id

The service is **not public**. It only answers for a device the VKF has registered, and the two values the integration asks for — the **device serial (`deviceId`)** and the **interface id (`hwtypeId`)** — are issued by the VKF at registration. You cannot pick them yourself, and the service answers *device not found* for anything it does not know. This is how you get them:

1. **Apply through the official site.** Fill in the interest form at [hagelschutz-einfach-automatisch.ch](https://www.hagelschutz-einfach-automatisch.ch/elektriker-architekten-planer/produkt/ich-habe-interesse.html). Your request goes to the cantonal building insurer responsible for your building, which also checks the financing — the signal box and the platform are free of charge, paid for by the cantonal building insurers; you only carry the internet connection and, for a box, the electrician.
2. **Say that you will use the REST interface.** The default delivery is a VKF signal box, a small device with a relay that an electrician wires to the blind controller. Home Assistant does not need it: state in the application that your building control system fetches the signal directly over the **METEO REST API** («Schnittstelle»), as described in the VKF interface sheet. The VKF then registers your installation as a building control system without a box.
3. **What you receive:** a login for the operator portal [meteo.netitservices.com](https://meteo.netitservices.com) and the completed **interface sheet** with the two fields *MAC-Adresse (deviceID)* and *Schnittstelle (hwtypeId)*. Those are the values you enter in the integration's setup dialog — nothing else is needed.
4. **If you already own a signal box,** its MAC address is the device serial; the interface id for the box is on the same sheet. The integration can poll alongside the box, so Home Assistant sees the same signal the relay switches.
5. **Finish the VKF procedure.** After setup, run the function test from the portal (switch on *Testalarm*, see [Function test](#function-test)), activate the alarm chain and return the signed acceptance protocol to the VKF — that part is yours, not the integration's.

Note that the VKF designed the system primarily for larger industrial, commercial and office buildings; owners of smaller buildings can apply too, and the VKF publishes a separate information sheet for them.

## What it provides

| Entity | Description |
|---|---|
| `binary_sensor.swiss_hail_protection_alarm_<id>` | **The signal to act on.** `on` while the service signals hail — for a real warning and for a test alarm alike, exactly as the VKF signal box closes its relay in both cases. Device class *safety*. Attributes: `state_code` (the raw value, 0/1/2) and `test_alarm` (`true` during a test alarm). |
| `sensor.swiss_hail_protection_status_<id>` | The state as a readable value: `no_hail`, `hail` or `test_alarm` (translated in the frontend). For dashboards and for telling a test alarm apart in a notification — automations should trigger on the binary sensor. Attribute: `state_code`. |

`<id>` is a four-character tag of the config entry (the last four characters of its id, lower-cased), so a second registered device gets distinct entity ids. These are the ids suggested when an entity is first created; any entity can be renamed in its settings.

Both entities become **unavailable** while the service is unreachable or refuses the poll, and come back on the next successful refresh — they never show a stale value. The VKF portal, for its part, notifies the registered contacts when a device has not polled for an hour (the *Alarmkette*), so an outage on either side is noticed.

## Language

Entity names, the device name/manufacturer/model, the config flow and the sensor states adapt to your Home Assistant language — German, English, French and Italian are supported, with English as the fallback.

## Installation

### HACS (recommended)

1. Open **HACS**, search for **"Swiss Hail Protection"** and download it — or use the button, which opens the integration directly in your HACS:

   [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=prusuino&repository=ha_swiss_hail_protection&category=integration)

2. Restart Home Assistant.

Until the integration shows up in the HACS search, the button above adds it as a custom repository.

### Manual

1. Copy the `custom_components/swiss_hail_protection` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **"Swiss Hail Protection (VKF)"**.
3. Enter the **device serial** (`deviceId`) and the **interface id** (`hwtypeId`) from your VKF interface sheet (see [Getting access](#getting-access-the-device-serial-and-interface-id)). The serial is letters and digits; the form upper-cases it for you.
4. Submit. The integration polls the service once with the values you entered: an unknown serial, an exhausted quota or an unreachable service shows up right here instead of as a failed setup afterwards.
5. Done. Add the integration again for a second registered device — each instance is independent.

If the service stops recognising the serial later (the VKF reassigned or deactivated the device, say), Home Assistant asks you to **reauthenticate** and you enter the current values. **Reconfigure** on the integration's entry changes the serial or interface id at any time; a changed serial is accepted as long as no other entry uses it.

## Automations

The VKF expects the building to **raise the blinds fully** while the signal is active and to restore them afterwards. A minimal pair of automations:

```yaml
automation:
  - alias: "Hail warning: raise blinds"
    triggers:
      - trigger: state
        entity_id: binary_sensor.swiss_hail_protection_alarm_7f3a
        to: "on"
    actions:
      - action: scene.create
        data:
          scene_id: blinds_before_hail
          snapshot_entities:
            - cover.living_room
            - cover.kitchen
      - action: cover.open_cover
        target:
          entity_id:
            - cover.living_room
            - cover.kitchen

  - alias: "Hail warning cleared: restore blinds"
    triggers:
      - trigger: state
        entity_id: binary_sensor.swiss_hail_protection_alarm_7f3a
        from: "on"
        to: "off"
    actions:
      - action: scene.turn_on
        target:
          entity_id: scene.blinds_before_hail
```

Two things worth building in:

- **Let the warning win.** While the alarm is `on`, your other blind automations (sun shading, wind, schedules) should not lower the blinds again — add a condition on the binary sensor to them, or stop them with the first automation and resume them with the second.
- **Trigger on `on`, not on a status text.** The binary sensor is `on` for a real warning, for a test alarm and for any state the VKF might add in the future. Use the `test_alarm` attribute (or the status sensor) only to word a notification differently — the blinds should move in both cases, that is what the VKF function test checks.

### Function test

The VKF asks every installation to run a **function test** before activating the alarm chain: in the portal at meteo.netitservices.com, switch on the *Testalarm*; within two minutes the binary sensor turns `on` and your blinds should go up; switch the test alarm off and, after the next poll, the sensor turns `off` and the blinds should return. The portal's activity log shows both the delivery and the pick-up of the test alarm. Completing the VKF acceptance protocol is still the owner's job — the integration does not replace it.

## Notes

- **Polling interval.** The service recalculates the hail forecast every five minutes and requires clients to poll every 120 seconds; the integration polls at exactly that interval, and it is not configurable. The service also caps the number of polls per device and day; the 120-second cadence stays within it with room for a few restarts, and if the cap is ever hit the entities go unavailable until the next accepted poll instead of the integration guessing.
- **What leaves your instance:** with every refresh, the device serial (in the URL path) and the interface id (as a query parameter) are sent to `https://meteo.netitservices.com/api/v1/devices/<deviceId>/poll` over HTTPS — nothing else, no coordinates, no account data. The serial is the service's only credential: it is stored with your config entry, never written to the log (a failed request is logged with its error type or HTTP status and the service's exception name, not with the URL), and shown only in the form you fill in yourself. See [SECURITY.md](SECURITY.md).
- **An undocumented state code** (a value other than 0, 1 or 2) is treated as an active warning, following the VKF's advice to read the state as zero / non-zero; the status sensor shows *unknown* for it, and a warning is logged once.
- The integration does not use the service's error-report endpoint; it only reads.
- This integration is unofficial and not affiliated with, endorsed by, or supported by the VKF, SRF Meteo or NetITServices. See [NOTICE.md](NOTICE.md).

## Data source

The hail-warning signal is provided by the VKF's «Hagelschutz – einfach automatisch» service for registered devices only, under the terms you accept at registration — see [NOTICE.md](NOTICE.md). Every entity sets Home Assistant's `attribution` attribute accordingly.

## Disclaimer

This integration is provided **as-is, without any warranty**. The signal is retrieved from a third-party service and may be delayed, incorrect or unavailable, and the integration may stop working if the service changes. **It controls nothing by itself** — what your blinds do is decided by automations you write, so test them, including the VKF function test, before relying on them, and keep in mind that no hail warning is perfect. Do not rely on this integration as your only protection against hail damage. The author(s) accept **no responsibility or liability** for any damage, loss, missed warning or other issues arising from using this integration, whether it stops working, behaves unexpectedly, or never worked correctly for your setup in the first place.

## License

Source code: MIT — see [LICENSE](LICENSE). The hail-warning signal: see [NOTICE.md](NOTICE.md).

## Related integrations

More Home Assistant integrations from the same author:

- [Swiss Public Alerts](https://github.com/prusuino/ha_swiss_public_alerts) — official Swiss public alerts (Alertswiss) with home-location matching
- [Swiss Waters](https://github.com/prusuino/ha_swiss_waters) — live water temperature, water level, discharge and flood danger levels of Swiss rivers and lakes
- [Swiss Earthquakes](https://github.com/prusuino/ha_swiss_earthquakes) — recent Swiss earthquakes on a map (SED)
- [Swiss Avalanche Bulletin](https://github.com/prusuino/ha_swiss_avalanche_bulletin) — the official SLF avalanche bulletin for your location
- [Swiss Charging Stations](https://github.com/prusuino/ha_swiss_charging_stations) — real-time availability and prices of public EV charging stations in Switzerland
- [Austrian Charging Stations](https://github.com/prusuino/ha_austrian_charging_stations) — real-time availability of public EV charging stations in Austria
- [Swiss Transport](https://github.com/prusuino/ha_swiss_transport) — live public-transport departure boards and saved connections
- [Swiss Parking](https://github.com/prusuino/ha_swiss_parking) — live free parking spaces in Swiss cities
- [Swiss Electricity Price](https://github.com/prusuino/ha_swiss_electricity_price) — electricity tariffs of any Swiss grid operator (ElCom)
- [Swiss Solar Reference Price](https://github.com/prusuino/ha_swiss_solar_reference_price) — the Swiss solar reference market price (SFOE)
- [Innoxel Master 3](https://github.com/prusuino/ha_innoxel_master3) — local control of the Innoxel Master 3 home-automation system

## Support

If this integration is useful to you, you can support its development:

<a href="https://www.buymeacoffee.com/prusuino"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="41"></a>
