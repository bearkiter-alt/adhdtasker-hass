"""DataUpdateCoordinator for ADHDTasker — polls board state, holds last webhook event."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AdhdtaskerApiClient, AdhdtaskerAuthError, AdhdtaskerError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AdhdtaskerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls `GET /api` for board state; webhook pushes trigger an early refresh."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AdhdtaskerApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.entry = entry
        self.last_event: dict[str, Any] | None = None
        self._consecutive_failures = 0

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.get_state()
        except AdhdtaskerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AdhdtaskerError as err:
            # The Firebase backend occasionally cold-starts past the request
            # timeout; don't flap every entity to unavailable over one bad
            # poll. Serve the last good board for up to two consecutive
            # failures, then surface the outage.
            self._consecutive_failures += 1
            if self.data is not None and self._consecutive_failures <= 2:
                _LOGGER.warning(
                    "ADHDTasker poll failed (%s consecutive, tolerating up to 2):"
                    " %s; keeping last known board state",
                    self._consecutive_failures,
                    err,
                )
                return self.data
            raise UpdateFailed(str(err)) from err
        self._consecutive_failures = 0
        return data

    def set_last_event(self, payload: dict[str, Any]) -> None:
        """Store the latest webhook payload and notify entities (e.g. last-event sensor)."""
        self.last_event = payload
        self.async_update_listeners()
