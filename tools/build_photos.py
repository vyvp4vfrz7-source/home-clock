"""Copy photos from a public iCloud Shared Album into photos/ and write photos.json.
Runs in GitHub Actions; the album token comes from the ALBUM_TOKEN repository secret.
Standard library only (OpenCC optional, for place names). Uses iCloud's public web-album endpoints."""
import base64, json, os, plistlib, re, shutil, struct, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

TOKEN = os.environ.get("ALBUM_TOKEN", "").strip()
# A second album (photos2.yml) uses its own folder and list: ALBUM_DIR=photos2, ALBUM_JSON=photos2.json
OUT_DIR = os.environ.get("ALBUM_DIR", "").strip() or "photos"
OUT_JSON = os.environ.get("ALBUM_JSON", "").strip() or "photos.json"
MAX_PHOTOS = 60
HDR = {"Content-Type": "text/plain", "Origin": "https://www.icloud.com",
       "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def first_host(token):
    n = B62.index(token[1]) if token[0] == "A" else B62.index(token[1]) * 62 + B62.index(token[2])
    return f"p{n:02d}-sharedstreams.icloud.com"

def post(host, path, body, hops=0):
    req = urllib.request.Request(f"https://{host}/{TOKEN}/sharedstreams/{path}", data=json.dumps(body).encode(), headers=HDR, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return host, json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 330 and hops < 3:  # album lives on another server
            new = json.loads(e.read() or b"{}").get("X-Apple-MMe-Host") or e.headers.get("X-Apple-MMe-Host")
            print("redirect to", new)
            return post(new, path, body, hops + 1)
        raise

# ---------- newer albums (photos.icloud.com/shared/album/<token>): CloudKit ----------
CK = "https://p01-ckdatabasews.icloud.com:443"
CK_DB = "/database/1/com.apple.photos.cloud/production/shared/"
CK_HDR = {**HDR, "Referer": "https://www.icloud.com/sharedalbum/", "Accept": "*/*"}

def ck_post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=CK_HDR, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def ck_val(rec, field):
    v = (rec.get("fields") or {}).get(field)
    return v.get("value") if isinstance(v, dict) else None

def ck_plist(rec, field):
    """Decode an ...Enc field (base64 bytes: a binary plist or plain UTF-8 text)."""
    raw = ck_val(rec or {}, field)
    if not raw:
        return None
    try:
        b = base64.b64decode(raw)
        return plistlib.loads(b) if b[:6] == b"bplist" else b.decode("utf-8")
    except Exception:
        return None

def cloudkit_photos():
    res = ck_post(CK + "/database/1/com.apple.photos.cloud/production/public/records/resolve",
                  {"shortGUIDs": [{"value": TOKEN, "shouldFetchRootRecord": True}]})
    r0 = (res.get("results") or [{}])[0]
    acc = r0.get("anonymousPublicAccess") or {}
    if not acc.get("token"):
        raise RuntimeError("album is not public: " + json.dumps(r0)[:300])
    part = acc.get("databasePartition") or CK
    q = urllib.parse.urlencode({"publicAccessAuthToken": acc["token"], "sharing_url_key": TOKEN})
    zone = r0.get("zoneID")
    print("album:", ((r0.get("rootRecord") or {}).get("fields") or {}).get("title", {}).get("value", "?"))
    recs, marker = [], None
    for _ in range(20):
        body = {"query": {"recordType": "CPLAssetAndMasterByAssetDateWithoutHiddenOrDeleted",
                          "filterBy": [{"fieldName": "direction", "comparator": "EQUALS",
                                        "fieldValue": {"value": "ASCENDING", "type": "STRING"}}]},
                "resultsLimit": 200, "zoneID": zone}
        if marker:
            body["continuationMarker"] = marker
        page = ck_post(f"{part}{CK_DB}records/query?{q}", body)
        recs += page.get("records", [])
        marker = page.get("continuationMarker")
        if not marker:
            break
    masters = {r["recordName"]: r for r in recs if r.get("recordType") == "CPLMaster"}
    # The text typed when photos are posted to the shared album lives on a CPLPost record;
    # its photos point to it through assetBatchId. (Comments added later aren't in the public feed.)
    post_text = {}
    try:
        sync = None
        for _ in range(20):
            z = (ck_post(f"{part}{CK_DB}changes/zone?{q}",
                         {"zones": [{"zoneID": zone, **({"syncToken": sync} if sync else {})}]}).get("zones") or [{}])[0]
            for r in z.get("records", []):
                if r.get("recordType") == "CPLPost" and (ck_val(r, "caption") or "").strip():
                    post_text[r["recordName"]] = ck_val(r, "caption").strip()
            sync = z.get("syncToken")
            if not z.get("moreComing"):
                break
    except Exception as e:
        print("post captions failed:", e)
    print("post captions:", len(post_text))
    out = []
    for a in recs:
        if a.get("recordType") != "CPLAsset":
            continue
        m = masters.get((ck_val(a, "masterRef") or {}).get("recordName"))
        url = None
        for rec, pre in ((a, "resJPEGMed"), (a, "resJPEGFull"), (m, "resJPEGMed"), (m, "resOriginal")):
            if rec and ck_val(rec, pre + "Res") and ck_val(rec, pre + "FileType") in ("public.jpeg", "public.png"):
                url = ck_val(rec, pre + "Res")["downloadURL"].replace("${f}", "photo.jpg")
                break
        video = ck_video(a, m)
        if video and not url:  # poster: the video's thumbnail, if Apple made one (else ffmpeg grabs a frame)
            for rec in (a, m):
                for f in sorted((rec or {}).get("fields") or {}):
                    if f.startswith("resJPEG") and f.endswith("Res") and ck_val(rec, f[:-3] + "FileType") in ("public.jpeg", None):
                        url = (ck_val(rec, f) or {}).get("downloadURL", "").replace("${f}", "poster.jpg") or None
                        if url:
                            break
                if url:
                    break
        if not url and not video:
            continue
        ms = ck_val(a, "assetDate") or (m and ck_val(m, "originalCreationDate")) or 0
        date = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d") if ms else ""
        taken = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ms else ""
        loc = ck_plist(a, "locationEnc")
        latlon = (loc["lat"], loc["lon"]) if isinstance(loc, dict) and "lat" in loc and "lon" in loc else None
        caption = post_text.get(ck_val(a, "assetBatchId") or "", "")
        for f in ("captionEnc", "extendedDescEnc", "titleEnc"):  # set in Photos' info panel, if Apple shares it
            v = ck_plist(a, f) or ck_plist(m, f)
            if isinstance(v, str) and v.strip() and not caption:
                caption = v.strip()
                break
        out.append({"id": a["recordName"], "url": url, "video": video, "date": date, "taken": taken, "caption": caption, "latlon": latlon})
    out.sort(key=lambda x: x["date"], reverse=True)
    print("photos:", len(out))
    return out[:MAX_PHOTOS]

# ---------- videos ----------
# Real videos have itemType com.apple.quicktime-movie and resVidMedRes / resVidSmallRes (small H.264 copies
# Apple makes for the web, about 0.5 MB a second). Live Photos have the same resVid* fields but itemType
# public.heic / public.jpeg, so they stay stills.
MAX_VIDEO_MB = 40     # GitHub Pages / git are happiest with small files

def ck_video(a, m):
    """Download info for the web-sized copy of a video, or None for photos and Live Photos."""
    kind = ck_val(m or {}, "itemType") or ck_val(a or {}, "itemType") or ""
    if "movie" not in kind and "mpeg" not in kind:   # Live Photos are public.heic / public.jpeg
        return None
    for rec in (m, a):
        for pre in ("resVidMed", "resVidSmall", "resVidFull"):
            v = ck_val(rec or {}, pre + "Res")
            if v and v.get("downloadURL"):
                return {"url": v["downloadURL"].replace("${f}", "video.mp4"), "size": v.get("size") or 0,
                        "type": ck_val(rec, pre + "FileType") or ""}
    return None

def have(cmd):
    return shutil.which(cmd) is not None

def save_video(info, path, poster):
    """Fetch Apple's web-sized H.264 copy. If ffmpeg is installed, also shrink it to 1280 px and grab a poster frame
    (GitHub's runners don't have ffmpeg, and Apple's copy is already small, so normally it is used as it is)."""
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, "raw")
        with urllib.request.urlopen(urllib.request.Request(info["url"], headers={"User-Agent": HDR["User-Agent"]}), timeout=180) as r, open(raw, "wb") as f:
            f.write(r.read())
        with open(raw, "rb") as f:
            head = f.read(4 * 1024 * 1024)
        codec = "h264" if b"avc1" in head else "hevc" if (b"hvc1" in head or b"hev1" in head) else "?"
        print("video:", os.path.basename(path), info.get("type"), codec, round(os.path.getsize(raw) / 1e6, 1), "MB, ffmpeg:", have("ffmpeg"))
        if have("ffmpeg"):
            tmp_out = os.path.join(tmp, "out.mp4")
            # at most 1280 px wide/high, 30 fps; quiet AAC kept so sound can be turned on later
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw,
                            "-vf", "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))',fps=30",
                            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-crf", "27", "-preset", "veryfast",
                            "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", tmp_out], check=True)
            if not os.path.exists(poster):
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "0.3", "-i", tmp_out, "-frames:v", "1", "-q:v", "4", poster], check=False)
            raw = tmp_out
        mb = os.path.getsize(raw) / 1e6
        print("  ->", round(mb, 1), "MB")
        if mb > MAX_VIDEO_MB:
            print("  too big, skipped")
            return False
        shutil.copyfile(raw, path)
    return True

# ---------- older albums (icloud.com/sharedalbum/#B0...): sharedstreams ----------
def sharedstreams_photos():
    host, stream = post(first_host(TOKEN), "webstream", {"streamCtag": None})
    photos = [p for p in stream.get("photos", []) if p.get("mediaAssetType") != "video"]
    print("album:", stream.get("streamName"), "photos:", len(photos))
    photos.sort(key=lambda p: p.get("dateCreated", ""), reverse=True)
    photos = photos[:MAX_PHOTOS]
    want = {}
    for p in photos:
        ders = sorted(p.get("derivatives", {}).values(), key=lambda d: int(d.get("width", 0)))
        best = [d for d in ders if int(d.get("width", 0)) <= 2100] or ders
        if best:
            want[p["photoGuid"]] = best[-1]["checksum"]
    host, urls = post(host, "webasseturls", {"photoGuids": list(want)})
    items, locs = urls.get("items", {}), urls.get("locations", {})
    out = []
    for p in photos:
        it = items.get(want.get(p["photoGuid"]))
        if not it:
            continue
        loc = locs[it["url_location"]]
        out.append({"id": p["photoGuid"], "url": f"{loc['scheme']}://{loc['hosts'][0]}{it['url_path']}",
                    "date": (p.get("dateCreated") or "")[:10], "taken": p.get("dateCreated") or "", "caption": (p.get("caption") or "").strip(), "latlon": None})
    return out

def exif_gps(path):
    """Return (lat, lon) from a JPEG's EXIF GPS tags, or None. Standard library only."""
    try:
        with open(path, "rb") as f:
            data = f.read(256 * 1024)
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker, size = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker == 0xE1 and data[i + 4:i + 10] == b"Exif\0\0":
            t = data[i + 10:i + 2 + size]
            break
        if marker == 0xDA:
            return None
        i += 2 + size
    else:
        return None
    end = "<" if t[:2] == b"II" else ">"
    u16 = lambda o: struct.unpack(end + "H", t[o:o + 2])[0]
    u32 = lambda o: struct.unpack(end + "I", t[o:o + 4])[0]
    def ifd(off):
        out = {}
        for k in range(u16(off)):
            e = off + 2 + 12 * k
            out[u16(e)] = (u16(e + 2), u32(e + 4), e + 8)
        return out
    try:
        gps_ptr = ifd(u32(4)).get(0x8825)
        if not gps_ptr:
            return None
        g = ifd(u32(gps_ptr[2]))
        def text(tag):
            v = g.get(tag)
            return t[v[2]:v[2] + 1].decode() if v else ""
        def dms(tag):
            typ, n, p = g[tag]
            o = u32(p)
            vals = [u32(o + 8 * j) / (u32(o + 8 * j + 4) or 1) for j in range(3)]
            return vals[0] + vals[1] / 60 + vals[2] / 3600
        lat, lon = dms(2), dms(4)
        if text(1) == "S": lat = -lat
        if text(3) == "W": lon = -lon
        return round(lat, 5), round(lon, 5)
    except (KeyError, struct.error, IndexError):
        return None
# ---------- place names in Hong Kong Chinese ----------
# OpenStreetMap (Nominatim) finds the town; its Chinese name comes from OSM or Wikidata,
# preferring zh-HK, then Traditional, then Simplified converted with OpenCC (s2hk) if installed.
# Results are cached in places.json by ~1 km grid square, so each place is looked up once.
PLACES_FILE = "places.json"
UA = {"User-Agent": "home-clock-photo-places/1.0 (+https://github.com/vyvp4vfrz7-source/home-clock)"}
FIX = {"大倫敦": "倫敦", "倫敦市": "倫敦", "英格蘭": "英國"}
try:
    with open(PLACES_FILE, encoding="utf-8") as _f:
        PLACES = json.load(_f)
except (OSError, ValueError):
    PLACES = {}
try:
    import opencc
    _S2HK = opencc.OpenCC("s2hk")
    _S2HK.convert("测试")
except Exception:
    _S2HK = None

def _get(url):
    time.sleep(1.1)  # Nominatim allows one request a second
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.loads(r.read())

def _has_han(t):
    return any("一" <= ch <= "鿿" for ch in t or "")

def _hk(t):
    return _S2HK.convert(t) if _S2HK and t else t

def _wikidata_zh(qid):
    try:
        d = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
        labels = d["entities"][qid]["labels"]
    except Exception:
        return ""
    for lang in ("zh-hk", "zh-hant", "zh-tw", "yue"):
        if lang in labels:
            return labels[lang]["value"]
    for lang in ("zh", "zh-hans", "zh-cn"):
        if lang in labels:
            return _hk(labels[lang]["value"])
    return ""

def _zh_name(obj):
    nd = obj.get("namedetails") or {}
    for k in ("name:zh-HK", "name:zh-Hant", "name:zh-TW", "name:yue"):
        if nd.get(k):
            return nd[k]
    qid = (obj.get("extratags") or {}).get("wikidata")
    zh = _wikidata_zh(qid) if qid else ""
    if zh:
        return zh
    for k in ("name:zh", "name:zh-Hans"):
        if nd.get(k):
            return _hk(nd[k].split(";")[0])
    return obj.get("name") or ""

def place_name(lat, lon):
    key = f"{lat:.2f},{lon:.2f}"
    if key in PLACES:
        return PLACES[key]
    base = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {"format": "jsonv2", "lat": f"{lat:.2f}", "lon": f"{lon:.2f}", "accept-language": "zh-HK,zh-Hant,zh-TW,zh,en",
         "namedetails": 1, "extratags": 1, "addressdetails": 1})
    objs = []
    for z in (14, 12, 10, 8):  # neighbourhood / town / city / county
        try:
            objs.append(_get(f"{base}&zoom={z}"))
        except Exception as e:
            print("place lookup failed:", e)
    if not objs:
        return ""
    addr = objs[0].get("address") or {}
    names = [FIX.get(n, n) for n in (_zh_name(o) for o in objs)]
    city = next((FIX.get(c, c) for o in objs for c in ((o.get("address") or {}).get("city"), (o.get("address") or {}).get("town"))
                 if _has_han(c)), "")
    country = _hk(addr.get("country") or "")
    # most specific Chinese name, then the next wider one: 諾斯伍德，倫敦 / 布拉格小城，布拉格 / 德比郡，英國
    han = [t for t in names if _has_han(t)]
    parts = han[:1]
    for t in [city] + han[1:] + [country]:
        if len(parts) == 2:
            break
        if _has_han(t) and not any(t in p or p in t for p in parts):
            parts.append(t)
    parts = parts or [t for t in (names[0], country) if t]
    name = "，".join(parts)
    if len(objs) == 4:  # only remember complete lookups
        PLACES[key] = name
    print("place:", key, "->", name)
    return name

def save_places():
    with open(PLACES_FILE, "w", encoding="utf-8") as f:
        json.dump(PLACES, f, ensure_ascii=False, indent=1, sort_keys=True)

def main():
    if not TOKEN:
        print("ALBUM_TOKEN secret not set; skipping")
        return
    old_style = len(TOKEN) == 15 and TOKEN[0] in "AB"
    try:
        photos = sharedstreams_photos() if old_style else cloudkit_photos()
    except Exception as e:
        print("first method failed:", e)
        photos = cloudkit_photos() if old_style else sharedstreams_photos()
    os.makedirs(OUT_DIR, exist_ok=True)
    keep, out = set(), []
    for p in photos:
        base = re.sub(r"[^A-Za-z0-9_-]", "", p["id"])[:40]
        name = base + ".jpg"   # the photo, or a video's poster frame
        path = os.path.join(OUT_DIR, name)
        vname = None
        if p.get("video"):
            vname = base + ".mp4"
            vpath = os.path.join(OUT_DIR, vname)
            if not os.path.exists(vpath):
                try:
                    if not save_video(p["video"], vpath, path):
                        continue
                except Exception as e:
                    print("video failed:", base, e)
                    continue
            keep.add(vname)
        if not os.path.exists(path) and p.get("url"):
            try:
                with urllib.request.urlopen(urllib.request.Request(p["url"], headers={"User-Agent": HDR["User-Agent"]}), timeout=60) as r, open(path, "wb") as f:
                    f.write(r.read())
            except Exception as e:
                if not vname:
                    raise
                print("poster failed:", base, e)
        if os.path.exists(path):
            keep.add(name)
        d = p["date"]
        when = f"{int(d[5:7])}月{int(d[8:10])}日" if len(d) == 10 else ""
        item = {"src": f"{OUT_DIR}/{name}" if os.path.exists(path) else "", "text": p["caption"], "when": when}
        if p.get("taken"):
            item["taken"] = p["taken"]  # full date + time (UTC); pages show it in local time
        if vname:
            item["video"] = f"{OUT_DIR}/{vname}"
        ll = p.get("latlon") or (exif_gps(path) if not vname else None)
        place = place_name(*ll) if ll else ""
        if place:
            item["place"] = place
        out.append(item)
    for f in os.listdir(OUT_DIR):  # drop photos removed from the album
        if f.endswith((".jpg", ".mp4")) and f not in keep:
            os.remove(os.path.join(OUT_DIR, f))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    save_places()
    try:   # face boxes for the full-photo clock (needs opencv-python-headless; fine to skip)
        import face_boxes
        face_boxes.update([i["src"] for i in out if i.get("src")])
    except Exception as e:
        print("face check skipped:", e)
    print("wrote", len(out), "items,", sum(1 for i in out if i.get("video")), "videos")

if __name__ == "__main__":
    main()
