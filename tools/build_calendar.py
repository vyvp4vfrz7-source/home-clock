"""Save the next two weeks of calendar events to calendar.json for the dashboard.

The calendar's private link (an iCloud "Public Calendar" webcal:// link, or a Google
"secret address in iCal format") is kept in the CALENDAR_ICS repository secret, never in
the code. Several links can be given, one per line, optionally as "link | #colour".
If the CALENDAR_KEY secret is set, the events are scrambled (AES-GCM, key from the passcode
via PBKDF2-SHA256) so the file on GitHub is unreadable; the iPad asks for the passcode once.
Needs: pip install icalendar recurring-ical-events cryptography
"""
import base64, json, os, sys, urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import icalendar, recurring_ical_events

TZ = ZoneInfo("Europe/London")
DAYS_AHEAD = 14
COLOURS = ["#6aaef8", "#f3b649", "#e58fb6", "#8bd17c", "#b49cf2"]

links = [l.strip() for l in os.environ.get("CALENDAR_ICS", "").splitlines() if l.strip()]
if not links:
    print("CALENDAR_ICS secret is not set; nothing to do.")
    sys.exit(0)

now = datetime.now(TZ)
start = datetime(now.year, now.month, now.day, tzinfo=TZ)
end = start + timedelta(days=DAYS_AHEAD)

def local(v):
    if isinstance(v, datetime):
        return (v.replace(tzinfo=TZ) if v.tzinfo is None else v.astimezone(TZ)), False
    return v, True  # a plain date = all-day event

events = []
for i, line in enumerate(links):
    url, _, colour = (p.strip() for p in line.partition("|"))
    url = url.replace("webcal://", "https://", 1)
    colour = colour or COLOURS[i % len(COLOURS)]
    req = urllib.request.Request(url, headers={"User-Agent": "home-clock-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        cal = icalendar.Calendar.from_ical(r.read())
    for ev in recurring_ical_events.of(cal).between(start, end):
        if str(ev.get("STATUS", "")).upper() == "CANCELLED":
            continue
        s, all_day = local(ev.decoded("DTSTART"))
        e = ev.decoded("DTEND") if ev.get("DTEND") else s
        e, _ = local(e)
        if all_day:
            e = e - timedelta(days=1) if e > s else s  # DTEND of all-day events is exclusive
            fmt = lambda d: d.isoformat()
        else:
            fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M")
        events.append({"start": fmt(s), "end": fmt(e), "allDay": all_day,
                       "title": str(ev.get("SUMMARY", "")).strip() or "(no title)", "color": colour})

events.sort(key=lambda x: (x["start"][:10], not x["allDay"], x["start"]))
saved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
out = {"saved": saved, "events": events[:80]}
key = os.environ.get("CALENDAR_KEY", "").strip()
if key:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ITER = 150000
    salt, iv = os.urandom(16), os.urandom(12)
    k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(key.encode())
    data = AESGCM(k).encrypt(iv, json.dumps(out["events"], ensure_ascii=False).encode(), None)
    b64 = lambda x: base64.b64encode(x).decode()
    out = {"saved": saved, "enc": {"iter": ITER, "salt": b64(salt), "iv": b64(iv), "data": b64(data)}}
else:
    print("CALENDAR_KEY not set: saving events unscrambled")
with open(sys.argv[1] if len(sys.argv) > 1 else "calendar.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("saved %d events" % len(events[:80]))
