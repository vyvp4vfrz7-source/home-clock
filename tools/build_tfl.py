"""Save TfL line status + Northwood departures to tfl.json (standard library only).
The iPad asks TfL itself every 30 s; this copy is only used when it can't reach TfL."""
import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

STOP = "940GZZLUNOW"  # Northwood Underground, same as CONFIG.tfl in index.html
MODES = "tube,elizabeth-line,overground,dlr"
MINE = {"metropolitan"}     # always listed in "coming weeks", even small changes
DAYS = 28                   # how far ahead to look for planned works


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

# ---- planned works for the coming weeks (TfL only gives this per line list, not per mode)
def norm(n):
    n = n.lower().replace("&", "and").replace("-", " ").replace("'", "")
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\(.*?\)", "", n)).strip()


MAP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tflmap.json")))
BYNAME = {}
for sid, v in MAP["st"].items():
    BYNAME.setdefault(norm(v[2]), sid)


def find(name):
    q = norm(name.split("/")[0])
    if q in BYNAME: return BYNAME[q]
    for k, sid in BYNAME.items():
        if k.startswith(q) or q.startswith(k + " "): return sid
    return None


def segment(line, reason):
    """Stations between 'X and Y' in the notice, along the line's own route (for the map)."""
    m = re.search(r"between ([A-Z][^.,;]*?) and ([A-Z][A-Za-z'&/ -]*?)(?=[.,;(]| via | on | for | until | from | in |$)", reason)
    if not m: return None
    a, b = find(m.group(1)), find(m.group(2))
    if not a or not b: return None
    for r in MAP["lines"].get(line, []):
        if a in r and b in r:
            i, j = sorted((r.index(a), r.index(b)))
            return r[i:j + 1]
    return None


ids = ",".join(l["id"] for l in status)
start = datetime.now(timezone.utc)
plan, seen = [], {}
try:
    fut = get("/Line/%s/Status/%s/to/%s" % (ids, start.strftime("%Y-%m-%d"), (start + timedelta(days=DAYS)).strftime("%Y-%m-%d")))
except Exception as e:
    fut = []
    print("plan:", e)
for l in fut:
    for s in l.get("lineStatuses") or []:
        sev, desc, why = s.get("statusSeverity", 10), s.get("statusSeverityDescription", ""), (s.get("reason") or "").strip()
        if sev in (10, 20) or not why or "resume later" in why: continue
        if sev in (7, 8, 9) and l["id"] not in MINE: continue   # single late trains etc.
        per = s.get("validityPeriods") or []
        if not per: continue
        fr, to = min(p["fromDate"] for p in per), max(p["toDate"] for p in per)
        if to < start.strftime("%Y-%m-%dT%H:%M"): continue
        if l["id"] not in MINE and (fr[11:13] in ("21", "22", "23") or to[:10] > (datetime.fromisoformat(fr[:10]) + timedelta(days=10)).strftime("%Y-%m-%d")):
            continue   # late-evening-only works and long-running notices: too much noise
        key = re.sub(r"^[A-Z &'-]+LINE:\s*", "", why)[:120] + fr[:10]
        seg = segment(l["id"], why)
        if key in seen:
            it = seen[key]
            if l["id"] not in it["lines"]: it["lines"].append(l["id"])
        else:
            it = seen[key] = {"lines": [l["id"]], "sev": sev, "desc": desc, "from": fr, "to": to, "reason": why, "segs": {}}
            plan.append(it)
        if seg: it["segs"][l["id"]] = seg
plan.sort(key=lambda x: x["from"])
for l in status:   # closed stretch for today's problems too
    sg = segment(l["id"], l["reason"]) if l["sev"] < 10 else None
    if sg: l["seg"] = sg

out = {"saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": status, "arrivals": arr, "plan": plan}
with open(sys.argv[1] if len(sys.argv) > 1 else "tfl.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
