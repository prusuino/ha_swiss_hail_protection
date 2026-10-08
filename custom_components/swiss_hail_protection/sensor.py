"""Sensors: the status for both sources, plus the radar values for MeteoSwiss."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCE_METEOSWISS, STATUS_OPTIONS
from .coordinator import HailCoordinator
from .device import attribution, device_info, entry_source, entry_suffix
from .localization import t


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HailCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [HailStatusSensor(hass, coordinator, entry)]
    if entry_source(entry) == SOURCE_METEOSWISS:
        entities += [
            HailProbabilitySensor(hass, coordinator, entry),
            HailSizeSensor(hass, coordinator, entry),
            RadarTimeSensor(hass, coordinator, entry),
        ]
    async_add_entities(entities)


class _HailSensor(CoordinatorEntity[HailCoordinator], SensorEntity):
    """Common wiring: name, unique id, device, attribution, suggested entity id."""

    _attr_has_entity_name = False
    name_key: str
    id_part: str

    def __init__(
        self, hass: HomeAssistant, coordinator: HailCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = t(self.name_key, hass)
        self._attr_unique_id = f"{entry.entry_id}_{self.id_part}"
        self._attr_device_info = device_info(hass, entry)
        self._attr_attribution = attribution(entry)
        # Suggested id only (see entry_suffix): existing entities keep theirs.
        self.entity_id = f"sensor.{DOMAIN}_{self.id_part}_{entry_suffix(entry)}"


class HailStatusSensor(_HailSensor):
    """no_hail / hail / test_alarm / off_season, translated by the frontend.

    Automations should trigger on the binary sensor instead: it is on for
    both VKF hail cases, as the specification advises, and for any state
    code a future API version might add. This sensor is for display and
    for the rare case where a test alarm should be told apart from real hail.
    """

    name_key = "status_sensor_name"
    id_part = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_translation_key = "hail_status"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        return data.status if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if not data:
            return {}
        if entry_source(self._entry) == SOURCE_METEOSWISS:
            return {"radar_time": data.radar_time}
        return {"state_code": data.state_code}


class HailProbabilitySensor(_HailSensor):
    """Highest probability of hail (POH) within the radius, in percent."""

    name_key = "probability_sensor_name"
    id_part = "probability"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "hail_probability"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.poh_max if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "poh_home": data.poh_home,
            "hail_cells": data.hail_cells,
            "nearest_hail_km": data.nearest_hail_km,
            "radar_time": data.radar_time,
        }


class HailSizeSensor(_HailSensor):
    """Largest expected severe hail size (MESHS) within the radius, in millimetres."""

    name_key = "size_sensor_name"
    id_part = "hail_size"
    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "hail_size"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.meshs_max if data else None


class RadarTimeSensor(_HailSensor):
    """Nominal time of the radar product the values are based on."""

    name_key = "radar_time_sensor_name"
    id_part = "radar_time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "radar_time"

    @property
    def native_value(self) -> datetime | None:
        data = self.coordinator.data
        return data.radar_time if data else None
