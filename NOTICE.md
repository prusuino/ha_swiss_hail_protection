# Data Source & Attribution

This integration reads, at runtime, the hail-warning signal of **«Hagelschutz – einfach automatisch»**, the hail-warning system of the **Association of Cantonal Fire Insurers (VKF / AEAI / AICAA)**, developed together with SRF Meteo and operated by **NetITServices** (`meteo.netitservices.com`).

The signal is not public: it is only available for a device (a VKF signal box or a building control system) that the owner has registered with the VKF. Using the signal is subject to the terms the VKF sets out at registration; this integration does not change them, it merely polls the documented REST interface on your behalf with the identifiers the VKF issued to you.

Every entity this integration creates carries Home Assistant's `attribution` attribute (*Signal: VKF hail-warning service (Hagelschutz - einfach automatisch)*), which Home Assistant shows in the entity's "More info" dialog.

This integration is unofficial and not affiliated with, endorsed by, or supported by the VKF, SRF Meteo or NetITServices. It is not a replacement for the VKF signal box, and completing the VKF function test and acceptance protocol remains the building owner's responsibility.

Official site: https://www.hagelschutz-einfach-automatisch.ch/

The VKF, AEAI and AICAA names are used only to identify the data source.
