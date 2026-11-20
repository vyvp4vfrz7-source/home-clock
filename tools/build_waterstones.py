"""Update the Waterstones column of bestsellers.json with Waterstones' current top 10.

Run weekly by .github/workflows/bestsellers.yml. Reads https://www.waterstones.com/books/bestsellers,
takes the first 10 book links (/book/<title>/<author>/<isbn>) in page order, then reads each book's
own page for its title, author, blurb and cover. If the page can't be read, the list is left as it was
and a short diagnostic is printed for fixing the parser.
"""
import html as H, json, re, sys, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept-Language": "en-GB,en;q=0.9", "Accept": "text/html,application/xhtml+xml"}
BASE = "https://www.waterstones.com"
N = 10


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def meta(page, prop):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), page) or \
        re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"' % re.escape(prop), page)
    return H.unescape(m.group(1)).strip() if m else ""


def short(text, n=420):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(". ", 1)[0]
    return cut + "." if len(cut) > 120 else text[:n].rsplit(" ", 1)[0] + "…"


def book(path, rank):
    isbn = path.rstrip("/").split("/")[-1]
    page = get(BASE + path)
    t = meta(page, "og:title") or (re.search(r"<title>([^<]*)</title>", page) or [None, ""])[1]
    t = re.sub(r"\s*\|\s*Waterstones.*$", "", H.unescape(t)).strip()
    a = ""
    m = re.match(r"(.*) by (.*?)(?:\s*\|.*)?$", t)
    if m:
        t, a = m.group(1).strip(), m.group(2).strip()
    if not a:
        a = path.split("/")[3].replace("-", " ").title() if len(path.split("/")) > 4 else ""
    desc = meta(page, "og:description") or meta(page, "description")
    img = meta(page, "og:image")
    b = {"id": "ws-" + isbn, "rank": rank, "t": t, "a": a, "isbn": isbn, "tag": "", "en": short(desc), "zh": "", "url": BASE + path}
    if img:
        b["cover"] = img
    return b


def main():
    try:
        page = get(BASE + "/books/bestsellers")
    except Exception as e:
        print("! could not read the bestsellers page:", e)
        return
    paths = list(dict.fromkeys(re.findall(r'href="(/book/[^"/]+/[^"/]+/\d{10,13})"', page)))
    print("book links found:", len(paths))
    if len(paths) < 5:
        print("! too few books; page sample:", len(page), page.count("/book/"), page[:1500].replace("\n", " "))
        return
    books = []
    for i, p in enumerate(paths[:N]):
        try:
            b = book(p, i + 1)
            books.append(b)
            print(b["rank"], b["t"], "-", b["a"], "|", b["en"][:60])
        except Exception as e:
            print("! %s %s" % (p, e))
        time.sleep(1)
    if len(books) < 5:
        print("! too few book pages read; keeping the old list")
        return
    for i, b in enumerate(books):
        b["rank"] = i + 1
    d = json.load(open("bestsellers.json", encoding="utf-8"))
    for l in d["lists"]:
        if l["key"] == "uk":
            l.update({"name": "Waterstones 暢銷榜", "en": "Waterstones, UK", "asof": "Updated " + time.strftime("%-d %b %Y"), "books": books})
            l.pop("note", None)
    open("bestsellers.json", "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
