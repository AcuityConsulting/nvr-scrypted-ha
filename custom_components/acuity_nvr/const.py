"""Constants for the Acuity NVR integration."""

DOMAIN = "acuity_nvr"

CONF_USE_SSL = "use_ssl"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 10444
DEFAULT_USE_SSL = True
DEFAULT_VERIFY_SSL = False

# Seconds between coordinator polls of the NVR API
UPDATE_INTERVAL_SECONDS = 15

# A motion/detection binary sensor stays "on" for this long after the
# most recent event (the NVR records event timestamps, not durations).
MOTION_ACTIVE_WINDOW_SECONDS = 60

# Maximum recordings listed per camera in the media browser
MEDIA_BROWSER_PAGE_SIZE = 100

HLS_CONTENT_TYPE = "application/vnd.apple.mpegurl"
