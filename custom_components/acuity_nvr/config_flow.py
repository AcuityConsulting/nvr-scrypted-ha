"""Config flow for the Acuity NVR integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AcuityNvrApi, AcuityNvrApiError
from .const import CONF_API_TOKEN, CONF_VERIFY_SSL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_API_TOKEN, default=""): str,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)


class AcuityNvrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")

            if not url.startswith(("http://", "https://")):
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()

                session = async_get_clientsession(
                    self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
                )
                api = AcuityNvrApi(
                    session, url, user_input.get(CONF_API_TOKEN) or None
                )

                try:
                    await api.get_cameras()
                except AcuityNvrApiError as err:
                    _LOGGER.debug("Connection test failed: %s", err)
                    errors["base"] = (
                        "invalid_auth" if "401" in str(err) or "token" in str(err).lower()
                        else "cannot_connect"
                    )
                else:
                    return self.async_create_entry(
                        title=f"Acuity NVR ({url.split('//', 1)[-1].split('/', 1)[0]})",
                        data={**user_input, CONF_URL: url},
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
