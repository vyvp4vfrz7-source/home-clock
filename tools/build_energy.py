"""Save home energy use from Octopus Energy to energy.json for the dashboard's energy page.

Repository secrets (never put these in the code, the repo is public):
  OCTOPUS_API_KEY   sk_live_...  (octopus.energy > Personal details > API access)
  OCTOPUS_ACCOUNT   A-1234ABCD
  CALENDAR_KEY      optional passcode: if set, energy.json is scrambled with it (same as the
                    calendar), so nobody can read from GitHub when the house is empty.
  OCTOPUS_GAS_UNIT  optional 'kwh' or 'm3'. Newer (SMETS2) gas meters report m3, older ones kWh.
                    Left out, it is guessed from the size of the readings.

Meters, tariffs and prices are found from the account. Smart meter readings usually reach
Octopus the next day, so the newest full day is normally yesterday.
Also saves Octopus Free Electricity sessions (public list kept by the Home Assistant
Octopus integration) and Saving Sessions you joined (Octopus GraphQL, best effort).
Standard library only, plus 'cryptography' when CALENDAR_KEY is set.
"""
import base64, json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api.octopus.energy/v1/"
TZ = ZoneInfo("Europe/London")
DAYS = 15                      # how far back to fetch (two weeks + today)
KEY = os.environ.get("OCTOPUS_API_KEY", "").strip()
ACCOUNT = os.environ.get("OCTOPUS_ACCOUNT", "").strip().upper()
OUT = sys.argv[1] if len(sys.argv) > 1 else "energy.json"
UA = {"User-Agent": "home-clock-energy/1.0"}


def get(url, auth=True):
    req = urllib.request.Request(url, headers=dict(UA))
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode((KEY + ":").encode()).decode())
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def get_all(url):
    out = []
    while url:
        d = get(url)
        out += d.get("results", [])
        url = d.get("next")
    return out


def iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def current_agreement(agreements, at):
    best = None
    for a in agreements or []:
        f, t = parse(a.get("valid_from")), parse(a.get("valid_to"))
        if (f is None or f <= at) and (t is None or t > at):
            best = a
    return best or (agreements[-1] if agreements else None)


def product_of(tariff):            # E-1R-VAR-22-11-01-C -> VAR-22-11-01
    return "-".join(tariff.split("-")[2:-1])


def rates(fuel, tariff, kind, since, until):
    url = "%sproducts/%s/%s-tariffs/%s/%s/?period_from=%s&period_to=%s&page_size=1500" % (
        API, product_of(tariff), fuel, tariff, kind, iso(since), iso(until))
    try:
        rs = get_all(url)
    except Exception as e:
        print("no %s for %s: %s" % (kind, tariff, e))
        return []
    dd = [r for r in rs if r.get("payment_method") in (None, "DIRECT_DEBIT")]
    return dd or rs


def price_at(rs, t):
    for r in rs:
        f, u = parse(r.get("valid_from")), parse(r.get("valid_to"))
        if (f is None or f <= t) and (u is None or u > t):
            return r["value_inc_vat"]
    return None


def fuel_block(fuel, point, since, until, now):
    ident = point.get("mpan") or point.get("mprn")
    readings = []
    for m in point.get("meters", []):        # some meter points list old meters too: use the one with data
        url = "%s%s-meter-points/%s/meters/%s/consumption/?period_from=%s&period_to=%s&page_size=25000&order_by=period" % (
            API, fuel, ident, urllib.parse.quote(m["serial_number"]), iso(since), iso(until))
        try:
            readings = get_all(url)
        except Exception as e:
            print("%s meter: %s" % (fuel, e))
        if readings:
            break
    ag = current_agreement(point.get("agreements"), now)
    if not ag:
        return None
    tariff = ag["tariff_code"]
    unit = rates(fuel, tariff, "standard-unit-rates", since, until)
    day, night = [], []
    if not unit:                             # Economy 7 style tariff: day and night prices
        day = rates(fuel, tariff, "day-unit-rates", since, until)
        night = rates(fuel, tariff, "night-unit-rates", since, until)
    stand = rates(fuel, tariff, "standing-charges", since, until)

    factor = 1.0
    if fuel == "gas" and readings:
        u = os.environ.get("OCTOPUS_GAS_UNIT", "").strip().lower()
        if not u:   # m3 readings are ~11x smaller than kWh; a home rarely uses >2.5 m3 in half an hour
            u = "kwh" if max(r["consumption"] for r in readings) > 2.5 else "m3"
        factor = 1.02264 * 39.5 / 3.6 if u.startswith("m") else 1.0
        print("gas readings in", u)

    def unit_price(t):
        if unit:
            return price_at(unit, t)
        lt = t.astimezone(timezone.utc)       # Economy 7 night is roughly 00:30-07:30 GMT
        mins = lt.hour * 60 + lt.minute
        return price_at(night if 30 <= mins < 450 else day, t) or price_at(day, t)

    days = {}
    for r in readings:
        t = parse(r["interval_start"])
        lt = t.astimezone(TZ)
        k = lt.strftime("%Y-%m-%d")
        d = days.setdefault(k, {"d": k, "kwh": 0.0, "p": 0.0, "n": 0, "hh": [0.0] * 48})
        kwh = r["consumption"] * factor
        p = unit_price(t)
        d["kwh"] += kwh
        d["p"] += kwh * (p or 0)
        d["n"] += 1
        d["hh"][min(47, lt.hour * 2 + lt.minute // 30)] += kwh
    out_days = []
    for k in sorted(days):
        d = days[k]
        noon = datetime.strptime(k, "%Y-%m-%d").replace(hour=12, tzinfo=TZ)
        sc = price_at(stand, noon) or 0
        out_days.append({"d": k, "kwh": round(d["kwh"], 2), "p": round(d["p"] + sc, 1),
                         "full": d["n"] >= 46, "hh": [round(x, 3) for x in d["hh"]]})
    for d in out_days[:-3]:                  # keep the half-hours only for the latest days (smaller file)
        del d["hh"]
    upcoming = []                            # today's and tomorrow's prices on time-of-use tariffs (Agile, Go...)
    if unit and len(set(r["value_inc_vat"] for r in unit if parse(r["valid_from"]) and parse(r["valid_from"]) >= now - timedelta(hours=24))) > 2:
        for r in sorted(unit, key=lambda r: r["valid_from"]):
            f = parse(r["valid_from"])
            if f and f >= now - timedelta(minutes=30):
                upcoming.append([iso(f), r["value_inc_vat"]])
    last = readings[-1]["interval_end"] if readings else None
    return {"tariff": tariff, "unit": unit_price(now), "standing": price_at(stand, now),
            "last": last, "days": out_days, "upcoming": upcoming[:96]}


def free_sessions(now):
    """Octopus Free Electricity sessions (opt-in, announced a day or two ahead)."""
    try:
        d = get("https://oe-api.davidskendall.co.uk/free_electricity.json", auth=False)
    except Exception as e:
        print("free electricity list:", e)
        return None
    out = []
    for e in d.get("data", []):
        if e.get("is_test"):
            continue
        s, t = parse(e.get("start")), parse(e.get("end"))
        if s and t and t > now - timedelta(days=1):
            out.append({"start": iso(s), "end": iso(t)})
    return sorted(out, key=lambda e: e["start"])


def saving_sessions(now):
    """Saving Sessions (use less, earn OctoPoints) you have joined. Best effort: Octopus changes this API."""
    gql = "https://api.octopus.energy/v1/graphql/"

    def q(body, token=None):
        req = urllib.request.Request(gql, data=json.dumps(body).encode(), headers=dict(UA, **{"Content-Type": "application/json"}))
        if token:
            req.add_header("Authorization", token)
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            try:
                msg = "; ".join(x.get("message", "") for x in json.loads(msg).get("errors", []))
            except Exception:
                pass
            raise RuntimeError("HTTP %s: %s" % (e.code, msg[:300].replace(KEY, "***") if KEY else msg[:300]))
    try:
        tok = q({"query": "mutation($k:String!){obtainKrakenToken(input:{APIKey:$k}){token}}", "variables": {"k": KEY}})
        token = tok["data"]["obtainKrakenToken"]["token"]
        d = q({"query": "query($a:String!){customerFlexibilityCampaignEvents(accountNumber:$a,campaignSlug:\"octoplus-saving-sessions\",first:20)"
                        "{edges{node{name code startAt endAt}}}}", "variables": {"a": ACCOUNT}}, token)
        if d.get("errors"):
            raise RuntimeError("; ".join(x.get("message", "") for x in d["errors"]))
        edges = ((d.get("data") or {}).get("customerFlexibilityCampaignEvents") or {}).get("edges") or []
    except Exception as e:
        print("saving sessions:", e)
        return None
    out = []
    for ed in edges:
        e = ed.get("node") or {}
        s, t = parse(e.get("startAt")), parse(e.get("endAt"))
        if s and t and t > now - timedelta(days=1):
            out.append({"start": iso(s), "end": iso(t), "joined": True})
    return sorted(out, key=lambda e: e["start"])


def main():
    now = datetime.now(timezone.utc)
    old = {}
    try:
        with open(OUT) as f:
            old = json.load(f)
    except Exception:
        pass
    if not KEY or not ACCOUNT:
        print("OCTOPUS_API_KEY / OCTOPUS_ACCOUNT not set yet: nothing to do")
        return
    since = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=DAYS - 1)
    acct = get("%saccounts/%s/" % (API, ACCOUNT))
    props = [p for p in acct.get("properties", []) if not p.get("moved_out_at")] or acct.get("properties", [])
    data = {"saved": now.strftime("%Y-%m-%dT%H:%MZ")}
    for p in props[:1]:
        imp = [m for m in p.get("electricity_meter_points", []) if not m.get("is_export")]
        if imp:
            data["elec"] = fuel_block("electricity", imp[0], since, now, now)
        if p.get("gas_meter_points"):
            data["gas"] = fuel_block("gas", p["gas_meter_points"][0], since, now, now)
    free = free_sessions(now)
    if free is not None:
        data["free"] = free
    saving = saving_sessions(now)
    if saving is not None:
        data["saving"] = saving

    body = dict(data); body.pop("saved")
    plain = json.dumps(body, separators=(",", ":"))
    digest = __import__("hashlib").sha256(plain.encode()).hexdigest()[:16]
    if old.get("h") == digest:
        print("no new readings: energy.json left as it is")
        return
    out = dict(data, h=digest)
    key = os.environ.get("CALENDAR_KEY", "").strip()
    if key:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        ITER = 150000
        salt, iv = os.urandom(16), os.urandom(12)
        k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(key.encode())
        enc = AESGCM(k).encrypt(iv, plain.encode(), None)
        b64 = lambda x: base64.b64encode(x).decode()
        out = {"saved": data["saved"], "h": digest, "enc": {"iter": ITER, "salt": b64(salt), "iv": b64(iv), "data": b64(enc)}}
    else:
        print("CALENDAR_KEY not set: saving energy use unscrambled")
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    for fuel in ("elec", "gas"):
        if data.get(fuel):
            ds = data[fuel]["days"]
            print("%s: %s, %d days, newest %s" % (fuel, data[fuel]["tariff"], len(ds), ds[-1]["d"] if ds else "-"))


main()
