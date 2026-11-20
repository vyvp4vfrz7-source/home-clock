"""Find YouTube book reviews for the prize page and the bestsellers page, save them to bookvids.json.

Run by .github/workflows/bookvids.yml (weekly, and when the book lists change). It reads
YouTube's normal search page (no key) for "<title> <author> book review" (or 書評 for Chinese
books) and keeps up to 3 videos whose title mentions the book. A book whose search fails keeps
the videos it had last time. The page also has a 🔎 button that opens the full YouTube search.
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept-Language": "en-GB,en;q=0.8,zh-HK;q=0.6", "Cookie": "CONSENT=YES+1"}
OUT = "bookvids.json"
KEEP = 3


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def has_cjk(s):
    return bool(re.search(r"[㐀-鿿]", s or ""))


def query(b):
    """Chinese books (Taiwan / HK, or no English title) are searched in Chinese."""
    if b.get("_zh") and b.get("tz") and not b.get("hktw"):   # translated book on Taiwan's list
        return "%s 說書 書評" % re.sub(r"[《》]", "", b["tz"])
    if b.get("hktw") or b.get("_zh") or (has_cjk(b.get("tz")) and b.get("az") and not b.get("t")):
        return "%s %s 書評 說書" % (re.sub(r"[《》]", "", b.get("tz") or b["t"]), b.get("az") or b.get("a", ""))
    a = (b.get("a") or "").split("&")[0].split(",")[0].strip().split(" ")[-1]
    return "%s %s book review" % (b["t"], a)


def keys(b):
    """Words that a matching video's title should contain."""
    out = []
    for t in (b.get("t"), b.get("tz")):
        if not t:
            continue
        t = re.sub(r"[《》]", "", t).split(":")[0].split("?")[0].strip().lower()
        if has_cjk(t):
            out.append(re.sub(r"\s.*", "", t))   # Chinese title without any English after it
        else:
            out.append(re.sub(r"^(the|a|an) ", "", t))
    return [k for k in out if len(k) >= 2]


def walk(o, found):
    if isinstance(o, dict):
        v = o.get("videoRenderer")
        if v and v.get("videoId"):
            found.append(v)
        for x in o.values():
            walk(x, found)
    elif isinstance(o, list):
        for x in o:
            walk(x, found)


def text(x):
    if not x:
        return ""
    return x.get("simpleText") or "".join(r.get("text", "") for r in x.get("runs", []))


def search(b):
    html = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query(b)))
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html) or re.search(r'ytInitialData"\] = (\{.*?\});', html)
    if not m:
        raise ValueError("no results data")
    found = []
    walk(json.loads(m.group(1)), found)
    ks, out = keys(b), []
    for v in found:
        t, ln = text(v.get("title")), text(v.get("lengthText"))
        if not ln or ln.count(":") == 1 and int(ln.split(":")[0]) < 2:   # skip Shorts / live / very short clips
            continue
        if ks and not any(k in t.lower() for k in ks):
            continue
        out.append({"v": v["videoId"], "t": t, "ch": text(v.get("ownerText")), "len": ln})
        if len(out) >= KEEP:
            break
    return out


def main():
    books = [b for b in json.load(open("books.json", encoding="utf-8"))["books"] if b.get("pp")]
    byid = {b["id"]: b for b in json.load(open("books.json", encoding="utf-8"))["books"]}
    for l in json.load(open("bestsellers.json", encoding="utf-8"))["lists"]:
        for b in l["books"]:
            b = byid.get(b.get("ref"), b)
            if l["key"] == "eslite":   # Taiwan's list: look for Chinese reviews
                b = dict(b, _zh=True)
            books.append(b)
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("books", {})
    except Exception:
        old = {}
    res, seen = {}, set()
    for b in books:
        if b["id"] in seen or not b.get("t"):
            continue
        seen.add(b["id"])
        try:
            vs = search(b)
            print("%-34s %d  %s" % (b["id"], len(vs), " | ".join(v["t"][:40] for v in vs)))
        except Exception as e:
            print("! %s %s" % (b["id"], e))
            vs = None
        res[b["id"]] = vs if vs else old.get(b["id"], [])
        time.sleep(2)   # be gentle
    json.dump({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "books": res},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
