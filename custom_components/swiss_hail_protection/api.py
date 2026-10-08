"""Minimal client for the VKF hail-warning REST API.

One documented call: GET <VKF_API_BASE_URL>/<deviceId>/poll?hwtypeId=<n>,
which answers {"currentState": 0|1|2}. Errors come back as an HTTP error
status with a JSON body {"exception": "<Name>", "message": "<text>"}.

Nothing here ever puts the request URL into an exception message: the URL
carries the device serial, which is the only credential of the service and
must not end up in the Home Assistant log.
"""
from __future__ import annotations

from typing import Any

import aiohttp

from .const import VKF_API_BASE_URL, VKF_REQUEST_TIMEOUT_SECONDS


class HailApiError(Exception):
    """Base class for all errors raised by this client."""


class HailApiCommunicationError(HailApiError):
    """The service could not be reached or did not answer in time."""


class HailApiDeviceNotFoundError(HailApiError):
    """The service does not know the device serial / interface id."""


class HailApiTooManyPollsError(HailApiError):
    """The service refused the request because the poll quota is exhausted."""


class HailApiVendorError(HailApiError):
    """Any other error reported by the service, identified by its exception name."""

    def __init__(self, status: int, exception_name: str | None) -> None:
        self.status = status
        self.exception_name = exception_name
        super().__init__(f"HTTP {status} {exception_name or ''}".rstrip())


async def _read_json(resp: aiohttp.ClientResponse) -> Any:
    """Decode the body as JSON regardless of the Content-Type header, or None."""
    try:
        return await resp.json(content_type=None)
    except (ValueError, aiohttp.ClientError):
        return None


async def async_poll_state(
    session: aiohttp.ClientSession, device_id: str, hwtype_id: int
) -> int:
    """Return the current state code (0 = no hail, 1 = hail, 2 = test alarm).

    Raises one of the HailApiError subclasses on any failure. Values outside
    0..2 are returned as they are; the caller decides how to treat them.
    """
    url = f"{VKF_API_BASE_URL}/{device_id}/poll"
    try:
        async with session.get(
            url,
            params={"hwtypeId": hwtype_id},
            timeout=aiohttp.ClientTimeout(total=VKF_REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status >= 400:
                payload = await _read_json(resp)
                name = payload.get("exception") if isinstance(payload, dict) else None
                if name == "DeviceNotFoundException" or resp.status == 404:
                    raise HailApiDeviceNotFoundError(name or f"HTTP {resp.status}")
                if name == "TooManyPollsException" or resp.status == 429:
                    raise HailApiTooManyPollsError(name or f"HTTP {resp.status}")
                raise HailApiVendorError(resp.status, name)
            payload = await _read_json(resp)
    except TimeoutError as err:
        raise HailApiCommunicationError("timeout") from err
    except aiohttp.ClientError as err:
        # Only the error type: aiohttp's messages may include the request URL.
        raise HailApiCommunicationError(type(err).__name__) from err

    if not isinstance(payload, dict) or not isinstance(payload.get("currentState"), int):
        raise HailApiError("unexpected response: currentState missing")
    return payload["currentState"]
