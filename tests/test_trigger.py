"""The alarm triggers with real automations, on registered entities whose
state is set by hand: a new alarm, an alarm that begins during an outage,
one that was already on, the all-clear, the VKF test alarm."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.swiss_hail_protection import trigger
from custom_components.swiss_hail_protection.const import DOMAIN, STATUS_TEST_ALARM


def _entity(hass: HomeAssistant, domain: str, device_class: str, platform: str = DOMAIN, name: str = "hail") -> str:
    return er.async_get(hass).async_get_or_create(domain, platform, f"entry_{name}", suggested_object_id=name, original_device_class=device_class).entity_id


def _set(hass: HomeAssistant, entity_id: str, state: str) -> None:
    hass.states.async_set(entity_id, state, {"device_class": "safety" if entity_id.startswith("binary_sensor.") else "enum"})


async def _automation(hass: HomeAssistant, name: str, entity_ids) -> list:
    calls = async_mock_service(hass, "test", name)
    assert await async_setup_component(hass, "automation", {"automation": {
        "alias": name, "trigger": {"trigger": f"swiss_hail_protection.{name}", "target": {"entity_id": entity_ids}},
        "action": {"action": f"test.{name}"},
    }})
    await hass.async_block_till_done()
    assert hass.states.get(f"automation.{name}") is not None, "the automation was rejected"
    return calls


async def _play(hass: HomeAssistant, entity_id: str, *states: str) -> None:
    for state in states:
        _set(hass, entity_id, state)
        await hass.async_block_till_done()


async def test_alarm_started_and_other_integrations_are_ignored(hass: HomeAssistant, enable_custom_integrations) -> None:
    assert set(await trigger.async_get_triggers(hass)) == {"alarm_started", "alarm_cleared", "test_alarm_started"}
    alarm = _entity(hass, "binary_sensor", "safety")
    foreign = _entity(hass, "binary_sensor", "safety", "another_integration", "smoke")
    _set(hass, alarm, "off")
    _set(hass, foreign, "off")
    calls = await _automation(hass, "alarm_started", [alarm, foreign])
    await _play(hass, foreign, "on")  # not ours
    assert len(calls) == 0
    await _play(hass, alarm, "on")
    assert len(calls) == 1
    await _play(hass, alarm, "off", "on")
    assert len(calls) == 2


async def test_an_alarm_that_begins_during_an_outage_fires(hass: HomeAssistant, enable_custom_integrations) -> None:
    alarm = _entity(hass, "binary_sensor", "safety")
    _set(hass, alarm, "on")
    calls = await _automation(hass, "alarm_started", alarm)
    await _play(hass, alarm, "off", "unavailable", "on")  # off before the outage, on after it
    assert len(calls) == 1
    await _play(hass, alarm, "unavailable", "on")  # still the same alarm: no second notification
    assert len(calls) == 1
    await _play(hass, alarm, "unknown", "off", "unknown", "on")
    assert len(calls) == 2


async def test_nothing_known_before_the_outage(hass: HomeAssistant, enable_custom_integrations) -> None:
    alarm = _entity(hass, "binary_sensor", "safety")
    _set(hass, alarm, "unavailable")
    started = await _automation(hass, "alarm_started", alarm)
    await _play(hass, alarm, "on")
    assert len(started) == 1  # rather one notification too many than one too few


async def test_alarm_cleared(hass: HomeAssistant, enable_custom_integrations) -> None:
    alarm = _entity(hass, "binary_sensor", "safety")
    _set(hass, alarm, "unavailable")
    calls = await _automation(hass, "alarm_cleared", alarm)
    await _play(hass, alarm, "off")  # nothing known from before: no all-clear
    assert len(calls) == 0
    await _play(hass, alarm, "on", "off")
    assert len(calls) == 1
    await _play(hass, alarm, "on", "unavailable", "off")  # it ended during the outage
    assert len(calls) == 2
    await _play(hass, alarm, "unavailable", "off")
    assert len(calls) == 2


async def test_test_alarm_started(hass: HomeAssistant, enable_custom_integrations) -> None:
    status = _entity(hass, "sensor", "enum", name="hail_status")
    _set(hass, status, "no_hail")
    calls = await _automation(hass, "test_alarm_started", status)
    await _play(hass, status, STATUS_TEST_ALARM)
    assert len(calls) == 1
    await _play(hass, status, "unavailable", STATUS_TEST_ALARM)  # the same test alarm after an outage
    assert len(calls) == 1
    await _play(hass, status, "no_hail", "unavailable", STATUS_TEST_ALARM)
    assert len(calls) == 2
