"""Config flow for Fahrradwetter integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.core import HomeAssistant

DOMAIN = "fahrradwetter"

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

MODE_HYBRID = "hybrid"
MODE_OWM = "owm"
MODE_LOCAL = "local"

WIND_UNIT_KMH = "kmh"
WIND_UNIT_MS = "ms"


def _entity_selector(domain: str | None = None) -> selector.EntitySelector:
    if domain:
        return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))
    return selector.EntitySelector(selector.EntitySelectorConfig())


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        # Defaults (nice UX)
        defaults = {
            CONF_MODE: MODE_HYBRID,
            CONF_TOMORROW_TIME_1: "06:30",
            CONF_TOMORROW_TIME_2: "16:00",
            CONF_UPDATE_INTERVAL: 30,  # minutes
            CONF_WIND_UNIT: WIND_UNIT_KMH,
        }

        if user_input is not None:
            # Minimal validation
            mode = user_input.get(CONF_MODE, MODE_HYBRID)

            # Mode-specific required fields validation (extra safety)
            if mode in (MODE_OWM, MODE_HYBRID):
                if not user_input.get(CONF_API_KEY):
                    errors[CONF_API_KEY] = "required"
                if user_input.get(CONF_LAT) in (None, ""):
                    errors[CONF_LAT] = "required"
                if user_input.get(CONF_LON) in (None, ""):
                    errors[CONF_LON] = "required"

            if mode in (MODE_LOCAL, MODE_HYBRID):
                if not user_input.get(CONF_LOCAL_TEMP_ENTITY):
                    errors[CONF_LOCAL_TEMP_ENTITY] = "required"

            # If validation ok -> create entry
            if not errors:
                # Use a stable title
                title = "Fahrradwetter"
                return self.async_create_entry(title=title, data=user_input)

        # Build dynamic schema depending on selected mode
        mode_selected = (user_input or {}).get(CONF_MODE, defaults[CONF_MODE])

        base_schema = {
            vol.Required(CONF_MODE, default=mode_selected): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": MODE_HYBRID, "label": "Hybrid (lokal + OWM Forecast/Fallback)"},
                        {"value": MODE_OWM, "label": "Nur OpenWeatherMap (mit Forecast)"},
                        {"value": MODE_LOCAL, "label": "Nur lokale Sensoren (ohne Forecast)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_TOMORROW_TIME_1, default=(user_input or {}).get(CONF_TOMORROW_TIME_1, defaults[CONF_TOMORROW_TIME_1])): selector.TimeSelector(),
            vol.Optional(CONF_TOMORROW_TIME_2, default=(user_input or {}).get(CONF_TOMORROW_TIME_2, defaults[CONF_TOMORROW_TIME_2])): selector.TimeSelector(),
            vol.Optional(CONF_UPDATE_INTERVAL, default=(user_input or {}).get(CONF_UPDATE_INTERVAL, defaults[CONF_UPDATE_INTERVAL])): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=180, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="min")
            ),
            vol.Optional(CONF_WIND_UNIT, default=(user_input or {}).get(CONF_WIND_UNIT, defaults[CONF_WIND_UNIT])): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": WIND_UNIT_KMH, "label": "km/h"},
                        {"value": WIND_UNIT_MS, "label": "m/s"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        # Add OWM fields only if needed
        if mode_selected in (MODE_OWM, MODE_HYBRID):
            base_schema.update(
                {
                    vol.Required(CONF_API_KEY, default=(user_input or {}).get(CONF_API_KEY, "")): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    vol.Required(CONF_LAT, default=(user_input or {}).get(CONF_LAT, "")): vol.Coerce(float),
                    vol.Required(CONF_LON, default=(user_input or {}).get(CONF_LON, "")): vol.Coerce(float),
                }
            )

        # Add local sensor fields only if needed
        if mode_selected in (MODE_LOCAL, MODE_HYBRID):
            base_schema.update(
                {
                    vol.Required(CONF_LOCAL_TEMP_ENTITY, default=(user_input or {}).get(CONF_LOCAL_TEMP_ENTITY, "")): _entity_selector("sensor"),
                    vol.Optional(CONF_LOCAL_WIND_ENTITY, default=(user_input or {}).get(CONF_LOCAL_WIND_ENTITY, "")): _entity_selector("sensor"),
                    vol.Optional(CONF_LOCAL_RAIN_ENTITY, default=(user_input or {}).get(CONF_LOCAL_RAIN_ENTITY, "")): _entity_selector("sensor"),
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(base_schema),
            errors=errors,
        )
