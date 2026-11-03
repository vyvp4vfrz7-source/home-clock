"""Copy photos from a public iCloud Shared Album into photos/ and write photos.json.
Runs in GitHub Actions; the album token comes from the ALBUM_TOKEN repository secret.
Standard library only. Uses iCloud's public web-album endpoints."""
import json, os, re, sys, urllib.error, urllib.request

TOKEN = os.environ.get("ALBUM_TOKEN", "").strip()
OUT_DIR = "photos"
MAX_PHOTOS = 60
HDR = {"Content-Type": "text/plain", "User-Agent": "Mozilla/5.0", "Origin": "https://www.icloud.com"}
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

def main():
    if not TOKEN:
        print("ALBUM_TOKEN secret not set; skipping")
        return
    host, stream = post(first_host(TOKEN), "webstream", {"streamCtag": None})
    photos = [p for p in stream.get("photos", []) if p.get("mediaAssetType") != "video"]
    print("album:", stream.get("streamName"), "photos:", len(photos))
    photos.sort(key=lambda p: p.get("dateCreated", ""), reverse=True)
    photos = photos[:MAX_PHOTOS]
    want = {}
    for p in photos:  # largest version up to about 2000px wide
        ders = sorted(p.get("derivatives", {}).values(), key=lambda d: int(d.get("width", 0)))
        best = [d for d in ders if int(d.get("width", 0)) <= 2100] or ders
        if best:
            want[p["photoGuid"]] = best[-1]["checksum"]
    host, urls = post(host, "webasseturls", {"photoGuids": list(want)})
    items, locs = urls.get("items", {}), urls.get("locations", {})
    os.makedirs(OUT_DIR, exist_ok=True)
    keep, out = set(), []
    for p in photos:
        it = items.get(want.get(p["photoGuid"]))
        if not it:
            continue
        loc = locs[it["url_location"]]
        url = f"{loc['scheme']}://{loc['hosts'][0]}{it['url_path']}"
        name = re.sub(r"[^A-Za-z0-9_-]", "", p["photoGuid"])[:40] + ".jpg"
        path = os.path.join(OUT_DIR, name)
        if not os.path.exists(path):
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r, open(path, "wb") as f:
                f.write(r.read())
        keep.add(name)
        d = (p.get("dateCreated") or "")[:10]
        when = f"{int(d[5:7])}月{int(d[8:10])}日" if len(d) == 10 else ""
        out.append({"src": f"{OUT_DIR}/{name}", "text": (p.get("caption") or "").strip(), "when": when})
    for f in os.listdir(OUT_DIR):  # drop photos removed from the album
        if f.endswith(".jpg") and f not in keep:
            os.remove(os.path.join(OUT_DIR, f))
    with open("photos.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", len(out), "photos")

if __name__ == "__main__":
    main()
