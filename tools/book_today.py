"""Copy the morning's book pick (book.json on the 'book' branch, written by a Claude scheduled
task) to the site, and save its cover as books/today.jpg.

Run from the main branch checkout:  python3 tools/book_today.py <path to the book branch's book.json>
Cover search order: "cover_url" in book.json, then each ISBN on Open Library, then an Open Library
title + author search. If nothing is found the old cover is removed and the page draws a plain one.
"""
import io, json, os, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from build_books import get, shrink  # same download + resize helpers as the book list covers

src = sys.argv[1]
new = json.load(open(src, encoding="utf-8"))
if not new.get("t") or not new.get("date"):
    sys.exit("book.json on the book branch looks empty; leaving the site as it is")
try:
    old = json.load(open("book.json", encoding="utf-8"))
except Exception:
    old = {}
if old.get("id") == new.get("id") and old.get("date") == new.get("date") and os.path.exists("books/today.jpg"):
    print("already up to date:", new.get("id")); sys.exit(0)

json.dump(new, open("book.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("book of the day:", new["t"])

urls = []
if new.get("cover_url"):
    urls.append(new["cover_url"])
isbns = new.get("isbn") or []
if isinstance(isbns, str):
    isbns = [isbns]
urls += ["https://covers.openlibrary.org/b/isbn/%s-L.jpg?default=false" % i.replace("-", "") for i in isbns]
data = None
for u in urls:
    try:
        data = shrink(get(u, tries=2))
    except Exception as e:
        print("no cover from", u, e)
    if data:
        break
if not data:
    try:
        q = urllib.parse.urlencode({"title": new["t"].split(":")[0], "author": new["a"].split("&")[0].strip(),
                                    "limit": 5, "lang": "en", "fields": "cover_i"})
        docs = [d for d in json.loads(get("https://openlibrary.org/search.json?" + q)).get("docs", []) if d.get("cover_i")]
        if docs:
            data = shrink(get("https://covers.openlibrary.org/b/id/%s-L.jpg" % docs[0]["cover_i"]))
    except Exception as e:
        print("search failed", e)
os.makedirs("books", exist_ok=True)
if data:
    open("books/today.jpg", "wb").write(data); print("cover saved", len(data) // 1024, "KB")
elif os.path.exists("books/today.jpg"):
    os.remove("books/today.jpg"); print("no cover found; the page will draw one")
