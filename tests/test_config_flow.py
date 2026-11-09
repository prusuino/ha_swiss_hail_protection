"""Config flow tests for both sources: VKF (serial check, unknown serial,
duplicate, reauth) and MeteoSwiss (location check, coverage, duplicate,
reconfigure). The VKF poll and the MeteoSwiss downloads are faked."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swiss_hail_protection.api import HailApiDeviceNotFoundError
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
from custom_components.swiss_hail_protection.meteoswiss import RadarEvaluation

FLOW = "custom_components.swiss_hail_protection.config_flow."
SLOT = datetime(2026, 7, 15, 14, 35, tzinfo=timezone.utc)
COVERED = RadarEvaluation(poh_home=0.0, poh_max=0.0, meshs_max=None, hail_cells=0, nearest_hail_km=None, home_covered=True)
UNCOVERED = RadarEvaluation(poh_home=None, poh_max=None, meshs_max=None, hail_cells=0, nearest_hail_km=None, home_covered=False)
BERN = {CONF_LATITUDE: 46.951, CONF_LONGITUDE: 7.439, CONF_RADIUS_KM: 10, CONF_POH_THRESHOLD: 80}


@pytest.fixture
def fake_vkf():
    with patch(FLOW + "async_poll_state", return_value=0):
        yield


@pytest.fixture
def fake_radar():
    with (
        patch(FLOW + "async_fetch_latest_products", return_value=(SLOT, b"poh", b"meshs")),
        patch(FLOW + "meteoswiss.evaluate", return_value=COVERED),
    ):
        yield


async def _menu(hass, source):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": source})
    assert result["step_id"] == source
    return result


async def test_vkf_setup_normalises_the_serial(hass: HomeAssistant, enable_custom_integrations, fake_vkf) -> None:
    result = await _menu(hass, SOURCE_VKF)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: " a1b2c3d4e5f6 ", CONF_HWTYPE_ID: 42})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SOURCE: SOURCE_VKF, CONF_DEVICE_ID: "A1B2C3D4E5F6", CONF_HWTYPE_ID: 42}
    assert result["result"].unique_id == "A1B2C3D4E5F6"
    assert "A1B2C3D4E5F6" not in result["title"]  # the serial is a credential and stays out of the title


async def test_vkf_unknown_serial_is_a_form_error(hass: HomeAssistant, enable_custom_integrations) -> None:
    with patch(FLOW + "async_poll_state", side_effect=HailApiDeviceNotFoundError("DeviceNotFoundException")):
        result = await _menu(hass, SOURCE_VKF)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: "A1B2C3D4E5F6", CONF_HWTYPE_ID: 42})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "device_not_found"}


async def test_vkf_bad_serial_is_rejected_without_a_poll(hass: HomeAssistant, enable_custom_integrations) -> None:
    with patch(FLOW + "async_poll_state") as poll:
        result = await _menu(hass, SOURCE_VKF)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: "ab:cd", CONF_HWTYPE_ID: 42})
    assert result["errors"] == {CONF_DEVICE_ID: "invalid_device_id"}
    poll.assert_not_called()


async def test_vkf_same_serial_twice_is_refused(hass: HomeAssistant, enable_custom_integrations, fake_vkf) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="A1B2C3D4E5F6", title="VKF", data={CONF_SOURCE: SOURCE_VKF, CONF_DEVICE_ID: "A1B2C3D4E5F6", CONF_HWTYPE_ID: 42}).add_to_hass(hass)
    result = await _menu(hass, SOURCE_VKF)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: "a1b2c3d4e5f6", CONF_HWTYPE_ID: 42})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_vkf_reauth_accepts_a_new_serial(hass: HomeAssistant, enable_custom_integrations, fake_vkf) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="A1B2C3D4E5F6", title="VKF", data={CONF_SOURCE: SOURCE_VKF, CONF_DEVICE_ID: "A1B2C3D4E5F6", CONF_HWTYPE_ID: 42})
    entry.add_to_hass(hass)
    with patch("custom_components.swiss_hail_protection.async_setup_entry", return_value=True):
        result = await entry.start_reauth_flow(hass)
        assert result["step_id"] == "reauth_confirm"
        assert result["data_schema"]({CONF_HWTYPE_ID: 42, CONF_DEVICE_ID: "x"})  # the old serial is not pre-filled
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_DEVICE_ID: "FFFFFFFFFFFF", CONF_HWTYPE_ID: 42})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.unique_id == "FFFFFFFFFFFF"
    assert entry.data[CONF_DEVICE_ID] == "FFFFFFFFFFFF"


async def test_meteoswiss_setup(hass: HomeAssistant, enable_custom_integrations, fake_radar) -> None:
    result = await _menu(hass, SOURCE_METEOSWISS)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], BERN)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SOURCE] == SOURCE_METEOSWISS
    assert result["data"][CONF_RADIUS_KM] == 10.0
    assert result["result"].unique_id == "meteoswiss_46.951_7.439_10"


async def test_meteoswiss_location_outside_coverage(hass: HomeAssistant, enable_custom_integrations, fake_radar) -> None:
    result = await _menu(hass, SOURCE_METEOSWISS)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BERN, CONF_LATITUDE: 52.52, CONF_LONGITUDE: 13.40})
    assert result["errors"] == {CONF_LATITUDE: "outside_coverage"}
    # inside the grid, but the location's cell carries no data
    with patch(FLOW + "meteoswiss.evaluate", return_value=UNCOVERED):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BERN, CONF_LATITUDE: 47.8, CONF_LONGITUDE: 10.4})
    assert result["errors"] == {CONF_LATITUDE: "outside_coverage"}


async def test_meteoswiss_radius_limits(hass: HomeAssistant, enable_custom_integrations, fake_radar) -> None:
    result = await _menu(hass, SOURCE_METEOSWISS)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BERN, CONF_RADIUS_KM: 80})
    assert result["errors"] == {CONF_RADIUS_KM: "invalid_radius"}


async def test_meteoswiss_reconfigure_moves_the_location(hass: HomeAssistant, enable_custom_integrations, fake_radar) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="meteoswiss_46.951_7.439_10", title="Radar", data={CONF_SOURCE: SOURCE_METEOSWISS, **BERN})
    entry.add_to_hass(hass)
    with patch("custom_components.swiss_hail_protection.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id})
        assert result["step_id"] == "reconfigure_meteoswiss"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {**BERN, CONF_LATITUDE: 47.377, CONF_LONGITUDE: 8.54, CONF_RADIUS_KM: 20})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "meteoswiss_47.377_8.54_20"
    assert entry.data[CONF_RADIUS_KM] == 20.0
