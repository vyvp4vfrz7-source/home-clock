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
import base64, bisect, json, os, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api.octopus.energy/v1/"
TZ = ZoneInfo("Europe/London")
DAYS = 31                      # half-hours fetched (a month: peak hours, always-on power, tariff check)
KEEP = 15                      # days kept on the main energy page (two weeks + today)
HIST = 760                     # daily history for the review page: this year vs last year
LAT, LON = 51.611, -0.424      # Northwood, for heating vs outdoor temperature
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
    full = [d for d in out_days if d["full"]][-28:]
    profile = [round(sum(d["hh"][i] for d in full) / len(full), 3) for i in range(48)] if full else []
    base = [[d["d"], round(min(d["hh"]) * 2000)] for d in full]      # lowest half-hour of the day, in watts
    month = {d["d"]: (d["hh"], d["p"]) for d in full}
    out_days = out_days[-KEEP:]
    for d in out_days[:-3]:                  # keep the half-hours only for the latest days (smaller file)
        del d["hh"]
    upcoming = []                            # today's and tomorrow's prices on time-of-use tariffs (Agile, Go...)
    if unit and len(set(r["value_inc_vat"] for r in unit if parse(r["valid_from"]) and parse(r["valid_from"]) >= now - timedelta(hours=24))) > 2:
        for r in sorted(unit, key=lambda r: r["valid_from"]):
            f = parse(r["valid_from"])
            if f and f >= now - timedelta(minutes=30):
                upcoming.append([iso(f), r["value_inc_vat"]])
    last = readings[-1]["interval_end"] if readings else None
    hist = history(fuel, point, ident, factor, now)
    return {"tariff": tariff, "unit": unit_price(now), "standing": price_at(stand, now),
            "from": ag.get("valid_from"), "until": ag.get("valid_to"),
            "last": last, "days": out_days, "upcoming": upcoming[:96],
            "profile": profile, "base": base, "hist": hist, "_month": month}


class Prices:
    """Unit rates and standing charges over all past agreements, looked up by time (bisect)."""
    def __init__(self, fuel, agreements, since, until):
        self.u, self.s = [], []
        for a in agreements or []:
            f, t = parse(a.get("valid_from")) or since, parse(a.get("valid_to")) or until
            f, t = max(f, since), min(t, until)
            if f >= t:
                continue
            tc = a["tariff_code"]
            u = rates(fuel, tc, "standard-unit-rates", f, t) or rates(fuel, tc, "day-unit-rates", f, t)
            self.u += [(parse(r.get("valid_from")) or since, parse(r.get("valid_to")) or until, r["value_inc_vat"]) for r in u]
            self.s += [(parse(r.get("valid_from")) or since, parse(r.get("valid_to")) or until, r["value_inc_vat"]) for r in rates(fuel, tc, "standing-charges", f, t)]
        self.u.sort(key=lambda x: x[0]); self.s.sort(key=lambda x: x[0])
        self.uk = [x[0] for x in self.u]; self.sk = [x[0] for x in self.s]

    def _at(self, rows, keys, t):
        i = bisect.bisect_right(keys, t) - 1
        for j in range(i, max(-1, i - 50), -1):              # newest rate that covers t
            if rows[j][0] <= t < rows[j][1]:
                return rows[j][2]
        return None

    def day(self, k):
        """Average unit price over the day (time-of-use tariffs averaged) and the standing charge."""
        d0 = datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=TZ)
        ps = [self._at(self.u, self.uk, d0 + timedelta(hours=h)) for h in (1, 5, 9, 13, 17, 21)]
        ps = [p for p in ps if p is not None]
        return (sum(ps) / len(ps) if ps else None), self._at(self.s, self.sk, d0 + timedelta(hours=12))


def history(fuel, point, ident, factor, now):
    """Daily kWh and £ for about two years (as far back as the smart meter goes)."""
    since = (datetime.now(TZ) - timedelta(days=HIST)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = []
    for m in point.get("meters", []):
        url = "%s%s-meter-points/%s/meters/%s/consumption/?period_from=%s&period_to=%s&group_by=day&page_size=1000&order_by=period" % (
            API, fuel, ident, urllib.parse.quote(m["serial_number"]), iso(since), iso(now))
        try:
            rows = get_all(url)
        except Exception as e:
            print("%s history: %s" % (fuel, e))
        if rows:
            break
    if not rows:
        return []
    pr = Prices(fuel, point.get("agreements"), since, now)
    out = []
    for r in rows:
        k = parse(r["interval_start"]).astimezone(TZ).strftime("%Y-%m-%d")
        kwh = r["consumption"] * factor
        unit, sc = pr.day(k)
        out.append([k, round(kwh, 2), round(kwh * (unit or 0) + (sc or 0), 1)])
    print("%s history: %d days from %s" % (fuel, len(out), out[0][0]))
    return out


def other_tariffs(data, now):
    """What the last four weeks would have cost on Agile and Tracker, from your own half-hours."""
    e = data.get("elec") or {}
    region = (e.get("tariff") or "").split("-")[-1]
    if not region or not e.get("_month"):
        return None
    try:
        prods = get_all(API + "products/?brand=OCTOPUS_ENERGY&is_business=false&page_size=100")
    except Exception as ex:
        print("products:", ex)
        return None

    print("products:", " ".join(sorted(p["code"] for p in prods if p["code"].startswith(("AGILE", "SILVER", "TRACKER")))))

    def pick(prefix):
        ps = [p for p in prods if p["code"].startswith(prefix) and "OUTGOING" not in p["code"] and not p.get("available_to")]
        return max(ps, key=lambda p: p.get("available_from") or "")["code"] if ps else None

    out = {}
    for name, prefix in (("agile", "AGILE-"), ("tracker", "SILVER-")):
        code = pick(prefix) or (pick("TRACKER-") if name == "tracker" else None)
        if not code:
            continue
        try:
            det = get(API + "products/%s/" % code, auth=False)
        except Exception as ex:
            print(code, ex)
            continue
        for fuel, key in (("elec", "electricity"), ("gas", "gas")):
            if fuel == "gas" and name == "agile":           # Agile is electricity only
                continue
            f = data.get(fuel) or {}
            m = f.get("_month") or {}
            reg = (det.get("single_register_%s_tariffs" % key) or {}).get("_" + region) or {}
            tc = (reg.get("direct_debit_monthly") or {}).get("code")
            if not tc or not m:
                continue
            ks = sorted(m)
            a = datetime.strptime(ks[0], "%Y-%m-%d").replace(tzinfo=TZ)
            b = datetime.strptime(ks[-1], "%Y-%m-%d").replace(tzinfo=TZ) + timedelta(days=1)
            unit = {r["valid_from"]: r["value_inc_vat"] for r in rates(key, tc, "standard-unit-rates", a, b)}
            urows = sorted((parse(k) or a, v) for k, v in unit.items())
            ukeys = [u[0] for u in urows]
            stand = rates(key, tc, "standing-charges", a, b)
            if not urows:
                continue
            tot, now_tot = 0.0, 0.0
            for k in ks:
                hh, paid = m[k]
                d0 = datetime.strptime(k, "%Y-%m-%d").replace(tzinfo=TZ)
                for i, kwh in enumerate(hh):
                    t = (d0 + timedelta(minutes=30 * i)).astimezone(timezone.utc)
                    j = bisect.bisect_right(ukeys, t) - 1
                    tot += kwh * (urows[j][1] if j >= 0 else urows[0][1])
                tot += price_at(stand, d0 + timedelta(hours=12)) or 0
                now_tot += paid
            out.setdefault(fuel, {"days": len(ks), "now": round(now_tot)})[name] = round(tot)
            print("%s on %s (%s): %dp vs now %dp over %d days" % (fuel, name, tc, tot, now_tot, len(ks)))
    return out or None


def outdoor_temps():
    """Daily mean temperature at home for the last three months (Open-Meteo, no key)."""
    for attempt in range(3):          # Open-Meteo sometimes times out from GitHub's runners
      try:
        d = get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&daily=temperature_2m_mean&past_days=92&forecast_days=1&timezone=Europe%%2FLondon" % (LAT, LON), auth=False)
        return [[k, v] for k, v in zip(d["daily"]["time"], d["daily"]["temperature_2m_mean"]) if v is not None]
      except Exception as e:
        print("outdoor temperature:", e)
        __import__("time").sleep(5)
    return None


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


def saving_sessions(now, mpan):
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
        d = q({"query": "query($a:String!,$m:String!){customerFlexibilityCampaignEvents(accountNumber:$a,supplyPointIdentifier:$m,campaignSlug:\"octoplus-saving-sessions\",first:20)"
                        "{edges{node{name code startAt endAt}}}}", "variables": {"a": ACCOUNT, "m": mpan}}, token)
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
    mpan = None
    for p in props[:1]:
        imp = [m for m in p.get("electricity_meter_points", []) if not m.get("is_export")]
        if imp:
            mpan = imp[0].get("mpan")
            data["elec"] = fuel_block("electricity", imp[0], since, now, now)
        if p.get("gas_meter_points"):
            data["gas"] = fuel_block("gas", p["gas_meter_points"][0], since, now, now)
    cmp = other_tariffs(data, now)
    if cmp:
        data["compare"] = cmp
    for fuel in ("elec", "gas"):
        if data.get(fuel):
            data[fuel].pop("_month", None)
    temps = outdoor_temps()
    if temps:
        data["temps"] = temps
    free = free_sessions(now)
    if free is not None:
        data["free"] = free
    saving = saving_sessions(now, mpan) if mpan else None
    if saving is not None:
        data["saving"] = saving

    body = dict(data); body.pop("saved")
    plain = json.dumps(body, separators=(",", ":"))
    same = dict(body); same.pop("temps", None)            # weather alone is no reason to save again
    digest = __import__("hashlib").sha256(json.dumps(same, separators=(",", ":")).encode()).hexdigest()[:16]
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
