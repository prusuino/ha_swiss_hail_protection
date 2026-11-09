"""Repair notices: an unreachable VKF service after three failed polls, a
MeteoSwiss publication gap after about an hour, both withdrawn on recovery."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swiss_hail_protection.api import HailApiCommunicationError
from custom_components.swiss_hail_protection.const import (
    CONF_DEVICE_ID,
    CONF_HWTYPE_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POH_THRESHOLD,
    CONF_RADIUS_KM,
    CONF_SOURCE,
    DOMAIN,
    SOURCE_METEOSWISS,
    SOURCE_VKF,
)
from custom_components.swiss_hail_protection.coordinator import MeteoSwissCoordinator, VkfCoordinator
from custom_components.swiss_hail_protection.meteoswiss import MeteoSwissNoDataError, RadarEvaluation

COORD = "custom_components.swiss_hail_protection.coordinator."


def _issue(hass, key, entry):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{key}_{entry.entry_id}")


async def test_vkf_unreachable_after_three_polls(hass: HomeAssistant, enable_custom_integrations) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="A1B2C3D4E5F6", title="VKF", data={CONF_SOURCE: SOURCE_VKF, CONF_DEVICE_ID: "A1B2C3D4E5F6", CONF_HWTYPE_ID: 42})
    entry.add_to_hass(hass)
    coordinator = VkfCoordinator(hass, entry)
    with patch(COORD + "async_poll_state", side_effect=HailApiCommunicationError("timeout")):
        for n in range(3):
            await coordinator.async_refresh()
            assert (_issue(hass, "unreachable", entry) is not None) is (n == 2)
    assert _issue(hass, "unreachable", entry).translation_placeholders == {"host": "meteo.netitservices.com"}
    with patch(COORD + "async_poll_state", return_value=0):
        await coordinator.async_refresh()
    assert coordinator.data.alarm is False
    assert _issue(hass, "unreachable", entry) is None


async def test_meteoswiss_publication_gap_after_an_hour(hass: HomeAssistant, enable_custom_integrations) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="meteoswiss_46.951_7.439_10", title="Radar",
                            data={CONF_SOURCE: SOURCE_METEOSWISS, CONF_LATITUDE: 46.951, CONF_LONGITUDE: 7.439, CONF_RADIUS_KM: 10, CONF_POH_THRESHOLD: 80})
    entry.add_to_hass(hass)
    coordinator = MeteoSwissCoordinator(hass, entry)
    with patch(COORD + "async_fetch_latest_products", side_effect=MeteoSwissNoDataError("gap")):
        for n in range(12):
            await coordinator.async_refresh()
            assert (_issue(hass, "no_products", entry) is not None) is (n == 11), f"after gap {n + 1}"
    assert _issue(hass, "unreachable", entry) is None
    slot = datetime(2026, 7, 15, 14, 35, tzinfo=timezone.utc)
    calm = RadarEvaluation(poh_home=0.0, poh_max=0.0, meshs_max=None, hail_cells=0, nearest_hail_km=None, home_covered=True)
    with (
        patch(COORD + "async_fetch_latest_products", return_value=(slot, b"poh", b"meshs")),
        patch(COORD + "meteoswiss.evaluate", return_value=calm),
    ):
        await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert _issue(hass, "no_products", entry) is None
