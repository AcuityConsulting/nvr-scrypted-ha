"""Async client for the Acuity NVR REST API.

Supports both access paths the NVR plugin (>= 0.5.0) exposes:
  - Scrypted public endpoint (through a reverse proxy):
      https://scrypted.example.com/endpoint/@acuity/nvr/public
  - Standalone server:  https://<host>:10444

When the plugin has an API Token configured, requests send it as an
X-API-Key header, and media URLs (fetched by players without headers)
carry it as a ?token= query parameter — the server rewrites HLS playlists
so segment URIs include it too.
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import aiohttp


class AcuityNvrApiError(Exception):
    """Raised when the NVR API returns an error or is unreachable."""


class AcuityNvrApi:
    """Thin async wrapper over the NVR's REST endpoints."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        api_token: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_token = (api_token or "").strip() or None

    @property
    def base_url(self) -> str:
        return self._base_url

    def absolute_url(self, path: str) -> str:
        """Turn an API-relative path (e.g. /hls/...) into an absolute URL."""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base_url}/{path.lstrip('/')}"

    def media_url(self, path: str) -> str:
        """Absolute URL with the API token appended for header-less fetches."""
        url = self.absolute_url(path)
        if self._api_token:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}token={quote(self._api_token)}"
        return url

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self.absolute_url(path)
        headers = {"X-API-Key": self._api_token} if self._api_token else None
        try:
            async with asyncio.timeout(15):
                response = await self._session.get(url, params=params, headers=headers)
                if response.status == 401:
                    raise AcuityNvrApiError(
                        "NVR rejected the API token (401). Check the API Token "
                        "setting in the Acuity NVR plugin."
                    )
                if response.status != 200:
                    raise AcuityNvrApiError(
                        f"NVR API {path} returned HTTP {response.status}"
                    )
                return await response.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AcuityNvrApiError(f"Cannot reach NVR at {url}: {err}") from err

    async def get_cameras(self) -> list[dict[str, Any]]:
        """List cameras with the NVR extension enabled."""
        data = await self._get_json("/api/cameras")
        return data.get("cameras", [])

    async def get_stream_url(self, camera_id: str) -> str | None:
        """Get an absolute live HLS URL for a camera.

        The NVR starts an on-demand stream if the camera is not recording and
        waits for the first segment, so this call can take several seconds.
        """
        data = await self._get_json(f"/api/cameras/{camera_id}/stream")
        url = data.get("url")
        return self.media_url(url) if url else None

    async def get_recordings(
        self, camera_id: str, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """List recordings for a camera, newest first."""
        data = await self._get_json(
            "/api/recordings",
            params={"cameraId": camera_id, "pageSize": page_size},
        )
        return data.get("recordings", [])

    async def get_recent_events(self, page_size: int = 50) -> list[dict[str, Any]]:
        """List the most recent motion/detection events across all cameras."""
        data = await self._get_json("/api/events", params={"pageSize": page_size})
        return data.get("events", [])

    def recording_playback_url(self, recording_id: int | str) -> str:
        """Absolute HLS playlist URL for a finished or live recording."""
        return self.media_url(f"/hls/recording/{recording_id}/playlist.m3u8")
