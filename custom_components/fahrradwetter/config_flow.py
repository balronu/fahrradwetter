"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

from datetime import time
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Robust const import (fallbacks, so the flow never crashes on missing consts)
# -----------------------------------------------------------------------------
try:
    from .const import (
        DOMAIN,
        # Mode handling (optional in older versions)
        CONF_MODE,
        MODE_HYBRID,
        MODE_OWM,
        MODE_LOCAL,
        # OWM / location
        CONF_API_KEY,
        CONF_LAT,
        CONF_LON,
        # Local sensors
        CONF_LOCAL_TEMP_ENTITY,
        CONF_LOCAL_WIND_ENTITY,
        CONF_LOCAL_RAIN_ENTITY,
        # Settings
        CONF_TOMORROW_TIME_1,
        CONF_TOMORROW_TIME_2,
        CONF_UPDATE_INTERVAL,
        CONF_WIND_UNIT,
        WIND_UNIT_KMH,
        WIND_UNIT_MS,
        DEFAULT_UPDATE_INTERVAL_MIN,
    )
except Exception as err:  # pragma: no cover
    _LOGGER.error("Failed to import const.py, using fallbacks: %s", err)

    DOMAIN = "fahrradwetter"

    CONF_MODE = "mode"
    MODE_HYBRID = "hybrid"
    MODE_OWM = "owm"
    MODE_LOCAL = "local"

    CONF_API_KEY = "api_key"
    CONF_LAT = "lat"
    CONF_LON = "lon"

    CONF_LOCAL_TEMP_ENTITY = "local_temp_entity"
    CONF_LOCAL_WIND_ENTITY = "local_wind_entity"
    CONF_LOCAL_RAIN_ENTITY = "local_rain_entity"

    CONF_TOMORROW_TIME_1 = "tomorrow_time_1"
    CONF_TOMORROW_TIME_2 = "tomorrow_time_2"
    CONF_UPDATE_INTERVAL = "update_interval"
    CONF_WIND_UNIT = "wind_unit"
    WIND_UNIT_KMH = "kmh"
    WIND_UNIT_MS = "ms"
    DEFAULT_UPDATE_INTERVAL_MIN = 30


def _sensor_entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))


def _defaults(d: dict) -> dict:
    return {
        CONF_TOMORROW_TIME_1: d.get(CONF_TOMORROW_TIME_1, time(6, 30, 0)),
        CONF_TOMORROW_TIME_2: d.get(CONF_TOMORROW_TIME_2, time(16, 0, 0)),
        CONF_UPDATE_INTERVAL: d.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN),
        CONF_WIND_UNIT: d.get(CONF_WIND_UNIT, WIND_UNIT_KMH),
    }


def _api_key_selector():
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


def _lat_selector():
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-90,
            max=90,
            step=0.0001,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _lon_selector():
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-180,
            max=180,
            step=0.0001,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _wind_unit_selector(default_value: str):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": WIND_UNIT_KMH, "label": "km/h"},
                {"value": WIND_UNIT_MS, "label": "m/s"},
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _update_interval_selector(default_value: int):
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=5,
            max=180,
            step=5,
            mode=selector.NumberSelectorMode.SLIDER,
            unit_of_measurement="min",
        )
    )


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str = MODE_HYBRID
        self._data: dict = {}

    def _home_lat_lon_defaults(self) -> tuple[float, float]:
        # HA "Zone Home" / core config location
        lat = float(getattr(self.hass.config, "latitude", 0.0) or 0.0)
        lon = float(getattr(self.hass.config, "longitude", 0.0) or 0.0)
        return lat, lon

    async def async_step_user(self, user_input=None):
        """Step 1: choose mode."""
        errors = {}

        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._data[CONF_MODE] = self._mode

            if self._mode == MODE_LOCAL:
                return await self.async_step_local()
            if self._mode == MODE_OWM:
                return await self.async_step_owm()
            return await self.async_step_hybrid()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=MODE_HYBRID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_HYBRID, "label": "Hybrid (lokal + OWM Forecast/Fallback)"},
                            {"value": MODE_OWM, "label": "Nur OpenWeatherMap (mit Forecast)"},
                            {"value": MODE_LOCAL, "label": "Nur lokale Sensoren (ohne Forecast)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_local(self, user_input=None):
        """Local sensors only (no OWM)."""
        errors = {}
        defaults = _defaults(self._data)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_entity_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="local", data_schema=schema, errors=errors)

    async def async_step_owm(self, user_input=None):
        """OWM only."""
        errors = {}
        defaults = _defaults(self._data)
        home_lat, home_lon = self._home_lat_lon_defaults()

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): _api_key_selector(),
                vol.Required(CONF_LAT, default=home_lat): _lat_selector(),
                vol.Required(CONF_LON, default=home_lon): _lon_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="owm", data_schema=schema, errors=errors)

    async def async_step_hybrid(self, user_input=None):
        """Hybrid: local sensors + OWM forecast/fallback."""
        errors = {}
        defaults = _defaults(self._data)
        home_lat, home_lon = self._home_lat_lon_defaults()

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): _api_key_selector(),
                vol.Required(CONF_LAT, default=home_lat): _lat_selector(),
                vol.Required(CONF_LON, default=home_lon): _lon_selector(),

                vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_entity_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="hybrid", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlowHandler(config_entry)


class FahrradwetterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Fahrradwetter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._mode: str = config_entry.options.get(
            CONF_MODE, config_entry.data.get(CONF_MODE, MODE_HYBRID)
        )
        self._opts: dict = dict(config_entry.options)

    def _current(self, key: str, default=None):
        if key in self._opts:
            return self._opts.get(key)
        return self.config_entry.data.get(key, default)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._opts[CONF_MODE] = self._mode

            if self._mode == MODE_LOCAL:
                return await self.async_step_local()
            if self._mode == MODE_OWM:
                return await self.async_step_owm()
            return await self.async_step_hybrid()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=self._mode): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_HYBRID, "label": "Hybrid (lokal + OWM Forecast/Fallback)"},
                            {"value": MODE_OWM, "label": "Nur OpenWeatherMap (mit Forecast)"},
                            {"value": MODE_LOCAL, "label": "Nur lokale Sensoren (ohne Forecast)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_local(self, user_input=None):
        errors = {}
        defaults = _defaults(self._opts)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_LOCAL
                return self.async_create_entry(title="", data=self._opts)

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_TEMP_ENTITY, default=self._current(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY, default=self._current(CONF_LOCAL_WIND_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=self._current(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_entity_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="local", data_schema=schema, errors=errors)

    async def async_step_owm(self, user_input=None):
        errors = {}
        defaults = _defaults(self._opts)

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_OWM
                return self.async_create_entry(title="", data=self._opts)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=self._current(CONF_API_KEY, "")): _api_key_selector(),
                vol.Required(CONF_LAT, default=self._current(CONF_LAT, 0.0)): _lat_selector(),
                vol.Required(CONF_LON, default=self._current(CONF_LON, 0.0)): _lon_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="owm", data_schema=schema, errors=errors)

    async def async_step_hybrid(self, user_input=None):
        errors = {}
        defaults = _defaults(self._opts)

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_HYBRID
                return self.async_create_entry(title="", data=self._opts)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=self._current(CONF_API_KEY, "")): _api_key_selector(),
                vol.Required(CONF_LAT, default=self._current(CONF_LAT, 0.0)): _lat_selector(),
                vol.Required(CONF_LON, default=self._current(CONF_LON, 0.0)): _lon_selector(),

                vol.Required(CONF_LOCAL_TEMP_ENTITY, default=self._current(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY, default=self._current(CONF_LOCAL_WIND_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=self._current(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_entity_selector(),

                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): _update_interval_selector(defaults[CONF_UPDATE_INTERVAL]),
                vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): _wind_unit_selector(defaults[CONF_WIND_UNIT]),
            }
        )
        return self.async_show_form(step_id="hybrid", data_schema=schema, errors=errors)
