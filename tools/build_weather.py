"""Save Open-Meteo weather for the dashboard to weather.json.
The page uses this copy when a device can't reach Open-Meteo itself. Standard library only."""
import json, sys, urllib.request
from datetime import datetime, timezone

LAT, LON, TZ = 51.6111, -0.4237, "Europe%2FLondon"  # Northwood, same as CONFIG in index.html
URL = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
       "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day"
       "&hourly=temperature_2m,weather_code,precipitation_probability,is_day"
       "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset"
       "&timezone=%s&forecast_days=14") % (LAT, LON, TZ)

req = urllib.request.Request(URL, headers={"User-Agent": "home-clock-weather/1.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)
if "current" not in d:
    sys.exit("unexpected reply: %s" % str(d)[:200])
d["saved"] = datetime.now(timezone.utc).strftime("%H:%M UTC")
with open(sys.argv[1] if len(sys.argv) > 1 else "weather.json", "w") as f:
    json.dump(d, f, separators=(",", ":"))
