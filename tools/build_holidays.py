"""Save UK (England & Wales) bank holidays and Hong Kong public holidays to holidays.json
for the calendar page. Sources: gov.uk/bank-holidays.json and the 1823.gov.hk holiday calendar.
If a source can't be reached, the old list for it is kept. Standard library only."""
import json, sys, urllib.request
from datetime import date, datetime, timezone

OUT = sys.argv[1] if len(sys.argv) > 1 else "holidays.json"
FROM = "%d-01-01" % (date.today().year - 1)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "home-clock-holidays/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8-sig"))

try:
    old = json.load(open(OUT, encoding="utf-8"))
except Exception:
    old = {}
out = {"uk": old.get("uk", []), "hk": old.get("hk", [])}

try:
    ev = get("https://www.gov.uk/bank-holidays.json")["england-and-wales"]["events"]
    uk = [{"date": e["date"], "title": e["title"]} for e in ev if e["date"] >= FROM]
    if uk:
        out["uk"] = uk
except Exception as e:
    print("UK holidays not updated:", e)

def hk_list(lang):
    cal = get("https://www.1823.gov.hk/common/ical/%s.json" % lang)["vcalendar"][0]["vevent"]
    res = {}
    for v in cal:
        d = v["dtstart"][0] if isinstance(v["dtstart"], list) else v["dtstart"]
        d = "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
        if d >= FROM:
            res[d] = v["summary"]
    return res

try:
    zh, en = hk_list("tc"), hk_list("en")
    hk = [{"date": d, "zh": zh[d], "title": en.get(d, "")} for d in sorted(zh)]
    if hk:
        out["hk"] = hk
except Exception as e:
    print("HK holidays not updated:", e)

if not out["uk"] and not out["hk"]:
    sys.exit("no holidays found")
if out["uk"] == old.get("uk") and out["hk"] == old.get("hk"):
    print("no change"); sys.exit(0)
out["saved"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=0)
print("saved", len(out["uk"]), "UK and", len(out["hk"]), "HK holidays")
