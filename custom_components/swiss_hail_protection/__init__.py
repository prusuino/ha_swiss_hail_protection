"""Swiss Hail Protection integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, DOMAIN, SOURCE_VKF
from .coordinator import create_coordinator
from .device import entry_source, entry_title

PLATFORMS = ["binary_sensor", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Before 1.1.2 the title of a VKF entry carried the device serial.
    serial = entry.data.get(CONF_DEVICE_ID)
    if entry_source(entry) == SOURCE_VKF and serial and serial in entry.title:
        hass.config_entries.async_update_entry(
            entry, title=entry_title(hass, SOURCE_VKF, entry.data)
        )

    coordinator = create_coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
