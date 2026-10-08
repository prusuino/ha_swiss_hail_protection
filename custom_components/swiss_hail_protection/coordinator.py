"""DataUpdateCoordinator for the VKF hail-warning signal."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    HailApiDeviceNotFoundError,
    HailApiError,
    HailApiTooManyPollsError,
    async_poll_state,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_HWTYPE_ID,
    DOMAIN,
    STATE_CODE_NO_HAIL,
    STATE_CODE_TEST_ALARM,
    STATE_CODE_TO_STATUS,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HailData:
    """One successful poll, as the entities read it."""

    state_code: int
    status: str | None  # no_hail / hail / test_alarm, None for an unknown code
    alarm: bool  # True for every non-zero code, as the VKF specification advises
    test_alarm: bool


def parse_state_code(state_code: int) -> HailData:
    """Map a currentState value to HailData.

    The specification encourages clients to treat the state as zero / non-zero
    and not to distinguish between the two hail cases, so an unknown non-zero
    code (a value a future API version might add) still raises the alarm;
    only the status sensor reports it as unknown.
    """
    return HailData(
        state_code=state_code,
        status=STATE_CODE_TO_STATUS.get(state_code),
        alarm=state_code != STATE_CODE_NO_HAIL,
        test_alarm=state_code == STATE_CODE_TEST_ALARM,
    )


class HailCoordinator(DataUpdateCoordinator[HailData]):
    """Polls the hail-warning state for one registered device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._entry = entry
        self._unknown_code_logged = False

    async def _async_update_data(self) -> HailData:
        data = self._entry.data
        try:
            state_code = await async_poll_state(
                async_get_clientsession(self.hass),
                data[CONF_DEVICE_ID],
                int(data[CONF_HWTYPE_ID]),
            )
        except HailApiDeviceNotFoundError as err:
            # The serial is the only credential: if the service no longer
            # knows it, the user has to enter a new one (reauth flow).
            raise ConfigEntryAuthFailed(
                "The VKF service does not recognise the configured device serial"
            ) from err
        except HailApiTooManyPollsError as err:
            raise UpdateFailed(
                "VKF hail-warning service refused the poll: daily quota exhausted"
            ) from err
        except HailApiError as err:
            raise UpdateFailed(f"VKF hail-warning service unreachable: {err}") from err

        if state_code not in STATE_CODE_TO_STATUS and not self._unknown_code_logged:
            self._unknown_code_logged = True
            _LOGGER.warning(
                "VKF hail-warning service returned the undocumented state %s; "
                "treating it as an active warning",
                state_code,
            )
        return parse_state_code(state_code)
