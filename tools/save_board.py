"""Family message board: add (or remove) a message in board.json.

Phones (the "留言板" Shortcut or post.html) and the iPad send repository_dispatch "board-post" with
client_payload {"who": "媽媽", "text": "今晚食火鍋"}, or {"remove": "<message id>"}.
The message is read from the event file, not from env vars, so it never shows in the public run log.

If the BOARD_KEY passcode is set (the workflow passes the CALENDAR_KEY secret), board.json is scrambled
(AES-GCM, key from the passcode via PBKDF2, same as calendar.json) so the messages can't be read on GitHub.
Keeps the newest 30 messages from the last 14 days.

{"to": "parents"} in the payload uses parents/board.json instead: the board on the grandparents' screen in Hong Kong.
"""
import base64, datetime, json, os, sys, time

ev = {}
if os.environ.get("GITHUB_EVENT_PATH"):
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        ev = json.load(f)
p = ev.get("client_payload") or {}
inputs = ev.get("inputs") or {}
who = " ".join(str(p.get("who") or "").split())[:12]
text = " ".join(str(p.get("text") or "").split())[:200]
remove = str(p.get("remove") or "")[:40]
clear = str(inputs.get("clear") or "") == "1"
FILE = "parents/board.json" if str(p.get("to") or inputs.get("to") or "") == "parents" else "board.json"

key = os.environ.get("BOARD_KEY", "").strip()
b64e = lambda x: base64.b64encode(x).decode()


def aes(salt):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return AESGCM(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=150000).derive(key.encode()))


msgs = []
try:
    with open(FILE, encoding="utf-8") as f:
        old = json.load(f)
    if "enc" in old:
        e = old["enc"]
        msgs = json.loads(aes(base64.b64decode(e["salt"])).decrypt(base64.b64decode(e["iv"]), base64.b64decode(e["data"]), None))
    else:
        msgs = old.get("msgs", [])
except (OSError, ValueError, KeyError):
    pass
except Exception as err:  # wrong passcode after a change: start a fresh board
    print("could not read the old board:", type(err).__name__)

now = datetime.datetime.now(datetime.timezone.utc)
if clear:
    msgs = []
elif remove:
    msgs = [m for m in msgs if m.get("id") != remove]
elif text:
    msgs.append({"id": "%x" % int(time.time() * 1000), "who": who, "text": text, "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")})
else:
    sys.exit("Empty message")

cut = (now - datetime.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
msgs = [m for m in msgs if m.get("at", "") >= cut][-30:]
out = {"saved": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
if key:
    salt, iv = os.urandom(16), os.urandom(12)
    data = aes(salt).encrypt(iv, json.dumps(msgs, ensure_ascii=False).encode(), None)
    out["enc"] = {"iter": 150000, "salt": b64e(salt), "iv": b64e(iv), "data": b64e(data)}
else:
    print("BOARD_KEY not set: saving messages unscrambled")
    out["msgs"] = msgs
with open(FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("%s has %d messages" % (FILE, len(msgs)))
