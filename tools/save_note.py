"""Add a note left on the dashboard (tap a photo) to notes.json.

The page sends repository_dispatch "photo-note" with client_payload {"photo": "<photo id>", "who": "...", "text": "..."}.
Set DELETE=1 (Actions tab, run by hand) to remove the notes on that photo instead.
"""
import datetime, json, os, re, sys

photo = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("PHOTO", ""))[:40]
who = " ".join((os.environ.get("WHO") or "").split())[:12]
text = " ".join((os.environ.get("TEXT") or "").split())[:200]
if not photo or not os.path.exists(f"photos/{photo}.jpg"):
    sys.exit(f"No such photo: {photo!r}")
try:
    with open("notes.json", encoding="utf-8") as f:
        notes = json.load(f)
except (OSError, ValueError):
    notes = {}
if os.environ.get("DELETE") == "1":
    notes.pop(photo, None)
elif text:
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    notes.setdefault(photo, []).append({"who": who, "text": text, "at": at})
    notes[photo] = notes[photo][-10:]
else:
    sys.exit("Empty note")
notes = {k: v for k, v in notes.items() if os.path.exists(f"photos/{k}.jpg")}  # forget photos removed from the album
with open("notes.json", "w", encoding="utf-8") as f:
    json.dump(notes, f, ensure_ascii=False, indent=1, sort_keys=True)
print("notes on", photo, ":", len(notes.get(photo, [])))
