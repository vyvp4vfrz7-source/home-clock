"""Temporary probe 3: record types + field names (no values) after comments were added."""
import json, urllib.parse, collections, base64, plistlib
import build_photos as bp

res = bp.ck_post(bp.CK + "/database/1/com.apple.photos.cloud/production/public/records/resolve",
                 {"shortGUIDs": [{"value": bp.TOKEN, "shouldFetchRootRecord": True}]})
r0 = res["results"][0]
acc = r0["anonymousPublicAccess"]; part = acc.get("databasePartition") or bp.CK
q = urllib.parse.urlencode({"publicAccessAuthToken": acc["token"], "sharing_url_key": bp.TOKEN})
zone = r0.get("zoneID")
print("root fields:", sorted(((r0.get("rootRecord") or {}).get("fields") or {}).keys()))
allrecs, sync = [], None
for _ in range(10):
    body = {"zones": [{"zoneID": zone, **({"syncToken": sync} if sync else {})}]}
    d = bp.ck_post(f"{part}{bp.CK_DB}changes/zone?{q}", body)
    z = (d.get("zones") or [{}])[0]
    allrecs += z.get("records", []); sync = z.get("syncToken")
    if not z.get("moreComing"): break
types = collections.defaultdict(lambda: collections.Counter()); n = collections.Counter()
for r in allrecs:
    t = r.get("recordType"); n[t] += 1
    for k, v in (r.get("fields") or {}).items(): types[t][f"{k}:{(v or {}).get('type')}"] += 1
for t in n: print("TYPE", t, n[t], dict(types[t]))
# any field name hinting at comments/captions
for r in allrecs:
    for k, v in (r.get("fields") or {}).items():
        if any(w in k.lower() for w in ("comment", "caption", "title", "desc", "text", "message")):
            val = (v or {}).get("value"); info = type(val).__name__
            if isinstance(val, str) and v.get("type") in ("ENCRYPTED_BYTES", "BYTES"):
                try:
                    b = base64.b64decode(val); info = "bplist" if b[:6] == b"bplist" else f"utf8 len {len(b.decode('utf-8'))}"
                except Exception as e: info = "undecodable"
            print("HINT", r.get("recordType"), k, v.get("type"), info)
posts = [r for r in allrecs if r.get("recordType") == "CPLPost"]
assets = [r for r in allrecs if r.get("recordType") == "CPLAsset"]
batches = collections.Counter(((a.get("fields") or {}).get("assetBatchId") or {}).get("value") for a in assets)
for po in posts:
    f = po.get("fields") or {}
    print("POST keys", sorted(k for k in po if k != "fields"), "parent", bool(po.get("parent")),
          "ts", (f.get("postTimestamp") or {}).get("value"), "caption len", len((f.get("caption") or {}).get("value") or ""),
          "assets in batch w/ same name", batches.get(po.get("recordName")),
          "name prefix", (po.get("recordName") or "")[:8])
print("batch sizes", sorted(batches.values()), "batch prefixes", [str(b)[:8] for b in batches])
for a in assets[:3]:
    print("ASSET top keys", sorted(k for k in a if k != "fields"), "parent", a.get("parent"))
for t in ["CPLComment", "CPLAssetComment", "CPLSharedComment", "CPLCommentByAsset", "CPLAssetCommentsByAsset", "CPLAssetLikesAndComments", "CPLSocialComment", "CPLAssetSocialData"]:
    try:
        d = bp.ck_post(f"{part}{bp.CK_DB}records/query?{q}", {"query": {"recordType": t}, "resultsLimit": 50, "zoneID": zone})
        print("query", t, "n:", len(d.get("records", [])), sorted({k for r in d.get("records", []) for k in (r.get('fields') or {})}))
    except Exception as e:
        print("query", t, "failed:", str(e)[:60])
