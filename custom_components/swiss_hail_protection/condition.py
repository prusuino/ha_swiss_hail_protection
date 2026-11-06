"""Conditions for Swiss Hail Protection.

"Hail alarm is active" and "Hail alarm is not active" for the automation
editor's condition list, so other blind automations can stand back while a
warning is on without a state condition on a specific entity. As with the
triggers, a target that expands to other entities is narrowed to the ones
this integration created.

The condition platform API arrived in Home Assistant 2026.11. On an older
version the module still imports, but offers no conditions.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

try:
    from homeassistant.helpers.automation import DomainSpec
    from homeassistant.helpers.condition import Condition, make_entity_state_condition
except ImportError:  # Home Assistant before 2026.11: no condition platform API
    CONDITIONS: dict = {}
else:
    ALARM_DOMAIN_SPECS = {
        BINARY_SENSOR_DOMAIN: DomainSpec(device_class=BinarySensorDeviceClass.SAFETY),
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

    class _IsAlarmActive(make_entity_state_condition(ALARM_DOMAIN_SPECS, STATE_ON)):
        """The alarm entity is on."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _IsAlarmInactive(make_entity_state_condition(ALARM_DOMAIN_SPECS, STATE_OFF)):
        """The alarm entity is off."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    CONDITIONS: dict[str, type[Condition]] = {
        "is_alarm_active": _IsAlarmActive,
        "is_alarm_inactive": _IsAlarmInactive,
    }


async def async_get_conditions(hass: HomeAssistant) -> dict:
    """Return the conditions of this integration."""
    return CONDITIONS
