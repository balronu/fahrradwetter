# Fahrradwetter (Home Assistant Custom Integration)

Custom Integration für Home Assistant: Sensoren für **Jetzt**, **Nächster Forecast-Block (3h)** und **frei definierbare Uhrzeiten für morgen** (z.B. `06:30,16:00`).

Du kannst die Datenquelle auswählen:
- **OWM direkt** (OpenWeatherMap API Key + lat/lon)
- **Entities Mode** (du wählst deine vorhandenen Sensoren/Entities)

## Features
- ✅ Config Flow (UI-Setup) + ✅ Options (nachträglich Zeiten/Grenzwerte ändern)
- ✅ Sensoren:
  - `… Jetzt` (°C) + Attribute (wind m/s, wind_kmh, rain, wetter, ok)
  - `… Nächster Block (3h)` (°C) + Attribute
  - `… Morgen HH:MM` (°C) + Attribute (closest 3h-block)
- ✅ Binary Sensoren:
  - `… OK Jetzt`
  - `… OK Morgen HH:MM`
- ✅ Keine template.yaml nötig

## Installation (HACS)
1. HACS → **Integrationen**
2. Menü (⋮) → **Benutzerdefinierte Repositories**
3. URL: `https://github.com/balronu/fahrradwetter`
4. Kategorie: **Integration**
5. Installieren → Home Assistant neu starten
6. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → `Fahrradwetter`

## OpenWeatherMap API Key
- OWM Account erstellen
- API Key im OWM Dashboard kopieren
- Im HA-Setup eintragen

## Konfiguration (UI)
Beim Hinzufügen:
- **Quelle**: OWM oder Entities
- **Zeiten**: z.B. `06:30,16:00`
- Grenzwerte:
  - min_temp (°C) (Default 10)
  - max_wind_kmh (km/h) (Default 15)
  - max_rain (mm) (Default 0)

### Hinweis zu Regen
OWM Forecast liefert Regen in 3h-Blöcken (`rain['3h']`). Wir übernehmen diesen Wert in `rain` für Forecast-Sensoren.
OWM Current nutzt `rain['1h']` (Fallback 0).

## Entity IDs (Entities Mode)
- temp_entity: Temperatur in °C
- wind_entity: **m/s empfohlen** (wenn du km/h nimmst, stimmt `wind_kmh` nicht)
- rain_entity: mm/h oder mm (wird nur als Zahl genutzt)
- forecast_entity: Sensor der ein Attribut `list` enthält (OWM 5day/3h forecast als JSON)

## Troubleshooting
- Schau in **Einstellungen → System → Protokolle** nach `fahrradwetter`
- Wenn Sensoren `unknown` sind: Quelle prüfen (API Key/lat/lon) bzw. ob forecast_entity wirklich ein `list`-Attribut hat.
