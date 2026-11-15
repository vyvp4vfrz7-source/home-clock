"""Save an indoor reading sent by the "Send home temp" Shortcut to home.json.

Reads TEMP and HUM from the environment (text such as "21.5", "21,5 °C" or "48%"),
keeps only the number, and refuses anything that is not a plausible room reading.
"""
import datetime, json, os, re, sys


def number(text):
    m = re.search(r"-?\d+(?:[.,]\d+)?", text or "")
    return float(m.group(0).replace(",", ".")) if m else None


temp, hum = number(os.environ.get("TEMP")), number(os.environ.get("HUM"))
if temp is None or not -20 <= temp <= 50:
    sys.exit(f"Not a room temperature: {os.environ.get('TEMP')!r}")
out = {"temp": round(temp, 1)}
if hum is not None and 0 <= hum <= 100:
    out["hum"] = round(hum)
out["at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open("home.json", "w") as f:
    json.dump(out, f)
print(out)
