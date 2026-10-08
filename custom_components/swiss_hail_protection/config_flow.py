"""Config flow for the Swiss Hail Protection integration.

Two sources, chosen in a menu when the integration is added:
- vkf: the VKF hail-warning signal for a registered device (serial + interface id)
- meteoswiss: the MeteoSwiss hail radar products around a location
"""
from __future__ import annotations

import logging
import math
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import meteoswiss
from .api import (
    HailApiCommunicationError,
    HailApiDeviceNotFoundError,
    HailApiError,
    HailApiTooManyPollsError,
    async_poll_state,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_HWTYPE_ID,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_POH_THRESHOLD,
    CONF_RADIUS_KM,
    CONF_SOURCE,
    DEFAULT_POH_THRESHOLD,
    DEFAULT_RADIUS_KM,
    DOMAIN,
    MAX_RADIUS_KM,
    METEOSWISS_MESHS_SUFFIX,
    METEOSWISS_POH_SUFFIX,
    SOURCE_METEOSWISS,
    SOURCE_VKF,
)
from .coordinator import async_fetch_latest_products
from .device import entry_source, entry_title

_LOGGER = logging.getLogger(__name__)

# The VKF specification describes the serial as a 12-character identifier
# (the MAC address of a signal box, or an identifier the VKF issues for
# building control systems without a box). Letters and digits only, so the
# value can go into the request path unchanged; the length is deliberately
# not pinned to 12 in case the VKF issues a different format for API clients.
_DEVICE_ID_RE = re.compile(r"^[A-Z0-9]{4,32}$")


def _vkf_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_DEVICE_ID, default=defaults.get(CONF_DEVICE_ID, vol.UNDEFINED)
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT, autocomplete="off"
                )
            ),
            vol.Required(
                CONF_HWTYPE_ID, default=defaults.get(CONF_HWTYPE_ID, vol.UNDEFINED)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=99999, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
    )


def _meteoswiss_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LATITUDE, default=defaults[CONF_LATITUDE]): vol.Coerce(float),
            vol.Required(CONF_LONGITUDE, default=defaults[CONF_LONGITUDE]): vol.Coerce(float),
            vol.Required(CONF_RADIUS_KM, default=defaults[CONF_RADIUS_KM]): vol.Coerce(float),
            vol.Required(
                CONF_POH_THRESHOLD, default=defaults[CONF_POH_THRESHOLD]
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=100, step=1, mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="%",
                )
            ),
        }
    )


def _meteoswiss_unique_id(lat: float, lon: float, radius: float) -> str:
    return f"{SOURCE_METEOSWISS}_{round(lat, 3)}_{round(lon, 3)}_{radius:g}"


class SwissHailProtectionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: pick a source, enter its parameters, verified with one fetch."""

    VERSION = 1

    # ----- menu ---------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[SOURCE_VKF, SOURCE_METEOSWISS])

    # ----- VKF ----------------------------------------------------------------

    async def _async_validate_vkf(
        self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Normalise the input and poll the service once with it.

        Returns (errors, data). Keys of errors are form fields or "base";
        values are keys under config.error in strings.json."""
        errors: dict[str, str] = {}
        device_id = str(user_input[CONF_DEVICE_ID]).strip().upper()
        hwtype_id = int(user_input[CONF_HWTYPE_ID])
        data = {CONF_SOURCE: SOURCE_VKF, CONF_DEVICE_ID: device_id, CONF_HWTYPE_ID: hwtype_id}
        if not _DEVICE_ID_RE.match(device_id):
            errors[CONF_DEVICE_ID] = "invalid_device_id"
            return errors, data

        # One poll with the entered values, so an unknown serial or an
        # unreachable service shows up in the form instead of as a failed
        # setup afterwards. The serial itself is never logged.
        try:
            await async_poll_state(async_get_clientsession(self.hass), device_id, hwtype_id)
        except HailApiDeviceNotFoundError:
            errors["base"] = "device_not_found"
        except HailApiTooManyPollsError:
            errors["base"] = "too_many_polls"
        except HailApiCommunicationError as err:
            _LOGGER.warning(
                "Connection test to the VKF hail-warning service failed: %s", err
            )
            errors["base"] = "cannot_connect"
        except HailApiError as err:
            _LOGGER.warning(
                "The VKF hail-warning service gave an unexpected answer: %s", err
            )
            errors["base"] = "unknown"
        return errors, data

    async def async_step_vkf(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = str(user_input[CONF_DEVICE_ID]).strip().upper()
            # Cheap check first: no poll for a serial that is already set up.
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            errors, data = await self._async_validate_vkf(user_input)
            if not errors:
                return self.async_create_entry(
                    title=entry_title(self.hass, SOURCE_VKF, data), data=data
                )

        return self.async_show_form(
            step_id=SOURCE_VKF, data_schema=_vkf_schema(user_input), errors=errors
        )

    # ----- MeteoSwiss ---------------------------------------------------------

    def _meteoswiss_defaults(self, current: Mapping[str, Any] | None = None) -> dict[str, Any]:
        current = current or {}
        return {
            CONF_LATITUDE: current.get(CONF_LATITUDE, self.hass.config.latitude),
            CONF_LONGITUDE: current.get(CONF_LONGITUDE, self.hass.config.longitude),
            CONF_RADIUS_KM: current.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
            CONF_POH_THRESHOLD: current.get(CONF_POH_THRESHOLD, DEFAULT_POH_THRESHOLD),
        }

    async def _async_validate_meteoswiss(
        self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Range checks, then one real fetch and evaluation with the values.

        The fetch proves that the data service is reachable and that the
        location lies inside the radar composite — a location outside the
        coverage would otherwise create an entry that never shows hail."""
        errors: dict[str, str] = {}
        lat = float(user_input[CONF_LATITUDE])
        lon = float(user_input[CONF_LONGITUDE])
        radius = float(user_input[CONF_RADIUS_KM])
        threshold = float(user_input[CONF_POH_THRESHOLD])
        data = {
            CONF_SOURCE: SOURCE_METEOSWISS,
            CONF_LATITUDE: lat,
            CONF_LONGITUDE: lon,
            CONF_RADIUS_KM: radius,
            CONF_POH_THRESHOLD: threshold,
        }
        if not -90 <= lat <= 90:
            errors[CONF_LATITUDE] = "invalid_latitude"
        if not -180 <= lon <= 180:
            errors[CONF_LONGITUDE] = "invalid_longitude"
        if not (math.isfinite(radius) and 0 < radius <= MAX_RADIUS_KM):
            errors[CONF_RADIUS_KM] = "invalid_radius"
        if errors:
            return errors, data

        col, row = meteoswiss.grid_position(lat, lon)
        if not meteoswiss.inside_grid(col, row):
            errors[CONF_LATITUDE] = "outside_coverage"
            return errors, data

        try:
            _slot, poh, meshs = await async_fetch_latest_products(
                self.hass, [METEOSWISS_POH_SUFFIX, METEOSWISS_MESHS_SUFFIX]
            )
            evaluation = await self.hass.async_add_executor_job(
                meteoswiss.evaluate, poh, meshs, col, row, radius, threshold
            )
        except meteoswiss.MeteoSwissNoDataError:
            errors["base"] = "no_data"
        except meteoswiss.MeteoSwissCommunicationError as err:
            _LOGGER.warning("Connection test to the MeteoSwiss data service failed: %s", err)
            errors["base"] = "cannot_connect"
        except meteoswiss.MeteoSwissError as err:
            _LOGGER.warning("The MeteoSwiss hail product could not be decoded: %s", err)
            errors["base"] = "unknown"
        else:
            if not evaluation.home_covered:
                errors[CONF_LATITUDE] = "outside_coverage"
        return errors, data

    async def async_step_meteoswiss(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, data = await self._async_validate_meteoswiss(user_input)
            if not errors:
                await self.async_set_unique_id(
                    _meteoswiss_unique_id(
                        data[CONF_LATITUDE], data[CONF_LONGITUDE], data[CONF_RADIUS_KM]
                    )
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=entry_title(self.hass, SOURCE_METEOSWISS, data), data=data
                )

        schema = _meteoswiss_schema(self._meteoswiss_defaults())
        if user_input is not None:
            # Show the rejected values again instead of the defaults.
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id=SOURCE_METEOSWISS, data_schema=schema, errors=errors
        )

    # ----- reauth (VKF only) and reconfigure ---------------------------------

    async def _async_update_vkf_entry(
        self,
        step_id: str,
        entry: ConfigEntry,
        user_input: dict[str, Any] | None,
        reason: str,
    ) -> ConfigFlowResult:
        """Shared body of the reauth and VKF reconfigure steps.

        A changed serial is accepted (the VKF may issue a new one), as long as
        no other entry already uses it; the entry's unique id and title follow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, data = await self._async_validate_vkf(user_input)
            if not errors:
                await self.async_set_unique_id(data[CONF_DEVICE_ID])
                if data[CONF_DEVICE_ID] != entry.unique_id:
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=data[CONF_DEVICE_ID],
                    title=entry_title(self.hass, SOURCE_VKF, data),
                    data=data,
                    reason=reason,
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=_vkf_schema(user_input or entry.data),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Started by the VKF coordinator when the service no longer knows the serial."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_update_vkf_entry(
            "reauth_confirm", self._get_reauth_entry(), user_input, "reauth_successful"
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if entry_source(entry) == SOURCE_METEOSWISS:
            return await self.async_step_reconfigure_meteoswiss(user_input)
        return await self._async_update_vkf_entry(
            "reconfigure", entry, user_input, "reconfigure_successful"
        )

    async def async_step_reconfigure_meteoswiss(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, data = await self._async_validate_meteoswiss(user_input)
            if not errors:
                unique_id = _meteoswiss_unique_id(
                    data[CONF_LATITUDE], data[CONF_LONGITUDE], data[CONF_RADIUS_KM]
                )
                await self.async_set_unique_id(unique_id)
                if unique_id != entry.unique_id:
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=entry_title(self.hass, SOURCE_METEOSWISS, data),
                    data=data,
                    reason="reconfigure_successful",
                )

        schema = _meteoswiss_schema(self._meteoswiss_defaults(entry.data))
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="reconfigure_meteoswiss", data_schema=schema, errors=errors
        )
