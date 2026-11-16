"""Fetch Hong Kong and UK headlines (Traditional Chinese and English) and write news.json.
Runs in GitHub Actions every 30 minutes. Standard library only."""
import json, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

# (label, feed, how many, language). The page shows Chinese and English side by side;
# the Cantonese spoken summary only reads the Chinese ones.
FEEDS = [
    ("香港", "https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml", 8, "zh"),
    ("國際", "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml", 8, "zh"),
    ("HONG KONG", "https://rthk.hk/rthk/news/rss/e_expressnews_elocal.xml", 8, "en"),
    ("UK", "https://feeds.bbci.co.uk/news/uk/rss.xml", 8, "en"),
]

def titles(url, n):
    req = urllib.request.Request(url, headers={"User-Agent": "home-clock-news/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    out = []
    for item in root.iter("item"):
        t = (item.findtext("title") or "").strip()
        if t and not re.search(r"\bon TV3\d|^(Morning|Evening|Midday) News\b", t):  # skip RTHK programme notices
            out.append(t)
        if len(out) >= n:
            break
    return out

def main(path):
    groups = []
    for src, url, n, lang in FEEDS:
        try:
            groups.append([{"src": src, "t": t, "lang": lang} for t in titles(url, n)])
        except Exception as e:  # keep going if one feed is down
            groups.append([])
            print(f"skip {url}: {e}", file=sys.stderr)
    # interleave the feeds of each language (HK, world, HK, world...) so both show on screen
    mixed = []
    for lang in ("zh", "en"):
        g = [x for x in groups if x and x[0]["lang"] == lang]
        for i in range(max([len(x) for x in g] or [0])):
            mixed += [x[i] for x in g if i < len(x)]
    if not mixed:
        sys.exit("no headlines fetched; leaving the old news.json in place")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "items": mixed}, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "news.json")
