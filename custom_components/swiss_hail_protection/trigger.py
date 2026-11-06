"""Triggers for Swiss Hail Protection.

Lets an automation start on "Hail alarm started" picked from the automation
editor's trigger list, instead of a state trigger on the alarm entity. Each
trigger targets the integration's own entities: a target that expands to
other entities (an area, say) is narrowed to the ones this integration
created, so a hail trigger never fires on an unrelated safety sensor.

The trigger platform API arrived in Home Assistant 2026.10. On an older
version the module still imports, but offers no triggers: the integration
keeps working, the editor just does not list them.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, STATUS_TEST_ALARM

try:
    from homeassistant.helpers.automation import DomainSpec
    from homeassistant.helpers.trigger import Trigger, make_entity_target_state_trigger
except ImportError:  # Home Assistant before 2026.10: no trigger platform API
    TRIGGERS: dict = {}
else:
    ALARM_DOMAIN_SPECS = {
        BINARY_SENSOR_DOMAIN: DomainSpec(device_class=BinarySensorDeviceClass.SAFETY),
    }
    STATUS_DOMAIN_SPECS = {
        SENSOR_DOMAIN: DomainSpec(device_class=SensorDeviceClass.ENUM),
    }

    def _own_entities(hass: HomeAssistant, entities: set[str]) -> set[str]:
        """Keep only entities created by this integration."""
        registry = er.async_get(hass)
        return {
            entity_id
            for entity_id in entities
            if (entry := registry.async_get(entity_id)) is not None
            and entry.platform == DOMAIN
        }

    class _AlarmStarted(make_entity_target_state_trigger(ALARM_DOMAIN_SPECS, STATE_ON)):
        """The alarm entity switches to on (real warning or test alarm)."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _AlarmCleared(make_entity_target_state_trigger(ALARM_DOMAIN_SPECS, STATE_OFF)):
        """The alarm entity switches to off."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _TestAlarmStarted(
        make_entity_target_state_trigger(STATUS_DOMAIN_SPECS, STATUS_TEST_ALARM)
    ):
        """The status entity switches to test_alarm (VKF function test)."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    TRIGGERS: dict[str, type[Trigger]] = {
        "alarm_started": _AlarmStarted,
        "alarm_cleared": _AlarmCleared,
        "test_alarm_started": _TestAlarmStarted,
    }


async def async_get_triggers(hass: HomeAssistant) -> dict:
    """Return the triggers of this integration."""
    return TRIGGERS
