"""Build tflmap.json: every station's position (lat, lon, name) and each line's routes as station lists,
for the TfL map page (drawn over an Esri basemap). Run by hand when lines change:
    python3 tools/build_tfl_map.py tflmap.json"""
import json, sys, urllib.request

LINES = ["bakerloo", "central", "circle", "district", "hammersmith-city", "jubilee", "metropolitan", "northern",
         "piccadilly", "victoria", "waterloo-city", "elizabeth", "dlr",
         "liberty", "lioness", "mildmay", "suffragette", "weaver", "windrush"]


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

used = {s for rs in raw.values() for r in rs for s in r}
out = {"st": {s: [round(pts[s][0], 5), round(pts[s][1], 5), pts[s][2]] for s in sorted(used)}, "lines": raw}
with open(sys.argv[1] if len(sys.argv) > 1 else "tflmap.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(len(used), "stations")
