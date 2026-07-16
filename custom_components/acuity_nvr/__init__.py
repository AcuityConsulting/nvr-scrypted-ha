"""The Acuity NVR integration.

Connects Home Assistant to an Acuity NVR (Scrypted plugin) via its REST
API — either the token-gated Scrypted public endpoint
(https://<scrypted-host>/endpoint/@acuity/nvr/public) or the standalone
server (https://<host>:10444): recordings in the media browser, optional
camera entities and motion sensors, and an optional sidebar panel that
embeds the NVR web UI.
"""

from __future__ import annotations

import logging

from homeassistant.components import frontend
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AcuityNvrApi, AcuityNvrApiError
from .const import CONF_API_TOKEN, CONF_VERIFY_SSL, CONF_WEB_UI_URL, DOMAIN
from .coordinator import AcuityNvrCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CAMERA]

type AcuityNvrConfigEntry = ConfigEntry[AcuityNvrCoordinator]


def get_entry_option(entry: ConfigEntry, key: str, default=None):
    """Read a setting from entry options, falling back to setup data."""
    return entry.options.get(key, entry.data.get(key, default))


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _panel_registry(hass: HomeAssistant) -> dict[str, str]:
    """entry_id -> registered sidebar panel url path."""
    return hass.data.setdefault(DOMAIN, {}).setdefault("panels", {})


def _register_web_ui_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Add a sidebar iframe panel embedding the NVR web UI, if configured."""
    web_ui_url = (get_entry_option(entry, CONF_WEB_UI_URL) or "").strip()
    if not web_ui_url:
        return

    panels = _panel_registry(hass)
    url_path = "acuity-nvr"
    if url_path in panels.values():
        url_path = f"acuity-nvr-{entry.entry_id[:8]}"

    try:
        frontend.async_register_built_in_panel(
            hass,
            "iframe",
            sidebar_title="Acuity NVR",
            sidebar_icon="mdi:cctv",
            frontend_url_path=url_path,
            config={"url": web_ui_url},
            require_admin=False,
        )
        panels[entry.entry_id] = url_path
    except ValueError:
        # Panel path already registered (e.g. reload race) — not fatal
        _LOGGER.debug("Sidebar panel %s already registered", url_path)


def _remove_web_ui_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    panels = _panel_registry(hass)
    url_path = panels.pop(entry.entry_id, None)
    if url_path:
        frontend.async_remove_panel(hass, url_path)


async def async_setup_entry(hass: HomeAssistant, entry: AcuityNvrConfigEntry) -> bool:
    """Set up Acuity NVR from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True)
    )
    api = AcuityNvrApi(
        session,
        entry.data[CONF_URL],
        entry.data.get(CONF_API_TOKEN) or None,
    )

    coordinator = AcuityNvrCoordinator(hass, api)
    try:
        await coordinator.async_config_entry_first_refresh()
    except AcuityNvrApiError as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _register_web_ui_panel(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AcuityNvrConfigEntry) -> bool:
    """Unload a config entry."""
    _remove_web_ui_panel(hass, entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
