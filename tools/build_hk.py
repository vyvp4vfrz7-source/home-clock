"""Save Hong Kong Observatory weather (open data) to hk.json for the HK corner page.
The page reads the Observatory directly and only uses this copy if that fails. Standard library only."""
import json, sys, urllib.request
from datetime import datetime, timezone

API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?lang=tc&dataType="
out = {}
for key, kind in (("now", "rhrread"), ("fnd", "fnd"), ("flw", "flw"), ("warn", "warnsum")):
    req = urllib.request.Request(API + kind, headers={"User-Agent": "home-clock-hk/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out[key] = json.load(r)
if "temperature" not in out["now"]:
    sys.exit("unexpected reply: %s" % str(out["now"])[:200])
out["fnd"]["weatherForecast"] = out["fnd"].get("weatherForecast", [])[:5]
out["saved"] = datetime.now(timezone.utc).strftime("%H:%M UTC")
with open(sys.argv[1] if len(sys.argv) > 1 else "hk.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
