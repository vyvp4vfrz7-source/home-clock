"""Save TfL line status + Northwood departures to tfl.json (standard library only).
The iPad asks TfL itself every 30 s; this copy is only used when it can't reach TfL."""
import json, sys, urllib.request
from datetime import datetime, timezone

STOP = "940GZZLUNOW"  # Northwood Underground, same as CONFIG.tfl in index.html
MODES = "tube,elizabeth-line,overground,dlr"


def get(path):
    req = urllib.request.Request("https://api.tfl.gov.uk" + path, headers={"User-Agent": "home-clock-tfl/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


status = []
for l in get("/Line/Mode/%s/Status" % MODES):
    s = sorted(l.get("lineStatuses") or [], key=lambda x: x.get("statusSeverity", 10))
    status.append({"id": l["id"], "name": l["name"],
                   "sev": s[0]["statusSeverity"] if s else 10,
                   "desc": [x["statusSeverityDescription"] for x in s] or ["Good Service"],
                   "reason": (s[0].get("reason") or "") if s else ""})

arr = []
for a in get("/StopPoint/%s/Arrivals" % STOP):
    arr.append({"line": a.get("lineId"), "platform": a.get("platformName", ""), "dest": a.get("destinationName", ""),
                "towards": a.get("towards", ""), "loc": a.get("currentLocation", ""), "exp": a.get("expectedArrival")})
arr.sort(key=lambda x: x["exp"] or "")

out = {"saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": status, "arrivals": arr}
with open(sys.argv[1] if len(sys.argv) > 1 else "tfl.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
