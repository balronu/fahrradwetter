from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_LAT,
    CONF_LON,
    CONF_MODE,
    MODE_OWM_ONLY,
    MODE_LOCAL_ONLY,
    MODE_HYBRID,
    CONF_LOCAL_TEMP_ENTITY,
    CONF_LOCAL_WIND_ENTITY,
    CONF_LOCAL_RAIN_ENTITY,
    CONF_LOCAL_WIND_UNIT,
    WIND_UNIT_MS,
    WIND_UNIT_KMH,
    CONF_TIME_MORNING,
    CONF_TIME_AFTERNOON,
)

DEFAULTS = {
    CONF_MODE: MODE_HYBRID,
    CONF_TIME_MORNING: "06:30",
    CONF_TIME_AFTERNOON: "16:00",
    CONF_LOCAL_WIND_UNIT: WIND_UNIT_MS,
}

def _base_schema(user_input: dict | None = None):
    ui = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_MODE, default=ui.get(CONF_MODE, DEFAULTS[CONF_MODE])): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": MODE_HYBRID, "label": "Hybrid (lokal bevorzugt + OWM Fallback + Forecast)"},
                        {"value": MODE_OWM_ONLY, "label": "Nur OpenWeatherMap (OWM)"},
                        {"value": MODE_LOCAL_ONLY, "label": "Nur lokale Sensoren (ohne Forecast)"},
                    ],
                    mode="dropdown",
                )
            ),
            vol.Optional(CONF_API_KEY, default=ui.get(CONF_API_KEY, "")): TextSelector(TextSelectorConfig(type="password")),
            vol.Required(CONF_LAT, default=ui.get(CONF_LAT, "")): TextSelector(TextSelectorConfig()),
            vol.Required(CONF_LON, default=ui.get(CONF_LON, "")): TextSelector(TextSelectorConfig()),
            vol.Optional(CONF_LOCAL_TEMP_ENTITY, default=ui.get(CONF_LOCAL_TEMP_ENTITY, "")): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_LOCAL_WIND_ENTITY, default=ui.get(CONF_LOCAL_WIND_ENTITY, "")): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=ui.get(CONF_LOCAL_RAIN_ENTITY, "")): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_LOCAL_WIND_UNIT, default=ui.get(CONF_LOCAL_WIND_UNIT, DEFAULTS[CONF_LOCAL_WIND_UNIT])): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": WIND_UNIT_MS, "label": "m/s"},
                        {"value": WIND_UNIT_KMH, "label": "km/h"},
                    ],
                    mode="dropdown",
                )
            ),
            vol.Required(CONF_TIME_MORNING, default=ui.get(CONF_TIME_MORNING, DEFAULTS[CONF_TIME_MORNING])): TextSelector(
                TextSelectorConfig()
            ),
            vol.Required(CONF_TIME_AFTERNOON, default=ui.get(CONF_TIME_AFTERNOON, DEFAULTS[CONF_TIME_AFTERNOON])): TextSelector(
                TextSelectorConfig()
            ),
        }
    )

def _validate_input(data: dict):
    mode = data.get(CONF_MODE, MODE_HYBRID)

    # OWM ist Pflicht für owm_only und hybrid (weil Forecast)
    if mode in (MODE_OWM_ONLY, MODE_HYBRID):
        if not data.get(CONF_API_KEY):
            return "missing_api_key"
        if not data.get(CONF_LAT) or not data.get(CONF_LON):
            return "missing_lat_lon"

    # local_only braucht zumindest TEMP+WIND+RAIN oder du bekommst "unvollständig"
    if mode == MODE_LOCAL_ONLY:
        if not (data.get(CONF_LOCAL_TEMP_ENTITY) and data.get(CONF_LOCAL_WIND_ENTITY) and data.get(CONF_LOCAL_RAIN_ENTITY)):
            return "missing_local_entities"

    return None

class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            err = _validate_input(user_input)
            if err:
                errors["base"] = err
            else:
                title = "Fahrradwetter"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_base_schema(user_input),
            errors=errors,
        )
