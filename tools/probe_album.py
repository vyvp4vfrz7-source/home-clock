"""Temporary probe: list record types and FIELD NAMES (no values) in the shared album zone."""
import json, urllib.parse, collections
import build_photos as bp

res = bp.ck_post(bp.CK + "/database/1/com.apple.photos.cloud/production/public/records/resolve",
                 {"shortGUIDs": [{"value": bp.TOKEN, "shouldFetchRootRecord": True}]})
r0 = res["results"][0]
acc = r0["anonymousPublicAccess"]; part = acc.get("databasePartition") or bp.CK
q = urllib.parse.urlencode({"publicAccessAuthToken": acc["token"], "sharing_url_key": bp.TOKEN})
zone = r0.get("zoneID")
print("root fields:", sorted(((r0.get("rootRecord") or {}).get("fields") or {}).keys()))
def show(label, recs):
    types = collections.defaultdict(set)
    for r in recs:
        types[r.get("recordType")].update(((r.get("fields") or {}).keys()))
    for t, f in types.items():
        print(label, t, sum(1 for r in recs if r.get("recordType") == t), sorted(f))
for path, body in [("changes/zone", {"zones": [{"zoneID": zone}]}),
                   ("records/query", {"query": {"recordType": "CPLAssetAndMasterByAssetDateWithoutHiddenOrDeleted",
                     "filterBy": [{"fieldName": "direction", "comparator": "EQUALS", "fieldValue": {"value": "ASCENDING", "type": "STRING"}}]},
                     "resultsLimit": 5, "zoneID": zone})]:
    try:
        d = bp.ck_post(f"{part}{bp.CK_DB}{path}?{q}", body)
        recs = d.get("records") or sum([z.get("records", []) for z in d.get("zones", [])], [])
        print(path, "keys:", list(d.keys()), "n:", len(recs)); show(path, recs)
    except Exception as e:
        print(path, "failed:", e)
for t in ["CPLComment", "CPLAssetComment", "Comment", "CPLLike", "CPLSharedComment", "CPLPostComment"]:
    try:
        d = bp.ck_post(f"{part}{bp.CK_DB}records/query?{q}", {"query": {"recordType": t}, "resultsLimit": 5, "zoneID": zone})
        print("query", t, "n:", len(d.get("records", []))); show(t, d.get("records", []))
    except Exception as e:
        print("query", t, "failed:", str(e)[:120])
