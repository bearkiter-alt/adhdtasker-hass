"""Sensors for ADHDTasker: open/pending counts, per-kid points & balance, last event."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import AdhdtaskerCoordinator
from .entity import AdhdtaskerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AdhdtaskerCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            OpenTasksSensor(coordinator, entry),
            PendingApprovalSensor(coordinator, entry),
            LastEventSensor(coordinator, entry),
        ]
    )

    # Per-kid sensors are dynamic — add new ones as kids appear in the leaderboard.
    known: set[str] = set()

    @callback
    def _sync_kids() -> None:
        new: list[SensorEntity] = []
        for kid in (coordinator.data or {}).get("leaderboard", []):
            name = (kid.get("name") or "").strip()
            if name and name not in known:
                known.add(name)
                new.append(KidSensor(coordinator, entry, name, "lifetime", "points", "mdi:star"))
                new.append(KidSensor(coordinator, entry, name, "balance", "bank", "mdi:bank"))
        if new:
            async_add_entities(new)

    _sync_kids()
    entry.async_on_unload(coordinator.async_add_listener(_sync_kids))


class OpenTasksSensor(AdhdtaskerEntity, SensorEntity):
    """Total open tasks; exposes counts + the full board + leaderboard as attributes."""

    _attr_icon = "mdi:clipboard-list-outline"
    _attr_native_unit_of_measurement = "tasks"
    _attr_state_class = SensorStateClass.MEASUREMENT
    # The board/leaderboard are large and change often — keep them live for the
    # dashboard but out of the recorder so history doesn't bloat (counts are kept).
    _unrecorded_attributes = frozenset({"tasks", "leaderboard"})

    def __init__(self, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "ADHDTasker Open tasks"
        self._attr_unique_id = f"{entry.entry_id}_open_tasks"

    @property
    def native_value(self) -> int | None:
        return (self.coordinator.data or {}).get("open")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        counts = data.get("counts") or {}
        return {
            "todo": counts.get("todo"),
            "in_progress": counts.get("in_progress"),
            "pending_approval": counts.get("pending_approval"),
            "tasks": data.get("tasks", []),
            "leaderboard": data.get("leaderboard", []),
        }


class PendingApprovalSensor(AdhdtaskerEntity, SensorEntity):
    """Tasks marked done and waiting for a parent to approve."""

    _attr_icon = "mdi:clipboard-check-outline"
    _attr_native_unit_of_measurement = "tasks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "ADHDTasker Pending approval"
        self._attr_unique_id = f"{entry.entry_id}_pending_approval"

    @property
    def native_value(self) -> int | None:
        return ((self.coordinator.data or {}).get("counts") or {}).get("pending_approval")


class KidSensor(AdhdtaskerEntity, SensorEntity):
    """A single profile's lifetime points or spendable balance."""

    _attr_native_unit_of_measurement = "pts"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AdhdtaskerCoordinator,
        entry: ConfigEntry,
        kid: str,
        field: str,
        suffix: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._kid = kid
        self._field = field
        self._attr_icon = icon
        self._attr_name = f"ADHDTasker {kid} {suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{slugify(kid)}_{field}"

    def _entry(self) -> dict[str, Any] | None:
        for k in (self.coordinator.data or {}).get("leaderboard", []):
            if (k.get("name") or "") == self._kid:
                return k
        return None

    @property
    def native_value(self) -> int | None:
        row = self._entry()
        return row.get(self._field) if row else None

    @property
    def available(self) -> bool:
        return super().available and self._entry() is not None


class LastEventSensor(AdhdtaskerEntity, SensorEntity):
    """The most recent event pushed to the HA webhook (task.completed, ping, …)."""

    _attr_icon = "mdi:bell-ring-outline"
    # The state (event name) is recorded; the payload attributes are not.
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "ADHDTasker Last event"
        self._attr_unique_id = f"{entry.entry_id}_last_event"

    @property
    def native_value(self) -> str | None:
        event = self.coordinator.last_event
        return event.get("event") if event else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.coordinator.last_event or {}
