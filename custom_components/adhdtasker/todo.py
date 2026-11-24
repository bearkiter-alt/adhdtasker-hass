"""A native To-do list entity backed by the ADHDTasker board.

Open tasks become to-do items. Add → add_task, rename → update_task, delete → delete_task.

Ticking an item off maps BY TYPE, because the two kinds of row mean different things and
both clients already treat them differently: a real task → complete_task (awards points),
an INTERRUPT → delete_task, which is what the PWA's "Clear" button does. An interrupt is a
zero-point capture that can never be completed — the API rejects it — so a tick on one
means "handled, drop it", not "credit me". Interrupts stay listed deliberately: an
unscored don't-forget is the row most likely to be forgotten.

The assignee/points annotation lives in the item *description* so the *summary* stays
equal to the task title (clean renames).
"""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AdhdtaskerError
from .const import DOMAIN
from .coordinator import AdhdtaskerCoordinator
from .entity import AdhdtaskerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AdhdtaskerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AdhdtaskerTodoList(coordinator, entry)])


class AdhdtaskerTodoList(AdhdtaskerEntity, TodoListEntity):
    """The family board as a To-do list."""

    _attr_name = "ADHDTasker Board"
    _attr_icon = "mdi:clipboard-check-multiple-outline"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_board"

    def _task(self, uid: str | None) -> dict | None:
        if not uid:
            return None
        for task in (self.coordinator.data or {}).get("tasks", []):
            if task.get("id") == uid:
                return task
        return None

    @property
    def todo_items(self) -> list[TodoItem]:
        items: list[TodoItem] = []
        for task in (self.coordinator.data or {}).get("tasks", []):
            extras: list[str] = []
            # An interrupt otherwise renders with an empty description: its points are 0
            # (falsy), it usually has no assignee or claimant, and it can never be
            # PENDING_APPROVAL. Say what it is, and that a tick clears rather than completes.
            if task.get("type") == "INTERRUPT":
                extras.extend(("note", "tick to clear"))
            if task.get("assignee"):
                extras.append(f"for {task['assignee']}")
            elif task.get("claimedBy"):
                extras.append(f"by {task['claimedBy']}")
            if task.get("points"):
                extras.append(f"{task['points']} pts")
            if task.get("status") == "PENDING_APPROVAL":
                extras.append("awaiting approval")
            items.append(
                TodoItem(
                    summary=task.get("title") or "(untitled)",
                    uid=task.get("id"),
                    status=TodoItemStatus.NEEDS_ACTION,
                    description=" · ".join(extras) or None,
                )
            )
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        try:
            await self.coordinator.api.add_task(item.summary)
        except AdhdtaskerError as err:
            raise HomeAssistantError(f"ADHDTasker: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        if not item.uid:
            return
        current = self._task(item.uid)
        try:
            if item.status == TodoItemStatus.COMPLETED:
                # Only divert when we positively know it's an interrupt: an unknown uid
                # (stale coordinator data) keeps the old behaviour rather than guessing
                # its way into a delete.
                if current and current.get("type") == "INTERRUPT":
                    await self.coordinator.api.delete_task(task_id=item.uid)
                else:
                    await self.coordinator.api.complete_task(task_id=item.uid)
            else:
                if current and item.summary and item.summary != current.get("title"):
                    await self.coordinator.api.update_task(
                        task_id=item.uid, title=item.summary
                    )
                else:
                    return  # nothing actionable (description edits aren't supported)
        except AdhdtaskerError as err:
            raise HomeAssistantError(f"ADHDTasker: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        try:
            for uid in uids:
                await self.coordinator.api.delete_task(task_id=uid)
        except AdhdtaskerError as err:
            raise HomeAssistantError(f"ADHDTasker: {err}") from err
        await self.coordinator.async_request_refresh()
