"""Save the coming birthdays to birthdays.json for the dashboard's countdown page.

The list lives in the BIRTHDAYS repository secret (never in the code, the repo is public),
one person per line:

    name | date | place | emoji

  date   1952-03-14 or 03-14              (normal birthday; the year gives the age)
         農曆 1950-08-15 or lunar 08-15     (Chinese lunar birthday, worked out each year)
  place  optional, e.g. 香港 (shown as a small tag)
  emoji  optional, e.g. 👵

Example:
    嫲嫲 | 農曆 1950-08-15 | 香港 | 👵
    仔仔 | 2016-05-02

If the CALENDAR_KEY secret is set, the list is scrambled with it (same passcode as the
calendar, so the iPad that already unlocked the calendar opens this too).
Needs: pip install lunardate cryptography
"""
import base64, json, os, re, sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from lunardate import LunarDate

TZ = ZoneInfo("Europe/London")
ZH_NUM = "一二三四五六七八九十"


def lunar_name(m, d):
    month = ("正" if m == 1 else "冬" if m == 11 else "臘" if m == 12 else ZH_NUM[m - 1]) + "月"
    if d <= 10:
        day = "初" + ZH_NUM[d - 1]
    elif d < 20:
        day = "十" + ZH_NUM[d - 11]
    elif d == 20:
        day = "二十"
    elif d < 30:
        day = "廿" + ZH_NUM[d - 21]
    else:
        day = "三十"
    return "農曆" + month + day


def to_solar(y, m, d):
    ld = LunarDate(y, m, d)
    f = getattr(ld, "to_solar_date", None) or ld.toSolarDate
    return f()


def next_date(today, m, d, lunar):
    """First date on or after today when this birthday falls."""
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            if lunar:
                try:
                    when = to_solar(y, m, d)
                except ValueError:  # e.g. 30th in a 29-day lunar month that year
                    when = to_solar(y, m, d - 1)
            else:
                when = date(y, m, d) if (m, d) != (2, 29) else date(y, 2, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28)
        except ValueError:
            continue
        if when >= today:
            return when, y
    raise ValueError("no date found")


lines = [l.strip() for l in os.environ.get("BIRTHDAYS", "").splitlines() if l.strip() and not l.strip().startswith("#")]
if not lines:
    print("BIRTHDAYS secret is not set; nothing to do.")
    sys.exit(0)

today = datetime.now(TZ).date()
people = []
for line in lines:
    parts = [p.strip() for p in line.split("|")] + ["", "", ""]
    name, when, place, emoji = parts[:4]
    lunar = bool(re.match(r"(農曆|农历|陰曆|lunar)", when, re.I))
    nums = [int(x) for x in re.findall(r"\d+", when)]
    if len(nums) == 3:
        born, m, d = nums
    elif len(nums) == 2:
        born, (m, d) = None, nums
    else:
        print("skipped a line: date not understood")
        continue
    try:
        nxt, year = next_date(today, m, d, lunar)
    except ValueError:
        print("skipped a line: date not valid")
        continue
    p = {"name": name, "next": nxt.isoformat()}
    if born:
        p["age"] = year - born
    if lunar:
        p["lunar"] = lunar_name(m, d)
    if place:
        p["place"] = place
    if emoji:
        p["emoji"] = emoji
    people.append(p)

people.sort(key=lambda p: p["next"])
saved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
out = {"saved": saved, "people": people}
key = os.environ.get("CALENDAR_KEY", "").strip()
if key:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ITER = 150000
    salt, iv = os.urandom(16), os.urandom(12)
    k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(key.encode())
    data = AESGCM(k).encrypt(iv, json.dumps(people, ensure_ascii=False).encode(), None)
    b64 = lambda x: base64.b64encode(x).decode()
    out = {"saved": saved, "enc": {"iter": ITER, "salt": b64(salt), "iv": b64(iv), "data": b64(data)}}
else:
    print("CALENDAR_KEY not set: saving birthdays unscrambled")
with open(sys.argv[1] if len(sys.argv) > 1 else "birthdays.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("saved %d birthdays" % len(people))
