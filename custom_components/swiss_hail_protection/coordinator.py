"""DataUpdateCoordinators for the two hail-signal sources."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import meteoswiss
from .api import (
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
    DOMAIN,
    METEOSWISS_MAX_SLOTS_BACK,
    METEOSWISS_MESHS_PREFIX,
    METEOSWISS_MESHS_SUFFIX,
    METEOSWISS_POH_PREFIX,
    METEOSWISS_POH_SUFFIX,
    METEOSWISS_PUBLISH_DELAY_SECONDS,
    METEOSWISS_SEASON_MONTHS,
    METEOSWISS_UPDATE_INTERVAL_SECONDS,
    SOURCE_METEOSWISS,
    SOURCE_VKF,
    STATE_CODE_NO_HAIL,
    STATE_CODE_TEST_ALARM,
    STATE_CODE_TO_STATUS,
    STATUS_HAIL,
    STATUS_NO_HAIL,
    STATUS_OFF_SEASON,
    VKF_UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def entry_source(entry: ConfigEntry) -> str:
    """The entry's source; entries created before 1.1.0 are VKF entries."""
    return entry.data.get(CONF_SOURCE, SOURCE_VKF)


@dataclass(frozen=True)
class HailData:
    """One successful refresh, as the entities read it.

    alarm / status / test_alarm are filled by both sources; the remaining
    fields belong to one source and stay None for the other.
    """

    alarm: bool  # the signal to act on: raise the blinds
    status: str | None  # no_hail / hail / test_alarm / off_season, None = unknown
    test_alarm: bool = False
    # VKF
    state_code: int | None = None
    # MeteoSwiss
    radar_time: datetime | None = None
    poh_home: float | None = None
    poh_max: float | None = None
    meshs_max: float | None = None
    hail_cells: int | None = None
    nearest_hail_km: float | None = None


def parse_state_code(state_code: int) -> HailData:
    """Map a VKF currentState value to HailData.

    The specification encourages clients to treat the state as zero / non-zero
    and not to distinguish between the two hail cases, so an unknown non-zero
    code (a value a future API version might add) still raises the alarm;
    only the status sensor reports it as unknown.
    """
    return HailData(
        alarm=state_code != STATE_CODE_NO_HAIL,
        status=STATE_CODE_TO_STATUS.get(state_code),
        test_alarm=state_code == STATE_CODE_TEST_ALARM,
        state_code=state_code,
    )


class HailCoordinator(DataUpdateCoordinator[HailData]):
    """Common base: one coordinator per config entry."""

    source: str

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.source}",
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
        )
        self._entry = entry


class VkfCoordinator(HailCoordinator):
    """Polls the VKF hail-warning state for one registered device."""

    source = SOURCE_VKF

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, VKF_UPDATE_INTERVAL_SECONDS)
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


async def async_fetch_latest_products(
    hass: HomeAssistant,
    suffixes: list[str],
    skip_slot: datetime | None = None,
) -> tuple[datetime, bytes | None, bytes | None]:
    """Newest available POH and MESHS files among the recent five-minute slots.

    Returns (slot, poh_bytes, meshs_bytes). poh_bytes is None only when the
    newest available slot equals skip_slot (nothing new to download). If no
    slot in the window has a POH file, the current suffixes are re-discovered
    from the day's STAC item and the window is tried once more with them
    (suffixes is updated in place); then MeteoSwissNoDataError.
    """
    session = async_get_clientsession(hass)
    newest = meteoswiss.latest_slot(
        dt_util.utcnow(), timedelta(seconds=METEOSWISS_PUBLISH_DELAY_SECONDS)
    )
    slots = [newest - timedelta(minutes=5 * i) for i in range(METEOSWISS_MAX_SLOTS_BACK)]

    for attempt in range(2):
        poh_suffix, meshs_suffix = suffixes
        for slot in slots:
            if skip_slot is not None and slot == skip_slot:
                return slot, None, None
            poh = await meteoswiss.async_download(
                session, meteoswiss.slot_url(METEOSWISS_POH_PREFIX, poh_suffix, slot)
            )
            if poh is None:
                continue
            meshs = await meteoswiss.async_download(
                session, meteoswiss.slot_url(METEOSWISS_MESHS_PREFIX, meshs_suffix, slot)
            )
            return slot, poh, meshs
        if attempt == 0:
            discovered = await meteoswiss.async_discover_suffixes(session, newest)
            if discovered == (None, None) or list(discovered) == suffixes:
                break
            suffixes[0] = discovered[0] or suffixes[0]
            suffixes[1] = discovered[1] or suffixes[1]
            _LOGGER.info("MeteoSwiss product file names changed; using suffixes %s", suffixes)
    raise meteoswiss.MeteoSwissNoDataError(
        f"no hail product published for the last {METEOSWISS_MAX_SLOTS_BACK} slots"
    )


def _status_for(evaluation: meteoswiss.RadarEvaluation, slot: datetime, threshold: float) -> HailData:
    alarm = evaluation.poh_max is not None and evaluation.poh_max >= threshold
    if evaluation.poh_max is None:
        status = None  # no data within the radius
    elif alarm:
        status = STATUS_HAIL
    elif slot.month not in METEOSWISS_SEASON_MONTHS and not evaluation.poh_max:
        # Outside April..September the products are published but empty.
        status = STATUS_OFF_SEASON
    else:
        status = STATUS_NO_HAIL
    return HailData(
        alarm=alarm,
        status=status,
        radar_time=slot,
        poh_home=evaluation.poh_home,
        poh_max=evaluation.poh_max,
        meshs_max=evaluation.meshs_max,
        hail_cells=evaluation.hail_cells,
        nearest_hail_km=evaluation.nearest_hail_km,
    )


class MeteoSwissCoordinator(HailCoordinator):
    """Downloads the newest hail radar products and evaluates them around the location."""

    source = SOURCE_METEOSWISS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry, METEOSWISS_UPDATE_INTERVAL_SECONDS)
        self._suffixes = [METEOSWISS_POH_SUFFIX, METEOSWISS_MESHS_SUFFIX]
        self._last_slot: datetime | None = None

    async def _async_update_data(self) -> HailData:
        data = self._entry.data
        try:
            slot, poh, meshs = await async_fetch_latest_products(
                self.hass, self._suffixes, skip_slot=self._last_slot
            )
            if poh is None:
                # Nothing newer than what the entities already show.
                return self.data
            col, row = meteoswiss.grid_position(data[CONF_LATITUDE], data[CONF_LONGITUDE])
            evaluation = await self.hass.async_add_executor_job(
                meteoswiss.evaluate,
                poh,
                meshs,
                col,
                row,
                float(data[CONF_RADIUS_KM]),
                float(data[CONF_POH_THRESHOLD]),
            )
        except meteoswiss.MeteoSwissError as err:
            raise UpdateFailed(f"MeteoSwiss hail radar data unavailable: {err}") from err

        self._last_slot = slot
        return _status_for(evaluation, slot, float(data[CONF_POH_THRESHOLD]))


def create_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> HailCoordinator:
    if entry_source(entry) == SOURCE_METEOSWISS:
        return MeteoSwissCoordinator(hass, entry)
    return VkfCoordinator(hass, entry)
