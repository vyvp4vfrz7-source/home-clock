"""Save the next two weeks of calendar events to calendar.json for the dashboard.

The calendar's private link (an iCloud "Public Calendar" webcal:// link, or a Google
"secret address in iCal format") is kept in the CALENDAR_ICS repository secret, never in
the code. Several links can be given, one per line, optionally as "link | #colour".
Needs: pip install icalendar recurring-ical-events
"""
import json, os, sys, urllib.request
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
out = {"saved": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "events": events[:80]}
with open(sys.argv[1] if len(sys.argv) > 1 else "calendar.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("saved %d events" % len(out["events"]))
