from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    EntitySelector, EntitySelectorConfig,
    NumberSelector, NumberSelectorConfig, NumberSelectorMode,
    TextSelector, TextSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_SOURCE_MODE,
    CONF_OWM_API_KEY,
    CONF_LAT,
    CONF_LON,
    CONF_LANG,
    CONF_UNITS,
    CONF_UPDATE_INTERVAL,
    CONF_TEMP_ENTITY,
    CONF_WIND_ENTITY,
    CONF_RAIN_ENTITY,
    CONF_FORECAST_ENTITY,
    CONF_FALLBACK_TEMP_ENTITY,
    CONF_TIMES,
    CONF_MIN_TEMP,
    CONF_MAX_WIND_KMH,
    CONF_MAX_RAIN,
    DEFAULT_TIMES,
    DEFAULT_LANG,
    DEFAULT_UNITS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_WIND_KMH,
    DEFAULT_MAX_RAIN,
)

def _times_str(times: list[str] | None) -> str:
    return ",".join(times or DEFAULT_TIMES)

def _parse_times(s: str | None) -> list[str]:
    raw = (s or "").strip()
    times = [t.strip() for t in raw.split(",") if t.strip()]
    out = []
    for t in times:
        if len(t) == 5 and t[2] == ":":
            out.append(t)
    return out or DEFAULT_TIMES

COMMON_SCHEMA = {
    vol.Optional(CONF_TIMES, default=_times_str(DEFAULT_TIMES)): TextSelector(TextSelectorConfig(multiline=False)),
    vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP):
        NumberSelector(NumberSelectorConfig(min=-30, max=40, step=0.5, mode=NumberSelectorMode.BOX)),
    vol.Optional(CONF_MAX_WIND_KMH, default=DEFAULT_MAX_WIND_KMH):
        NumberSelector(NumberSelectorConfig(min=0, max=120, step=0.5, mode=NumberSelectorMode.BOX)),
    vol.Optional(CONF_MAX_RAIN, default=DEFAULT_MAX_RAIN):
        NumberSelector(NumberSelectorConfig(min=0, max=50, step=0.1, mode=NumberSelectorMode.BOX)),
    vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL):
        NumberSelector(NumberSelectorConfig(min=5, max=180, step=5, mode=NumberSelectorMode.BOX)),
}

class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_SOURCE_MODE, default="owm"):
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"value": "owm", "label": "OpenWeatherMap direkt (API Key)"},
                                {"value": "entities", "label": "Vorhandene Sensoren/Entities nutzen"},
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                vol.Optional(CONF_NAME, default="Fahrradwetter"): str,
            })
            return self.async_show_form(step_id="user", data_schema=schema)

        self._name = user_input.get(CONF_NAME, "Fahrradwetter")
        self._mode = user_input[CONF_SOURCE_MODE]
        if self._mode == "owm":
            return await self.async_step_owm()
        return await self.async_step_entities()

    async def async_step_owm(self, user_input=None):
        if user_input is None:
            schema = vol.Schema({
                **COMMON_SCHEMA,
                vol.Required(CONF_OWM_API_KEY): str,
                vol.Required(CONF_LAT): vol.Coerce(float),
                vol.Required(CONF_LON): vol.Coerce(float),
                vol.Optional(CONF_LANG, default=DEFAULT_LANG): str,
                vol.Optional(CONF_UNITS, default=DEFAULT_UNITS):
                    SelectSelector(SelectSelectorConfig(options=["metric", "imperial"], mode=SelectSelectorMode.DROPDOWN)),
            })
            return self.async_show_form(step_id="owm", data_schema=schema)

        data = dict(user_input)
        data[CONF_SOURCE_MODE] = "owm"
        data[CONF_TIMES] = _parse_times(data.get(CONF_TIMES))

        options = {
            CONF_LANG: data.pop(CONF_LANG, DEFAULT_LANG),
            CONF_UNITS: data.pop(CONF_UNITS, DEFAULT_UNITS),
            CONF_UPDATE_INTERVAL: data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            CONF_TIMES: data.get(CONF_TIMES, DEFAULT_TIMES),
            CONF_MIN_TEMP: data.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
            CONF_MAX_WIND_KMH: data.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH),
            CONF_MAX_RAIN: data.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN),
        }
        return self.async_create_entry(title=self._name, data=data, options=options)

    async def async_step_entities(self, user_input=None):
        if user_input is None:
            schema = vol.Schema({
                **COMMON_SCHEMA,
                vol.Required(CONF_TEMP_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_WIND_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_RAIN_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Optional(CONF_FALLBACK_TEMP_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor")),
                vol.Required(CONF_FORECAST_ENTITY): EntitySelector(EntitySelectorConfig(domain="sensor")),
            })
            return self.async_show_form(step_id="entities", data_schema=schema)

        data = dict(user_input)
        data[CONF_SOURCE_MODE] = "entities"
        data[CONF_TIMES] = _parse_times(data.get(CONF_TIMES))

        options = {
            CONF_UPDATE_INTERVAL: data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            CONF_TIMES: data.get(CONF_TIMES, DEFAULT_TIMES),
            CONF_MIN_TEMP: data.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
            CONF_MAX_WIND_KMH: data.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH),
            CONF_MAX_RAIN: data.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN),
        }
        return self.async_create_entry(title=self._name, data=data, options=options)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlow(config_entry)

class FahrradwetterOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            schema = vol.Schema({
                vol.Optional(CONF_TIMES, default=_times_str(self.entry.options.get(CONF_TIMES, DEFAULT_TIMES))):
                    TextSelector(TextSelectorConfig(multiline=False)),
                vol.Optional(CONF_MIN_TEMP, default=self.entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)):
                    NumberSelector(NumberSelectorConfig(min=-30, max=40, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Optional(CONF_MAX_WIND_KMH, default=self.entry.options.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH)):
                    NumberSelector(NumberSelectorConfig(min=0, max=120, step=0.5, mode=NumberSelectorMode.BOX)),
                vol.Optional(CONF_MAX_RAIN, default=self.entry.options.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN)):
                    NumberSelector(NumberSelectorConfig(min=0, max=50, step=0.1, mode=NumberSelectorMode.BOX)),
                vol.Optional(CONF_UPDATE_INTERVAL, default=self.entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)):
                    NumberSelector(NumberSelectorConfig(min=5, max=180, step=5, mode=NumberSelectorMode.BOX)),
            })
            if self.entry.data.get(CONF_SOURCE_MODE) == "owm":
                schema = schema.extend({
                    vol.Optional(CONF_LANG, default=self.entry.options.get(CONF_LANG, DEFAULT_LANG)): str,
                    vol.Optional(CONF_UNITS, default=self.entry.options.get(CONF_UNITS, DEFAULT_UNITS)):
                        SelectSelector(SelectSelectorConfig(options=["metric", "imperial"], mode=SelectSelectorMode.DROPDOWN)),
                })
            return self.async_show_form(step_id="init", data_schema=schema)

        opts = dict(self.entry.options)
        opts.update(user_input)
        opts[CONF_TIMES] = _parse_times(opts.get(CONF_TIMES))
        return self.async_create_entry(title="", data=opts)
