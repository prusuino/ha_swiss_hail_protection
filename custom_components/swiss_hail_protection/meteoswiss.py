"""MeteoSwiss hail radar products: download, decode and evaluate around a location.

The products come as ODIM HDF5 files on the 1 km Swiss radar composite grid
(LV95). They are read with pyfive, a pure-Python HDF5 reader, so no compiled
HDF5 library is needed on the Home Assistant host. Decoding and the grid
arithmetic run in the executor; only the download is asynchronous.

Privacy: one file covers all of Switzerland, so the request carries nothing
about the configured location. The location only ever enters the arithmetic
on this machine.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import aiohttp

from .const import (
    GRID_CELL_M,
    GRID_COLS,
    GRID_NORTH_N,
    GRID_ROWS,
    GRID_WEST_E,
    METEOSWISS_BASE_URL,
    METEOSWISS_MESHS_PREFIX,
    METEOSWISS_MESHS_SUFFIX,
    METEOSWISS_POH_PREFIX,
    METEOSWISS_POH_SUFFIX,
    METEOSWISS_REQUEST_TIMEOUT_SECONDS,
    METEOSWISS_STAC_ITEMS_URL,
)


class MeteoSwissError(Exception):
    """Base class for all errors raised by this module."""


class MeteoSwissCommunicationError(MeteoSwissError):
    """The data service could not be reached or did not answer in time."""


class MeteoSwissNoDataError(MeteoSwissError):
    """No product file was found for any of the recent time slots."""


class MeteoSwissDecodeError(MeteoSwissError):
    """A downloaded file could not be decoded as the expected product."""


def wgs84_to_lv95(lat: float, lon: float) -> tuple[float, float]:
    """Convert WGS84 degrees to LV95 metres (E, N).

    The approximate formulas published by swisstopo, accurate to about a
    metre within Switzerland — far below the 1 km grid cell, and without a
    dependency on a projection library.
    """
    phi = (lat * 3600 - 169028.66) / 10000
    lam = (lon * 3600 - 26782.5) / 10000
    east = (
        2600072.37
        + 211455.93 * lam
        - 10938.51 * lam * phi
        - 0.36 * lam * phi * phi
        - 44.54 * lam**3
    )
    north = (
        1200147.07
        + 308807.95 * phi
        + 3745.25 * lam * lam
        + 76.63 * phi * phi
        - 194.56 * lam * lam * phi
        + 119.79 * phi**3
    )
    return east, north


def grid_position(lat: float, lon: float) -> tuple[float, float]:
    """Fractional (column, row) of a WGS84 point on the radar grid.

    Column 0 / row 0 is the north-western cell; cell centres sit at x.5.
    Values outside 0..GRID_COLS / 0..GRID_ROWS lie outside the grid.
    """
    east, north = wgs84_to_lv95(lat, lon)
    return (east - GRID_WEST_E) / GRID_CELL_M, (GRID_NORTH_N - north) / GRID_CELL_M


def inside_grid(col: float, row: float) -> bool:
    return 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS


def slot_filename(prefix: str, suffix: str, slot: datetime) -> str:
    """File name of a product for a five-minute slot (UTC): <prefix>YYJJJHHMM<suffix>."""
    return f"{prefix}{slot:%y%j%H%M}{suffix}"


def slot_url(prefix: str, suffix: str, slot: datetime) -> str:
    return f"{METEOSWISS_BASE_URL}/{slot:%Y%m%d}-ch/{slot_filename(prefix, suffix, slot)}"


def latest_slot(now: datetime, publish_delay: timedelta) -> datetime:
    """Newest five-minute slot whose file can realistically exist at `now`."""
    ready = (now - publish_delay).astimezone(timezone.utc)
    return ready.replace(second=0, microsecond=0, minute=ready.minute - ready.minute % 5)


async def async_download(session: aiohttp.ClientSession, url: str) -> bytes | None:
    """Fetch a product file; None if it does not exist (yet)."""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=METEOSWISS_REQUEST_TIMEOUT_SECONDS)
        ) as resp:
            if resp.status == 404:
                return None
            if resp.status >= 400:
                raise MeteoSwissCommunicationError(f"HTTP {resp.status}")
            return await resp.read()
    except TimeoutError as err:
        raise MeteoSwissCommunicationError("timeout") from err
    except aiohttp.ClientError as err:
        raise MeteoSwissCommunicationError(type(err).__name__) from err


async def async_discover_suffixes(
    session: aiohttp.ClientSession, day: datetime
) -> tuple[str | None, str | None]:
    """Current file-name suffixes of the two products, from the day's STAC item.

    Only used when the built-in suffixes stop matching. Returns (POH, MESHS);
    either is None if the day lists no such product.
    """
    url = f"{METEOSWISS_STAC_ITEMS_URL}/{day:%Y%m%d}-ch"
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=METEOSWISS_REQUEST_TIMEOUT_SECONDS)
        ) as resp:
            if resp.status >= 400:
                raise MeteoSwissCommunicationError(f"HTTP {resp.status}")
            item = await resp.json(content_type=None)
    except TimeoutError as err:
        raise MeteoSwissCommunicationError("timeout") from err
    except (aiohttp.ClientError, ValueError) as err:
        raise MeteoSwissCommunicationError(type(err).__name__) from err

    def suffix_for(prefix: str) -> str | None:
        names = sorted(
            n for n in (item.get("assets") or {}) if n.startswith(prefix) and len(n) > 12
        )
        # <prefix>YYJJJHHMM is 12 characters; the rest is the suffix.
        return names[-1][12:] if names else None

    return suffix_for(METEOSWISS_POH_PREFIX), suffix_for(METEOSWISS_MESHS_PREFIX)


@dataclass(frozen=True)
class RadarEvaluation:
    """What the two products say for one location and radius."""

    poh_home: float | None  # % in the cell of the location
    poh_max: float | None  # highest % within the radius
    meshs_max: float | None  # largest expected hail size (mm) within the radius
    hail_cells: int  # cells within the radius at or above the threshold
    nearest_hail_km: float | None  # distance to the closest such cell
    home_covered: bool  # the location's cell carries data (not nodata)


def _decode(data: bytes):
    """Decode a product file to a float array in physical units (NaN = nodata)."""
    import numpy as np  # noqa: PLC0415 - heavy import, executor only
    import pyfive  # noqa: PLC0415

    try:
        h5 = pyfive.File(io.BytesIO(data))
        dataset = h5["/dataset1/data1/data"]
        what = dict(h5["/dataset1/data1/what"].attrs)
        values = np.asarray(dataset[...], dtype=float)
    except Exception as err:  # noqa: BLE001 - any decode failure is reported the same way
        raise MeteoSwissDecodeError(f"{type(err).__name__}: {err}") from err
    if values.shape != (GRID_ROWS, GRID_COLS):
        raise MeteoSwissDecodeError(f"unexpected grid {values.shape}")
    gain = float(what.get("gain", 1.0))
    offset = float(what.get("offset", 0.0))
    nodata = what.get("nodata")
    if nodata is not None and not math.isnan(float(nodata)):
        values[values == float(nodata)] = np.nan
    values = values * gain + offset
    quantity = what.get("quantity", b"")
    quantity = quantity.decode() if isinstance(quantity, bytes) else str(quantity)
    if quantity == "POH" and np.isfinite(values).any() and np.nanmax(values) <= 1.0:
        # The documentation gives POH in percent; the files published in
        # 2026 store a fraction 0..1. Normalise to percent either way.
        values = values * 100.0
    return values


def evaluate(
    poh_bytes: bytes,
    meshs_bytes: bytes | None,
    col: float,
    row: float,
    radius_km: float,
    threshold: float,
) -> RadarEvaluation:
    """Blocking: decode the files and evaluate them around (col, row)."""
    import numpy as np  # noqa: PLC0415

    poh = _decode(poh_bytes)
    meshs = _decode(meshs_bytes) if meshs_bytes is not None else None

    rows = np.arange(GRID_ROWS, dtype=float)[:, None] + 0.5
    cols = np.arange(GRID_COLS, dtype=float)[None, :] + 0.5
    distance = np.hypot(cols - col, rows - row)  # km, one cell = 1 km
    within = distance <= radius_km

    def nanmax_within(values) -> float | None:
        selected = values[within]
        selected = selected[np.isfinite(selected)]
        return float(selected.max()) if selected.size else None

    home_value = poh[int(row), int(col)] if inside_grid(col, row) else np.nan
    home_covered = bool(np.isfinite(home_value))
    hail = within & (np.nan_to_num(poh, nan=-1.0) >= threshold)
    hail_cells = int(hail.sum())
    nearest = float(distance[hail].min()) if hail_cells else None

    return RadarEvaluation(
        poh_home=float(home_value) if home_covered else None,
        poh_max=nanmax_within(poh),
        meshs_max=nanmax_within(meshs) if meshs is not None else None,
        hail_cells=hail_cells,
        nearest_hail_km=round(nearest, 1) if nearest is not None else None,
        home_covered=home_covered,
    )


__all__ = [
    "METEOSWISS_MESHS_SUFFIX",
    "METEOSWISS_POH_SUFFIX",
    "MeteoSwissCommunicationError",
    "MeteoSwissDecodeError",
    "MeteoSwissError",
    "MeteoSwissNoDataError",
    "RadarEvaluation",
    "async_discover_suffixes",
    "async_download",
    "evaluate",
    "grid_position",
    "inside_grid",
    "latest_slot",
    "slot_url",
    "wgs84_to_lv95",
]
