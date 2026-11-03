"""Copy photos from a public iCloud Shared Album into photos/ and write photos.json.
Runs in GitHub Actions; the album token comes from the ALBUM_TOKEN repository secret.
Standard library only. Uses iCloud's public web-album endpoints."""
import json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

TOKEN = os.environ.get("ALBUM_TOKEN", "").strip()
OUT_DIR = "photos"
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
        if not url:
            continue
        ms = ck_val(a, "assetDate") or (m and ck_val(m, "originalCreationDate")) or 0
        date = datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d") if ms else ""
        out.append({"id": a["recordName"], "url": url, "date": date, "caption": ""})
    out.sort(key=lambda x: x["date"], reverse=True)
    print("photos:", len(out))
    return out[:MAX_PHOTOS]

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
                    "date": (p.get("dateCreated") or "")[:10], "caption": (p.get("caption") or "").strip()})
    return out

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
        name = re.sub(r"[^A-Za-z0-9_-]", "", p["id"])[:40] + ".jpg"
        path = os.path.join(OUT_DIR, name)
        if not os.path.exists(path):
            with urllib.request.urlopen(urllib.request.Request(p["url"], headers={"User-Agent": HDR["User-Agent"]}), timeout=60) as r, open(path, "wb") as f:
                f.write(r.read())
        keep.add(name)
        d = p["date"]
        when = f"{int(d[5:7])}月{int(d[8:10])}日" if len(d) == 10 else ""
        out.append({"src": f"{OUT_DIR}/{name}", "text": p["caption"], "when": when})
    for f in os.listdir(OUT_DIR):  # drop photos removed from the album
        if f.endswith(".jpg") and f not in keep:
            os.remove(os.path.join(OUT_DIR, f))
    with open("photos.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", len(out), "photos")

if __name__ == "__main__":
    main()
