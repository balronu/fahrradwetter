from __future__ import annotations

from datetime import timedelta, datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_TIMES,
    CONF_MIN_TEMP,
    CONF_MAX_WIND_KMH,
    CONF_MAX_RAIN,
    DEFAULT_TIMES,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_WIND_KMH,
    DEFAULT_MAX_RAIN,
)
from .coordinator import FahrradwetterCoordinator

def ms_to_kmh(ms: float | None) -> float | None:
    if ms is None:
        return None
    try:
        return float(ms) * 3.6
    except Exception:
        return None

def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _block_values(block: dict[str, Any]) -> dict[str, Any]:
    temp = _safe_float((block.get("main") or {}).get("temp"))
    wind_ms = _safe_float((block.get("wind") or {}).get("speed"))
    rain = 0.0
    r = block.get("rain") or {}
    if isinstance(r, dict) and "3h" in r:
        rain = _safe_float(r.get("3h")) or 0.0
    weather = block.get("weather") or []
    desc = None
    if isinstance(weather, list) and weather:
        desc = (weather[0] or {}).get("description")
    return {"temp": temp, "wind_ms": wind_ms, "rain_3h": rain, "desc": desc, "dt": block.get("dt")}

def find_next_block(forecast_list: list[dict[str, Any]], now_ts: float) -> dict[str, Any] | None:
    blocks = [b for b in forecast_list if isinstance(b, dict) and "dt" in b]
    blocks.sort(key=lambda x: x.get("dt", 0))
    for b in blocks:
        try:
            if float(b["dt"]) > now_ts:
                return b
        except Exception:
            continue
    return None

def find_closest_block(forecast_list: list[dict[str, Any]], target: datetime) -> dict[str, Any] | None:
    blocks = [b for b in forecast_list if isinstance(b, dict) and "dt" in b]
    if not blocks:
        return None
    target_ts = target.timestamp()
    best = None
    best_dist = None
    for b in blocks:
        try:
            dist = abs(float(b["dt"]) - target_ts)
        except Exception:
            continue
        if best is None or dist < best_dist:
            best = b
            best_dist = dist
    return best

def ok_eval(temp: float | None, wind_kmh: float | None, rain: float | None,
            min_temp: float, max_wind: float, max_rain: float) -> bool:
    if temp is None or wind_kmh is None or rain is None:
        return False
    return (temp > min_temp) and (wind_kmh < max_wind) and (rain <= max_rain)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = FahrradwetterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    times = entry.options.get(CONF_TIMES, entry.data.get(CONF_TIMES, DEFAULT_TIMES)) or DEFAULT_TIMES
    min_temp = float(entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
    max_wind = float(entry.options.get(CONF_MAX_WIND_KMH, DEFAULT_MAX_WIND_KMH))
    max_rain = float(entry.options.get(CONF_MAX_RAIN, DEFAULT_MAX_RAIN))

    entities: list = [
        FahrradwetterNow(coordinator, entry, min_temp, max_wind, max_rain),
        FahrradwetterNextBlock(coordinator, entry, min_temp, max_wind, max_rain),
        FahrradwetterOkNow(coordinator, entry, min_temp, max_wind, max_rain),
    ]

    for t in times:
        if isinstance(t, str) and len(t) == 5 and ":" in t:
            entities.append(FahrradwetterTomorrowAt(coordinator, entry, t, min_temp, max_wind, max_rain))
            entities.append(FahrradwetterOkTomorrowAt(coordinator, entry, t, min_temp, max_wind, max_rain))

    async_add_entities(entities)


class FahrradwetterBase(CoordinatorEntity[FahrradwetterCoordinator], SensorEntity):
    _attr_should_poll = False
    _attr_unit_of_measurement = "Â°C"

    def __init__(self, coordinator, entry: ConfigEntry, unique_suffix: str, name_suffix: str,
                 min_temp: float, max_wind: float, max_rain: float):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = f"{entry.title} {name_suffix}"
        self.min_temp = min_temp
        self.max_wind = max_wind
        self.max_rain = max_rain

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class FahrradwetterNow(FahrradwetterBase):
    def __init__(self, coordinator, entry, min_temp, max_wind, max_rain):
        super().__init__(coordinator, entry, "now", "Jetzt", min_temp, max_wind, max_rain)

    @property
    def native_value(self):
        return _safe_float((self.coordinator.data.get("current") or {}).get("temp"))

    @property
    def extra_state_attributes(self):
        cur = self.coordinator.data.get("current") or {}
        temp = _safe_float(cur.get("temp"))
        wind_ms = _safe_float(cur.get("wind_ms"))
        wind_kmh = ms_to_kmh(wind_ms)
        rain = _safe_float(cur.get("rain_1h")) or 0.0
        desc = cur.get("desc")
        return {
            "source": self.coordinator.data.get("source"),
            "wind": wind_ms,
            "wind_kmh": wind_kmh,
            "rain": rain,
            "wetter": desc,
            "ok": ok_eval(temp, wind_kmh, rain, self.min_temp, self.max_wind, self.max_rain),
            "fetched_at": self.coordinator.data.get("fetched_at"),
        }


class FahrradwetterNextBlock(FahrradwetterBase):
    def __init__(self, coordinator, entry, min_temp, max_wind, max_rain):
        super().__init__(coordinator, entry, "next_block", "NÃ¤chster Block (3h)", min_temp, max_wind, max_rain)

    @property
    def native_value(self):
        fl = self.coordinator.data.get("forecast_list") or []
        b = find_next_block(fl, dt_util.now().timestamp())
        if not b:
            return None
        return _block_values(b)["temp"]

    @property
    def extra_state_attributes(self):
        fl = self.coordinator.data.get("forecast_list") or []
        b = find_next_block(fl, dt_util.now().timestamp())
        if not b:
            return {"ok": False}
        vals = _block_values(b)
        wind_kmh = ms_to_kmh(vals["wind_ms"])
        return {
            "dt": vals["dt"],
            "wind": vals["wind_ms"],
            "wind_kmh": wind_kmh,
            "rain": vals["rain_3h"],
            "wetter": vals["desc"],
            "ok": ok_eval(vals["temp"], wind_kmh, vals["rain_3h"], self.min_temp, self.max_wind, self.max_rain),
        }


class FahrradwetterTomorrowAt(FahrradwetterBase):
    def __init__(self, coordinator, entry, time_str: str, min_temp, max_wind, max_rain):
        self.time_str = time_str
        key = time_str.replace(":", "")
        super().__init__(coordinator, entry, f"tomorrow_{key}", f"Morgen {time_str}", min_temp, max_wind, max_rain)

    @property
    def native_value(self):
        fl = self.coordinator.data.get("forecast_list") or []
        hh, mm = [int(x) for x in self.time_str.split(":")]
        target = dt_util.now() + timedelta(days=1)
        target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
        b = find_closest_block(fl, target)
        if not b:
            return None
        return _block_values(b)["temp"]

    @property
    def extra_state_attributes(self):
        fl = self.coordinator.data.get("forecast_list") or []
        hh, mm = [int(x) for x in self.time_str.split(":")]
        target = dt_util.now() + timedelta(days=1)
        target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
        b = find_closest_block(fl, target)
        if not b:
            return {"ok": False}
        vals = _block_values(b)
        wind_kmh = ms_to_kmh(vals["wind_ms"])
        return {
            "target": target.isoformat(),
            "dt": vals["dt"],
            "wind": vals["wind_ms"],
            "wind_kmh": wind_kmh,
            "rain": vals["rain_3h"],
            "wetter": vals["desc"],
            "ok": ok_eval(vals["temp"], wind_kmh, vals["rain_3h"], self.min_temp, self.max_wind, self.max_rain),
        }


class FahrradwetterOkBase(CoordinatorEntity[FahrradwetterCoordinator], BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator, entry: ConfigEntry, unique_suffix: str, name_suffix: str,
                 min_temp: float, max_wind: float, max_rain: float):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = f"{entry.title} {name_suffix}"
        self.min_temp = min_temp
        self.max_wind = max_wind
        self.max_rain = max_rain

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class FahrradwetterOkNow(FahrradwetterOkBase):
    def __init__(self, coordinator, entry, min_temp, max_wind, max_rain):
        super().__init__(coordinator, entry, "ok_now", "OK Jetzt", min_temp, max_wind, max_rain)

    @property
    def is_on(self):
        cur = self.coordinator.data.get("current") or {}
        temp = _safe_float(cur.get("temp"))
        wind_kmh = ms_to_kmh(_safe_float(cur.get("wind_ms")))
        rain = _safe_float(cur.get("rain_1h")) or 0.0
        return ok_eval(temp, wind_kmh, rain, self.min_temp, self.max_wind, self.max_rain)


class FahrradwetterOkTomorrowAt(FahrradwetterOkBase):
    def __init__(self, coordinator, entry, time_str: str, min_temp, max_wind, max_rain):
        self.time_str = time_str
        key = time_str.replace(":", "")
        super().__init__(coordinator, entry, f"ok_tomorrow_{key}", f"OK Morgen {time_str}", min_temp, max_wind, max_rain)

    @property
    def is_on(self):
        fl = self.coordinator.data.get("forecast_list") or []
        hh, mm = [int(x) for x in self.time_str.split(":")]
        target = dt_util.now() + timedelta(days=1)
        target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
        b = find_closest_block(fl, target)
        if not b:
            return False
        vals = _block_values(b)
        wind_kmh = ms_to_kmh(vals["wind_ms"])
        return ok_eval(vals["temp"], wind_kmh, vals["rain_3h"], self.min_temp, self.max_wind, self.max_rain)