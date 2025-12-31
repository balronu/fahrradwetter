"""Config flow for Fahrradwetter integration (v1.1.5)."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    # required settings
    CONF_API_KEY,
    CONF_LAT,
    CONF_LON,
    # options/settings used by sensor.py
    CONF_TIMES,
    CONF_MIN_TEMP,
    CONF_MAX_WIND_KMH,
    CONF_MAX_RAIN,
    DEFAULT_TIMES,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_WIND_KMH,
    DEFAULT_MAX_RAIN,
)

TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _api_key_selector() -> selector.TextSelector:
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


def _lat_selector(default: float) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-90,
            max=90,
            step=0.0001,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="°",
        )
    )


def _lon_selector(default: float) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-180,
            max=180,
            step=0.0001,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="°",
        )
    )


def _parse_times(times_str: str) -> list[str]:
    """
    Parse "06:30, 16:00" -> ["06:30", "16:00"]
    """
    raw = [t.strip() for t in (times_str or "").split(",") if t.strip()]
    out: list[str] = []
    for t in raw:
        if not TIME_RE.match(t):
            raise ValueError("invalid_time_format")
        hh, mm = t.split(":")
        if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
            raise ValueError("invalid_time_value")
        out.append(f"{int(hh):02d}:{int(mm):02d}")
    # dedupe, keep order
    seen: set[str] = set()
    uniq: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    if not uniq:
        raise ValueError("empty_times")
    return uniq


def _times_default_str(times: Any) -> str:
    if isinstance(times, list):
        return ", ".join(str(x) for x in times)
    if isinstance(times, str) and times.strip():
        return times.strip()
    return ", ".join(DEFAULT_TIMES)


class FahrradwetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fahrradwetter."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        # Default to HA Home location
        ha_lat = float(self.hass.config.latitude or 0.0)
        ha_lon = float(self.hass.config.longitude or 0.0)

        if user_input is not None:
            # Validate required fields
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if not api_key:
                errors[CONF_API_KEY] = "required"

            # lat/lon are numbers (selector gives number), but still validate
            lat = user_input.get(CONF_LAT)
            lon = user_input.get(CONF_LON)
            if lat is None:
                errors[CONF_LAT] = "required"
            if lon is None:
                errors[CONF_LON] = "required"

            # Parse times
            try:
                times = _parse_times(user_input.get(CONF_TIMES, ""))
            except ValueError:
                errors[CONF_TIMES] = "invalid_times"

            # Validate thresholds
            try:
                min_temp = float(user_input.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
                max_wind = float(user_input.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH))
                max_rain = float(user_input.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN))
            except Exception:
                errors["base"] = "invalid_values"

            if not errors:
                # store normalized data
                data = {
                    CONF_API_KEY: api_key,
                    CONF_LAT: float(lat),
                    CONF_LON: float(lon),
                    CONF_TIMES: times,
                    CONF_MIN_TEMP: float(min_temp),
                    CONF_MAX_WIND_KMH: float(max_wind),
                    CONF_MAX_RAIN: float(max_rain),
                }

                # Optional: only one instance
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title="Fahrradwetter", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): _api_key_selector(),
                vol.Required(CONF_LAT, default=ha_lat): _lat_selector(ha_lat),
                vol.Required(CONF_LON, default=ha_lon): _lon_selector(ha_lon),

                # comma-separated list, stored as list[str] in entry.data[CONF_TIMES]
                vol.Required(CONF_TIMES, default=_times_default_str(DEFAULT_TIMES)): selector.TextSelector(
                    selector.TextSelectorConfig(
                        multiline=False,
                        placeholder="z.B. 06:30, 16:00",
                    )
                ),

                vol.Required(CONF_MIN_TEMP, default=float(DEFAULT_MIN_TEMP)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-30,
                        max=50,
                        step=0.5,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="°C",
                    )
                ),
                vol.Required(CONF_MAX_WIND_KMH, default=float(DEFAULT_MAX_WIND_KMH)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=200,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="km/h",
                    )
                ),
                vol.Required(CONF_MAX_RAIN, default=float(DEFAULT_MAX_RAIN)): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=0.1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="mm",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FahrradwetterOptionsFlowHandler(config_entry)


class FahrradwetterOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow: adjust times/thresholds without re-adding integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        current_data = self.config_entry.data
        current_opts = self.config_entry.options

        def cur(key: str, default: Any):
            return current_opts.get(key, current_data.get(key, default))

        ha_lat = float(self.hass.config.latitude or 0.0)
        ha_lon = float(self.hass.config.longitude or 0.0)

        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if not api_key:
                errors[CONF_API_KEY] = "required"

            lat = user_input.get(CONF_LAT)
            lon = user_input.get(CONF_LON)
            if lat is None:
                errors[CONF_LAT] = "required"
            if lon is None:
                errors[CONF_LON] = "required"

            try:
                times = _parse_times(user_input.get(CONF_TIMES, ""))
            except ValueError:
                errors[CONF_TIMES] = "invalid_times"

            try:
                min_temp = float(user_input.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
                max_wind = float(user_input.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH))
                max_rain = float(user_input.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN))
            except Exception:
                errors["base"] = "invalid_values"

            if not errors:
                # store as options so user can tune without recreating entry
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_API_KEY: api_key,
                        CONF_LAT: float(lat),
                        CONF_LON: float(lon),
                        CONF_TIMES: times,
                        CONF_MIN_TEMP: float(min_temp),
                        CONF_MAX_WIND_KMH: float(max_wind),
                        CONF_MAX_RAIN: float(max_rain),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=str(cur(CONF_API_KEY, ""))): _api_key_selector(),
                vol.Required(CONF_LAT, default=float(cur(CONF_LAT, ha_lat))): _lat_selector(ha_lat),
                vol.Required(CONF_LON, default=float(cur(CONF_LON, ha_lon))): _lon_selector(ha_lon),

                vol.Required(CONF_TIMES, default=_times_default_str(cur(CONF_TIMES, DEFAULT_TIMES))): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=False, placeholder="z.B. 06:30, 16:00")
                ),

                vol.Required(CONF_MIN_TEMP, default=float(cur(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=-30, max=50, step=0.5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="°C")
                ),
                vol.Required(CONF_MAX_WIND_KMH, default=float(cur(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH))): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=200, step=1, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="km/h")
                ),
                vol.Required(CONF_MAX_RAIN, default=float(cur(CONF_MAX_RAIN, DEFAULT_MAX_RAIN))): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=0.1, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="mm")
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)