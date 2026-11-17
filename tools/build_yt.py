"""Save the latest videos of a few Hong Kong news channels on YouTube to yt.json.

Run by .github/workflows/yt.yml every 30 minutes. Uses YouTube's public RSS
feed (no key): https://www.youtube.com/feeds/videos.xml?channel_id=UC...
A channel with no 'id' yet is looked up by its @handle (or a search), and
the id it finds is printed in the log so it can be written in below.
"""
import json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

CHANNELS = [
    # 'must': the channel's own name has to match this, so a look-up never picks a stranger's channel
    {"key": "gb", "zh": "綠豆", "en": "Green Bean", "id": "UCLYWo70xBDrPYJgJsxoX7Qg"},
    {"key": "wit", "zh": "法庭線", "en": "The Witness", "id": "UCYRpTuLTvC7S6zfATKNfDXw"},
    {"key": "col", "zh": "集誌社", "en": "The Collective", "id": "UCfQa67fC_15Aiaywz8lPMNg"},
    {"key": "cable", "zh": "有線新聞", "en": "Cable News", "id": "UC_q7e5XYJB0JDGagcF0KW0w"},
]
PER = 12  # videos kept per channel
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept-Language": "en-GB,en;q=0.8", "Cookie": "CONSENT=YES+1"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def find_id(ch):
    must = re.compile(ch.get("must", "."))
    cands = []
    for h in ch.get("handles", []):
        try:
            html = get("https://www.youtube.com/@" + urllib.parse.quote(h))
        except Exception as e:
            print("  @%s: %s" % (h, e)); continue
        m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', html) or \
            re.search(r'"externalId":"(UC[\w-]{22})"', html)
        t = re.search(r'<meta property="og:title" content="([^"]*)"', html)
        t = t.group(1) if t else ""
        print("  @%s -> %s (%s)" % (h, m and m.group(1), t))
        if m and must.search(t):
            cands.append(m.group(1))
    for q in ch.get("q", []):  # YouTube search, channels only
        try:
            html = get("https://www.youtube.com/results?sp=EgIQAg%253D%253D&search_query=" + urllib.parse.quote(q))
        except Exception as e:
            print("  search: %s" % e); continue
        found = re.findall(r'"channelRenderer":\{"channelId":"(UC[\w-]{22})","title":\{"simpleText":"((?:[^"\\]|\\.)*)"', html)
        print("  search '%s': %s" % (q, found[:8]))
        cands += [cid for cid, t in found if must.search(t)]
    best, when = "", ""
    for cid in dict.fromkeys(cands):  # the matching channel that posted most recently
        try:
            title, vs = videos(cid)
        except Exception:
            continue
        top = max([v["at"] for v in vs] or [""])
        print("  candidate %s %s newest %s: %s" % (cid, title, top[:10], " | ".join(v["t"] for v in vs[:2])))
        if top > when:
            best, when = cid, top
    return best


NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}


def videos(cid):
    root = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid))
    title = root.findtext("a:title", "", NS)
    out = []
    for e in root.findall("a:entry", NS)[:PER]:
        link = e.find("a:link", NS)
        href = link.get("href") if link is not None else ""
        views = e.find("m:group/m:community/m:statistics", NS)
        out.append({
            "v": e.findtext("yt:videoId", "", NS),
            "t": e.findtext("a:title", "", NS).strip(),
            "at": e.findtext("a:published", "", NS),
            "short": "/shorts/" in href,
            "views": int(views.get("views", 0)) if views is not None else 0,
        })
    return title, out


def main(path):
    try:
        old = {c["key"]: c for c in json.load(open(path, encoding="utf-8")).get("channels", [])}
    except Exception:
        old = {}
    chans = []
    for ch in CHANNELS:
        print(ch["en"])
        cid = ch["id"] or (old.get(ch["key"]) or {}).get("id") or find_id(ch)
        row = {"key": ch["key"], "zh": ch["zh"], "en": ch["en"], "id": cid, "title": "", "videos": []}
        if cid:
            try:
                row["title"], row["videos"] = videos(cid)
                print("  %s: %d videos: %s" % (row["title"], len(row["videos"]), " | ".join(v["at"][:10] + " " + v["t"] for v in row["videos"][:4])))
            except Exception as e:
                print("  feed failed: %s" % e)
        if not row["videos"] and ch["key"] in old:   # keep what we had if the feed failed this time
            row["videos"] = old[ch["key"]].get("videos", [])
            row["title"] = old[ch["key"]].get("title", "")
        chans.append(row)
    if not any(c["videos"] for c in chans):
        print("nothing fetched; keeping old file"); return
    json.dump({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "channels": chans},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "yt.json")
