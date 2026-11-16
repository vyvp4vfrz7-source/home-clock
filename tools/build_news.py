"""Fetch Hong Kong, UK and world headlines (Traditional Chinese and English) and write news.json.
Runs in GitHub Actions every 30 minutes. Standard library only.

Each item: {"src", "t" (title), "lang", and when found: "d" (short summary), "img" (picture),
"at" (published, ISO), "where" ([lat, lon, place name in Chinese]) for the world map on the news page}."""
import html, json, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# (label, feed, how many, language, default place). The news page alternates Chinese and English stories;
# the Cantonese spoken summary only reads the Chinese ones. Stories with no place named in them
# are pinned at the feed's default place (RTHK local news -> Hong Kong, BBC UK -> UK,
# BBC world regions -> that region).
FEEDS = [
    ("香港", "https://rthk.hk/rthk/news/rss/c_expressnews_clocal.xml", 10, "zh", "香港"),
    ("國際", "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml", 10, "zh", None),
    ("大中華", "https://rthk.hk/rthk/news/rss/c_expressnews_cgreaterchina.xml", 8, "zh", "中國"),
    ("世界", "https://rthk.hk/rthk/news/rss/c_expressnews_cinternational.xml", 8, "zh", None),
    ("HONG KONG", "https://rthk.hk/rthk/news/rss/e_expressnews_elocal.xml", 10, "en", "香港"),
    ("UK", "https://feeds.bbci.co.uk/news/uk/rss.xml", 10, "en", "英國"),
    ("ASIA", "https://feeds.bbci.co.uk/news/world/asia/rss.xml", 8, "en", None),
    ("US & CANADA", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", 8, "en", "美國"),
    ("EUROPE", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", 8, "en", "歐洲"),
    ("AUSTRALIA", "https://feeds.bbci.co.uk/news/world/australia/rss.xml", 8, "en", "澳洲"),
    ("LATIN AMERICA", "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml", 8, "en", "拉丁美洲"),
    ("AFRICA", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", 8, "en", "非洲"),
]

# Place name -> (lat, lon). Keys are Chinese map labels; each lists the words that point to it.
# More specific places come first so "深圳" wins over "中國".
PLACES = [
    ("深圳", 22.54, 114.06, "深圳 Shenzhen"), ("澳門", 22.19, 113.54, "澳門 Macau"), ("廣州", 23.13, 113.26, "廣州 Guangzhou"),
    ("台灣", 23.7, 121.0, "台灣 臺灣 台北 臺北 Taiwan Taiwanese Taipei 里長 賴清德 高雄 台中 Kaohsiung"), ("北京", 39.9, 116.4, "北京 Beijing"),
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
    ("柬埔寨", 12.6, 104.99, "柬埔寨 Cambodia"), ("南韓", 37.57, 126.98, "南韓 韓國 South_Korea Korean Seoul 首爾 Busan 釜山 李在明 Lee_Jae-myung"),
    ("北韓", 39.03, 125.75, "北韓 朝鮮 North_Korea Pyongyang 金正恩"), ("日本", 35.68, 139.69, "日本 Japan Japanese Tokyo 東京 千葉 大阪 Osaka 高市 Takaichi"),
    ("中國", 34.0, 108.0, "中國 中方 內地 China Chinese mainland 習近平 Xi_Jinping 國家主席 APEC"),
    ("澳洲", -25.3, 133.8, "澳洲 澳大利亞 Australia Sydney 悉尼 Melbourne 墨爾本"), ("紐西蘭", -41.3, 174.8, "紐西蘭 新西蘭 New_Zealand"),
    ("加拿大", 56.1, -106.3, "加拿大 Canada Canadian Toronto 多倫多 Vancouver 溫哥華"),
    ("美國", 38.9, -77.04, "美國 美方 USA US America American Washington 華盛頓 White_House 白宮 特朗普 Trump"),
    ("墨西哥", 23.6, -102.6, "墨西哥 Mexico"), ("巴西", -14.2, -51.9, "巴西 Brazil"), ("阿根廷", -38.4, -63.6, "阿根廷 Argentina"),
    ("委內瑞拉", 6.4, -66.6, "委內瑞拉 Venezuela"), ("古巴", 21.5, -77.8, "古巴 Cuba"), ("香港", 22.32, 114.17, "香港 Hong_Kong HK 港府 特首"),
    # more of the Americas, Africa, Europe and Australia (for the BBC world feeds)
    ("紐約", 40.71, -74.0, "紐約 New_York Manhattan Brooklyn"), ("洛杉磯", 34.05, -118.24, "洛杉磯 Los_Angeles Hollywood"),
    ("加州", 37.0, -120.0, "加州 California San_Francisco 三藩市 舊金山"), ("德州", 31.0, -99.0, "德州 Texas Houston Dallas"),
    ("佛羅里達", 28.0, -82.0, "佛羅里達 Florida Miami"), ("芝加哥", 41.88, -87.63, "芝加哥 Chicago Illinois"),
    ("西雅圖", 47.6, -122.33, "西雅圖 Seattle Washington_state Oregon Portland"), ("阿拉斯加", 61.2, -149.9, "阿拉斯加 Alaska"),
    ("夏威夷", 21.3, -157.86, "夏威夷 Hawaii"), ("渥太華", 45.42, -75.7, "渥太華 Ottawa Quebec Montreal 滿地可 Carney"),
    ("多倫多", 43.65, -79.38, "多倫多 Toronto Ontario"), ("溫哥華", 49.28, -123.12, "溫哥華 Vancouver British_Columbia Alberta"),
    ("智利", -33.45, -70.67, "智利 Chile Chilean Santiago"), ("哥倫比亞", 4.6, -74.08, "哥倫比亞 Colombia Bogota"),
    ("秘魯", -12.05, -77.04, "秘魯 Peru Lima"), ("厄瓜多爾", -0.18, -78.47, "厄瓜多爾 Ecuador"), ("玻利維亞", -16.5, -68.15, "玻利維亞 Bolivia"),
    ("海地", 18.54, -72.34, "海地 Haiti"), ("巴拿馬", 8.98, -79.52, "巴拿馬 Panama"), ("危地馬拉", 14.63, -90.51, "危地馬拉 Guatemala Honduras El_Salvador"),
    ("埃塞俄比亞", 9.0, 38.75, "埃塞俄比亞 Ethiopia Eritrea Tigray"), ("剛果", -4.32, 15.31, "剛果 Congo DR_Congo Kinshasa Goma"),
    ("索馬里", 2.05, 45.32, "索馬里 Somalia"), ("加納", 5.6, -0.19, "加納 Ghana"), ("摩洛哥", 33.97, -6.85, "摩洛哥 Morocco"),
    ("阿爾及利亞", 36.75, 3.06, "阿爾及利亞 Algeria"), ("利比亞", 32.89, 13.19, "利比亞 Libya"), ("突尼斯", 36.8, 10.18, "突尼斯 Tunisia"),
    ("津巴布韋", -17.83, 31.05, "津巴布韋 Zimbabwe"), ("烏干達", 0.35, 32.58, "烏干達 Uganda"), ("坦桑尼亞", -6.8, 39.28, "坦桑尼亞 Tanzania"),
    ("塞內加爾", 14.7, -17.44, "塞內加爾 Senegal Mali Burkina_Faso Niger"), ("喀麥隆", 3.87, 11.52, "喀麥隆 Cameroon"),
    ("莫桑比克", -25.97, 32.57, "莫桑比克 Mozambique Malawi Zambia"), ("馬達加斯加", -18.88, 47.5, "馬達加斯加 Madagascar"),
    ("希臘", 37.98, 23.73, "希臘 Greece Greek Athens"), ("葡萄牙", 38.72, -9.14, "葡萄牙 Portugal Portuguese Lisbon"),
    ("瑞典", 59.33, 18.07, "瑞典 Sweden Swedish Stockholm"), ("挪威", 59.91, 10.75, "挪威 Norway Norwegian Oslo"),
    ("丹麥", 55.68, 12.57, "丹麥 Denmark Danish Copenhagen Greenland 格陵蘭"), ("芬蘭", 60.17, 24.94, "芬蘭 Finland Finnish Helsinki"),
    ("奧地利", 48.21, 16.37, "奧地利 Austria Vienna"), ("匈牙利", 47.5, 19.04, "匈牙利 Hungary Hungarian Budapest Orban"),
    ("捷克", 50.08, 14.44, "捷克 Czech Prague Slovakia"), ("羅馬尼亞", 44.43, 26.1, "羅馬尼亞 Romania Moldova Bulgaria"),
    ("塞爾維亞", 44.79, 20.45, "塞爾維亞 Serbia Kosovo Bosnia Croatia Belgrade"), ("白俄羅斯", 53.9, 27.56, "白俄羅斯 Belarus"),
    ("格魯吉亞", 41.72, 44.79, "格魯吉亞 Georgia Armenia Azerbaijan"), ("波羅的海", 56.95, 24.1, "波羅的海 Latvia Lithuania Estonia Baltic"),
    ("冰島", 64.15, -21.94, "冰島 Iceland"), ("梵蒂岡", 41.9, 12.45, "梵蒂岡 Vatican Pope 教宗"),
    ("悉尼", -33.87, 151.21, "悉尼 Sydney New_South_Wales NSW"), ("墨爾本", -37.81, 144.96, "墨爾本 Melbourne Victoria"),
    ("布里斯班", -27.47, 153.03, "布里斯班 Brisbane Queensland Gold_Coast"), ("珀斯", -31.95, 115.86, "珀斯 Perth Western_Australia"),
    ("阿德萊德", -34.93, 138.6, "阿德萊德 Adelaide South_Australia"), ("坎培拉", -35.28, 149.13, "坎培拉 Canberra Albanese"),
    ("巴布亞", -9.44, 147.18, "巴布亞 Papua Fiji Solomon Pacific_islands"),
    # whole regions, used when a BBC world story names no country
    ("歐洲", 50.0, 10.0, "歐洲 Europe European"), ("非洲", 5.0, 20.0, "非洲 Africa African"),
    ("拉丁美洲", -12.0, -60.0, "拉丁美洲 拉美 Latin_America South_America"),
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
