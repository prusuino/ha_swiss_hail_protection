"""Shared device info and entity-id helpers for all platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    CONF_DEVICE_ID,
    CONF_RADIUS_KM,
    CONF_SOURCE,
    DOMAIN,
    METEOSWISS_ATTRIBUTION,
    SOURCE_METEOSWISS,
    SOURCE_VKF,
    VKF_ATTRIBUTION,
)
from .localization import t

VKF_CONFIGURATION_URL = "https://meteo.netitservices.com"
METEOSWISS_CONFIGURATION_URL = (
    "https://opendatadocs.meteoswiss.ch/d-radar-data/d3-hail-radar-products"
)


def entry_source(entry: ConfigEntry) -> str:
    return entry.data.get(CONF_SOURCE, SOURCE_VKF)


def entry_suffix(entry: ConfigEntry) -> str:
    """Short per-entry discriminator for suggested entity ids: the last four
    characters of the config entry id, lower-cased (entry ids are ULIDs, so
    the tail is random and stays fixed for the life of the entry).

    A second entry (a second device, or the radar next to the VKF signal)
    would otherwise suggest the very same object ids, which Home Assistant
    resolves by appending _2 to whichever entry loads second. The suffix only
    affects the id suggested on first creation; existing entities keep the
    ids they have."""
    return entry.entry_id[-4:].lower()


def display_radius(radius: float | int | None) -> str:
    """The radius without a trailing .0 (the form stores it as a float)."""
    try:
        value = float(radius)
    except (TypeError, ValueError):
        return str(radius)
    return str(int(value)) if value.is_integer() else f"{value:g}"


def attribution(entry: ConfigEntry) -> str:
    return (
        METEOSWISS_ATTRIBUTION
        if entry_source(entry) == SOURCE_METEOSWISS
        else VKF_ATTRIBUTION
    )


def entry_title(hass: HomeAssistant, source: str, data: dict) -> str:
    if source == SOURCE_METEOSWISS:
        return t(
            "meteoswiss_device_name", hass, radius=display_radius(data.get(CONF_RADIUS_KM))
        )
    return t("vkf_device_name", hass, device_id=data.get(CONF_DEVICE_ID, ""))


def device_info(hass: HomeAssistant, entry: ConfigEntry) -> DeviceInfo:
    source = entry_source(entry)
    if source == SOURCE_METEOSWISS:
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry_title(hass, source, entry.data),
            manufacturer=t("meteoswiss_manufacturer", hass),
            model=t("meteoswiss_model", hass),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=METEOSWISS_CONFIGURATION_URL,
        )
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry_title(hass, source, entry.data),
        manufacturer=t("vkf_manufacturer", hass),
        model=t("vkf_model", hass),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=VKF_CONFIGURATION_URL,
    )
