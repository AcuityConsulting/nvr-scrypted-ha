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
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AcuityNvrApi, AcuityNvrApiError
from .const import (
    CONF_API_TOKEN,
    CONF_CREATE_CAMERAS,
    CONF_CREATE_MOTION,
    CONF_VERIFY_SSL,
    CONF_WEB_UI_URL,
    DOMAIN,
)
from .coordinator import AcuityNvrCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CAMERA]

type AcuityNvrConfigEntry = ConfigEntry[AcuityNvrCoordinator]


def get_entry_option(entry: ConfigEntry, key: str, default=None):
    """Read a setting from entry options, falling back to setup data."""
    return entry.options.get(key, entry.data.get(key, default))


def default_web_ui_url(entry: ConfigEntry) -> str:
    """Derive the NVR web UI URL from the connection settings.

    The plugin (>= 0.5.4) serves its web UI on both token-auth surfaces
    (public endpoint and standalone server), so appending ?token= to the
    configured base URL yields a working, embeddable UI address.
    """
    base = (entry.data.get(CONF_URL) or "").rstrip("/")
    if not base:
        return ""
    token = entry.data.get(CONF_API_TOKEN)
    return f"{base}/?token={token}" if token else f"{base}/"


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _panel_registry(hass: HomeAssistant) -> dict[str, str]:
    """entry_id -> registered sidebar panel url path."""
    return hass.data.setdefault(DOMAIN, {}).setdefault("panels", {})


def _register_web_ui_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Add a sidebar iframe panel embedding the NVR web UI.

    Enabled by default using a URL derived from the connection settings;
    saving an empty Web UI URL in the options disables the panel.
    """
    if CONF_WEB_UI_URL in entry.options:
        web_ui_url = (entry.options[CONF_WEB_UI_URL] or "").strip()
    else:
        web_ui_url = default_web_ui_url(entry)
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
            sidebar_title="NVR",
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


def _cleanup_disabled_platforms(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove registry entities/devices for platforms the user turned off.

    Without this, unchecking "Create camera entities" / "Create motion
    sensors" leaves orphaned devices behind in the device registry.
    """
    create_cameras = get_entry_option(entry, CONF_CREATE_CAMERAS, True)
    create_motion = get_entry_option(entry, CONF_CREATE_MOTION, True)
    if create_cameras and create_motion:
        return

    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if (entity.domain == "camera" and not create_cameras) or (
            entity.domain == "binary_sensor" and not create_motion
        ):
            entity_registry.async_remove(entity.entity_id)

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        remaining = er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=True
        )
        if not remaining:
            device_registry.async_update_device(
                device.id, remove_config_entry_id=entry.entry_id
            )


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
    _cleanup_disabled_platforms(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AcuityNvrConfigEntry) -> bool:
    """Unload a config entry."""
    _remove_web_ui_panel(hass, entry)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
