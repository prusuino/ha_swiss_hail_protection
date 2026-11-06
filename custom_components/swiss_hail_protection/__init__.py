"""Swiss Hail Protection integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_DEVICE_ID, DOMAIN, SOURCE_VKF
from .coordinator import MeteoSwissCoordinator, MeteoSwissNoCurrentData, create_coordinator
from .device import entry_source, entry_title
from .frontend import async_serve_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Before 1.1.2 the title of a VKF entry carried the device serial.
    serial = entry.data.get(CONF_DEVICE_ID)
    if entry_source(entry) == SOURCE_VKF and serial and serial in entry.title:
        hass.config_entries.async_update_entry(
            entry, title=entry_title(hass, SOURCE_VKF, entry.data)
        )

    coordinator = create_coordinator(hass, entry)
    if isinstance(coordinator, MeteoSwissCoordinator):
        # A publication gap at MeteoSwiss is not a reason to fail the setup: the
        # entities stay unavailable and recover with the next product. Anything
        # else (service unreachable, decode error) is retried the usual way.
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            if not isinstance(coordinator.last_exception, MeteoSwissNoCurrentData):
                raise ConfigEntryNotReady(str(coordinator.last_exception))
            _LOGGER.warning(
                "%s: MeteoSwiss has published no hail product for the recent slots; "
                "the entities stay unavailable until one appears",
                entry.title,
            )
    else:
        await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_serve_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
