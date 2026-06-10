"""The ADHDTasker integration — native HA entities + services over the family API."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol
from aiohttp.web import Request

from homeassistant.components import persistent_notification, webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AdhdtaskerApiClient, AdhdtaskerError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_SECRET,
    CONF_WEBHOOK_ID,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_RECEIVED,
    PLATFORMS,
    SERVICE_ADD_INTERRUPT,
    SERVICE_ADD_TASK,
    SERVICE_APPROVE_TASK,
    SERVICE_CLAIM_TASK,
    SERVICE_COMPLETE_TASK,
    SERVICE_NAMES,
    SERVICE_PING,
)
from .coordinator import AdhdtaskerCoordinator

_LOGGER = logging.getLogger(__name__)

_SERVICES_KEY = f"{DOMAIN}_services_registered"

# --- service schemas -------------------------------------------------------
_ENTRY = {vol.Optional("config_entry_id"): cv.string}

ADD_TASK_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Required("title"): cv.string,
        vol.Optional("type"): cv.string,
        vol.Optional("onerousness"): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
        vol.Optional("minutes"): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
        vol.Optional("assignee"): cv.string,
        vol.Optional("days"): [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))],
    }
)
ADD_INTERRUPT_SCHEMA = vol.Schema({**_ENTRY, vol.Required("title"): cv.string})
TASK_TARGET_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Optional("task_id"): cv.string,
        vol.Optional("task_title"): cv.string,
        vol.Optional("profile"): cv.string,
    }
)
PING_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Optional("title"): cv.string,
        vol.Optional("message"): cv.string,
        vol.Optional("profile"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ADHDTasker from a config entry."""
    session = async_get_clientsession(hass)
    api = AdhdtaskerApiClient(
        session,
        entry.data.get(CONF_BASE_URL, DEFAULT_API_URL),
        entry.data[CONF_API_KEY],
    )
    scan = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = AdhdtaskerCoordinator(hass, entry, api, scan)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Register a webhook so completions/dues/pings push an early refresh + fire an event.
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    fresh = False
    if not webhook_id:
        webhook_id = webhook.async_generate_id()
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_WEBHOOK_ID: webhook_id}
        )
        fresh = True
    try:
        webhook.async_register(
            hass,
            DOMAIN,
            "ADHDTasker",
            webhook_id,
            _make_webhook_handler(hass, coordinator, entry),
            allowed_methods=["POST"],
            local_only=False,
        )
    except ValueError:
        # already registered (e.g. reload race) — ignore
        pass

    if fresh:
        url = webhook.async_generate_url(hass, webhook_id)
        persistent_notification.async_create(
            hass,
            "Optional real-time push: paste this URL into the web app → "
            f"**Manage → Home Assistant** (or enable a Nabu Casa cloudhook for it):\n\n`{url}`\n\n"
            "Polling already works without it.",
            title="ADHDTasker webhook",
            notification_id=f"{DOMAIN}_webhook_{entry.entry_id}",
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))
    _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        if webhook_id := entry.data.get(CONF_WEBHOOK_ID):
            webhook.async_unregister(hass, webhook_id)
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for name in SERVICE_NAMES:
                hass.services.async_remove(DOMAIN, name)
            hass.data.pop(_SERVICES_KEY, None)
    return unloaded


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (e.g. scan interval, secret)."""
    await hass.config_entries.async_reload(entry.entry_id)


def _make_webhook_handler(
    hass: HomeAssistant, coordinator: AdhdtaskerCoordinator, entry: ConfigEntry
) -> Callable[[HomeAssistant, str, Request], Awaitable[None]]:
    async def _handle(hass: HomeAssistant, webhook_id: str, request: Request) -> None:
        try:
            data = await request.json()
        except ValueError:
            _LOGGER.warning("ADHDTasker webhook: non-JSON body ignored")
            return
        if not isinstance(data, dict):
            return
        secret = entry.options.get(CONF_SECRET)
        if secret and str(data.get("secret", "")) != str(secret):
            _LOGGER.warning("ADHDTasker webhook: secret mismatch, ignoring")
            return
        payload = {k: v for k, v in data.items() if k != "secret"}
        coordinator.set_last_event(payload)
        hass.bus.async_fire(EVENT_RECEIVED, payload)
        await coordinator.async_request_refresh()

    return _handle


# --- services --------------------------------------------------------------
def _async_register_services(hass: HomeAssistant) -> None:
    if hass.data.get(_SERVICES_KEY):
        return

    def _coordinator(call: ServiceCall) -> AdhdtaskerCoordinator:
        entries: dict[str, AdhdtaskerCoordinator] = hass.data[DOMAIN]
        entry_id = call.data.get("config_entry_id")
        if entry_id:
            if entry_id not in entries:
                raise HomeAssistantError(f"Unknown config_entry_id '{entry_id}'.")
            return entries[entry_id]
        if len(entries) == 1:
            return next(iter(entries.values()))
        raise HomeAssistantError(
            "Multiple ADHDTasker families are configured — pass config_entry_id."
        )

    async def _run(coord: AdhdtaskerCoordinator, awaitable: Awaitable[Any]) -> None:
        try:
            await awaitable
        except AdhdtaskerError as err:
            raise HomeAssistantError(f"ADHDTasker: {err}") from err
        await coord.async_request_refresh()

    async def _add_task(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await _run(
            coord,
            coord.api.add_task(
                call.data["title"],
                type=call.data.get("type"),
                onerousness=call.data.get("onerousness"),
                minutes=call.data.get("minutes"),
                assignee=call.data.get("assignee"),
                days=call.data.get("days"),
            ),
        )

    async def _add_interrupt(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await _run(coord, coord.api.add_interrupt(call.data["title"]))

    def _require_target(call: ServiceCall) -> tuple[str | None, str | None]:
        tid = call.data.get("task_id")
        ttl = call.data.get("task_title")
        if not tid and not ttl:
            raise HomeAssistantError("Provide either task_id or task_title.")
        return tid, ttl

    async def _claim_task(call: ServiceCall) -> None:
        coord = _coordinator(call)
        tid, ttl = _require_target(call)
        await _run(
            coord, coord.api.claim_task(task_id=tid, title=ttl, profile=call.data.get("profile"))
        )

    async def _complete_task(call: ServiceCall) -> None:
        coord = _coordinator(call)
        tid, ttl = _require_target(call)
        await _run(
            coord,
            coord.api.complete_task(task_id=tid, title=ttl, profile=call.data.get("profile")),
        )

    async def _approve_task(call: ServiceCall) -> None:
        coord = _coordinator(call)
        tid, ttl = _require_target(call)
        await _run(
            coord,
            coord.api.approve_task(task_id=tid, title=ttl, profile=call.data.get("profile")),
        )

    async def _ping(call: ServiceCall) -> None:
        coord = _coordinator(call)
        await _run(
            coord,
            coord.api.ping(
                title=call.data.get("title"),
                message=call.data.get("message"),
                profile=call.data.get("profile"),
            ),
        )

    hass.services.async_register(DOMAIN, SERVICE_ADD_TASK, _add_task, schema=ADD_TASK_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_INTERRUPT, _add_interrupt, schema=ADD_INTERRUPT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLAIM_TASK, _claim_task, schema=TASK_TARGET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_COMPLETE_TASK, _complete_task, schema=TASK_TARGET_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_APPROVE_TASK, _approve_task, schema=TASK_TARGET_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_PING, _ping, schema=PING_SCHEMA)
    hass.data[_SERVICES_KEY] = True
