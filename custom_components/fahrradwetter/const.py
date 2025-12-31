"""Constants for Fahrradwetter integration."""

DOMAIN = "fahrradwetter"

# OWM / Location
CONF_API_KEY = "api_key"
CONF_LAT = "lat"
CONF_LON = "lon"

# Local sensors
CONF_LOCAL_TEMP_ENTITY = "local_temp_entity"
CONF_LOCAL_WIND_ENTITY = "local_wind_entity"
CONF_LOCAL_RAIN_ENTITY = "local_rain_entity"

# Evaluation settings
CONF_TIMES = "times"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_WIND_KMH = "max_wind_kmh"
CONF_MAX_RAIN = "max_rain"

# Defaults
DEFAULT_TIMES = ["06:30", "16:00"]
DEFAULT_MIN_TEMP = 5.0
DEFAULT_MAX_WIND_KMH = 25.0
DEFAULT_MAX_RAIN = 0.5