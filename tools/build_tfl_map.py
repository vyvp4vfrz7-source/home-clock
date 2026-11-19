"""Build tflmap.json: our own simple London rail map for the TfL page, drawn from TfL's station
positions (squeezed towards the centre so outer stations still fit). Run by hand when lines change:
    python3 tools/build_tfl_map.py tflmap.json"""
import json, math, sys, urllib.request

LINES = ["bakerloo", "central", "circle", "district", "hammersmith-city", "jubilee", "metropolitan", "northern",
         "piccadilly", "victoria", "waterloo-city", "elizabeth", "dlr",
         "liberty", "lioness", "mildmay", "suffragette", "weaver", "windrush"]
LAT0, LON0 = 51.5150, -0.1300          # centre of the map (near Tottenham Court Road)
W, H, PAD = 820, 800, 22               # drawing box in page pixels
POW, CAP = 0.42, 30                    # POW < 1 squeezes the suburbs (keeps the centre roomy); far ends pulled in to CAP km


def get(path):
    req = urllib.request.Request("https://api.tfl.gov.uk" + path, headers={"User-Agent": "home-clock-tfl/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def short(n):
    for t in (" Underground Station", " DLR Station", " Rail Station", " (Elizabeth line)", " Station"):
        n = n.replace(t, "")
    return n.strip()


raw, pts, names = {}, {}, {}
for lid in LINES:
    d = get("/Line/%s/Route/Sequence/all?excludeCrowding=true" % lid)
    for s in d["stations"] + [p for q in d["stopPointSequences"] for p in q["stopPoint"]]:
        sid = s.get("topMostParentId") or s.get("stationId") or s["id"]
        names[s["id"]] = sid
        if s.get("stationId"): names[s["stationId"]] = sid
        if sid not in pts or s["id"] == sid:
            pts[sid] = (s["lat"], s["lon"], short(s["name"]))
    routes, seen = [], set()
    for r in d["orderedLineRoutes"]:
        seq = [names.get(x, x) for x in r["naptanIds"]]
        seq = [x for i, x in enumerate(seq) if x in pts and (i == 0 or x != seq[i - 1])]
        key = tuple(seq)
        if len(seq) < 2 or key in seen or tuple(reversed(seq)) in seen:
            continue
        seen.add(key); routes.append(seq)
    # drop routes that are just a piece of a longer one
    strs = [",".join(r) for r in routes]
    keep = [r for i, r in enumerate(routes) if not any(i != j and ("," + strs[i] + ",") in ("," + strs[j] + ",") or
            (i != j and ("," + ",".join(reversed(r)) + ",") in ("," + strs[j] + ",")) for j in range(len(routes)))]
    raw[lid] = keep

kx = math.cos(math.radians(LAT0)) * 111.32
xy = {}
for sid, (lat, lon, n) in pts.items():
    dx, dy = (lon - LON0) * kx, (LAT0 - lat) * 110.57
    r = math.hypot(dx, dy)
    f = (min(r, CAP) ** POW) / r if r > 0 else 0
    xy[sid] = (dx * f, dy * f)
used = {s for rs in raw.values() for r in rs for s in r}
xs = [xy[s][0] for s in used]; ys = [xy[s][1] for s in used]
sx = (W - 2 * PAD) / (max(xs) - min(xs)); sy = min(sx * 1.25, (H - 2 * PAD) / (max(ys) - min(ys)))
ox = PAD - min(xs) * sx
oy = (H - (max(ys) - min(ys)) * sy) / 2 - min(ys) * sy
out = {"w": W, "h": H, "st": {}, "lines": raw}
for s in sorted(used):
    out["st"][s] = [round(xy[s][0] * sx + ox, 1), round(xy[s][1] * sy + oy, 1), pts[s][2]]
with open(sys.argv[1] if len(sys.argv) > 1 else "tflmap.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(len(used), "stations")
