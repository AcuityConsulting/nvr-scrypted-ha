"""Data update coordinator for the Acuity NVR integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AcuityNvrApi, AcuityNvrApiError
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


@dataclass
class AcuityNvrData:
    """Snapshot of NVR state fetched each poll."""

    cameras: dict[str, dict[str, Any]] = field(default_factory=dict)
    # camera_id -> most recent event dict ({timestamp, type, id, ...})
    latest_events: dict[str, dict[str, Any]] = field(default_factory=dict)


class AcuityNvrCoordinator(DataUpdateCoordinator[AcuityNvrData]):
    """Polls cameras and recent events from the NVR."""

    def __init__(self, hass: HomeAssistant, api: AcuityNvrApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.api = api

    async def _async_update_data(self) -> AcuityNvrData:
        try:
            cameras = await self.api.get_cameras()
            events = await self.api.get_recent_events()
        except AcuityNvrApiError as err:
            raise UpdateFailed(str(err)) from err

        latest_events: dict[str, dict[str, Any]] = {}
        for event in events:
            camera_id = event.get("cameraId")
            if not camera_id:
                continue
            current = latest_events.get(camera_id)
            if current is None or event.get("timestamp", 0) > current.get("timestamp", 0):
                latest_events[camera_id] = event

        return AcuityNvrData(
            cameras={cam["id"]: cam for cam in cameras if cam.get("id")},
            latest_events=latest_events,
        )
