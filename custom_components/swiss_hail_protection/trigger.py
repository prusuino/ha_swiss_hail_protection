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
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
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

    _GAP = (STATE_UNAVAILABLE, STATE_UNKNOWN)

    class _AcrossGaps:
        """Lets a target-state trigger see a change that follows a gap.

        The core skips every change out of "unavailable" or "unknown". While
        the source cannot be reached the entities are unavailable, so
        whatever began during the outage would switch an entity from
        unavailable straight to its new state, and the core would not fire.
        Such a change is let through here and judged against the last state
        seen before the gap: it fires when that state was not already the
        target. With nothing known from before the gap, a trigger that
        announces something (`_fire_without_history`) fires, the others
        stay quiet. The core asks is_valid_state for every state with a
        value and only then is_valid_transition, so the states are
        remembered there.
        """

        _excluded_from_states = frozenset()
        _fire_without_history = False

        def __init__(self, hass: HomeAssistant, config) -> None:
            super().__init__(hass, config)
            self._last_state: dict[str, str] = {}
            self._previous_state: dict[str, str | None] = {}

        def entity_filter(self, entities: set[str]) -> set[str]:
            # Start from what the entities show now, so that a gap right
            # after the automation starts is judged against a known state.
            kept = super().entity_filter(entities)
            for entity_id in kept:
                state = self._hass.states.get(entity_id)
                if entity_id not in self._last_state and state is not None and state.state not in _GAP:
                    self._last_state[entity_id] = state.state
            return kept

        def is_valid_state(self, state, report_not_triggered) -> bool:
            self._previous_state[state.entity_id] = self._last_state.get(state.entity_id)
            self._last_state[state.entity_id] = state.state
            return super().is_valid_state(state, report_not_triggered)

        def is_valid_transition(self, from_state, to_state) -> bool:
            if from_state.state not in _GAP:
                return super().is_valid_transition(from_state, to_state)
            before = self._previous_state.get(to_state.entity_id)
            if before is None:
                return self._fire_without_history
            return before not in self._to_states

    class _AlarmStarted(_AcrossGaps, make_entity_target_state_trigger(ALARM_DOMAIN_SPECS, STATE_ON)):
        """The alarm entity switches to on (real warning or test alarm).

        After an outage it fires unless the alarm was already on before it;
        with nothing known from before it fires, because a hail alarm is worth
        one notification too many rather than one too few."""

        _fire_without_history = True

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _AlarmCleared(_AcrossGaps, make_entity_target_state_trigger(ALARM_DOMAIN_SPECS, STATE_OFF)):
        """The alarm entity switches to off; after an outage only when it was on
        before it."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _TestAlarmStarted(
        _AcrossGaps, make_entity_target_state_trigger(STATUS_DOMAIN_SPECS, STATUS_TEST_ALARM)
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
