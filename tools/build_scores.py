"""Save today's football scores for the dashboard to scores.json.
Source: ESPN's public scoreboard feed (no key), same family as build_table.py.
The iPad asks ESPN directly every minute during a match; this file is the backup
it uses when that fails. Standard library only. Only rewrites the file when a score,
clock or match list has changed, so quiet days make no commits."""
import json, os, sys, urllib.request
from datetime import datetime, timezone

LEAGUES = (os.environ.get("LEAGUES") or "eng.1").split(",")
OUT = sys.argv[1] if len(sys.argv) > 1 else "scores.json"


def side(c):
    t = c.get("team", {})
    return {
        "name": t.get("shortDisplayName") or t.get("displayName") or "?",
        "abbr": t.get("abbreviation", ""),
        "logo": t.get("logo", ""),
        "score": c.get("score", ""),
    }


matches = []
for lg in LEAGUES:
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard" % lg.strip()
    req = urllib.request.Request(url, headers={"User-Agent": "home-clock-scores/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    for e in d.get("events", []):
        comp = (e.get("competitions") or [{}])[0]
        cs = comp.get("competitors") or []
        home = next((c for c in cs if c.get("homeAway") == "home"), cs[0] if cs else {})
        away = next((c for c in cs if c.get("homeAway") == "away"), cs[1] if len(cs) > 1 else {})
        st = e.get("status", {})
        ty = st.get("type", {})
        matches.append({
            "id": e.get("id"), "league": lg, "date": e.get("date"),
            "state": ty.get("state", "pre"), "detail": ty.get("shortDetail", ""),
            "clock": st.get("displayClock", ""),
            "home": side(home), "away": side(away),
        })
matches.sort(key=lambda m: m["date"] or "")

old = None
try:
    with open(OUT) as f:
        old = json.load(f).get("matches")
except Exception:
    pass
if old == matches:
    print("no change, %d matches" % len(matches))
    sys.exit(0)
out = {"saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "matches": matches}
with open(OUT, "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("saved %d matches: %s" % (len(matches), "; ".join("%s %s-%s %s %s" % (m["home"]["abbr"], m["home"]["score"], m["away"]["score"], m["away"]["abbr"], m["detail"]) for m in matches)))
