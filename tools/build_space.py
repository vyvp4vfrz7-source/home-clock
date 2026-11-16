"""Save the space corner's data to space.json:
  - the newest raw photos from NASA's Mars rovers (Perseverance and Curiosity)
  - NASA's Astronomy Picture of the Day
  - when the International Space Station flies over Northwood (visible passes), and its path
    for the next 12 hours so the page can draw where it is right now
  - the next full / new moon, and how many people are in space
Each part is optional: if one source fails, the others are still saved, and anything that
failed keeps its value from the last good run. Needs `pip install skyfield`."""
import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "space.json"
LAT, LON, PLACE = 51.6111, -0.4237, "Northwood"
UA = {"User-Agent": "home-clock-space/1.0 (family wall clock)"}


def get(url, raw=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        b = r.read()
    return b.decode("utf-8", "replace") if raw else json.loads(b)


def log(*a):
    print(*a, flush=True)


try:
    with open(OUT, encoding="utf-8") as f:
        old = json.load(f)
except Exception:
    old = {}
out = {}

# ---------- Mars rover raw photos ----------
# Camera names for the page (English, HK Chinese). Grey-scale engineering cameras are kept,
# but colour cameras are preferred when choosing.
CAMS = [
    ("MCZ_LEFT", "Mastcam-Z", "桅杆變焦相機", 3), ("MAST_LEFT", "Mastcam", "桅杆相機", 3),
    ("SHERLOC_WATSON", "WATSON close-up", "近攝相機", 2), ("MAHLI", "MAHLI close-up", "手臂近攝相機", 2),
    ("NAVCAM_LEFT", "Navcam", "導航相機", 2), ("NAV_LEFT", "Navcam", "導航相機", 1),
    ("SUPERCAM_RMI", "SuperCam zoom", "超級相機", 0), ("CHEMCAM_RMI", "ChemCam zoom", "化學相機", 0),
    ("FRONT_HAZCAM_LEFT", "Front Hazcam", "前避險相機", 1), ("REAR_HAZCAM_LEFT", "Rear Hazcam", "後避險相機", 1),
    ("FHAZ_LEFT", "Front Hazcam", "前避險相機", 0), ("RHAZ_LEFT", "Rear Hazcam", "後避險相機", 0),
]


def cam(instr):
    for key, en, zh, score in CAMS:
        if instr.upper().startswith(key):
            return en, zh, score
    return None


def big_enough(dim):
    m = re.findall(r"\d+", str(dim or ""))
    return not m or (len(m) >= 2 and int(m[0]) >= 900 and int(m[1]) >= 600)


def pick(cands, n, per_cam=3):
    # from the newest few sols, colour cameras first; at most per_cam from one camera, one per 10 minutes
    top = max([c["sol"] for c in cands] or [0])
    cands.sort(key=lambda c: (c["sol"] < top - 10, -c["_score"], -c["sol"], c["at"]))
    seen, used, out_ = {}, set(), []
    for c in cands:
        k = c["cam"]
        slot = (c["rover"], c["at"][:15])
        if seen.get(k, 0) >= per_cam or slot in used:
            continue
        seen[k] = seen.get(k, 0) + 1; used.add(slot)
        out_.append({x: c[x] for x in c if not x.startswith("_")})
        if len(out_) >= n:
            break
    return out_


mars = []
try:
    ims = []
    for page in (0, 1, 2):
        ims += get("https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&ver=1.2&num=100&page=%d"
                   "&order=sol+desc&extended=sample_type::full," % page).get("images", [])
    cands = []
    for im in ims:
        c = cam((im.get("camera") or {}).get("instrument", ""))
        files = im.get("image_files") or {}
        src = files.get("large") or files.get("medium") or files.get("full_res")
        if not c or not src or str(im.get("sample_type", "Full")).lower() != "full":
            continue
        if not big_enough((im.get("extended") or {}).get("dimension")):
            continue
        cands.append({"rover": "Perseverance", "zh": "毅力號", "sol": int(im.get("sol") or 0), "cam": c[0], "camZh": c[1],
                      "src": src, "at": str(im.get("date_taken_utc") or "")[:19], "_score": c[2],
                      "link": im.get("link") or ""})
    log("Perseverance candidates:", len(cands), "of", len(ims))
    mars += pick(cands, 9, 4)
except Exception as e:
    log("Perseverance failed:", repr(e))
try:
    d = get("https://mars.nasa.gov/api/v1/raw_image_items/?order=sol%20desc,instrument_sort%20asc,sample_type_sort%20asc,%20date_taken%20desc"
            "&per_page=100&page=0&condition_1=msl:mission")
    if not d.get("items"):
        log("Curiosity reply:", str(d)[:300])
    cands = []
    for im in d.get("items", []):
        c = cam(im.get("instrument", ""))
        src = im.get("https_url") or im.get("url")
        if not c or not src or str(im.get("sample_type", "full")).lower() != "full":
            continue
        rect = re.findall(r"\d+", str((im.get("extended") or {}).get("subframe_rect") or ""))   # "(x,y,width,height)"
        if len(rect) == 4 and not big_enough("%s,%s" % (rect[2], rect[3])):
            continue
        cands.append({"rover": "Curiosity", "zh": "好奇號", "sol": int(im.get("sol") or 0), "cam": c[0], "camZh": c[1],
                      "src": src.replace("http://", "https://"), "at": str(im.get("date_taken") or "")[:19], "_score": c[2],
                      "link": im.get("link") or ""})
    log("Curiosity candidates:", len(cands), "of", len(d.get("items", [])))
    mars += pick(cands, 5, 2)
except Exception as e:
    log("Curiosity failed:", repr(e))
if mars:
    # mix the two rovers: P, P, C, P, P, C ...
    p = [m for m in mars if m["rover"] == "Perseverance"]; c = [m for m in mars if m["rover"] == "Curiosity"]
    mix = []
    while p or c:
        mix += p[:2]; p = p[2:]
        mix += c[:1]; c = c[1:]
    out["mars"] = mix
else:
    out["mars"] = old.get("mars", [])

# ---------- Astronomy Picture of the Day ----------
apod = None
try:
    a = get("https://api.nasa.gov/planetary/apod?thumbs=true&api_key=" + (os.environ.get("NASA_KEY") or "DEMO_KEY"))
    img = a.get("url") if a.get("media_type") == "image" else a.get("thumbnail_url")
    if img:
        apod = {"date": a.get("date"), "title": a.get("title", "").strip(), "text": a.get("explanation", "").strip(),
                "img": img, "by": (a.get("copyright") or "").strip().replace("\n", " "), "video": a.get("media_type") != "image"}
except Exception as e:
    log("APOD api failed:", repr(e))
# The API is often down: read the web page instead (today's, or the last few days' if today is a video)
for back in range(0, 6):
    if apod:
        break
    day = datetime.now(timezone.utc) - timedelta(days=back)
    try:
        h = get("https://apod.nasa.gov/apod/ap%s.html" % day.strftime("%y%m%d"), raw=True)
        m = re.search(r'<img[^>]+src="([^"]+\.(?:jpe?g|png|gif))"', h, re.I)
        t = re.search(r"<center>\s*<b>\s*(.+?)\s*</b>", h, re.I | re.S)
        x = re.search(r"Explanation:\s*</b>(.*?)<p>\s*<center>", h, re.I | re.S) or re.search(r"Explanation:\s*</b>(.*?)<p>", h, re.I | re.S)
        by = re.search(r"Credit.*?:\s*</b>(.*?)</center>", h, re.I | re.S)
        clean = lambda v: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", v)).strip()
        log("APOD page", day.strftime("%y%m%d"), "image:", bool(m), "title:", bool(t))
        if not t:
            log(h[:4000])
        if m:
            src = m.group(1)
            apod = {"date": day.strftime("%Y-%m-%d"), "title": clean(t.group(1)) if t else "", "text": clean(x.group(1)) if x else "",
                    "img": src if src.startswith("http") else "https://apod.nasa.gov/apod/" + src,
                    "by": clean(by.group(1))[:120] if by else "", "video": False}
    except Exception as e:
        log("APOD page failed:", repr(e))
out["apod"] = apod or old.get("apod")

# ---------- ISS passes, ISS path, moon ----------
DIRS_EN = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
DIRS_ZH = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]


def compass(az):
    i = int((az + 22.5) // 45) % 8
    return [DIRS_EN[i], DIRS_ZH[i]]


try:
    from skyfield.api import load, wgs84, EarthSatellite
    from skyfield import almanac
    ts = load.timescale()
    eph = load("de421.bsp")
    here = wgs84.latlon(LAT, LON)
    now = ts.now()
    try:
        tle = get("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE", raw=True).strip().splitlines()
        iss = EarthSatellite(tle[1].strip(), tle[2].strip(), "ISS", ts)
        out["tle"] = [tle[1].strip(), tle[2].strip()]
    except Exception as e:
        log("TLE download failed, using last one:", repr(e))
        iss = EarthSatellite(old["tle"][0], old["tle"][1], "ISS", ts)
        out["tle"] = old["tle"]
    # visible passes in the next 7 days: ISS above 10 deg, in sunlight, sky dark enough (sun below -6 deg)
    t1 = ts.from_datetime(now.utc_datetime() + timedelta(days=7))
    times, events = iss.find_events(here, now, t1, altitude_degrees=10.0)
    passes, cur = [], {}
    diff = iss - here
    sun = eph["sun"]; earth = eph["earth"]
    for t, ev in zip(times, events):
        alt, az, dist = diff.at(t).altaz()
        if ev == 0:
            cur = {"rise": t, "az0": az.degrees}
        elif ev == 1 and cur:
            cur.update(top=t, alt=alt.degrees, dist=dist.km)
        elif ev == 2 and "top" in cur:
            # visible if sunlit and the sky is dark at some point in the pass (check every 20 s)
            n = max(2, int((t - cur["rise"]) * 86400 / 20))
            span = ts.linspace(cur["rise"], t, n)
            lit = iss.at(span).is_sunlit(eph)
            sun_alt = (earth + here).at(span).observe(sun).apparent().altaz()[0].degrees
            ok = [i for i in range(n) if lit[i] and sun_alt[i] < -6]
            if ok:
                a0, a1 = span[ok[0]], span[ok[-1]]
                s_alt, s_az, _ = diff.at(a0).altaz(); e_alt, e_az, _ = diff.at(a1).altaz()
                passes.append({"start": a0.utc_iso(), "end": a1.utc_iso(), "top": cur["top"].utc_iso(),
                               "max": round(cur["alt"]), "from": compass(s_az.degrees), "to": compass(e_az.degrees),
                               "mins": max(1, round((a1 - a0) * 1440))})
            cur = {}
    out["passes"] = passes[:8]
    log("ISS visible passes:", len(passes))
    # ground track: one point a minute for 12 hours
    start = now.utc_datetime().replace(second=0, microsecond=0)
    span = ts.from_datetimes([start + timedelta(minutes=i) for i in range(721)])
    sp = wgs84.subpoint_of(iss.at(span))
    out["track"] = {"t0": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "step": 60,
                    "p": [[round(la, 1), round(lo, 1)] for la, lo in zip(sp.latitude.degrees, sp.longitude.degrees)]}
    out["marsKm"] = round(earth.at(now).observe(eph["mars barycenter"]).distance().km)   # Earth to Mars today
    # moon phases for the next 40 days
    tt, ph = almanac.find_discrete(now, ts.from_datetime(now.utc_datetime() + timedelta(days=40)), almanac.moon_phases(eph))
    out["moon"] = [{"at": t.utc_iso(), "phase": int(p)} for t, p in zip(tt, ph)]   # 0 new, 1 first quarter, 2 full, 3 last quarter
except Exception as e:
    log("ISS / moon failed:", repr(e))
    for k in ("tle", "passes", "track", "moon"):
        out[k] = out.get(k) or old.get(k)
    out["marsKm"] = out.get("marsKm") or old.get("marsKm")

# ---------- people in space ----------
try:
    p = get("http://api.open-notify.org/astros.json")
    out["crew"] = [{"name": x["name"], "craft": x["craft"]} for x in p.get("people", [])]
except Exception as e:
    log("crew failed:", repr(e))
    out["crew"] = old.get("crew", [])

out["saved"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
log("Mars photos:", len(out["mars"]), "| APOD:", (out.get("apod") or {}).get("title"), "| passes:", len(out.get("passes") or []),
    "| crew:", len(out.get("crew") or []))
for m in out["mars"]:
    log("  ", m["rover"], "sol", m["sol"], m["cam"], m["at"], m["src"])
for p in out.get("passes") or []:
    log("  pass", p)
