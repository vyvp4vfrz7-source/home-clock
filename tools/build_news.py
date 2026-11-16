"""Fetch Hong_Kong and UK headlines (Traditional Chinese and English) and write news.json.
Runs in GitHub Actions every 30 minutes. Standard library only.

Each item: {"src", "t" (title), "lang", and when found: "d" (short summary), "img" (picture),
"at" (published, ISO), "where" ([lat, lon, place name in Chinese]) for the world map on the news page}."""
import html, json, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# (label, feed, how many, language, default place). The dashboard shows Chinese and English side by side;
# the Cantonese spoken summary only reads the Chinese ones. Stories with no place named in them
# are pinned at the feed's default place (RTHK local news -> Hong_Kong, BBC UK -> UK).
FEEDS = [
    ("香港", "https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml", 10, "zh", "香港"),
    ("國際", "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml", 10, "zh", None),
    ("HONG KONG", "https://rthk.hk/rthk/news/rss/e_expressnews_elocal.xml", 10, "en", "香港"),
    ("UK", "https://feeds.bbci.co.uk/news/uk/rss.xml", 10, "en", "英國"),
]

# Place name -> (lat, lon). Keys are Chinese map labels; each lists the words that point to it.
# More specific places come first so "深圳" wins over "中國".
PLACES = [
    ("深圳", 22.54, 114.06, "深圳 Shenzhen"), ("澳門", 22.19, 113.54, "澳門 Macau"), ("廣州", 23.13, 113.26, "廣州 Guangzhou"),
    ("台灣", 23.7, 121.0, "台灣 臺灣 台北 臺北 Taiwan Taipei 里長"), ("北京", 39.9, 116.4, "北京 Beijing"),
    ("上海", 31.23, 121.47, "上海 Shanghai"), ("曼徹斯特", 53.48, -2.24, "曼徹斯特 Manchester"),
    ("伯明翰", 52.49, -1.89, "伯明翰 Birmingham"), ("利物浦", 53.41, -2.98, "利物浦 Liverpool"),
    ("蘇格蘭", 56.5, -4.2, "蘇格蘭 Scotland Scottish Edinburgh Glasgow 愛丁堡"), ("威爾士", 52.3, -3.7, "威爾士 Welsh Cardiff Senedd"),
    ("北愛爾蘭", 54.6, -6.7, "北愛 Northern_Ireland Belfast NI Stormont"), ("倫敦", 51.51, -0.13, "倫敦 London"),
    ("英國", 52.5, -1.5, "英國 Britain British UK England Brexit Starmer 施紀賢 NHS"),
    ("愛爾蘭", 53.3, -7.7, "愛爾蘭 Ireland Irish Dublin"), ("法國", 46.6, 2.4, "法國 France French Paris 巴黎 Macron 馬克龍"),
    ("德國", 51.2, 10.4, "德國 Germany German Berlin 柏林"), ("意大利", 42.8, 12.6, "意大利 義大利 Italy Italian Rome 羅馬"),
    ("西班牙", 40.3, -3.7, "西班牙 Spain Spanish Madrid"), ("荷蘭", 52.2, 5.3, "荷蘭 Netherlands Dutch Amsterdam"),
    ("比利時", 50.8, 4.4, "比利時 Belgium Brussels 布魯塞爾"), ("瑞士", 46.8, 8.2, "瑞士 Switzerland Swiss Geneva 日內瓦"),
    ("波蘭", 52.1, 19.4, "波蘭 Poland Polish"), ("烏克蘭", 49.0, 31.4, "烏克蘭 Ukraine Ukrainian Kyiv 基輔 澤連斯基 Zelensky"),
    ("俄羅斯", 55.75, 37.6, "俄羅斯 俄國 Russia Russian Moscow 莫斯科 普京 Putin"), ("土耳其", 39.0, 35.2, "土耳其 Turkey Türkiye"),
    ("以色列", 31.5, 34.9, "以色列 Israel Israeli"), ("加沙", 31.4, 34.4, "加沙 加薩 Gaza Hamas 哈馬斯 巴勒斯坦 Palestin"),
    ("黎巴嫩", 33.9, 35.9, "黎巴嫩 Lebanon"), ("敘利亞", 35.0, 38.5, "敘利亞 Syria"), ("伊朗", 32.4, 53.7, "伊朗 Iran"),
    ("伊拉克", 33.2, 43.7, "伊拉克 Iraq"), ("沙特", 24.7, 46.7, "沙特 沙地 Saudi"), ("阿聯酋", 24.4, 54.4, "阿聯酋 Dubai 杜拜 UAE"),
    ("埃及", 26.8, 30.8, "埃及 Egypt"), ("南非", -30.6, 22.9, "南非 South_Africa"), ("尼日利亞", 9.1, 8.7, "尼日利亞 Nigeria"),
    ("蘇丹", 15.5, 32.5, "蘇丹 Sudan"), ("肯尼亞", -0.02, 37.9, "肯尼亞 Kenya"), ("印度", 21.0, 78.0, "印度 India Indian Delhi 德里 Mumbai 孟買"),
    ("巴基斯坦", 30.4, 69.3, "巴基斯坦 Pakistan"), ("阿富汗", 33.9, 67.7, "阿富汗 Afghanistan Taliban 塔利班"),
    ("孟加拉", 23.7, 90.4, "孟加拉 Bangladesh"), ("泰國", 15.9, 100.99, "泰國 Thailand Thai Bangkok 曼谷"),
    ("越南", 14.06, 108.3, "越南 Vietnam"), ("菲律賓", 12.9, 121.8, "菲律賓 Philippines Manila 馬尼拉"),
    ("馬來西亞", 4.2, 101.97, "馬來西亞 Malaysia Kuala_Lumpur 吉隆坡"), ("新加坡", 1.35, 103.82, "新加坡 Singapore"),
    ("印尼", -0.8, 113.9, "印尼 印度尼西亞 Indonesia Jakarta 雅加達"), ("緬甸", 21.9, 95.96, "緬甸 Myanmar"),
    ("柬埔寨", 12.6, 104.99, "柬埔寨 Cambodia"), ("南韓", 37.57, 126.98, "南韓 韓國 South_Korea Korean Seoul 首爾"),
    ("北韓", 39.03, 125.75, "北韓 朝鮮 North_Korea Pyongyang 金正恩"), ("日本", 35.68, 139.69, "日本 Japan Japanese Tokyo 東京 千葉 大阪 Osaka 高市"),
    ("中國", 34.0, 108.0, "中國 中方 內地 China Chinese mainland 習近平 Xi_Jinping 國家主席 APEC"),
    ("澳洲", -25.3, 133.8, "澳洲 澳大利亞 Australia Sydney 悉尼 Melbourne 墨爾本"), ("紐西蘭", -41.3, 174.8, "紐西蘭 新西蘭 New_Zealand"),
    ("加拿大", 56.1, -106.3, "加拿大 Canada Canadian Toronto 多倫多 Vancouver 溫哥華"),
    ("美國", 38.9, -77.04, "美國 美方 USA US America American Washington 華盛頓 White_House 白宮 特朗普 Trump New_York 紐約"),
    ("墨西哥", 23.6, -102.6, "墨西哥 Mexico"), ("巴西", -14.2, -51.9, "巴西 Brazil"), ("阿根廷", -38.4, -63.6, "阿根廷 Argentina"),
    ("委內瑞拉", 6.4, -66.6, "委內瑞拉 Venezuela"), ("古巴", 21.5, -77.8, "古巴 Cuba"), ("香港", 22.32, 114.17, "香港 Hong_Kong HK 港府 特首"),
]
# Words are space-separated; _ stands for a space inside a name (New_York).
# Short ASCII words (UK, US, EU, HK…) must match as whole words; everything else matches anywhere.
_MATCH = []
for name, lat, lon, words in PLACES:
    for w in words.split():
        w = w.replace("_", " ")
        if re.fullmatch(r"[A-Za-z]{1,4}", w):
            _MATCH.append((re.compile(r"\b" + w + r"\b"), name))
        elif re.fullmatch(r"[A-Za-z ]+", w):
            _MATCH.append((re.compile(r"\b" + re.escape(w), re.I), name))
        else:
            _MATCH.append((re.compile(re.escape(w)), name))
_AT = {name: (lat, lon) for name, lat, lon, _ in PLACES}
_ORDER = {name: i for i, (name, *_r) in enumerate(PLACES)}

def place(title, desc, default):
    """Where a story happened: a place named in the headline (the most specific, and not the feed's
    home place if another is named). Feeds with a home place (RTHK -> Hong Kong, BBC UK -> UK) fall back
    to it, since their summaries often mention other places in passing; BBC 中文 also looks in the summary."""
    for text in ([title] if default else [title, desc]):
        hits = {name for rx, name in _MATCH if rx.search(text)}
        others = [h for h in hits if h != default]
        if others or hits:
            pick = min(others or hits, key=lambda h: _ORDER[h])
            return [_AT[pick][0], _AT[pick][1], pick]
    return [_AT[default][0], _AT[default][1], default] if default else None

MEDIA = "{http://search.yahoo.com/mrss/}"
IMG_IN_HTML = re.compile(r"<img[^>]+src=[\"']([^\"']+)", re.I)

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()

def get(url, n=600_000):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (home-clock news)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(n)

def picture(item, desc_html):
    for tag in ("thumbnail", "content"):
        el = item.find(MEDIA + tag)
        if el is not None and el.get("url"):
            u = el.get("url")
            return re.sub(r"/ace/(standard|ws)/\d+/", r"/ace/\1/800/", u)   # BBC: ask for a bigger copy
    el = item.find("enclosure")
    if el is not None and (el.get("type") or "image").startswith("image") and el.get("url"):
        return el.get("url")
    m = IMG_IN_HTML.search(desc_html or "")
    return m.group(1) if m else None

def og_image(link):
    try:
        page = get(link, 200_000).decode("utf-8", "replace")
    except Exception:
        return None
    m = re.search(r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)", page) or \
        re.search(r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+property=[\"']og:image", page)
    return html.unescape(m.group(1)) if m else None

def stories(url, n, default):
    root = ET.fromstring(get(url))
    out = []
    for item in root.iter("item"):
        t = clean(item.findtext("title"))
        if not t or re.search(r"\bon TV3\d|^(Morning|Evening|Midday) News\b", t):  # skip RTHK programme notices
            continue
        desc_html = item.findtext("description") or ""
        d = clean(desc_html)
        if d.startswith(t):
            d = d[len(t):].strip()
        s = {"t": t}
        if d:
            s["d"] = d[:220] + ("…" if len(d) > 220 else "")
        img = picture(item, desc_html)
        if not img and len(out) < 6 and item.findtext("link"):
            img = og_image(item.findtext("link").strip())   # top stories only, to keep the run short
        if img and img.startswith("//"):
            img = "https:" + img
        if img and img.startswith("http"):
            s["img"] = img
        try:
            s["at"] = parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            pass
        w = place(t, d, default)
        if w:
            s["where"] = w
        out.append(s)
        if len(out) >= n:
            break
    # a picture shared by every story is the site's logo, not a news photo
    imgs = [s.get("img") for s in out if s.get("img")]
    for s in out:
        if s.get("img") and imgs.count(s["img"]) > 1:
            del s["img"]
    return out

def main(path):
    groups = []
    for src, url, n, lang, default in FEEDS:
        try:
            groups.append([dict(src=src, lang=lang, **s) for s in stories(url, n, default)])
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
