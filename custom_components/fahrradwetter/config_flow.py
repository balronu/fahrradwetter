"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

from datetime import time

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


def _sensor_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))


def _api_key_selector() -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


def _defaults(d: dict) -> dict:
    return {
        CONF_TOMORROW_TIME_1: d.get(CONF_TOMORROW_TIME_1, time(6, 30, 0)),
        CONF_TOMORROW_TIME_2: d.get(CONF_TOMORROW_TIME_2, time(16, 0, 0)),
        CONF_UPDATE_INTERVAL: d.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN),
        CONF_WIND_UNIT: d.get(CONF_WIND_UNIT, WIND_UNIT_KMH),
    }


def _common_schema(defs: dict) -> dict:
    return {
        vol.Optional(CONF_TOMORROW_TIME_1, default=defs[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
        vol.Optional(CONF_TOMORROW_TIME_2, default=defs[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
        vol.Optional(CONF_UPDATE_INTERVAL, default=defs[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5, max=180, step=5,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="min",
            )
        ),
        vol.Optional(CONF_WIND_UNIT, default=defs[CONF_WIND_UNIT]): selector.SelectSelector(
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
    VERSION = 1

    def __init__(self) -> None:
        self._mode: str = MODE_HYBRID
        self._data: dict = {}

    def _home_lat_lon(self) -> tuple[float | None, float | None]:
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude
        try:
            return (float(lat) if lat is not None else None, float(lon) if lon is not None else None)
        except Exception:  # noqa: BLE001
            return (None, None)

    async def async_step_user(self, user_input=None):
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
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_local(self, user_input=None):
        errors = {}
        defs = _defaults(self._data)

        if user_input is not None:
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"
            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(title="Fahrradwetter", data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_selector(),
                **_common_schema(defs),
            }
        )
        return self.async_show_form(step_id="local", data_schema=schema, errors=errors)

    async def async_step_owm(self, user_input=None):
        errors = {}
        defs = _defaults(self._data)
        home_lat, home_lon = self._home_lat_lon()

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
                vol.Required(CONF_LAT, default=home_lat if home_lat is not None else 0.0): vol.Coerce(float),
                vol.Required(CONF_LON, default=home_lon if home_lon is not None else 0.0): vol.Coerce(float),
                **_common_schema(defs),
            }
        )
        return self.async_show_form(step_id="owm", data_schema=schema, errors=errors)

    async def async_step_hybrid(self, user_input=None):
        errors = {}
        defs = _defaults(self._data)
        home_lat, home_lon = self._home_lat_lon()

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
                vol.Required(CONF_LAT, default=home_lat if home_lat is not None else 0.0): vol.Coerce(float),
                vol.Required(CONF_LON, default=home_lon if home_lon is not None else 0.0): vol.Coerce(float),
                vol.Required(CONF_LOCAL_TEMP_ENTITY): _sensor_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY): _sensor_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY): _sensor_selector(),
                **_common_schema(defs),
            }
        )
        return self.async_show_form(step_id="hybrid", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlowHandler(config_entry)


class FahrradwetterOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Fahrradwetter."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Optional(CONF_UPDATE_INTERVAL, default=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN)):
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5,
                            max=180,
                            step=5,
                            mode=selector.NumberSelectorMode.SLIDER,
                            unit_of_measurement="min",
                        )
                    ),
                vol.Optional(CONF_WIND_UNIT, default=data.get(CONF_WIND_UNIT, WIND_UNIT_KMH)):
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": WIND_UNIT_KMH, "label": "km/h"},
                                {"value": WIND_UNIT_MS, "label": "m/s"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
