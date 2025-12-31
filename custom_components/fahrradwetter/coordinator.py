from __future__ import annotations

from datetime import timedelta
from typing import Any

import logging
from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

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
)

_LOGGER = logging.getLogger(__name__)

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _is_bad(state: str | None) -> bool:
    return state in (None, "unknown", "unavailable", "none", "")


class FahrradwetterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self.entry = entry
        self.mode = entry.data[CONF_SOURCE_MODE]

        update_minutes = int(entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, 30)))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(minutes=update_minutes),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.mode == "owm":
                return await self._fetch_owm()
            return self._read_entities()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch_owm(self) -> dict[str, Any]:
        api_key = self.entry.data[CONF_OWM_API_KEY]
        lat = self.entry.data[CONF_LAT]
        lon = self.entry.data[CONF_LON]
        lang = self.entry.options.get(CONF_LANG, self.entry.data.get(CONF_LANG, "de"))
        units = self.entry.options.get(CONF_UNITS, self.entry.data.get(CONF_UNITS, "metric"))

        params = {"lat": lat, "lon": lon, "appid": api_key, "units": units, "lang": lang}

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(OWM_CURRENT_URL, params=params, timeout=20) as r1:
                if r1.status != 200:
                    txt = await r1.text()
                    raise UpdateFailed(f"OWM current HTTP {r1.status}: {txt[:120]}")
                current = await r1.json()

            async with session.get(OWM_FORECAST_URL, params=params, timeout=20) as r2:
                if r2.status != 200:
                    txt = await r2.text()
                    raise UpdateFailed(f"OWM forecast HTTP {r2.status}: {txt[:120]}")
                forecast = await r2.json()
        except ClientError as err:
            raise UpdateFailed(f"OWM request failed: {err}") from err

        data: dict[str, Any] = {
            "source": "owm",
            "current": {
                "temp": (current.get("main") or {}).get("temp"),
                "wind_ms": (current.get("wind") or {}).get("speed"),
                "rain_1h": ((current.get("rain") or {}) or {}).get("1h", 0),
                "desc": ((current.get("weather") or [{}]) or [{}])[0].get("description"),
            },
            "forecast_list": forecast.get("list", []) or [],
            "fetched_at": dt_util.now().isoformat(),
        }
        return data

    def _read_entities(self) -> dict[str, Any]:
        temp_e = self.entry.data.get(CONF_TEMP_ENTITY)
        wind_e = self.entry.data.get(CONF_WIND_ENTITY)
        rain_e = self.entry.data.get(CONF_RAIN_ENTITY)
        fallback_temp_e = self.entry.data.get(CONF_FALLBACK_TEMP_ENTITY)
        forecast_e = self.entry.data.get(CONF_FORECAST_ENTITY)

        def state_float(eid: str | None):
            if not eid:
                return None
            st = self.hass.states.get(eid)
            if not st or _is_bad(st.state):
                return None
            try:
                return float(st.state)
            except Exception:
                return None

        def attr_list(eid: str | None, attr: str):
            if not eid:
                return []
            st = self.hass.states.get(eid)
            if not st:
                return []
            v = st.attributes.get(attr)
            return v if isinstance(v, list) else []

        temp = state_float(temp_e)
        if temp is None and fallback_temp_e:
            temp = state_float(fallback_temp_e)

        wind = state_float(wind_e)  # convention: m/s
        rain = state_float(rain_e)
        if rain is None:
            rain = 0

        data: dict[str, Any] = {
            "source": "entities",
            "current": {
                "temp": temp,
                "wind_ms": wind,
                "rain_1h": rain,
                "desc": None,
            },
            "forecast_list": attr_list(forecast_e, "list"),
            "fetched_at": dt_util.now().isoformat(),
        }
        return data
