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
    BYNAME.setdefault(norm(v[2]), []).append(sid)
ONLINE = {l: set(x for r in rs for x in r) for l, rs in MAP["lines"].items()}
LINEID = {}   # "CIRCLE LINE" -> circle
for l in MAP["lines"]:
    LINEID[l.replace("-", " & " if l == "hammersmith-city" else " ")] = l
LINEID["hammersmith and city"] = "hammersmith-city"
LINEID["elizabeth"] = "elizabeth"


def find(name, line=None):
    """Station id for a name in a notice, preferring a station on that line (two 'Edgware Road's etc.)."""
    q = norm(name)
    hits = BYNAME.get(q) or [sid for k, ids in BYNAME.items() if k.startswith(q) or q.startswith(k + " ") for sid in ids]
    on = [sid for sid in hits if line and sid in ONLINE.get(line, ())]
    return (on or hits or [None])[0]


def stretch(line, a, b):
    a, b = find(a, line), find(b, line)
    if not a or not b: return None
    best = None
    for r in MAP["lines"].get(line, []):
        if a in r and b in r:
            i, j = r.index(a), r.index(b)
            sg = r[i:j + 1] if i <= j else r[j:i + 1][::-1]   # always runs from the first-named station
            if not best or len(sg) < len(best): best = sg
    return best


NAME = r"[A-Z][A-Za-z'&. -]*?"
END = r"(?=[.,;(]| via | on | for | until | from | in | and | while | due |$)"


def parts(line, text):
    """Closed stretches in one sentence: 'between X / W and Y / Z', 'from X to Y', or the whole line."""
    if re.search(r"(entire|whole) line|line (is )?closed", text, re.I):
        return [r for r in MAP["lines"].get(line, [])]
    many = r"(?:%s)(?: ?/ ?%s)*" % (NAME, NAME)
    m = re.search(r"between (%s) and (%s)%s" % (many, many, END), text) or \
        re.search(r"(?:service|trains?) from (%s) to (%s)%s" % (many, many, END), text)
    if not m: return []
    out = []
    for a in re.split(r" ?/ ?", m.group(1)):
        for b in re.split(r" ?/ ?", m.group(2)):
            sg = stretch(line, a.strip(), b.strip())
            if sg and sg not in out: out.append(sg)
    return out


SHUT = re.compile(r"\bno (?:[A-Za-z &]+ )?service\b|\bclosed\b|\bsuspended\b")


def segments(line, reason):
    """{line: [stretch, ...]} for the notice's own line and any other line it says is shut too
    ('There will also be no CIRCLE LINE service between ...' / '... on this section').
    Only sentences that say something is shut count, so 'Use DISTRICT LINE services between ...' is skipped."""
    segs = {}
    text = re.sub(r" ?\([^)]*\)", "", re.sub(r"^[A-Z &'-]+LINE:\s*", "", reason))   # "(all terminals)", "(via ...)"
    sents = [x for x in re.split(r"(?<=[.!]) +(?=[A-Z])", text) if SHUT.search(x) and not x.startswith("Use ")]
    for sent in sents:
        m = re.search(r"no ([A-Z][A-Z &]+?) LINE service", sent)
        who = LINEID.get(m.group(1).lower()) if m else line
        if not who or who in segs: continue
        p = parts(who, sent)
        if not p and "this section" in sent and segs.get(line):   # same stretch, other line
            p = [x for x in (stretch(who, MAP["st"][s[0]][2], MAP["st"][s[-1]][2]) for s in segs[line]) if x]
        if p: segs[who] = p
    return segs


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
        seg = segments(l["id"], why)
        if key in seen:
            it = seen[key]
            if l["id"] not in it["lines"]: it["lines"].append(l["id"])
        else:
            it = seen[key] = {"lines": [l["id"]], "sev": sev, "desc": desc, "from": fr, "to": to, "reason": why, "segs": {}}
            plan.append(it)
        for k, v in seg.items():
            it["segs"].setdefault(k, v)
            if k not in it["lines"]: it["lines"].append(k)
plan.sort(key=lambda x: x["from"])
for l in status:   # closed stretch for today's problems too
    sg = segments(l["id"], l["reason"]).get(l["id"]) if l["sev"] < 10 else None
    if sg: l["seg"] = sg

out = {"saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": status, "arrivals": arr, "plan": plan}
with open(sys.argv[1] if len(sys.argv) > 1 else "tfl.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
