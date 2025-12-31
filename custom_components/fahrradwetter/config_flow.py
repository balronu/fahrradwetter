"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

from datetime import time
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MODE,
    MODE_HYBRID,
    MODE_OWM,
    MODE_LOCAL,
    CONF_API_KEY,
    CONF_LAT,
    CONF_LON,
    CONF_LOCAL_TEMP_ENTITY,
    CONF_LOCAL_WIND_ENTITY,
    CONF_LOCAL_RAIN_ENTITY,
    CONF_TOMORROW_TIME_1,
    CONF_TOMORROW_TIME_2,
    CONF_UPDATE_INTERVAL,
    CONF_WIND_UNIT,
    WIND_UNIT_KMH,
    WIND_UNIT_MS,
    DEFAULT_UPDATE_INTERVAL_MIN,
)

_LOGGER = logging.getLogger(__name__)


def _sensor_entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))


def _api_key_selector() -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


def _time_defaults(d: dict) -> dict:
    """Return safe defaults."""
    return {
        CONF_TOMORROW_TIME_1: d.get(CONF_TOMORROW_TIME_1, time(6, 30, 0)),
        CONF_TOMORROW_TIME_2: d.get(CONF_TOMORROW_TIME_2, time(16, 0, 0)),
        CONF_UPDATE_INTERVAL: d.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN),
        CONF_WIND_UNIT: d.get(CONF_WIND_UNIT, WIND_UNIT_KMH),
    }


def _common_schema(defaults: dict) -> dict:
    """Fields used in all modes (times, update interval, wind unit)."""
    return {
        vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
        vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
        vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5, max=180, step=5,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="min",
            )
        ),
        vol.Optional(CONF_WIND_UNIT, default=defaults[CONF_WIND_UNIT]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": WIND_UNIT_KMH, "label": "km/h"},
                    {"value": WIND_UNIT_MS, "label": "m/s"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }


def _required_with_optional_default(key: str, value_selector, default_value):
    """vol.Required(key, default=...) but only if default_value is valid/truthy."""
    if default_value is None:
        return vol.Required(key)
    if isinstance(default_value, str) and default_value.strip() == "":
        return vol.Required(key)
    return vol.Required(key, default=default_value)


def _optional_with_default_if_valid(key: str, value_selector, default_value):
    """vol.Optional(key, default=...) only if default_value is valid/truthy, else no default."""
    if default_value is None:
        return vol.Optional(key)
    if isinstance(default_value, str) and default_value.strip() == "":
        return vol.Optional(key)
    return vol.Optional(key, default=default_value)


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str = MODE_HYBRID
        self._data: dict = {}

    def _ha_lat_lon_defaults(self) -> tuple[float | None, float | None]:
        """Get defaults from HA core config (Home zone)."""
        try:
            lat = float(self.hass.config.latitude) if self.hass.config.latitude is not None else None
            lon = float(self.hass.config.longitude) if self.hass.config.longitude is not None else None
            return lat, lon
        except Exception:  # noqa: BLE001
            return None, None

    async def async_step_user(self, user_input=None):
        """Choose mode."""
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
        defaults = _time_defaults(self._data)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema_dict = {
            vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_entity_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_entity_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_entity_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="local", data_schema=vol.Schema(schema_dict), errors=errors)

    async def async_step_owm(self, user_input=None):
        """OWM only."""
        errors = {}
        defaults = _time_defaults(self._data)
        ha_lat, ha_lon = self._ha_lat_lon_defaults()

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

        schema_dict = {
            vol.Required(CONF_API_KEY): _api_key_selector(),
            _required_with_optional_default(CONF_LAT, None, ha_lat): vol.Coerce(float),
            _required_with_optional_default(CONF_LON, None, ha_lon): vol.Coerce(float),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="owm", data_schema=vol.Schema(schema_dict), errors=errors)

    async def async_step_hybrid(self, user_input=None):
        """Hybrid: local sensors + OWM forecast/fallback."""
        errors = {}
        defaults = _time_defaults(self._data)
        ha_lat, ha_lon = self._ha_lat_lon_defaults()

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

        schema_dict = {
            vol.Required(CONF_API_KEY): _api_key_selector(),
            _required_with_optional_default(CONF_LAT, None, ha_lat): vol.Coerce(float),
            _required_with_optional_default(CONF_LON, None, ha_lon): vol.Coerce(float),

            vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_entity_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_entity_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_entity_selector(),

            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="hybrid", data_schema=vol.Schema(schema_dict), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlowHandler(config_entry)


class FahrradwetterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Fahrradwetter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._mode: str = config_entry.options.get(CONF_MODE, config_entry.data.get(CONF_MODE, MODE_HYBRID))
        self._opts: dict = dict(config_entry.options)

    def _current(self, key: str, default=None):
        """Prefer options, fallback to entry.data."""
        if key in self._opts:
            return self._opts.get(key)
        return self.config_entry.data.get(key, default)

    def _ha_lat_lon_defaults(self) -> tuple[float | None, float | None]:
        try:
            lat = float(self.hass.config.latitude) if self.hass.config.latitude is not None else None
            lon = float(self.hass.config.longitude) if self.hass.config.longitude is not None else None
            return lat, lon
        except Exception:  # noqa: BLE001
            return None, None

    async def async_step_init(self, user_input=None):
        """Choose mode in options."""
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
        """Options: local only."""
        errors = {}
        defaults = _time_defaults(self._opts)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_LOCAL
                return self.async_create_entry(title="", data=self._opts)

        current_temp = self._current(CONF_LOCAL_TEMP_ENTITY)
        current_wind = self._current(CONF_LOCAL_WIND_ENTITY)
        current_rain = self._current(CONF_LOCAL_RAIN_ENTITY)

        schema_dict = {
            _required_with_optional_default(CONF_LOCAL_TEMP_ENTITY, None, current_temp): _sensor_entity_selector(),
            _optional_with_default_if_valid(CONF_LOCAL_WIND_ENTITY, None, current_wind): _sensor_entity_selector(),
            _optional_with_default_if_valid(CONF_LOCAL_RAIN_ENTITY, None, current_rain): _sensor_entity_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="local", data_schema=vol.Schema(schema_dict), errors=errors)

    async def async_step_owm(self, user_input=None):
        """Options: OWM only."""
        errors = {}
        defaults = _time_defaults(self._opts)
        ha_lat, ha_lon = self._ha_lat_lon_defaults()

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

        current_key = self._current(CONF_API_KEY)
        current_lat = self._current(CONF_LAT, ha_lat)
        current_lon = self._current(CONF_LON, ha_lon)

        schema_dict = {
            _required_with_optional_default(CONF_API_KEY, None, current_key): _api_key_selector(),
            _required_with_optional_default(CONF_LAT, None, current_lat): vol.Coerce(float),
            _required_with_optional_default(CONF_LON, None, current_lon): vol.Coerce(float),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="owm", data_schema=vol.Schema(schema_dict), errors=errors)

    async def async_step_hybrid(self, user_input=None):
        """Options: hybrid."""
        errors = {}
        defaults = _time_defaults(self._opts)
        ha_lat, ha_lon = self._ha_lat_lon_defaults()

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

        current_key = self._current(CONF_API_KEY)
        current_lat = self._current(CONF_LAT, ha_lat)
        current_lon = self._current(CONF_LON, ha_lon)
        current_temp = self._current(CONF_LOCAL_TEMP_ENTITY)
        current_wind = self._current(CONF_LOCAL_WIND_ENTITY)
        current_rain = self._current(CONF_LOCAL_RAIN_ENTITY)

        schema_dict = {
            _required_with_optional_default(CONF_API_KEY, None, current_key): _api_key_selector(),
            _required_with_optional_default(CONF_LAT, None, current_lat): vol.Coerce(float),
            _required_with_optional_default(CONF_LON, None, current_lon): vol.Coerce(float),

            _required_with_optional_default(CONF_LOCAL_TEMP_ENTITY, None, current_temp): _sensor_entity_selector(),
            _optional_with_default_if_valid(CONF_LOCAL_WIND_ENTITY, None, current_wind): _sensor_entity_selector(),
            _optional_with_default_if_valid(CONF_LOCAL_RAIN_ENTITY, None, current_rain): _sensor_entity_selector(),

            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="hybrid", data_schema=vol.Schema(schema_dict), errors=errors)
