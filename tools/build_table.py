"""Save the English Premier League table for the dashboard to table.json.
Source: ESPN's public standings feed (no key). Standard library only.
If the feed fails or looks wrong, the old table.json is kept."""
import json, sys, urllib.request
from datetime import datetime, timezone

URL = "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings"
OUT = sys.argv[1] if len(sys.argv) > 1 else "table.json"

req = urllib.request.Request(URL, headers={"User-Agent": "home-clock-table/1.0"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.load(r)

groups = d.get("children") or [d]
entries = (groups[0].get("standings") or {}).get("entries") or []
rows = []
for e in entries:
    st = {s.get("name"): s.get("value") for s in e.get("stats", [])}
    team = e.get("team", {})
    logos = team.get("logos") or []
    rows.append({
        "pos": int(st.get("rank") or 0),
        "name": team.get("shortDisplayName") or team.get("displayName") or "?",
        "abbr": team.get("abbreviation", ""),
        "logo": logos[0].get("href", "") if logos else "",
        "p": int(st.get("gamesPlayed") or 0),
        "w": int(st.get("wins") or 0),
        "d": int(st.get("ties") or 0),
        "l": int(st.get("losses") or 0),
        "gd": int(st.get("pointDifferential") or 0),
        "pts": int(st.get("points") or 0),
    })
if len(rows) < 18:
    sys.exit("unexpected reply, %d teams: %s" % (len(rows), str(d)[:300]))
if any(r["pos"] == 0 for r in rows):  # no rank given: order by points, goal difference
    rows.sort(key=lambda r: (-r["pts"], -r["gd"]))
    for i, r in enumerate(rows):
        r["pos"] = i + 1
rows.sort(key=lambda r: r["pos"])

season = (groups[0].get("standings") or {}).get("seasonDisplayName", "")
out = {"season": season or "", "saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rows": rows}
with open(OUT, "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("saved %d teams, leader %s on %d pts" % (len(rows), rows[0]["name"], rows[0]["pts"]))
