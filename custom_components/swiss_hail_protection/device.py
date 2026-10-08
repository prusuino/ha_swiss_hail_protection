"""Shared device info and entity-id helpers for all platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_DEVICE_ID, DOMAIN
from .localization import t

CONFIGURATION_URL = "https://meteo.netitservices.com"


def entry_suffix(entry: ConfigEntry) -> str:
    """Short per-entry discriminator for suggested entity ids: the last four
    characters of the config entry id, lower-cased (entry ids are ULIDs, so
    the tail is random and stays fixed for the life of the entry).

    A second entry (a second registered device, say) would otherwise suggest
    the very same object ids, which Home Assistant resolves by appending _2
    to whichever entry loads second. The suffix only affects the id suggested
    on first creation; existing entities keep the ids they have."""
    return entry.entry_id[-4:].lower()


def device_info(hass: HomeAssistant, entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=t("device_name", hass, device_id=entry.data.get(CONF_DEVICE_ID, "")),
        manufacturer=t("manufacturer", hass),
        model=t("model", hass),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=CONFIGURATION_URL,
    )
