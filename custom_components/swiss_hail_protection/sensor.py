"""Status sensor: the hail-warning state as a readable enum."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, STATUS_OPTIONS
from .coordinator import HailCoordinator
from .device import device_info, entry_suffix
from .localization import t


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HailCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HailStatusSensor(hass, coordinator, entry)])


class HailStatusSensor(CoordinatorEntity[HailCoordinator], SensorEntity):
    """no_hail / hail / test_alarm, translated by the frontend.

    Automations should trigger on the binary sensor instead: it is on for
    both hail cases, as the VKF specification advises, and for any state code
    a future API version might add. This sensor is for display and for the
    rare case where a test alarm should be told apart from real hail.
    """

    _attr_has_entity_name = False
    _attr_attribution = ATTRIBUTION
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_translation_key = "hail_status"

    def __init__(
        self, hass: HomeAssistant, coordinator: HailCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = t("status_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = device_info(hass, entry)
        # Suggested id only (see entry_suffix): existing entities keep theirs.
        self.entity_id = f"sensor.{DOMAIN}_status_{entry_suffix(entry)}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        return data.status if data else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {"state_code": data.state_code} if data else {}
