"""Constants for the Acuity NVR integration."""

DOMAIN = "acuity_nvr"

CONF_API_TOKEN = "api_token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_WEB_UI_URL = "web_ui_url"
CONF_CREATE_CAMERAS = "create_cameras"
CONF_CREATE_MOTION = "create_motion_sensors"

# Seconds between coordinator polls of the NVR API
UPDATE_INTERVAL_SECONDS = 15

# A motion/detection binary sensor stays "on" for this long after the
# most recent event (the NVR records event timestamps, not durations).
MOTION_ACTIVE_WINDOW_SECONDS = 60

# Maximum recordings listed per camera in the media browser
MEDIA_BROWSER_PAGE_SIZE = 100

HLS_CONTENT_TYPE = "application/vnd.apple.mpegurl"
