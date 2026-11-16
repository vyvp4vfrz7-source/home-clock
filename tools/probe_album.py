"""Temporary probe 2: field names only (no values) + geocoder test on a public landmark."""
import json, urllib.parse, urllib.request, collections, base64, plistlib
import build_photos as bp

res = bp.ck_post(bp.CK + "/database/1/com.apple.photos.cloud/production/public/records/resolve",
                 {"shortGUIDs": [{"value": bp.TOKEN, "shouldFetchRootRecord": True}]})
r0 = res["results"][0]
print("resolve keys:", sorted(r0.keys()))
acc = r0["anonymousPublicAccess"]; part = acc.get("databasePartition") or bp.CK
q = urllib.parse.urlencode({"publicAccessAuthToken": acc["token"], "sharing_url_key": bp.TOKEN})
zone = r0.get("zoneID")
d = bp.ck_post(f"{part}{bp.CK_DB}changes/zone?{q}", {"zones": [{"zoneID": zone}]})
for z in d.get("zones", []):
    print("zone keys:", sorted(z.keys()), "moreComing:", z.get("moreComing"))
    for r in z.get("records", []):
        print(" rec", r.get("recordType"), sorted(k for k in r.keys() if k != "fields"))
recs, marker = [], None
for _ in range(5):
    body = {"query": {"recordType": "CPLAssetAndMasterByAssetDateWithoutHiddenOrDeleted",
            "filterBy": [{"fieldName": "direction", "comparator": "EQUALS", "fieldValue": {"value": "ASCENDING", "type": "STRING"}}]},
            "resultsLimit": 200, "zoneID": zone}
    if marker: body["continuationMarker"] = marker
    p = bp.ck_post(f"{part}{bp.CK_DB}records/query?{q}", body); recs += p.get("records", []); marker = p.get("continuationMarker")
    if not marker: break
cnt = collections.Counter(); types = collections.Counter()
for r in recs:
    types[r.get("recordType")] += 1
    for k in (r.get("fields") or {}): cnt[(r.get("recordType"), k)] += 1
print(types)
print("fields not on every record:", sorted(f"{t}.{k}={n}" for (t, k), n in cnt.items() if n != types[t]))
for r in recs:
    if r.get("recordType") == "CPLAsset":
        v = (r["fields"].get("locationEnc") or {})
        print("locationEnc type:", v.get("type"), "len:", len(v.get("value") or ""))
        try:
            pl = plistlib.loads(base64.b64decode(v["value"]))
            print("locationEnc plist keys:", sorted(pl.keys()) if isinstance(pl, dict) else type(pl))
        except Exception as e:
            print("decode failed", e)
        break
for lang in ["zh-HK,zh-Hant,zh-TW,zh", "zh-HK"]:
    u = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode({"format": "jsonv2", "lat": 50.0870, "lon": 14.4208, "zoom": 10, "accept-language": lang, "addressdetails": 1})
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "home-clock-photo-places/1.0 (github.com/vyvp4vfrz7-source/home-clock)"}), timeout=20) as r:
            j = json.loads(r.read()); print("nominatim", lang, j.get("address"))
    except Exception as e:
        print("nominatim failed", e)
for (la, lo) in [(53.0603, -1.7776), (51.6080, -0.4230), (48.8105, 14.3150)]:
    u = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode({"format": "jsonv2", "lat": la, "lon": lo, "zoom": 12, "accept-language": "zh-HK,zh-Hant,zh-TW,zh,en", "addressdetails": 1})
    import time; time.sleep(1.2)
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "home-clock-photo-places/1.0 (github.com/vyvp4vfrz7-source/home-clock)"}), timeout=20) as r:
        print("nominatim z12", la, lo, json.loads(r.read()).get("address"))
