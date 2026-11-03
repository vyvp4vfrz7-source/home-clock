"""Fetch Hong Kong and UK headlines (Traditional Chinese) and write news.json.
Runs in GitHub Actions every 30 minutes. Standard library only."""
import json, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    ("香港", "https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml", 5),
    ("國際", "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml", 5),
]

def titles(url, n):
    req = urllib.request.Request(url, headers={"User-Agent": "home-clock-news/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    out = []
    for item in root.iter("item"):
        t = (item.findtext("title") or "").strip()
        if t:
            out.append(t)
        if len(out) >= n:
            break
    return out

def main(path):
    items = []
    for src, url, n in FEEDS:
        try:
            items += [{"src": src, "t": t} for t in titles(url, n)]
        except Exception as e:  # keep going if one feed is down
            print(f"skip {url}: {e}", file=sys.stderr)
    if not items:
        sys.exit("no headlines fetched; leaving the old news.json in place")
    # interleave HK and international so both show on screen
    hk = [i for i in items if i["src"] == "香港"]; intl = [i for i in items if i["src"] != "香港"]
    mixed = [x for pair in zip(hk, intl) for x in pair] + hk[len(intl):] + intl[len(hk):]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "items": mixed}, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "news.json")
