from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_KEY, CONF_LAT, CONF_LON,
    CONF_MODE, MODE_OWM_ONLY, MODE_LOCAL_ONLY, MODE_HYBRID,
    CONF_LOCAL_TEMP_ENTITY, CONF_LOCAL_WIND_ENTITY, CONF_LOCAL_RAIN_ENTITY,
    CONF_LOCAL_WIND_UNIT, WIND_UNIT_MS, WIND_UNIT_KMH,
    CONF_TIME_MORNING, CONF_TIME_AFTERNOON,
)

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

def _is_bad_state(val: str | None) -> bool:
    return val is None or val in ("unknown", "unavailable", "none", "")

def _to_float(state: str | None, default=0.0) -> float:
    try:
        if _is_bad_state(state):
            return default
        return float(state)  # type: ignore[arg-type]
    except Exception:
        return default

def _wind_to_kmh(value: float, unit: str) -> float:
    # if local in m/s -> km/h
    if unit == WIND_UNIT_MS:
        return value * 3.6
    return value

def _pick_nearest_forecast_block(forecast_list: list[dict], target_dt: datetime) -> dict | None:
    if not forecast_list:
        return None
    target_ts = int(target_dt.timestamp())
    best = None
    best_diff = None
    for item in forecast_list:
        dt_val = item.get("dt")
        if dt_val is None:
            continue
        diff = abs(int(dt_val) - target_ts)
        if best is None or diff < best_diff:
            best = item
            best_diff = diff
    return best

@dataclass
class FahrradwetterData:
    now_temp: float | None
    now_wind_kmh: float | None
    now_rain: float | None
    now_source_temp: str
    now_source_wind: str
    now_source_rain: str

    next_block: dict | None
    tomorrow_morning: dict | None
    tomorrow_afternoon: dict | None

class FahrradwetterCoordinator(DataUpdateCoordinator[FahrradwetterData]):
    def __init__(self, hass: HomeAssistant, entry_data: dict):
        super().__init__(
            hass,
            logger=None,
            name="Fahrradwetter",
            update_interval=timedelta(minutes=30),
        )
        self.entry_data = entry_data

    async def _fetch_owm_current(self, session: aiohttp.ClientSession) -> dict:
        params = {
            "lat": self.entry_data[CONF_LAT],
            "lon": self.entry_data[CONF_LON],
            "appid": self.entry_data[CONF_API_KEY],
            "units": "metric",
            "lang": "de",
        }
        async with session.get(OWM_CURRENT_URL, params=params, timeout=20) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"OWM current HTTP {resp.status}")
            return await resp.json()

    async def _fetch_owm_forecast(self, session: aiohttp.ClientSession) -> dict:
        params = {
            "lat": self.entry_data[CONF_LAT],
            "lon": self.entry_data[CONF_LON],
            "appid": self.entry_data[CONF_API_KEY],
            "units": "metric",
            "lang": "de",
        }
        async with session.get(OWM_FORECAST_URL, params=params, timeout=20) as resp:
            if resp.status != 200:
                raise UpdateFailed(f"OWM forecast HTTP {resp.status}")
            return await resp.json()

    def _read_local(self) -> tuple[float | None, float | None, float | None, str, str, str]:
        temp_ent = self.entry_data.get(CONF_LOCAL_TEMP_ENTITY)
        wind_ent = self.entry_data.get(CONF_LOCAL_WIND_ENTITY)
        rain_ent = self.entry_data.get(CONF_LOCAL_RAIN_ENTITY)
        wind_unit = self.entry_data.get(CONF_LOCAL_WIND_UNIT, WIND_UNIT_MS)

        # Temp
        temp_state = self.hass.states.get(temp_ent).state if temp_ent else None
        temp_ok = not _is_bad_state(temp_state)
        temp = _to_float(temp_state, 0.0) if temp_ok else None

        # Wind
        wind_state = self.hass.states.get(wind_ent).state if wind_ent else None
        wind_ok = not _is_bad_state(wind_state)
        wind_raw = _to_float(wind_state, 0.0) if wind_ok else None
        wind_kmh = _wind_to_kmh(wind_raw, wind_unit) if wind_raw is not None else None

        # Rain
        rain_state = self.hass.states.get(rain_ent).state if rain_ent else None
        rain_ok = not _is_bad_state(rain_state)
        rain = _to_float(rain_state, 0.0) if rain_ok else None

        return (
            temp, wind_kmh, rain,
            "local" if temp is not None else "none",
            "local" if wind_kmh is not None else "none",
            "local" if rain is not None else "none",
        )

    async def _async_update_data(self) -> FahrradwetterData:
        mode = self.entry_data.get(CONF_MODE, MODE_HYBRID)

        local_temp, local_wind, local_rain, src_t, src_w, src_r = self._read_local()

        owm_current = None
        owm_forecast = None

        if mode in (MODE_OWM_ONLY, MODE_HYBRID):
            async with aiohttp.ClientSession() as session:
                owm_current = await self._fetch_owm_current(session)
                owm_forecast = await self._fetch_owm_forecast(session)

        # OWM current parsing (wind is m/s → convert to km/h)
        owm_temp = None
        owm_wind_kmh = None
        owm_rain = None
        if owm_current:
            owm_temp = float(owm_current.get("main", {}).get("temp", 0.0))
            owm_wind_ms = float(owm_current.get("wind", {}).get("speed", 0.0))
            owm_wind_kmh = owm_wind_ms * 3.6
            # OWM current rain can be {"1h": x} or absent
            rain_obj = owm_current.get("rain") or {}
            if isinstance(rain_obj, dict):
                owm_rain = float(rain_obj.get("1h", 0.0))
            else:
                owm_rain = 0.0

        # Choose current values
        if mode == MODE_OWM_ONLY:
            now_temp = owm_temp
            now_wind = owm_wind_kmh
            now_rain = owm_rain
            src_t, src_w, src_r = "owm", "owm", "owm"

        elif mode == MODE_LOCAL_ONLY:
            now_temp = local_temp
            now_wind = local_wind
            now_rain = local_rain
            # src_... already local/none

        else:  # MODE_HYBRID
            now_temp = local_temp if local_temp is not None else owm_temp
            now_wind = local_wind if local_wind is not None else owm_wind_kmh
            now_rain = local_rain if local_rain is not None else owm_rain

            src_t = "local" if local_temp is not None else "owm"
            src_w = "local" if local_wind is not None else "owm"
            src_r = "local" if local_rain is not None else "owm"

        # Forecast blocks (OWM only)
        next_block = None
        tomorrow_morning = None
        tomorrow_afternoon = None

        if mode != MODE_LOCAL_ONLY and owm_forecast:
            lst = owm_forecast.get("list") or []
            if isinstance(lst, list):
                # next block = first item after now
                now_ts = int(dt_util.utcnow().timestamp())
                after = [it for it in lst if isinstance(it, dict) and it.get("dt", 0) > now_ts]
                next_block = after[0] if after else None

                # tomorrow times
                t_m = self.entry_data.get(CONF_TIME_MORNING, "06:30")
                t_a = self.entry_data.get(CONF_TIME_AFTERNOON, "16:00")

                def _tomorrow_at(hhmm: str) -> datetime:
                    hh, mm = [int(x) for x in hhmm.split(":")]
                    local_now = dt_util.now()
                    t = (local_now + timedelta(days=1)).replace(hour=hh, minute=mm, second=0, microsecond=0)
                    return dt_util.as_utc(t)

                tomorrow_morning = _pick_nearest_forecast_block(lst, _tomorrow_at(t_m))
                tomorrow_afternoon = _pick_nearest_forecast_block(lst, _tomorrow_at(t_a))

        return FahrradwetterData(
            now_temp=now_temp,
            now_wind_kmh=now_wind,
            now_rain=now_rain,
            now_source_temp=src_t,
            now_source_wind=src_w,
            now_source_rain=src_r,
            next_block=next_block,
            tomorrow_morning=tomorrow_morning,
            tomorrow_afternoon=tomorrow_afternoon,
        )
