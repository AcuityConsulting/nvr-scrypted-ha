# Acuity NVR — Home Assistant Integration

Connects Home Assistant to an [Acuity NVR](https://www.npmjs.com/package/@acuity/nvr)
(Scrypted plugin) via its standalone REST API.

## Features

- **Camera entities** — live view of every NVR camera over HLS, with
  recording/online status. Names sync from Scrypted.
- **Media Browser** — browse and play recordings natively in Home Assistant's
  media panel (*Media → Acuity NVR → camera → recording*). Castable to
  Chromecast and other HLS-capable players.
- **Motion sensors** — a binary sensor per camera that turns on when the NVR
  records a motion/detection event, with the detection type (person, vehicle,
  animal) as an attribute. Polling-based: expect up to ~15 s latency, so
  prefer your camera's native motion entity for time-critical automations.

## Requirements

- Acuity NVR plugin **v0.5.0 or newer** running in Scrypted
- An **API Token** set in the plugin's Network settings (recommended)
- Home Assistant **2024.6** or newer

Two ways for HA to reach the NVR:

1. **Scrypted public endpoint (recommended)** — works through your SSL
   reverse proxy with a real certificate:
   `https://<scrypted-host>/endpoint/@acuity/nvr/public` + the API token.
2. **Standalone server** — `https://<host>:10444`. Uses Scrypted's
   self-signed cert by default (disable *Verify SSL certificate*), or set
   custom cert paths in the plugin. When an API token is configured, the
   standalone API requires it too.

## Installation

### Option A: manual copy

Copy `custom_components/acuity_nvr/` into your Home Assistant `config/custom_components/`
directory (create it if needed), then restart Home Assistant.

### Option B: HACS custom repository

HACS → Integrations → ⋮ → *Custom repositories* → paste
`https://github.com/AcuityConsulting/nvr-scrypted-ha`, category
*Integration* → install → restart HA.

## Setup

*Settings → Devices & Services → Add Integration → **Acuity NVR***

Enter the NVR URL (one of the two forms above) and the API token. Keep
**Verify SSL certificate** on for a reverse-proxied URL with a real cert;
turn it off for the standalone server's self-signed cert.

## Development

The integration is pure glue over the NVR REST API:

| Endpoint | Used for |
|----------|----------|
| `GET /api/cameras` | camera entities, availability |
| `GET /api/cameras/:id/stream` | live HLS stream source |
| `GET /api/recordings?cameraId=` | media browser listings |
| `GET /api/events` | motion sensors |
| `GET /hls/recording/:id/playlist.m3u8` | recording playback |
