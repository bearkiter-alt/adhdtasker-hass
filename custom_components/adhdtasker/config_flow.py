"""Config + options flow for ADHDTasker."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AdhdtaskerApiClient, AdhdtaskerAuthError, AdhdtaskerError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_SECRET,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


def _key_uid(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


class AdhdtaskerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ADHDTasker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            base = (user_input.get(CONF_BASE_URL) or DEFAULT_API_URL).strip()
            state = await self._validate(key, base, errors)
            if state is not None:
                # Prefer a stable family id so rotating the API key keeps the same entry.
                await self.async_set_unique_id(state.get("familyId") or _key_uid(key))
                self._abort_if_unique_id_configured()
                family = state.get("family") or "ADHDTasker"
                return self.async_create_entry(
                    title=family, data={CONF_API_KEY: key, CONF_BASE_URL: base}
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Optional(CONF_BASE_URL, default=DEFAULT_API_URL): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            key = user_input[CONF_API_KEY].strip()
            base = entry.data.get(CONF_BASE_URL, DEFAULT_API_URL)
            if await self._validate(key, base, errors) is not None:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_API_KEY: key}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    async def _validate(
        self, key: str, base: str, errors: dict[str, str]
    ) -> dict | None:
        """Return the board-state dict on success, else populate errors and return None."""
        session = async_get_clientsession(self.hass)
        api = AdhdtaskerApiClient(session, base, key)
        try:
            return await api.get_state()
        except AdhdtaskerAuthError:
            errors["base"] = "invalid_auth"
        except AdhdtaskerError:
            errors["base"] = "cannot_connect"
        return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AdhdtaskerOptionsFlow()


class AdhdtaskerOptionsFlow(OptionsFlow):
    """Tune scan interval and the webhook shared secret."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=3600)),
                vol.Optional(
                    CONF_SECRET, default=opts.get(CONF_SECRET, "")
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
