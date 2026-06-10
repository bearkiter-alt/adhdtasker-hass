"""Shared base entity for ADHDTasker — binds every entity to one family device."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AdhdtaskerCoordinator


class AdhdtaskerEntity(CoordinatorEntity[AdhdtaskerCoordinator]):
    """Base entity: shared device info.

    Names are set explicitly (with an ``ADHDTasker`` prefix) rather than via
    ``has_entity_name`` so the resulting entity_ids are stable/predictable
    (``sensor.adhdtasker_open_tasks`` etc.) and the example dashboard pastes in
    without editing — at the cost of the family name not prefixing each entity.
    """

    def __init__(self, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        family = (coordinator.data or {}).get("family") or "ADHDTasker"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=family,
            manufacturer="ADHDTasker",
            model="Family chore board",
            configuration_url="https://app.adhdtasker.com",
        )
