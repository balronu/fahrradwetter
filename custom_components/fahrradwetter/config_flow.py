"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

DOMAIN = "fahrradwetter"

# ---- keys ----
CONF_MODE = "mode"
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

# ---- modes ----
MODE_HYBRID = "hybrid"
MODE_OWM = "owm"
MODE_LOCAL = "local"

# ---- wind units ----
WIND_UNIT_KMH = "kmh"
WIND_UNIT_MS = "ms"


def _sensor_entity_selector():
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))


def _defaults(user_input: dict | None = None) -> dict:
    user_input = user_input or {}
    return {
        CONF_TOMORROW_TIME_1: user_input.get(CONF_TOMORROW_TIME_1, "06:30:00"),
        CONF_TOMORROW_TIME_2: user_input.get(CONF_TOMORROW_TIME_2, "16:00:00"),
        CONF_UPDATE_INTERVAL: user_input.get(CONF_UPDATE_INTERVAL, 30),
        CONF_WIND_UNIT: user_input.get(CONF_WIND_UNIT, WIND_UNIT_KMH),
    }


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    def __init__(self) -> None:
        self._mode: str | None = None
        self._base: dict = {}

    async def async_step_user(self, user_input=None):
        """Step 1: select mode only (prevents wrong required fields)."""
        errors = {}

        if user_input is not None:
            self._mode = user_input[CONF_MODE]

            # Store base/common settings already entered (none here yet, but keep structure)
            self._base = {}
            # Go to mode-specific step
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
        """Step 2a: local only."""
        errors = {}
        defaults = _defaults(user_input)

        if user_input is not None:
            # local temp is required
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                data = {
                    **self._base,
                    CONF_MODE: MODE_LOCAL,
                    **user_input,
                }
                return self.async_create_entry(title="Fahrradwetter", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCAL_TEMP_ENTITY, default=(user_input or {}).get(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY, default=(user_input or {}).get(CONF_LOCAL_WIND_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=(user_input or {}).get(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=180, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="min"
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
        )

        return self.async_show_form(step_id="local", data_schema=schema, errors=errors)

    async def async_step_owm(self, user_input=None):
        """Step 2b: OWM only."""
        errors = {}
        defaults = _defaults(user_input)

        if user_input is not None:
            # required owm fields
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"

            if not errors:
                data = {
                    **self._base,
                    CONF_MODE: MODE_OWM,
                    **user_input,
                }
                return self.async_create_entry(title="Fahrradwetter", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=(user_input or {}).get(CONF_API_KEY, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_LAT, default=(user_input or {}).get(CONF_LAT, "")): vol.Coerce(float),
                vol.Required(CONF_LON, default=(user_input or {}).get(CONF_LON, "")): vol.Coerce(float),
                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=180, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="min"
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
        )

        return self.async_show_form(step_id="owm", data_schema=schema, errors=errors)

    async def async_step_hybrid(self, user_input=None):
        """Step 2c: Hybrid (local + OWM)."""
        errors = {}
        defaults = _defaults(user_input)

        if user_input is not None:
            # required for hybrid: api_key/lat/lon + local temp entity
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "required"
            if user_input.get(CONF_LAT) in (None, ""):
                errors[CONF_LAT] = "required"
            if user_input.get(CONF_LON) in (None, ""):
                errors[CONF_LON] = "required"
            if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            if not errors:
                data = {
                    **self._base,
                    CONF_MODE: MODE_HYBRID,
                    **user_input,
                }
                return self.async_create_entry(title="Fahrradwetter", data=data)

        schema = vol.Schema(
            {
                # OWM required
                vol.Required(CONF_API_KEY, default=(user_input or {}).get(CONF_API_KEY, "")): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Required(CONF_LAT, default=(user_input or {}).get(CONF_LAT, "")): vol.Coerce(float),
                vol.Required(CONF_LON, default=(user_input or {}).get(CONF_LON, "")): vol.Coerce(float),
                # local (temp required, others optional)
                vol.Required(CONF_LOCAL_TEMP_ENTITY, default=(user_input or {}).get(CONF_LOCAL_TEMP_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_WIND_ENTITY, default=(user_input or {}).get(CONF_LOCAL_WIND_ENTITY, "")): _sensor_entity_selector(),
                vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=(user_input or {}).get(CONF_LOCAL_RAIN_ENTITY, "")): _sensor_entity_selector(),
                # common
                vol.Optional(CONF_TOMORROW_TIME_1, default=defaults[CONF_TOMORROW_TIME_1]): selector.TimeSelector(),
                vol.Optional(CONF_TOMORROW_TIME_2, default=defaults[CONF_TOMORROW_TIME_2]): selector.TimeSelector(),
                vol.Optional(CONF_UPDATE_INTERVAL, default=defaults[CONF_UPDATE_INTERVAL]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=180, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="min"
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
        )

        return self.async_show_form(step_id="hybrid", data_schema=schema, errors=errors)
