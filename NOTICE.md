# Data Sources & Attribution

## VKF hail-warning signal

The VKF source reads, at runtime, the hail-warning signal of **«Hagelschutz – einfach automatisch»**, the hail-warning system of the **Association of Cantonal Fire Insurers (VKF / AEAI / AICAA)**, developed together with SRF Meteo and operated by **NetITServices** (`meteo.netitservices.com`).

The signal is not public: it is only available for a device (a VKF signal box or a building control system) that the owner has registered with the VKF. Using the signal is subject to the terms the VKF sets out at registration; this integration does not change them, it merely polls the documented REST interface on your behalf with the identifiers the VKF issued to you.

Entities of a VKF entry carry Home Assistant's `attribution` attribute *Signal: VKF hail-warning service (Hagelschutz - einfach automatisch)*, which Home Assistant shows in the entity's "More info" dialog.

This integration is not a replacement for the VKF signal box, and completing the VKF function test and acceptance protocol remains the building owner's responsibility.

Official site: https://www.hagelschutz-einfach-automatisch.ch/

## MeteoSwiss hail radar products

The MeteoSwiss source reads, at runtime, the radar products **POH** (probability of hail) and **MESHS** (maximum expected severe hail size) that the **Federal Office of Meteorology and Climatology MeteoSwiss** publishes as Open Government Data through the Federal Spatial Data Infrastructure (`data.geo.admin.ch`, collection `ch.meteoschweiz.ogd-radar-hail`).

MeteoSwiss open data may be used freely with attribution; the required statement of source is **Source: MeteoSwiss**. Entities of a MeteoSwiss entry carry exactly that text as their `attribution` attribute. If you build dashboards, automations or republish these values elsewhere, please keep that attribution visible or add your own equivalent notice.

The products are computed from 1 April to 30 September only. They are radar-based estimates of hail at the ground, not measurements and not a forecast; MeteoSwiss documents their methods and limits at https://opendatadocs.meteoswiss.ch/d-radar-data/d3-hail-radar-products.

## Non-affiliation

This integration is unofficial and not affiliated with, endorsed by, or supported by the VKF, SRF Meteo, NetITServices or MeteoSwiss. The VKF, AEAI, AICAA and MeteoSwiss names are used only to identify the data sources.
