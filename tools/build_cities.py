"""Save Open-Meteo weather for London, Birmingham and Hong Kong to cities.json (the two-city page).
The page uses this copy when a device can't reach Open-Meteo itself. Standard library only."""
import json, sys, urllib.request
from datetime import datetime, timezone

# Same places, same order as CITIES in index.html: London, Birmingham, Hong Kong
LATS, LONS = "51.5074,52.4814,22.3027", "-0.1278,-1.8998,114.1772"
URL = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
       "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day"
       "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset"
       "&timezone=auto&forecast_days=4") % (LATS, LONS)

req = urllib.request.Request(URL, headers={"User-Agent": "home-clock-weather/1.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)
if not isinstance(d, list) or len(d) != 3 or any("current" not in x for x in d):
    sys.exit("unexpected reply: %s" % str(d)[:200])
out = {"saved": datetime.now(timezone.utc).strftime("%H:%M UTC"), "list": d}
with open(sys.argv[1] if len(sys.argv) > 1 else "cities.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))
