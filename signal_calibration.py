"""
Calibrated buy/sell CONFIDENCE for the v2 signal.

The old "confidence" was just |score| — signal strength dressed up as a
probability. This module replaces it with the honest version, the same
"what actually happened next" machinery as watchlist_levels, but conditioned
on the SIGNAL BAND instead of the raw trend state:

  1. Reconstruct the price-only core of compute_signal v2 (trend, cross,
     momentum, RSI, day move + the crash guards: 52w-high drawdown, 200-day
     filter, vol spike, fast-crash override) through ~10 years of daily closes.
     Price-only, so it is exactly reconstructable — the macro/event/sector
     overlays are live-only and are NOT in the history (documented bias:
     live scores can sit a few points below their historical twin).
  2. Bucket every historical day into a band: strong_sell / sell / hold /
     buy / strong_buy.
  3. Grade each band by the forward return that FOLLOWED it: the share of
     days the price was higher 21 trading days (~1mo) and 252 days (~1yr)
     later, plus the average forward move.
  4. Live confidence = the band's historical hit-rate for the action taken
     (BUY -> P(up), SELL -> P(down), HOLD -> P(roughly flat)), shrunk toward
     the pooled watchlist rate when a ticker's own band history is thin
     (empirical Bayes: p = (hits + M0*pooled) / (n + M0)).

Cached daily in signal_calibration_state.json (the 10y fetch is slow).
Mechanical, history-based — NOT financial advice; the future need not rhyme.
"""

import json
import os

import numpy as np
import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signal_calibration_state.json")
PERIOD = "10y"
ST_H = 21            # ~1 month  — the horizon behind the headline confidence
LT_H = 252           # ~1 year   — used by the forever-hold entry blend
FLAT_BAND = 0.05     # HOLD counts as "right" if |21d move| <= 5%
M0 = 60              # empirical-Bayes prior weight (pseudo-samples of pooled rate)
MIN_OWN = 120        # band samples needed before the estimate counts as "own"
SCHEMA = 1

# Score bands (mirror SIGNAL_BUY=25 / SIGNAL_SELL=-25 in stock_dashboard.py)
BANDS = [("strong_sell", -101, -60), ("sell", -60, -25), ("hold", -25, 25),
         ("buy", 25, 60), ("strong_buy", 60, 101)]


def band_of(score):
    s = float(score or 0)
    for name, lo, hi in BANDS:
        if lo <= s < hi:
            return name
    return "strong_buy" if s >= 60 else "strong_sell"


def _rsi(s, period=14):
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    ru = up.ewm(alpha=1 / period, adjust=False).mean()
    rd = dn.ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd.replace(0, 1e-9))


def hist_scores(c):
    """Vectorized price-only v2 score series for one ticker (daily closes)."""
    sma20, sma50 = c.rolling(20).mean(), c.rolling(50).mean()
    sma200 = c.rolling(200, min_periods=200).mean()
    hi52 = c.rolling(252, min_periods=60).max()
    rsi = _rsi(c)
    mom1m = (c / c.shift(21) - 1) * 100
    ret10 = (c / c.shift(10) - 1) * 100
    chg = (c / c.shift(1) - 1) * 100
    r = c.pct_change()
    vol10, vol63 = r.rolling(10).std(), r.rolling(63).std()

    clip = lambda x: x.clip(-1, 1)
    tech = (30 * np.where(c > sma50, 1, -1) + 20 * np.where(sma20 > sma50, 1, -1)
            + 25 * clip(mom1m / 10.0) + 15 * clip((rsi - 50.0) / 20.0) + 10 * clip(chg / 3.0))
    raw = pd.Series(tech, index=c.index).clip(-100, 100)

    offh = (c / hi52 - 1) * 100
    raw = raw + pd.Series(np.where(offh <= -20, -25.0, np.where(offh <= -10, -12.0, 0.0)), index=c.index)
    below = (c < sma200) & sma200.notna()
    raw = pd.Series(np.where(below, np.minimum(raw - 10, 24.0), raw), index=c.index)   # Faber: no BUY below 200d
    spike = (vol10 / vol63 >= 1.8) & (raw > 0)
    raw = pd.Series(np.where(spike, raw * 0.6, raw), index=c.index)
    crash = (ret10 <= -12) | (mom1m <= -18)
    raw = pd.Series(np.where(crash, np.minimum(raw, -40.0), raw), index=c.index)       # fast-crash override
    return raw.clip(-100, 100).where(sma50.notna())


def _fetch(tickers):
    syms = sorted(set(t for t in tickers if t))
    d = yf.download(" ".join(syms), period=PERIOD, interval="1d", auto_adjust=True,
                    group_by="ticker", progress=False, threads=False)
    out = {}
    for s in syms:
        try:
            c = d[s]["Close"].dropna()
            if isinstance(c, pd.DataFrame):
                c = c.iloc[:, 0]
            if len(c) >= 120:
                out[s] = c
        except Exception:
            pass
    return out


def compute(tickers):
    px = _fetch(tickers)
    per = {}          # ticker -> band -> raw tallies
    pool = {name: {"n_st": 0, "up_st": 0, "flat_st": 0, "n_lt": 0, "up_lt": 0,
                   "sum_st": 0.0, "sum_lt": 0.0} for name, _, _ in BANDS}
    for t, c in px.items():
        sc = hist_scores(c)
        fwd_st = c.shift(-ST_H) / c - 1
        fwd_lt = c.shift(-LT_H) / c - 1
        rows = {}
        for name, lo, hi in BANDS:
            m = sc.notna() & (sc >= lo) & (sc < hi)
            vs, vl = fwd_st[m].dropna(), fwd_lt[m].dropna()
            rows[name] = {"n_st": int(len(vs)), "up_st": int((vs > 0).sum()),
                          "flat_st": int((vs.abs() <= FLAT_BAND).sum()),
                          "n_lt": int(len(vl)), "up_lt": int((vl > 0).sum()),
                          "sum_st": float(vs.sum()), "sum_lt": float(vl.sum())}
            for k in pool[name]:
                pool[name][k] += rows[name][k]
        per[t] = rows

    pooled = {}
    for name, agg in pool.items():
        pooled[name] = {
            "p_up_st": (agg["up_st"] / agg["n_st"]) if agg["n_st"] else 0.5,
            "p_flat_st": (agg["flat_st"] / agg["n_st"]) if agg["n_st"] else 0.3,
            "p_up_lt": (agg["up_lt"] / agg["n_lt"]) if agg["n_lt"] else 0.6,
            "fwd_st_avg_pct": round(agg["sum_st"] / agg["n_st"] * 100, 1) if agg["n_st"] else None,
            "fwd_lt_avg_pct": round(agg["sum_lt"] / agg["n_lt"] * 100, 1) if agg["n_lt"] else None,
            "n_st": agg["n_st"], "n_lt": agg["n_lt"]}

    def shrink(hits, n, prior):
        return (hits + M0 * prior) / (n + M0) if (n + M0) else prior

    tick = {}
    for t, rows in per.items():
        bands = {}
        for name, r in rows.items():
            pl = pooled[name]
            bands[name] = {
                "n": r["n_st"],
                "p_up_st": round(shrink(r["up_st"], r["n_st"], pl["p_up_st"]) * 100),
                "p_flat_st": round(shrink(r["flat_st"], r["n_st"], pl["p_flat_st"]) * 100),
                "p_up_lt": round(shrink(r["up_lt"], r["n_lt"], pl["p_up_lt"]) * 100),
                "fwd_st_avg_pct": round(r["sum_st"] / r["n_st"] * 100, 1) if r["n_st"] else pl["fwd_st_avg_pct"],
                "fwd_lt_avg_pct": round(r["sum_lt"] / r["n_lt"] * 100, 1) if r["n_lt"] else pl["fwd_lt_avg_pct"],
                "basis": "own" if r["n_st"] >= MIN_OWN else "pooled"}
        tick[t] = {"bands": bands, "hist_days": int(len(px[t]))}

    return {"meta": {"schema": SCHEMA, "st_h": ST_H, "lt_h": LT_H, "flat_band_pct": FLAT_BAND * 100,
                     "m0": M0, "min_own": MIN_OWN,
                     "pooled": {k: {"p_up_st": round(v["p_up_st"] * 100), "p_up_lt": round(v["p_up_lt"] * 100),
                                    "p_flat_st": round(v["p_flat_st"] * 100), "n_st": v["n_st"]}
                                for k, v in pooled.items()}},
            "tickers": tick}


def annotate(state, ticker, score, action):
    """Fields to merge into a live signal dict: calibrated confidence for the
    action taken + the band's raw up-odds (used by the forever-hold blend)."""
    if not state:
        return {}
    b = band_of(score)
    tk = (state.get("tickers") or {}).get(ticker)
    if tk and b in tk.get("bands", {}):
        e = tk["bands"][b]
        basis, n = e["basis"], e["n"]
        p_up_st, p_flat_st, p_up_lt = e["p_up_st"], e["p_flat_st"], e["p_up_lt"]
        fwd_st, fwd_lt = e.get("fwd_st_avg_pct"), e.get("fwd_lt_avg_pct")
    else:
        pl = ((state.get("meta") or {}).get("pooled") or {}).get(b)
        if not pl:
            return {}
        basis, n = "pooled", 0
        p_up_st, p_flat_st, p_up_lt = pl["p_up_st"], pl["p_flat_st"], pl["p_up_lt"]
        fwd_st = fwd_lt = None
    conf = p_up_st if action == "BUY" else (100 - p_up_st if action == "SELL" else p_flat_st)
    return {"band": b, "conf_pct": int(conf), "conf_basis": basis, "conf_n": int(n),
            "conf_h": ST_H, "p_up_1m_pct": int(p_up_st), "p_up_1y_pct": int(p_up_lt),
            "band_fwd_1m_pct": fwd_st, "band_fwd_1y_pct": fwd_lt}


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
        print(f"[warn] signal_calibration state save failed: {e}", flush=True)


def ensure(daily, tickers):
    """Recompute once per trading day (10y fetch is slow); reuse cache otherwise."""
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
        print(f"[warn] signal_calibration compute failed: {e}", flush=True)
        return state
    new["meta"]["seeded_through"] = latest
    if new.get("tickers"):
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    demo = ["NVDA", "MU", "AAPL", "VOO", "SMH", "TSLA", "GLD", "STX", "SNDK", "WDC"]
    r = compute(demo)
    print("pooled band rates (21d up / flat, 1y up):")
    for b, v in r["meta"]["pooled"].items():
        print(f"  {b:12s} up1m {v['p_up_st']:3d}%  flat1m {v['p_flat_st']:3d}%  up1y {v['p_up_lt']:3d}%  n={v['n_st']:,}")
    print(f"\n{'tkr':6s}{'band':13s}{'n':>6s}{'up1m':>6s}{'up1y':>6s}{'fwd1m':>7s}{'fwd1y':>7s}  basis")
    for t in demo:
        tk = r["tickers"].get(t)
        if not tk:
            continue
        for b, e in tk["bands"].items():
            print(f"{t:6s}{b:13s}{e['n']:6d}{e['p_up_st']:5d}%{e['p_up_lt']:5d}%"
                  f"{(str(e['fwd_st_avg_pct'])+'%') if e['fwd_st_avg_pct'] is not None else '—':>7s}"
                  f"{(str(e['fwd_lt_avg_pct'])+'%') if e['fwd_lt_avg_pct'] is not None else '—':>7s}  {e['basis']}")

# --- end of signal_calibration.py ---
