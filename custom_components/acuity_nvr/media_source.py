"""Media source: browse and play NVR recordings in Home Assistant.

Tree:  Acuity NVR  →  camera  →  recordings (newest first, playable HLS)

Identifier formats:
    ""                                   root (all cameras, all entries)
    "<entry_id>/cam/<camera_id>"         a camera's recording list
    "<entry_id>/rec/<recording_id>"      a playable recording
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN, HLS_CONTENT_TYPE, MEDIA_BROWSER_PAGE_SIZE
from .coordinator import AcuityNvrCoordinator


async def async_get_media_source(hass: HomeAssistant) -> "AcuityNvrMediaSource":
    """Set up the Acuity NVR media source."""
    return AcuityNvrMediaSource(hass)


def _format_duration(start_time: int, end_time: int | None) -> str:
    if not end_time:
        return "live"
    minutes = max(1, round((end_time - start_time) / 60_000))
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def _format_recording_title(recording: dict[str, Any]) -> str:
    start = dt_util.as_local(
        dt_util.utc_from_timestamp(recording.get("startTime", 0) / 1000)
    )
    duration = _format_duration(
        recording.get("startTime", 0), recording.get("endTime")
    )
    size_gb = recording.get("sizeBytes", 0) / 1_000_000_000
    size = f"{size_gb:.1f} GB" if size_gb >= 1 else f"{size_gb * 1000:.0f} MB"
    live = " (live)" if recording.get("isLive") else ""
    return f"{start.strftime('%b %d %I:%M %p')} — {duration}, {size}{live}"


class AcuityNvrMediaSource(MediaSource):
    """Expose NVR recordings to the Home Assistant media browser."""

    name = "Acuity NVR"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _coordinators(self) -> dict[str, AcuityNvrCoordinator]:
        """Config entry id -> coordinator, for all loaded entries."""
        return {
            entry.entry_id: entry.runtime_data
            for entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
        }

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        parts = (item.identifier or "").split("/")
        if len(parts) != 3 or parts[1] != "rec":
            raise Unresolvable(f"Invalid media identifier: {item.identifier}")

        entry_id, _, recording_id = parts
        coordinator = self._coordinators().get(entry_id)
        if coordinator is None:
            raise Unresolvable("NVR is not connected")

        url = coordinator.api.recording_playback_url(recording_id)
        return PlayMedia(url, HLS_CONTENT_TYPE)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        coordinators = self._coordinators()

        if not item.identifier:
            return self._browse_root(coordinators)

        parts = item.identifier.split("/")
        if len(parts) == 3 and parts[1] == "cam":
            entry_id, _, camera_id = parts
            coordinator = coordinators.get(entry_id)
            if coordinator is None:
                raise Unresolvable("NVR is not connected")
            return await self._browse_camera(coordinator, entry_id, camera_id)

        raise Unresolvable(f"Invalid media identifier: {item.identifier}")

    def _browse_root(
        self, coordinators: dict[str, AcuityNvrCoordinator]
    ) -> BrowseMediaSource:
        multiple_nvrs = len(coordinators) > 1
        children: list[BrowseMediaSource] = []

        for entry_id, coordinator in coordinators.items():
            host = coordinator.api.base_url
            for camera_id, camera in sorted(
                coordinator.data.cameras.items(),
                key=lambda kv: kv[1].get("name", kv[0]),
            ):
                name = camera.get("name", camera_id)
                if multiple_nvrs:
                    name = f"{name} ({host})"
                children.append(
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{entry_id}/cam/{camera_id}",
                        media_class=MediaClass.DIRECTORY,
                        media_content_type="",
                        title=name,
                        can_play=False,
                        can_expand=True,
                        children_media_class=MediaClass.VIDEO,
                    )
                )

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title="Acuity NVR",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=children,
        )

    async def _browse_camera(
        self,
        coordinator: AcuityNvrCoordinator,
        entry_id: str,
        camera_id: str,
    ) -> BrowseMediaSource:
        camera = coordinator.data.cameras.get(camera_id, {})
        recordings = await coordinator.api.get_recordings(
            camera_id, page_size=MEDIA_BROWSER_PAGE_SIZE
        )

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{entry_id}/rec/{recording['id']}",
                media_class=MediaClass.VIDEO,
                media_content_type=HLS_CONTENT_TYPE,
                title=_format_recording_title(recording),
                can_play=True,
                can_expand=False,
            )
            for recording in recordings
            if recording.get("id") is not None
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/cam/{camera_id}",
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=camera.get("name", camera_id),
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.VIDEO,
            children=children,
        )
