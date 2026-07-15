"""The Acuity NVR integration.

Connects Home Assistant to an Acuity NVR (Scrypted plugin) via its REST
API — either the token-gated Scrypted public endpoint
(https://<scrypted-host>/endpoint/@acuity/nvr/public) or the standalone
server (https://<host>:10444): live camera streams, recordings in the
media browser, and motion/detection sensors.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AcuityNvrApi, AcuityNvrApiError
from .const import CONF_API_TOKEN, CONF_VERIFY_SSL
from .coordinator import AcuityNvrCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CAMERA]

type AcuityNvrConfigEntry = ConfigEntry[AcuityNvrCoordinator]


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AcuityNvrConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
