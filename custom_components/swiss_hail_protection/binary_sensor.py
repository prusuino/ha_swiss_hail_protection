"""Alarm binary sensor: on while the VKF service signals hail (real or test)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import HailCoordinator
from .device import device_info, entry_suffix
from .localization import t


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HailCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HailAlarmBinarySensor(hass, coordinator, entry)])


class HailAlarmBinarySensor(CoordinatorEntity[HailCoordinator], BinarySensorEntity):
    """The signal a blind controller acts on: on = raise the blinds.

    Follows the VKF specification's advice to treat the state as zero /
    non-zero, so a test alarm switches it on exactly like real hail — that is
    what the VKF function test (Funktionskontrolle) expects of the building.
    The test_alarm attribute tells the two apart for notifications.
    """

    _attr_has_entity_name = False
    _attr_attribution = ATTRIBUTION
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_translation_key = "hail_alarm"

    def __init__(
        self, hass: HomeAssistant, coordinator: HailCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = t("alarm_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_alarm"
        self._attr_device_info = device_info(hass, entry)
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
        return {"state_code": data.state_code, "test_alarm": data.test_alarm}
