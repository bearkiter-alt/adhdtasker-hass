"""Thin async client for the ADHDTasker family-scoped inbound API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = 30


class AdhdtaskerError(Exception):
    """Generic error talking to the ADHDTasker API."""


class AdhdtaskerAuthError(AdhdtaskerError):
    """The API key is missing, invalid, or revoked."""


class AdhdtaskerApiClient:
    """Talks to the `/api` endpoint with an `X-API-Key` header.

    Mirrors the documented actions: GET (board state) + POST add_task,
    add_interrupt, claim_task, complete_task, ping.
    """

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str, api_key: str
    ) -> None:
        self._session = session
        self._url = base_url.rstrip("/")
        self._key = api_key

    async def _request(
        self, method: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {"X-API-Key": self._key, "Content-Type": "application/json"}
        try:
            async with asyncio.timeout(_TIMEOUT):
                async with self._session.request(
                    method, self._url, headers=headers, json=payload
                ) as resp:
                    if resp.status in (401, 403):
                        raise AdhdtaskerAuthError(f"Auth rejected ({resp.status}).")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise AdhdtaskerError(f"HTTP {resp.status}: {text[:200]}")
                    try:
                        data = await resp.json(content_type=None)
                    except (ValueError, aiohttp.ContentTypeError) as err:
                        raise AdhdtaskerError(
                            "ADHDTasker returned a non-JSON response."
                        ) from err
                    if not isinstance(data, dict):
                        raise AdhdtaskerError(
                            "ADHDTasker returned an unexpected (non-object) response."
                        )
                    return data
        except AdhdtaskerError:
            raise
        except aiohttp.ClientError as err:
            raise AdhdtaskerError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise AdhdtaskerError("Timed out talking to ADHDTasker.") from err

    async def get_state(self) -> dict[str, Any]:
        """Return board state: family, open, counts, tasks[], leaderboard[]."""
        return await self._request("GET")

    async def _post(self, action: str, **body: Any) -> dict[str, Any]:
        clean = {k: v for k, v in body.items() if v is not None}
        return await self._request("POST", {"action": action, **clean})

    async def add_task(
        self,
        title: str,
        *,
        type: str | None = None,
        onerousness: int | None = None,
        minutes: int | None = None,
        assignee: str | None = None,
        days: list[int] | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "add_task",
            title=title,
            type=type,
            onerousness=onerousness,
            minutes=minutes,
            assignee=assignee,
            days=days,
        )

    async def add_interrupt(self, title: str) -> dict[str, Any]:
        return await self._post("add_interrupt", title=title)

    async def update_task(
        self,
        *,
        task_id: str | None = None,
        title: str | None = None,
        onerousness: int | None = None,
        minutes: int | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        # The backend selects the task by `id` and uses `title` as the new title.
        return await self._post(
            "update_task",
            id=task_id,
            title=title,
            onerousness=onerousness,
            minutes=minutes,
            assignee=assignee,
        )

    async def delete_task(
        self, *, task_id: str | None = None, title: str | None = None
    ) -> dict[str, Any]:
        return await self._post("delete_task", id=task_id, title=title)

    async def approve_task(
        self,
        *,
        task_id: str | None = None,
        title: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        return await self._post("approve_task", id=task_id, title=title, profile=profile)

    async def claim_task(
        self,
        *,
        task_id: str | None = None,
        title: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        return await self._post("claim_task", id=task_id, title=title, profile=profile)

    async def complete_task(
        self,
        *,
        task_id: str | None = None,
        title: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            "complete_task", id=task_id, title=title, profile=profile
        )

    async def ping(
        self,
        *,
        title: str | None = None,
        message: str | None = None,
        profile: str | None = None,
    ) -> dict[str, Any]:
        return await self._post("ping", title=title, message=message, profile=profile)
