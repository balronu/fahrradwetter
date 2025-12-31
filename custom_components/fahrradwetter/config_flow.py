"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

from datetime import time
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    # Modes (keep names used by coordinator)
    CONF_MODE,
    MODE_HYBRID,
    MODE_OWM_ONLY,
    MODE_LOCAL_ONLY,
    # OWM settings
    CONF_API_KEY,
    CONF_LAT,
    CONF_LON,
    # Local sensors
    CONF_LOCAL_TEMP_ENTITY,
    CONF_LOCAL_WIND_ENTITY,
    CONF_LOCAL_RAIN_ENTITY,
    # Times & other options
    CONF_TIME_MORNING,
    CONF_TIME_AFTERNOON,
    CONF_UPDATE_INTERVAL,
    CONF_WIND_UNIT,
    WIND_UNIT_KMH,
    WIND_UNIT_MS,
    DEFAULT_UPDATE_INTERVAL_MIN,
)

_LOGGER = logging.getLogger(__name__)


def _sensor_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))


def _api_key_selector() -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


def _number_box(min_v: float, max_v: float, step: float) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_v,
            max=max_v,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _defaults(hass, current: dict) -> dict:
    """Return defaults for optional fields."""
    lat = current.get(CONF_LAT)
    lon = current.get(CONF_LON)

    # Prefer existing values, else use HA home location if available
    if lat in (None, "", 0) and getattr(hass, "config", None):
        lat = getattr(hass.config, "latitude", None)
    if lon in (None, "", 0) and getattr(hass, "config", None):
        lon = getattr(hass.config, "longitude", None)

    return {
        CONF_TIME_MORNING: current.get(CONF_TIME_MORNING, time(6, 30, 0)),
        CONF_TIME_AFTERNOON: current.get(CONF_TIME_AFTERNOON, time(16, 0, 0)),
        CONF_UPDATE_INTERVAL: current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN),
        CONF_WIND_UNIT: current.get(CONF_WIND_UNIT, WIND_UNIT_KMH),
        CONF_LAT: lat,
        CONF_LON: lon,
    }


def _common_schema(defaults: dict) -> dict:
    return {
        vol.Optional(CONF_TIME_MORNING, default=defaults[CONF_TIME_MORNING]): selector.TimeSelector(),
        vol.Optional(CONF_TIME_AFTERNOON, default=defaults[CONF_TIME_AFTERNOON]): selector.TimeSelector(),
        vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5,
                max=180,
                step=5,
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


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str = MODE_HYBRID
        self._data: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: choose mode."""
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._data[CONF_MODE] = self._mode

            if self._mode == MODE_LOCAL_ONLY:
                return await self.async_step_local()
            if self._mode == MODE_OWM_ONLY:
                return await self.async_step_owm()
            return await self.async_step_hybrid()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=MODE_HYBRID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_HYBRID, "label": "Hybrid (lokal + OWM Forecast/Fallback)"},
                            {"value": MODE_OWM_ONLY, "label": "Nur OpenWeatherMap (mit Forecast)"},
                            {"value": MODE_LOCAL_ONLY, "label": "Nur lokale Sensoren (ohne Forecast)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_local(self, user_input=None):
        """Local sensors only (no OWM)."""
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, self._data)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema = {
            vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="local", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_owm(self, user_input=None):
        """OWM only."""
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, self._data)

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

        schema = {
            vol.Required(CONF_API_KEY): _api_key_selector(),
            vol.Required(CONF_LAT, default=defaults[CONF_LAT]): _number_box(-90, 90, 0.0001),
            vol.Required(CONF_LON, default=defaults[CONF_LON]): _number_box(-180, 180, 0.0001),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="owm", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_hybrid(self, user_input=None):
        """Hybrid: local sensors + OWM forecast/fallback."""
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, self._data)

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

        schema = {
            vol.Required(CONF_API_KEY): _api_key_selector(),
            vol.Required(CONF_LAT, default=defaults[CONF_LAT]): _number_box(-90, 90, 0.0001),
            vol.Required(CONF_LON, default=defaults[CONF_LON]): _number_box(-180, 180, 0.0001),
            vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="hybrid", data_schema=vol.Schema(schema), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlowHandler(config_entry)


class FahrradwetterOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Fahrradwetter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._mode: str = config_entry.options.get(CONF_MODE, config_entry.data.get(CONF_MODE, MODE_HYBRID))
        self._opts: dict = dict(config_entry.options)  # only options

    def _current(self, key: str, default=None):
        if key in self._opts:
            return self._opts.get(key)
        return self.config_entry.data.get(key, default)

    async def async_step_init(self, user_input=None):
        """Choose mode in options."""
        if user_input is not None:
            self._mode = user_input[CONF_MODE]
            self._opts[CONF_MODE] = self._mode

            if self._mode == MODE_LOCAL_ONLY:
                return await self.async_step_local()
            if self._mode == MODE_OWM_ONLY:
                return await self.async_step_owm()
            return await self.async_step_hybrid()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=self._mode): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_HYBRID, "label": "Hybrid (lokal + OWM Forecast/Fallback)"},
                            {"value": MODE_OWM_ONLY, "label": "Nur OpenWeatherMap (mit Forecast)"},
                            {"value": MODE_LOCAL_ONLY, "label": "Nur lokale Sensoren (ohne Forecast)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_local(self, user_input=None):
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, {**self.config_entry.data, **self._opts})

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_LOCAL_ONLY
                return self.async_create_entry(title="", data=self._opts)

        schema = {
            vol.Required(CONF_LOCAL_TEMP_ENTITY, default=self._current(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY, default=self._current(CONF_LOCAL_WIND_ENTITY, "")): _sensor_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=self._current(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="local", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_owm(self, user_input=None):
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, {**self.config_entry.data, **self._opts})

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"
            if not errors:
                self._opts.update(user_input)
                self._opts[CONF_MODE] = MODE_OWM_ONLY
                return self.async_create_entry(title="", data=self._opts)

        schema = {
            vol.Required(CONF_API_KEY, default=self._current(CONF_API_KEY, "")): _api_key_selector(),
            vol.Required(CONF_LAT, default=self._current(CONF_LAT, defaults[CONF_LAT])): _number_box(-90, 90, 0.0001),
            vol.Required(CONF_LON, default=self._current(CONF_LON, defaults[CONF_LON])): _number_box(-180, 180, 0.0001),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="owm", data_schema=vol.Schema(schema), errors=errors)

    async def async_step_hybrid(self, user_input=None):
        errors: dict[str, str] = {}
        defaults = _defaults(self.hass, {**self.config_entry.data, **self._opts})

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

        schema = {
            vol.Required(CONF_API_KEY, default=self._current(CONF_API_KEY, "")): _api_key_selector(),
            vol.Required(CONF_LAT, default=self._current(CONF_LAT, defaults[CONF_LAT])): _number_box(-90, 90, 0.0001),
            vol.Required(CONF_LON, default=self._current(CONF_LON, defaults[CONF_LON])): _number_box(-180, 180, 0.0001),
            vol.Required(CONF_LOCAL_TEMP_ENTITY, default=self._current(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_selector(),
            vol.Optional(CONF_LOCAL_WIND_ENTITY, default=self._current(CONF_LOCAL_WIND_ENTITY, "")): _sensor_selector(),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=self._current(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_selector(),
            **_common_schema(defaults),
        }
        return self.async_show_form(step_id="hybrid", data_schema=vol.Schema(schema), errors=errors)
