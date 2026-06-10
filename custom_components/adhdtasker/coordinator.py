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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.get_state()
        except AdhdtaskerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AdhdtaskerError as err:
            raise UpdateFailed(str(err)) from err

    def set_last_event(self, payload: dict[str, Any]) -> None:
        """Store the latest webhook payload and notify entities (e.g. last-event sensor)."""
        self.last_event = payload
        self.async_update_listeners()
