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

- Acuity NVR plugin **v0.4.11 or newer** running in Scrypted
- The plugin's **standalone server enabled** (default port 10444 — see the
  plugin's Network settings)
- Home Assistant **2024.6** or newer
- HA must be able to reach the Scrypted host on the standalone port

> **Security note:** the standalone server is unauthenticated. Keep port
> 10444 restricted to your trusted LAN.

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

Enter the Scrypted host and standalone port (10444). Leave **Verify SSL
certificate** off — the standalone server uses Scrypted's self-signed cert.

## Development

The integration is pure glue over the NVR REST API:

| Endpoint | Used for |
|----------|----------|
| `GET /api/cameras` | camera entities, availability |
| `GET /api/cameras/:id/stream` | live HLS stream source |
| `GET /api/recordings?cameraId=` | media browser listings |
| `GET /api/events` | motion sensors |
| `GET /hls/recording/:id/playlist.m3u8` | recording playback |
