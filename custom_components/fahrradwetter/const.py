"""Constants for the Fahrradwetter integration."""

from __future__ import annotations

DOMAIN = "fahrradwetter"

# -----------------------------
# Modes
# -----------------------------
CONF_MODE = "mode"

MODE_HYBRID = "hybrid"
MODE_OWM = "owm"
MODE_LOCAL = "local"

# Backwards compatibility (falls irgendwo noch alte Namen genutzt wurden)
MODE_OWM_ONLY = MODE_OWM
MODE_LOCAL_ONLY = MODE_LOCAL

# -----------------------------
# OWM / Location
# -----------------------------
CONF_API_KEY = "api_key"
CONF_LAT = "lat"
CONF_LON = "lon"

# -----------------------------
# Local sensors (entities)
# -----------------------------
CONF_LOCAL_TEMP_ENTITY = "local_temp_entity"
CONF_LOCAL_WIND_ENTITY = "local_wind_entity"
CONF_LOCAL_RAIN_ENTITY = "local_rain_entity"

# -----------------------------
# Times / Update interval
# -----------------------------
CONF_TOMORROW_TIME_1 = "tomorrow_time_1"
CONF_TOMORROW_TIME_2 = "tomorrow_time_2"

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL_MIN = 30

# -----------------------------
# Units
# -----------------------------
CONF_WIND_UNIT = "wind_unit"
WIND_UNIT_KMH = "kmh"
WIND_UNIT_MS = "ms"
