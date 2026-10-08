"""Config flow for the Swiss Hail Protection (VKF) integration."""
from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    HailApiCommunicationError,
    HailApiDeviceNotFoundError,
    HailApiError,
    HailApiTooManyPollsError,
    async_poll_state,
)
from .const import CONF_DEVICE_ID, CONF_HWTYPE_ID, DOMAIN
from .localization import t

_LOGGER = logging.getLogger(__name__)

# The specification describes the serial as a 12-character identifier (the
# MAC address of a signal box, or an identifier the VKF issues for building
# control systems without a box). Letters and digits only, so the value can go
# into the request path unchanged; the length is deliberately not pinned to 12
# in case the VKF issues a different format for API clients.
_DEVICE_ID_RE = re.compile(r"^[A-Z0-9]{4,32}$")


def _schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """The one form used by the user, reauth and reconfigure steps."""
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


class SwissHailProtectionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow: device serial + interface id, verified with one poll."""

    VERSION = 1

    async def _async_validate(
        self, user_input: Mapping[str, Any]
    ) -> tuple[dict[str, str], str, int]:
        """Normalise the input and poll the service once with it.

        Returns (errors, device_id, hwtype_id). Keys of errors are form fields
        or "base"; values are keys under config.error in strings.json."""
        errors: dict[str, str] = {}
        device_id = str(user_input[CONF_DEVICE_ID]).strip().upper()
        hwtype_id = int(user_input[CONF_HWTYPE_ID])
        if not _DEVICE_ID_RE.match(device_id):
            errors[CONF_DEVICE_ID] = "invalid_device_id"
            return errors, device_id, hwtype_id

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
        return errors, device_id, hwtype_id

    def _entry_data(self, device_id: str, hwtype_id: int) -> dict[str, Any]:
        return {CONF_DEVICE_ID: device_id, CONF_HWTYPE_ID: hwtype_id}

    def _title(self, device_id: str) -> str:
        return t("device_name", self.hass, device_id=device_id)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = str(user_input[CONF_DEVICE_ID]).strip().upper()
            # Cheap check first: no poll for a serial that is already set up.
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            errors, device_id, hwtype_id = await self._async_validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self._title(device_id),
                    data=self._entry_data(device_id, hwtype_id),
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    async def _async_step_update_entry(
        self,
        step_id: str,
        entry: ConfigEntry,
        user_input: dict[str, Any] | None,
        reason: str,
    ) -> ConfigFlowResult:
        """Shared body of the reauth and reconfigure steps.

        A changed serial is accepted (the VKF may issue a new one), as long as
        no other entry already uses it; the entry's unique id and title follow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, device_id, hwtype_id = await self._async_validate(user_input)
            if not errors:
                await self.async_set_unique_id(device_id)
                if device_id != entry.unique_id:
                    self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=device_id,
                    title=self._title(device_id),
                    data=self._entry_data(device_id, hwtype_id),
                    reason=reason,
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=_schema(user_input or entry.data),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Started by the coordinator when the service no longer knows the serial."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_update_entry(
            "reauth_confirm", self._get_reauth_entry(), user_input, "reauth_successful"
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self._async_step_update_entry(
            "reconfigure",
            self._get_reconfigure_entry(),
            user_input,
            "reconfigure_successful",
        )
