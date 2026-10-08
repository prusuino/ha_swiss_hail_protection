"""Alarm binary sensor: on while the configured source signals hail."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_POH_THRESHOLD, CONF_RADIUS_KM, DOMAIN, SOURCE_METEOSWISS
from .coordinator import HailCoordinator
from .device import attribution, device_info, entry_source, entry_suffix
from .localization import t


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HailCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HailAlarmBinarySensor(hass, coordinator, entry)])


class HailAlarmBinarySensor(CoordinatorEntity[HailCoordinator], BinarySensorEntity):
    """The signal a blind controller acts on: on = raise the blinds.

    Identical for both sources, so an automation does not care where the
    signal comes from. For the VKF signal it follows the specification's
    advice to treat the state as zero / non-zero, so a test alarm switches
    it on exactly like real hail — that is what the VKF function test
    expects of the building. For the MeteoSwiss radar it is on while the
    probability of hail within the radius reaches the configured threshold.
    """

    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_translation_key = "hail_alarm"

    def __init__(
        self, hass: HomeAssistant, coordinator: HailCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = t("alarm_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_alarm"
        self._attr_device_info = device_info(hass, entry)
        self._attr_attribution = attribution(entry)
        # Suggested id only (see entry_suffix): existing entities keep theirs.
        self.entity_id = f"binary_sensor.{DOMAIN}_alarm_{entry_suffix(entry)}"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.alarm if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if not data:
            return {}
        if entry_source(self._entry) == SOURCE_METEOSWISS:
            return {
                "source": SOURCE_METEOSWISS,
                "radar_time": data.radar_time,
                "poh_max": data.poh_max,
                "poh_home": data.poh_home,
                "meshs_max": data.meshs_max,
                "hail_cells": data.hail_cells,
                "nearest_hail_km": data.nearest_hail_km,
                "radius_km": self._entry.data.get(CONF_RADIUS_KM),
                "poh_threshold": self._entry.data.get(CONF_POH_THRESHOLD),
            }
        return {
            "source": entry_source(self._entry),
            "state_code": data.state_code,
            "test_alarm": data.test_alarm,
        }
