"""Motion/detection binary sensors for the Acuity NVR integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import AcuityNvrConfigEntry, get_entry_option
from .const import CONF_CREATE_MOTION, DOMAIN, MOTION_ACTIVE_WINDOW_SECONDS
from .coordinator import AcuityNvrCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AcuityNvrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up motion sensors, adding new ones as cameras appear on the NVR."""
    # Optional: native camera integrations (e.g. Reolink) provide push-based
    # motion sensors, so the NVR's polled ones can be turned off.
    if not get_entry_option(entry, CONF_CREATE_MOTION, True):
        return

    coordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def _sync_entities() -> None:
        new_entities = [
            AcuityNvrMotionSensor(coordinator, entry.entry_id, camera_id)
            for camera_id in coordinator.data.cameras
            if camera_id not in known_ids
        ]
        known_ids.update(e.camera_id for e in new_entities)
        if new_entities:
            async_add_entities(new_entities)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class AcuityNvrMotionSensor(
    CoordinatorEntity[AcuityNvrCoordinator], BinarySensorEntity
):
    """On when the NVR recorded a motion/detection event recently.

    The NVR stores event timestamps (not durations), so the sensor reports
    "on" for MOTION_ACTIVE_WINDOW_SECONDS after the latest event. Detection
    details (person/vehicle/animal) are exposed as attributes.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "nvr_motion"

    def __init__(
        self,
        coordinator: AcuityNvrCoordinator,
        entry_id: str,
        camera_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.camera_id = camera_id
        self._attr_unique_id = f"{entry_id}_{camera_id}_motion"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{camera_id}")},
        )

    @property
    def _latest_event(self) -> dict[str, Any] | None:
        return self.coordinator.data.latest_events.get(self.camera_id)

    @property
    def is_on(self) -> bool:
        event = self._latest_event
        if not event:
            return False
        age_ms = dt_util.utcnow().timestamp() * 1000 - event.get("timestamp", 0)
        return age_ms <= MOTION_ACTIVE_WINDOW_SECONDS * 1000

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._latest_event
        if not event:
            return {}
        return {
            "last_event_type": event.get("type"),
            "last_event_time": dt_util.utc_from_timestamp(
                event.get("timestamp", 0) / 1000
            ).isoformat(),
        }
