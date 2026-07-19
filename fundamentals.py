"""
Fundamentals + Street-consensus + crash-risk overlay on the calibrated confidence.

signal_calibration.py answers "how often was this signal band right, historically?"
That is price-only. This module folds in the three things a price-only read misses:

  1. CRASH RISK — when the index-level crash gauges are elevated (factors.crash_risk
     score and/or the Crash Radar's model 1-month crash odds), bullish confidence is
     damped and bearish confidence gets a small boost. A 74%-confident BUY during a
     Severe-risk tape should not read 74%.
  2. FUNDAMENTALS (the industry-standard quality factors): revenue YoY growth,
     profit margin, earnings YoY growth, return on equity — scored 0-100 the same
     way quant "quality" factors are built. Good businesses nudge BUY confidence up
     and SELL confidence down; deteriorating ones do the reverse (±8 pts max).
  3. STREET ANCHOR — the confidence should not be far off what other places rank.
     Analyst consensus (recommendationMean 1=Strong Buy … 5=Sell, with coverage
     count) maps to a 0-100 buy-side anchor; our confidence is blended 75/25 toward
     it and clamped to ±20 pts of it whenever ≥4 analysts cover the name. ETFs and
     uncovered names skip this leg.

Data: yfinance `Ticker.info` (Yahoo Finance's own fundamentals + analyst consensus —
the same numbers Yahoo/Barchart-style sites display). Fetched once per trading day
and cached in fundamentals_state.json. NOT financial advice.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fundamentals_state.json")
SCHEMA = 1
MIN_ANALYSTS = 4      # coverage needed before the Street anchor applies
ANCHOR_BAND = 20      # final confidence must sit within ±this of the Street anchor
W_SELF = 0.75         # blend: 75% our calibrated read, 25% Street
MAX_FUND_ADJ = 8      # max points the quality score can move confidence
MAX_CRASH_DAMP = 12   # max points crash risk can strip from a BUY
MAX_CRASH_BOOST = 8   # max points crash risk can add to a SELL


def _clip01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _pct(v, nd=1):
    return round(v * 100, nd) if isinstance(v, (int, float)) else None


def _one(t):
    try:
        i = yf.Ticker(t).info or {}
    except Exception:
        return t, None
    qt = i.get("quoteType")
    g, eg = i.get("revenueGrowth"), i.get("earningsGrowth")
    m, roe = i.get("profitMargins"), i.get("returnOnEquity")
    comps = []
    if isinstance(g, (int, float)):   comps.append(_clip01(0.5 + g / 0.40))    # ±20% YoY spans the range
    if isinstance(m, (int, float)):   comps.append(_clip01(0.5 + m / 0.40))
    if isinstance(eg, (int, float)):  comps.append(_clip01(0.5 + eg / 0.60))
    if isinstance(roe, (int, float)): comps.append(_clip01(0.5 + roe / 0.40))
    quality = round(100 * sum(comps) / len(comps)) if comps else None
    rec, nan = i.get("recommendationMean"), i.get("numberOfAnalystOpinions")
    anchor = round((5.0 - rec) / 4.0 * 100) if isinstance(rec, (int, float)) else None
    px, tgt = i.get("currentPrice") or i.get("regularMarketPrice"), i.get("targetMeanPrice")
    upside = round((tgt / px - 1) * 100, 1) if (isinstance(px, (int, float)) and px and isinstance(tgt, (int, float))) else None
    return t, {"quote_type": qt, "quality": quality,
               "rev_growth_pct": _pct(g), "earn_growth_pct": _pct(eg),
               "margin_pct": _pct(m), "roe_pct": _pct(roe),
               "rec_mean": (round(rec, 2) if isinstance(rec, (int, float)) else None),
               "rec_key": i.get("recommendationKey"),
               "analysts": (int(nan) if isinstance(nan, (int, float)) else 0),
               "street_anchor": anchor, "target_upside_pct": upside}


def compute(tickers):
    out = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for t, row in ex.map(_one, sorted(set(x for x in tickers if x))):
            if row is not None:
                out[t] = row
    return {"meta": {"schema": SCHEMA, "min_analysts": MIN_ANALYSTS, "anchor_band": ANCHOR_BAND,
                     "w_self": W_SELF}, "tickers": out}


def crash_risk01(crash_score=None, radar_prob_pct=None):
    """0-1 severity of index-level crash risk. factors.crash_risk score is 0-100
    ('Low' < 25); the Crash Radar 1-month odds run ~5-6% in a normal tape."""
    c = 0.0
    if isinstance(crash_score, (int, float)):
        c = max(c, (crash_score - 25.0) / 75.0)
    if isinstance(radar_prob_pct, (int, float)):
        c = max(c, (radar_prob_pct - 6.0) / 24.0)
    return _clip01(c)


def apply(sig, fund, crash_score=None, radar_prob_pct=None):
    """Mutate a signal dict: adjust conf_pct for crash risk, fundamentals and the
    Street anchor. Keeps the raw calibrated number in conf_cal_pct and the
    per-leg deltas in conf_adj so the UI can show its work."""
    if not sig or sig.get("conf_pct") is None:
        return sig
    act = sig.get("action")
    conf0 = float(sig["conf_pct"])
    conf = conf0
    adj = {"crash": 0, "fund": 0, "street": 0}
    # 1) crash-risk weighting
    c01 = crash_risk01(crash_score, radar_prob_pct)
    if act == "BUY":
        adj["crash"] = -round(MAX_CRASH_DAMP * c01)
    elif act == "SELL":
        adj["crash"] = round(MAX_CRASH_BOOST * c01)
    conf += adj["crash"]
    # 2) fundamentals quality tilt
    q = (fund or {}).get("quality")
    if q is not None and act in ("BUY", "SELL"):
        tilt = (q - 50.0) / 50.0
        adj["fund"] = round(MAX_FUND_ADJ * tilt) if act == "BUY" else -round(MAX_FUND_ADJ * tilt)
        conf += adj["fund"]
    # 3) Street anchor: stay within shouting distance of consensus
    a, n = (fund or {}).get("street_anchor"), (fund or {}).get("analysts") or 0
    if a is not None and n >= MIN_ANALYSTS and act in ("BUY", "SELL"):
        aa = a if act == "BUY" else 100 - a
        blended = W_SELF * conf + (1 - W_SELF) * aa
        newc = min(max(blended, aa - ANCHOR_BAND), aa + ANCHOR_BAND)
        adj["street"] = round(newc - conf)
        conf = newc
    conf = int(round(max(5.0, min(95.0, conf))))
    sig["conf_cal_pct"] = int(round(conf0))
    sig["conf_pct"] = conf
    sig["conf_adj"] = adj
    return sig


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return None


def save_state(s):
    try:
        with open(STATE, "w") as f:
            json.dump(s, f)
    except Exception as e:
        print(f"[warn] fundamentals state save failed: {e}", flush=True)


def ensure(daily, tickers):
    """Refetch once per trading day; reuse the cache otherwise."""
    tickers = [t for t in (tickers or []) if t]
    latest = None
    for probe in ("SPY", "AAPL", "MSFT", "NVDA", "VOO"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    fresh = (state and state.get("tickers") and latest
             and state.get("meta", {}).get("seeded_through") == latest
             and state.get("meta", {}).get("schema") == SCHEMA)
    if fresh:
        return state
    try:
        new = compute(tickers)
    except Exception as e:
        print(f"[warn] fundamentals compute failed: {e}", flush=True)
        return state
    new["meta"]["seeded_through"] = latest
    if new.get("tickers"):
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    demo = ["MU", "NVDA", "AAPL", "TSLA", "GLD", "VOO", "STX"]
    r = compute(demo)
    print(f"{'tkr':6s}{'qual':>5s}{'rev%':>8s}{'marg%':>7s}{'roe%':>7s}{'rec':>6s}{'n':>4s}{'anchor':>7s}{'upside':>8s}")
    for t in demo:
        f = r["tickers"].get(t) or {}
        fmt = lambda v: '—' if v is None else str(v)
        print(f"{t:6s}{fmt(f.get('quality')):>5s}{fmt(f.get('rev_growth_pct')):>8s}{fmt(f.get('margin_pct')):>7s}"
              f"{fmt(f.get('roe_pct')):>7s}{fmt(f.get('rec_mean')):>6s}{fmt(f.get('analysts')):>4s}"
              f"{fmt(f.get('street_anchor')):>7s}{fmt(f.get('target_upside_pct')):>8s}")
    # demo adjustment: a 74% BUY in a High-risk tape on a strong name
    sig = {"action": "BUY", "conf_pct": 74}
    apply(sig, r["tickers"].get("NVDA"), crash_score=55, radar_prob_pct=14)
    print("BUY 74 + High crash risk + NVDA fundamentals ->", sig["conf_pct"], sig["conf_adj"])

# --- end of fundamentals.py ---
