DOMAIN = "fahrradwetter"

CONF_SOURCE_MODE = "source_mode"  # "owm" oder "entities"

# OWM Mode
CONF_OWM_API_KEY = "owm_api_key"
CONF_LAT = "lat"
CONF_LON = "lon"
CONF_LANG = "lang"
CONF_UNITS = "units"
CONF_UPDATE_INTERVAL = "update_interval"

# Entities Mode
CONF_TEMP_ENTITY = "temp_entity"
CONF_WIND_ENTITY = "wind_entity"
CONF_RAIN_ENTITY = "rain_entity"
CONF_FORECAST_ENTITY = "forecast_entity"
CONF_FALLBACK_TEMP_ENTITY = "fallback_temp_entity"

# Common
CONF_TIMES = "times"  # list like ["06:30","16:00"]
CONF_MIN_TEMP = "min_temp"
CONF_MAX_WIND_KMH = "max_wind_kmh"
CONF_MAX_RAIN = "max_rain"

DEFAULT_TIMES = ["06:30", "16:00"]
DEFAULT_MIN_TEMP = 10.0
DEFAULT_MAX_WIND_KMH = 15.0
DEFAULT_MAX_RAIN = 0.0

DEFAULT_LANG = "de"
DEFAULT_UNITS = "metric"
DEFAULT_UPDATE_INTERVAL = 30  # minutes
