"""
"VOO <-> best-indicator mega-cap, on dips" strategy (rotating, low-turnover).

Hold VOO. On each time VOO closes 5% below its recent peak, sell it and go all-in on the
mega-cap (AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA) with the best technical-indicator
score. Return to VOO when VOO recovers to a new high. Repeat -- but at most 5 trades
(switches) per calendar year, so turnover/slippage/taxes stay low.

Indicator score blends: price vs 50-day average, 20/50-day cross, 1-month momentum,
12-month momentum, and RSI(14). Highest score wins.

HONEST WARNING (also on the panel): when it's in a single stock it is fully concentrated,
so it can ride one name down hard (e.g. it held TSLA through 2022). It only modestly beats
VOO in backtest while taking much bigger drawdowns. Not a free lunch. NOT financial advice.
"""

import json
import math
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dip_state.json")
CANDS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
BENCH = "VOO"
BASE = 10000.0
DD = -0.05
MAX_TRADES_YR = 5
MAXP = 1100
SCHEMA = 7   # bumped: hindsight-universe warning surfaced in meta/UI


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _fetch():
    d = yf.download([BENCH] + CANDS, period="10y", auto_adjust=True, progress=False,
                    threads=False, group_by="ticker")
    if d is None or d.empty:
        return None, None
    try:
        voo = d[BENCH]["Close"].dropna()
    except Exception:
        return None, None
    if len(voo) < 300:
        return None, None
    cc = {}
    for t in CANDS:
        try:
            cc[t] = d[t]["Close"].reindex(voo.index).ffill()
        except Exception:
            pass
    return voo, cc


def _indicators(cc):
    ind = {}
    for t, c in cc.items():
        d = c.diff()
        up = d.clip(lower=0).rolling(14).mean()
        dn = (-d.clip(upper=0)).rolling(14).mean()
        ind[t] = {"sma20": c.rolling(20).mean(), "sma50": c.rolling(50).mean(),
                  "mom1": c / c.shift(21) - 1, "mom12": c / c.shift(252) - 1,
                  "rsi": 100 - 100 / (1 + up / dn.replace(0, 1e-9))}
    return ind


def _score(t, i, cc, ind):
    c = cc[t]
    p = c.iloc[i]
    a = ind[t]
    vals = [p, a["sma20"].iloc[i], a["sma50"].iloc[i], a["mom1"].iloc[i], a["mom12"].iloc[i], a["rsi"].iloc[i]]
    if any(pd.isna(v) for v in vals) or p <= 0:
        return None
    s = (25 if p > a["sma50"].iloc[i] else -25) + (15 if a["sma20"].iloc[i] > a["sma50"].iloc[i] else -15)
    s += _clamp(float(a["mom1"].iloc[i]) * 200, -20, 20) + _clamp(float(a["mom12"].iloc[i]) * 50, -25, 25)
    r = float(a["rsi"].iloc[i])
    s += 10 if 45 <= r <= 70 else (-10 if (r > 78 or r < 30) else 0)
    return s


def backtest(voo, cc):
    if voo is None or cc is None or len(voo) < 300:
        return _empty("insufficient history")
    idx = voo.index
    ind = _indicators(cc)
    sh_voo = BASE / float(voo.iloc[0])
    sh_bh = sh_voo
    state = "VOO"
    held = None
    sh_st = 0.0
    peak = float(voo.iloc[0])
    dip_peak = None
    tby = {}
    eq, bench, hold_series = [], [], []
    events = {}
    last_pick, last_pick_date = None, None
    for i in range(len(idx)):
        px = float(voo.iloc[i])
        yr = idx[i].year
        tby.setdefault(yr, 0)
        if state == "VOO":
            peak = max(peak, px)
            if i > 0 and px <= peak * (1 + DD) and tby[yr] < MAX_TRADES_YR:
                scored = {t: _score(t, i, cc, ind) for t in cc}
                scored = {t: v for t, v in scored.items() if v is not None}
                if scored:
                    held = max(scored, key=scored.get)
                    sh_st = (sh_voo * px) / float(cc[held].iloc[i])
                    events[i] = {"entered": [held], "exited": ["VOO"]}
                    state = "STOCK"; dip_peak = peak; tby[yr] += 1
                    last_pick, last_pick_date = held, str(idx[i].date())
            eq.append(sh_voo * px)
        else:
            if px >= dip_peak and tby[yr] < MAX_TRADES_YR:
                sh_voo = (sh_st * float(cc[held].iloc[i])) / px
                events[i] = {"entered": ["VOO"], "exited": [held]}
                state = "VOO"; peak = px; tby[yr] += 1; held = None
                eq.append(sh_voo * px)
            else:
                eq.append(sh_st * float(cc[held].iloc[i]))
        bench.append(sh_bh * px)
        hold_series.append("VOO" if state == "VOO" else held)

    dates_full = [str(d.date()) for d in idx]
    stats = _stats(eq, bench, dates_full)
    stats["trades"] = int(sum(tby.values()))
    stats["max_trades_yr"] = int(max(tby.values())) if tby else 0
    stats["picked"] = last_pick if state == "STOCK" else None
    stats["pick_date"] = last_pick_date if state == "STOCK" else None

    n = len(idx)
    stride = max(1, math.ceil(n / MAXP))
    sel = list(range(0, n, stride))
    if sel and sel[-1] != n - 1:
        sel.append(n - 1)
    dts, e2, b2, trades = [], [], [], []
    last = 0
    for j in sel:
        ent, exi = [], []
        for k in range(last, j + 1):
            if k in events:
                ent += events[k]["entered"]; exi += events[k]["exited"]
        last = j + 1
        dts.append(str(idx[j].date())); e2.append(round(eq[j], 2)); b2.append(round(bench[j], 2))
        trades.append({"date": str(idx[j].date()), "entered": ent, "exited": exi, "hold": hold_series[j]})

    return {
        "meta": {"strategy": (f"Hold VOO; on each 5%-from-peak dip rotate into the best-indicator mega-cap, "
                              f"return to VOO when it recovers to a new high — capped at {MAX_TRADES_YR} trades/year."),
                 "benchmark": BENCH, "base": BASE, "schema": SCHEMA, "candidates": CANDS,
                 "max_trades_yr": MAX_TRADES_YR, "current_pick": stats["picked"], "pick_date": stats["pick_date"],
                 "hindsight_note": ("The candidate list is TODAY'S 'Magnificent 7' — names everyone now "
                                    "knows dominated the past decade — backtested over that same decade. "
                                    "A list drawn up 10 years ago would have included losers too, and the "
                                    "results would be far more muted."),
                 "state": state, "since": dts[0] if dts else None, "seeded_through": str(idx[-1].date()),
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dts, "equity": e2, "benchmark_equity": b2, "trades": trades,
        "stats": stats, "recommendation": _reco(state, stats["picked"], stats["pick_date"]),
    }


def _stats(eq, bm, dates):
    yrs = max(1e-6, (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25)

    def cagr(a):
        return (a[-1] / a[0]) ** (1 / yrs) - 1

    def mdd(a):
        pk, d = a[0], 0.0
        for v in a:
            pk = max(pk, v); d = min(d, v / pk - 1)
        return d

    si = pd.Series(eq, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    bi = pd.Series(bm, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    k = min(len(si), len(bi))
    return {"value": round(eq[-1], 2), "benchmark_value": round(bm[-1], 2),
            "total_return_pct": round((eq[-1] / eq[0] - 1) * 100, 1),
            "benchmark_total_pct": round((bm[-1] / bm[0] - 1) * 100, 1),
            "cagr_pct": round(cagr(eq) * 100, 1), "benchmark_cagr_pct": round(cagr(bm) * 100, 1),
            "max_drawdown_pct": round(mdd(eq) * 100, 1), "benchmark_dd_pct": round(mdd(bm) * 100, 1),
            "years": round(yrs, 1),
            "years_beat": int((si.values[:k] > bi.values[:k]).sum()), "years_total": int(k)}


def _reco(state, picked, pdate):
    if state == "STOCK":
        now = {"horizon": "Right now", "action": f"HOLD {picked}",
               "note": f"Rotated in on the {pdate} dip; returns to VOO on a new high (or when the year's trade cap is hit)."}
    else:
        now = {"horizon": "Right now", "action": "HOLD VOO",
               "note": "In VOO — waiting for the next 5%-from-peak dip to rotate into the best-indicator mega-cap."}
    rule = {"horizon": "The pick", "action": "Best indicators",
            "note": "Trend (vs 50d), 20/50 cross, 1-mo & 12-mo momentum, and RSI score each mega-cap; highest wins."}
    cap = {"horizon": "Turnover", "action": f"Max {MAX_TRADES_YR} trades/yr",
           "note": f"At most {MAX_TRADES_YR} switches per calendar year keeps slippage and taxes low; rides the rest out."}
    return [now, rule, cap]


def _empty(reason):
    return {"meta": {"strategy": "", "benchmark": BENCH, "schema": SCHEMA, "seeded_through": None,
                     "note": reason, "current_pick": None, "pick_date": None,
                     "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "dates": [], "equity": [], "benchmark_equity": [], "trades": [], "stats": {}, "recommendation": []}


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
        print(f"[warn] dip state save failed: {e}", flush=True)


def ensure(daily):
    latest = None
    for probe in ("SPY", "VOO", "AAPL", "MSFT"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    if state and state.get("dates") and latest and state["meta"].get("seeded_through") == latest \
            and state["meta"].get("schema") == SCHEMA:
        return state
    voo, cc = _fetch()
    new = backtest(voo, cc)
    if new.get("dates"):
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    voo, cc = _fetch()
    r = backtest(voo, cc)
    s = r["stats"]
    print("now holding", s.get("picked") or "VOO", "| trades", s.get("trades"), "max/yr", s.get("max_trades_yr"))
    for k in ("value", "benchmark_value", "cagr_pct", "benchmark_cagr_pct", "max_drawdown_pct", "years_beat", "years_total"):
        print(f"  {k}: {s[k]}")

# --- end of dip_rotate.py ---
