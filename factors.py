"""
Extra inputs for the buy/sell signals + market context:

- Live **futures** + an index-futures sentiment bias.
- A **commodity supply/demand proxy** that tilts Energy and Materials signals.
- An **event calendar** (FOMC, CPI, jobs, share-issuance/lockups, SpaceX share
  releases) with per-event **risk levels** and an overall event_risk dampener.
- A daily **crash-risk gauge** built from the factors that historically precede big
  drawdowns (valuation, S&P vs 200-day, yield-curve, drawdown, volatility, momentum).
  It is a RISK READING, not a crash prediction — nobody can reliably time crashes.
- Best-effort **market news + war/geopolitical risk** flag.

Everything here is mechanical context, NOT financial advice.
"""

import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import yfinance as yf

ET = ZoneInfo("America/New_York")


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


# --------------------------------------------------------------------------
# Futures
# --------------------------------------------------------------------------
FUTURES = [
    ("ES=F", "S&P 500", "index"), ("NQ=F", "Nasdaq 100", "index"), ("YM=F", "Dow", "index"),
    ("CL=F", "WTI Crude", "energy"), ("NG=F", "Nat Gas", "energy"),
    ("GC=F", "Gold", "metal"), ("SI=F", "Silver", "metal"), ("HG=F", "Copper", "metal"),
]
FUT_TICKERS = [f[0] for f in FUTURES]


def _mom(df, days=21):
    if df is None or df.empty or "Close" not in df:
        return None, None, None
    c = df["Close"].dropna()
    if c.empty:
        return None, None, None
    price = float(c.iloc[-1])
    chg = float((c.iloc[-1] / c.iloc[-2] - 1) * 100) if len(c) >= 2 else 0.0
    n = min(days, len(c) - 1)
    mom = float((c.iloc[-1] / c.iloc[-1 - n] - 1) * 100) if n > 0 else 0.0
    return price, chg, mom


def fetch_futures(daily_map):
    items, idx_chg = [], []
    for sym, name, grp in FUTURES:
        price, chg, mom = _mom(daily_map.get(sym))
        items.append({"symbol": sym, "name": name, "group": grp,
                      "price": round(price, 2) if price is not None else None,
                      "chg_pct": round(chg, 2) if chg is not None else None,
                      "mom1m": round(mom, 1) if mom is not None else None})
        if grp == "index" and chg is not None:
            idx_chg.append(chg)
    bias = _clamp(_avg(idx_chg) / 1.5, -1, 1) if idx_chg else 0.0
    return {"items": items, "bias": round(bias, 3)}


def commodity_supply_demand(daily_map):
    def mom(sym):
        return _mom(daily_map.get(sym))[2]
    crude, gas, copper, gold, silver = mom("CL=F"), mom("NG=F"), mom("HG=F"), mom("GC=F"), mom("SI=F")
    energy_tilt = _clamp(_avg([crude, gas]) / 12.0, -0.4, 0.4)
    materials_tilt = _clamp(_avg([copper, gold, silver]) / 12.0, -0.4, 0.4)
    notes = []
    if energy_tilt > 0.05:
        notes.append("Energy demand firm (crude/gas rising)")
    elif energy_tilt < -0.05:
        notes.append("Energy demand soft (crude/gas falling)")
    if materials_tilt > 0.05:
        notes.append("Metals bid (copper/precious up)")
    elif materials_tilt < -0.05:
        notes.append("Metals weak")
    rd = {"crude_1mo": crude, "natgas_1mo": gas, "copper_1mo": copper, "gold_1mo": gold, "silver_1mo": silver}
    rd = {k: (round(v, 1) if v is not None else None) for k, v in rd.items()}
    return {"energy_tilt": round(energy_tilt, 3), "materials_tilt": round(materials_tilt, 3),
            "readings": rd, "notes": notes or ["Commodities mixed"]}


SECTOR_TILT = {"Energy": "energy_tilt", "Materials": "materials_tilt"}


def sector_tilt(commod, sector):
    key = SECTOR_TILT.get(sector)
    return commod.get(key, 0.0) if key else 0.0


# --------------------------------------------------------------------------
# Crash-risk gauge  (daily)
# --------------------------------------------------------------------------
def _rsi_last(closes, period=14):
    d = closes.diff()
    up = d.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = up / dn.replace(0, 1e-9)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def crash_risk(daily_map, cape, cape_mean, next_fed=None):
    out = {"score": None, "level": "n/a", "components": [], "drivers": [],
           "scale_note": "", "timing_note": "", "readings": {}, "as_of": None}
    g = daily_map.get("^GSPC")
    if g is None or g.empty:
        return out
    gc = g["Close"].dropna()
    if gc.empty:
        return out
    price = float(gc.iloc[-1])
    sma200 = float(gc.tail(200).mean()) if len(gc) >= 200 else float(gc.mean())
    vs200 = (price / sma200 - 1) * 100
    hi1y = float(gc.tail(252).max())
    dd1y = (price / hi1y - 1) * 100
    rsi = _rsi_last(gc) if len(gc) > 15 else 50.0

    def last(sym):
        df = daily_map.get(sym)
        if df is None or df.empty:
            return None
        c = df["Close"].dropna()
        return float(c.iloc[-1]) if not c.empty else None
    vix = last("^VIX")
    tnx = last("^TNX")
    if tnx and tnx > 20:
        tnx /= 10.0
    irx = last("^IRX")
    if irx and irx > 20:
        irx /= 10.0
    curve = (tnx - irx) if (tnx is not None and irx is not None) else None

    val_c = _clamp((cape - 18) / 22.0, 0, 1)
    trend_c = 1.0 if vs200 < 0 else (0.5 if vs200 < 3 else 0.1)
    if curve is None:
        curve_c = 0.3
    else:
        curve_c = 1.0 if curve < 0 else (0.5 if curve < 0.5 else 0.1)
    dd_c = _clamp(-dd1y / 20.0, 0, 1)
    if vix is None:
        vix_c = 0.2
    elif vix < 13:
        vix_c = 0.4
    elif vix < 20:
        vix_c = 0.2
    elif vix < 30:
        vix_c = 0.6
    else:
        vix_c = 0.9
    rsi_c = 0.7 if rsi >= 75 else (0.4 if rsi >= 68 else 0.1)

    W = {"val": 0.30, "trend": 0.25, "curve": 0.15, "dd": 0.10, "vix": 0.10, "rsi": 0.10}
    score = round((W["val"] * val_c + W["trend"] * trend_c + W["curve"] * curve_c
                   + W["dd"] * dd_c + W["vix"] * vix_c + W["rsi"] * rsi_c) * 100)
    level = "Low" if score < 25 else "Elevated" if score < 45 else "High" if score < 65 else "Severe"

    def lvl(c):
        return "High" if c >= 0.66 else "Medium" if c >= 0.4 else "Low"
    components = [
        {"name": f"Valuation — CAPE {cape:.0f} (avg {cape_mean:.0f})", "risk": lvl(val_c)},
        {"name": f"Trend — S&P {vs200:+.0f}% vs 200-day", "risk": lvl(trend_c)},
        {"name": (f"Yield curve — 10y−3m {curve:+.2f}" if curve is not None else "Yield curve — n/a"), "risk": lvl(curve_c)},
        {"name": f"Drawdown — {dd1y:+.0f}% from 1y high", "risk": lvl(dd_c)},
        {"name": (f"Volatility — VIX {vix:.0f}" if vix is not None else "Volatility — n/a"), "risk": lvl(vix_c)},
        {"name": f"Momentum — S&P RSI {rsi:.0f}", "risk": lvl(rsi_c)},
    ]
    drivers = [c["name"].split(" — ")[0] for c in components if c["risk"] == "High"]

    if score < 25:
        scale = "Low risk: no major fragility flags. Pullbacks under ~10% are always possible, but no crash setup is present."
    elif score < 45:
        scale = ("Elevated, valuation-driven: the market is expensive but the up-trend is intact. A shock would more likely "
                 "bring a ~10–15% correction; a >30% bear market has historically required a recession or credit event, none of which is flashing.")
    elif score < 65:
        scale = ("High: several fragility flags are aligned. Setups like this have historically preceded drawdowns of roughly 20–35%.")
    else:
        scale = ("Severe: stretched valuation AND a technical/credit breakdown together — the conditions that preceded the worst bears (−30% to −50%+).")
    timing = ("This is a risk gauge, not a timing call — overvalued markets can keep rising for years. Watch the real triggers: "
              "the S&P closing below its 200-day average, the yield curve inverting, or VIX spiking above 30."
              + (f" Next Fed decision: {next_fed['date']} ({next_fed['days']}d)." if next_fed else ""))

    out.update(score=score, level=level, components=components, drivers=drivers or ["No single factor at High risk"],
               scale_note=scale, timing_note=timing,
               readings={"cape": cape, "sp_vs_200d_pct": round(vs200, 1),
                         "curve": round(curve, 2) if curve is not None else None,
                         "vix": round(vix, 1) if vix is not None else None,
                         "drawdown_1y_pct": round(dd1y, 1), "rsi": round(rsi)},
               as_of=str(gc.index[-1].date()))
    return out


# --------------------------------------------------------------------------
# Event calendar
# --------------------------------------------------------------------------
FOMC_2026 = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
             "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
CPI_2026 = ["2026-07-14", "2026-08-12", "2026-09-11", "2026-10-13", "2026-11-13", "2026-12-10"]
SUPPLY_EVENTS = []
SPACEX_EVENTS = [
    {"date": "2026-09-10", "label": "SpaceX (SPCX) staggered lockup — partial release",
     "note": "~90 days post-IPO; staggered early release (approx, editable)"},
    {"date": "2026-12-09", "label": "SpaceX (SPCX) 180-day lockup expiry",
     "note": "180 days after the Jun 12 2026 IPO — bulk of employee shares unlock"},
]
IMPACT = {"fed": 1.0, "cpi": 0.85, "jobs": 0.6, "supply": 0.5, "spacex": 0.5, "ipo": 0.55}


def _first_friday(y, m):
    d = date(y, m, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def _prox(days):
    if days <= 2:
        return 1.0
    if days <= 7:
        return 0.85
    if days <= 21:
        return 0.65
    return 0.5


def _risk_level(score):
    return "High" if score >= 0.7 else "Medium" if score >= 0.45 else "Low"


def event_calendar(now_et=None):
    now = now_et or datetime.now(ET)
    today = now.date()
    raw = []
    for s in FOMC_2026:
        raw.append((date.fromisoformat(s), "Fed rate decision", "fed", "FOMC interest-rate decision (2pm ET)"))
    for i, s in enumerate(CPI_2026):
        lbl = "CPI inflation report" + ("" if i == 0 else " (approx)")
        raw.append((date.fromisoformat(s), lbl, "cpi", "Consumer Price Index (8:30am ET)"))
    for k in range(0, 4):
        m = now.month + k
        y = now.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        raw.append((_first_friday(y, m), "Jobs report (NFP)", "jobs", "Nonfarm payrolls (8:30am ET)"))
    for e in SUPPLY_EVENTS:
        try:
            raw.append((date.fromisoformat(e["date"]), f"Share supply: {e['ticker']} {e['type']}", "supply", e.get("note", "")))
        except Exception:
            pass
    for e in SPACEX_EVENTS:
        try:
            raw.append((date.fromisoformat(e["date"]), e["label"], "spacex", e.get("note", "")))
        except Exception:
            pass

    fut = [r for r in raw if r[0] >= today]
    macro = sorted([r for r in fut if r[2] in ("fed", "cpi", "jobs")], key=lambda r: r[0])[:8]
    curated = sorted([r for r in fut if r[2] in ("supply", "spacex", "ipo")], key=lambda r: r[0])
    upcoming = sorted(macro + curated, key=lambda r: r[0])

    events = []
    for r in upcoming:
        days = (r[0] - today).days
        score = round(IMPACT.get(r[2], 0.5) * _prox(days), 2)
        events.append({"date": r[0].isoformat(), "days": days, "label": r[1], "kind": r[2],
                       "note": r[3], "risk": _risk_level(score), "risk_score": score})

    risk = 0.0
    for e in events:
        if e["kind"] == "fed":
            if e["days"] <= 1: risk = max(risk, 1.0)
            elif e["days"] <= 2: risk = max(risk, 0.7)
            elif e["days"] <= 4: risk = max(risk, 0.4)
        elif e["kind"] == "cpi":
            if e["days"] <= 1: risk = max(risk, 0.5)
            elif e["days"] <= 2: risk = max(risk, 0.3)
    next_fed = next((e for e in events if e["kind"] == "fed"), None)
    return {"events": events, "event_risk": round(risk, 2), "next_fed": next_fed}


# --------------------------------------------------------------------------
# News + war/geopolitical risk (best-effort)
# --------------------------------------------------------------------------
WAR_KEYWORDS = ["war", "missile", "strike", "invasion", "conflict", "attack", "sanction",
                "ceasefire", "nuclear", "troops", "airstrike", "escalat", "military", "hostage", "drone"]


def score_geo(titles):
    if not titles:
        return 0.0
    hits = sum(1 for t in titles for k in WAR_KEYWORDS if k in (t or "").lower())
    return round(min(1.0, hits / 6.0), 2)


def fetch_news(timeout=6):
    try:
        import urllib.request
        url = ("https://news.google.com/rss/search?q=stock+market+OR+geopolitical+OR+war+when:1d"
               "&hl=en-US&gl=US&ceid=US:en")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
        titles = re.findall(r"<title>(.*?)</title>", raw, flags=re.S)[1:13]
        clean = []
        for t in titles:
            t = re.sub(r"<!\[CDATA\[|\]\]>", "", t)
            t = re.sub(r"<.*?>", "", t).replace("&apos;", "'").replace("&amp;", "&").replace("&#39;", "'").strip()
            if t:
                clean.append(t)
        return {"headlines": clean[:8], "geo_risk": score_geo(clean), "note": None}
    except Exception:
        return {"headlines": [], "geo_risk": 0.0, "note": "news feed unavailable"}


# --- end of factors.py ---
