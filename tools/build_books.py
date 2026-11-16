"""Save a cover picture for every book in books.json as books/<id>.jpg.

Covers come from Open Library (free, no key). Books that already have a cover are
skipped, so this only downloads new ones. A book can set "isbn" (best match) or
"cover" (a direct picture link) in books.json if the search picks the wrong edition.
The page draws a plain coloured cover when a picture is missing.
"""
import io, json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "home-clock-books/1.0 (GitHub Actions)"}
OUT = "books"
MAX_W = 420


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read()
        except Exception as e:  # network hiccup: wait and retry
            err = e
            time.sleep(2 + i * 3)
    raise err


def find_cover(b):
    if "cover" in b:   # a direct link, or "" for no picture (the page draws a plain cover)
        return b["cover"] or None
    if b.get("isbn"):
        return "https://covers.openlibrary.org/b/isbn/%s-L.jpg?default=false" % b["isbn"]
    author = b["a"].split("&")[0].strip()
    q = urllib.parse.urlencode({"title": b["t"], "author": author, "limit": 10, "lang": "en",
                                "fields": "cover_i,title,edition_count,language"})
    docs = json.loads(get("https://openlibrary.org/search.json?" + q)).get("docs", [])
    docs = [d for d in docs if d.get("cover_i")]
    if not docs:
        return None
    docs.sort(key=lambda d: -(d.get("edition_count") or 0))   # the best-known edition first
    return "https://covers.openlibrary.org/b/id/%s-L.jpg" % docs[0]["cover_i"]


def shrink(data):
    try:
        from PIL import Image
    except ImportError:
        return data
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if im.width < 60:   # Open Library's 1x1 "no cover" image
        return None
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return buf.getvalue()


def main():
    books = json.load(open("books.json", encoding="utf-8"))["books"]
    os.makedirs(OUT, exist_ok=True)
    missing = []
    for b in books:
        path = os.path.join(OUT, b["id"] + ".jpg")
        if os.path.exists(path):
            continue
        try:
            url = find_cover(b)
            data = shrink(get(url)) if url else None
        except Exception as e:
            print("!", b["id"], e)
            data = None
        if not data:
            missing.append(b["id"])
            continue
        open(path, "wb").write(data)
        print("saved", path, len(data) // 1024, "KB")
        time.sleep(1)   # be gentle with Open Library
    if missing:
        print("No cover found for:", ", ".join(missing))


if __name__ == "__main__":
    sys.exit(main())
