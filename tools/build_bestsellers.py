"""Update the weekly lists in bestsellers.json: NYT hardcover fiction and the American indie bookshops'
hardcover fiction list (IndieBound / American Booksellers Association). Run weekly by
.github/workflows/bestsellers.yml. A list that can't be read keeps last week's books.

NYT comes from a public library's "latest issue" newsletter of the list (LibraryAware), since nytimes.com
needs a key. Books get an English blurb; zh is left empty.
"""
import html as H, json, re, sys, time, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
      "Accept-Language": "en-GB,en;q=0.9"}
NYT = "https://libraryaware.com/3368/NewsletterIssues/LatestIssueForList/b298acb5-c1ff-4451-9e5d-b5cf67e89419"
INDIE = "https://www.indiebound.org/bestseller-list-v2"
N = 10


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def lines(page):
    """The page as plain text lines."""
    page = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|td|tr|li|h\d|table|a)>", "\n", page)
    page = H.unescape(re.sub(r"<[^>]+>", " ", page))
    return [re.sub(r"\s+", " ", l).strip() for l in page.split("\n") if l.strip()]


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48]


def nyt():
    page = get(NYT)
    ls = lines(page)
    m = re.search(r"Bestsellers,?\s+([A-Z][a-z]+ \d{1,2}, \d{4})", " ".join(ls[:60]))
    isbns = re.findall(r"isbn=(\d{13})", page, re.I)
    books = []
    for i, l in enumerate(ls):
        r = re.match(r"^(\d{1,2})\.\s+(.+)$", l)
        if not r or int(r.group(1)) != len(books) + 1:
            continue
        by = ls[i + 1] if i + 1 < len(ls) else ""
        if not by.lower().startswith("by "):
            continue
        desc = ls[i + 2] if i + 2 < len(ls) and not re.match(r"^\d{1,2}\.\s", ls[i + 2]) else ""
        t = r.group(2).strip()
        b = {"id": "nyt-" + slug(t), "rank": len(books) + 1, "t": t, "a": by[3:].strip(), "tag": "小說", "en": desc, "zh": ""}
        if len(isbns) > len(books):
            b["isbn"] = isbns[len(books)]
        books.append(b)
        if len(books) >= N:
            break
    return (m.group(1) if m else ""), books


def indie():
    ls = lines(get(INDIE))
    m = re.search(r"Bestsellers for ([A-Z][a-z]+ \d{1,2}, \d{4})", " ".join(ls[:200]))
    try:
        start = next(i for i, l in enumerate(ls) if l.strip("* ") == "Hardcover Fiction")
    except StopIteration:
        raise ValueError("no Hardcover Fiction heading")
    books, i = [], start + 1
    while i < len(ls) and len(books) < N:
        l = ls[i]
        if l.strip("* ") in ("Hardcover Nonfiction", "Paperback Fiction"):
            break
        if re.match(r"^\d{1,2}$", l) and int(l) == len(books) + 1 and i + 2 < len(ls):
            t, meta = ls[i + 1], ls[i + 2]
            isbn = re.search(r"(97[89]\d{10})", meta)
            parts = [p.strip() for p in meta.split(",")]
            desc = ls[i + 3] if i + 3 < len(ls) and not re.match(r"^\d{1,2}$", ls[i + 3]) and not re.match(r"^(New|\d+) / \d+$", ls[i + 3]) else ""
            t = re.sub(r":\s*(A Novel|The [^:]+ Cycle.*)$", "", t)
            b = {"id": "ib-" + (isbn.group(1) if isbn else slug(t)), "rank": len(books) + 1, "t": t, "a": parts[0], "tag": "小說", "en": desc, "zh": ""}
            if isbn:
                b["isbn"] = isbn.group(1)
            books.append(b)
            i += 3
            continue
        i += 1
    return (m.group(1) if m else ""), books


def main():
    d = json.load(open("bestsellers.json", encoding="utf-8"))
    L = {l["key"]: l for l in d["lists"]}
    for key, fn, label in (("nyt", nyt, "Hardcover fiction"), ("indie", indie, "Hardcover fiction")):
        try:
            when, books = fn()
        except Exception as e:
            print("! %s: %s" % (key, e))
            continue
        print("%s %s: %d books" % (key, when, len(books)))
        for b in books:
            print("  %d %s - %s | %s" % (b["rank"], b["t"], b["a"], b["en"][:60]))
        if len(books) < 5:
            print("! %s: too few books, keeping last week's list" % key)
            continue
        old = {b.get("t", "").lower(): b for b in L[key]["books"]} if key in L else {}
        for b in books:   # keep hand-written Chinese briefs for books still on the list
            o = old.get(b["t"].lower())
            if o and o.get("zh"):
                b["zh"] = o["zh"]
        if key in L:
            L[key]["books"] = books
            L[key]["asof"] = (when + " · " if when else "") + label + " Top 10"
    open("bestsellers.json", "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
