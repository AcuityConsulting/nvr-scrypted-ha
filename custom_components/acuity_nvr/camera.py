"""Camera platform for the Acuity NVR integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AcuityNvrConfigEntry, get_entry_option
from .const import CONF_CREATE_CAMERAS, DOMAIN
from .coordinator import AcuityNvrCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AcuityNvrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up camera entities, adding new ones as they appear on the NVR."""
    # Recordings-only mode: cameras may already be provided by a native
    # integration (e.g. Reolink), so entity creation can be turned off.
    if not get_entry_option(entry, CONF_CREATE_CAMERAS, True):
        return

    coordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def _sync_entities() -> None:
        new_entities = [
            AcuityNvrCamera(coordinator, entry.entry_id, camera_id)
            for camera_id in coordinator.data.cameras
            if camera_id not in known_ids
        ]
        known_ids.update(e.camera_id for e in new_entities)
        if new_entities:
            async_add_entities(new_entities)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class AcuityNvrCamera(CoordinatorEntity[AcuityNvrCoordinator], Camera):
    """A camera recorded by the Acuity NVR, streamed over HLS."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(
        self,
        coordinator: AcuityNvrCoordinator,
        entry_id: str,
        camera_id: str,
    ) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self.camera_id = camera_id
        self._attr_unique_id = f"{entry_id}_{camera_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{camera_id}")},
            name=self._camera.get("name", camera_id),
            manufacturer="Acuity",
            model="NVR Camera",
            configuration_url=coordinator.api.base_url,
        )

    @property
    def _camera(self) -> dict[str, Any]:
        return self.coordinator.data.cameras.get(self.camera_id, {})

    @property
    def available(self) -> bool:
        return super().available and self._camera.get("online", False)

    @property
    def is_recording(self) -> bool:
        return self._camera.get("recording", False)

    @property
    def use_stream_for_stills(self) -> bool:
        """Grab still images from the HLS stream (no snapshot endpoint needed)."""
        return True

    async def stream_source(self) -> str | None:
        """Return the live HLS playlist URL for this camera."""
        try:
            return await self.coordinator.api.get_stream_url(self.camera_id)
        except Exception as err:  # noqa: BLE001 - surface as unavailable stream
            _LOGGER.warning(
                "Could not get stream for camera %s: %s", self.camera_id, err
            )
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "nvr_camera_id": self.camera_id,
            "nvr_recording": self._camera.get("recording", False),
        }
