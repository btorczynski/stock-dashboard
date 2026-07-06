"""
Second simulator: a **buy-the-dip** strategy on the S&P 500 (VOO).

RULE: buy 1 share of VOO on day one, then buy 1 MORE share every day VOO closes
down by the DIP threshold or more (currently -2%). Capital is contributed on each
purchase (it's not a fixed pot), so the total invested grows over time.

FAIR BENCHMARK ("same money, no dip-timing"): each calendar year, take the dollars
the dip strategy spent that year and invest that whole amount as a LUMP SUM on the
first trading day of that year, then hold. Both lines therefore deploy the exact
same dollars each year — the only difference is WHEN: dribbled onto big down-days vs
invested up front. This isolates whether "waiting for dips" actually pays.

Daily recommendation: whether to buy a share today, the price that triggers a buy
tomorrow, and the typical monthly dip cadence.

Prices are dividend-adjusted. NOT financial advice.
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

VOO_STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voo_state.json")
TICKER = "VOO"
START_DATE = "2010-09-01"
DIP = -0.02                 # buy 1 share whenever the daily change is <= this (e.g. -0.02 = a 2% drop)
PCT = int(round(abs(DIP) * 100))
MAX_POINTS = 1200


def _fetch():
    d = yf.download(TICKER, start=START_DATE, interval="1d", auto_adjust=True, progress=False, threads=False)
    if d is None or d.empty:
        return None
    cl = d["Close"]
    if isinstance(cl, pd.DataFrame):
        cl = cl.iloc[:, 0]
    return cl.dropna()


def backtest(c):
    if c is None or len(c) < 30:
        return _empty("insufficient VOO history")
    ret = c.pct_change()
    buy = (ret <= DIP).fillna(False).astype(bool)
    buy.iloc[0] = True   # initial investment: 1 share on day one

    shares = 0.0
    invested = 0.0
    value, inv_series, buy_flags, shares_series = [], [], [], []
    year_contrib = defaultdict(float)
    for i in range(len(c)):
        p = float(c.iloc[i])
        is_buy = bool(buy.iloc[i])
        if is_buy:
            shares += 1
            invested += p
            year_contrib[c.index[i].year] += p
        value.append(shares * p)
        inv_series.append(invested)
        buy_flags.append(is_buy)
        shares_series.append(shares)
    n_buys = int(buy.sum())

    first_of_year = {}
    for ts in c.index:
        first_of_year.setdefault(ts.year, ts)
    add_on = {first_of_year[y]: amt for y, amt in year_contrib.items()}
    bsh = 0.0
    bench = []
    for i in range(len(c)):
        ts, p = c.index[i], float(c.iloc[i])
        if ts in add_on and p > 0:
            bsh += add_on[ts] / p
        bench.append(bsh * p)

    stats = _stats(value, bench, inv_series, c, n_buys)
    rec, levels = _recommendation(c, ret, shares, invested, n_buys)

    n = len(c)
    stride = max(1, math.ceil(n / MAX_POINTS))
    sel = list(range(0, n, stride))
    if sel and sel[-1] != n - 1:
        sel.append(n - 1)
    dates_s, eq_s, bm_s, trades = [], [], [], []
    price_s, shares_s, inv_s2 = [], [], []
    last = 0
    for j in sel:
        bought = any(buy_flags[k] for k in range(last, j + 1))
        last = j + 1
        dates_s.append(str(c.index[j].date())); eq_s.append(round(value[j], 2)); bm_s.append(round(bench[j], 2))
        price_s.append(round(float(c.iloc[j]), 2)); shares_s.append(int(shares_series[j])); inv_s2.append(round(inv_series[j], 2))
        trades.append({"date": str(c.index[j].date()), "entered": ["VOO"] if bought else [], "exited": [],
                       "invested": round(inv_series[j], 2), "n": 1 if bought else 0,
                       "equity": round(value[j], 2)})

    return {
        "meta": {"benchmark": TICKER, "since": str(c.index[0].date()), "levels": levels,
                 "start_capital": round(invested, 0), "dip_pct": PCT, "schema": 2,
                 "strategy": (f"Buy 1 VOO share on day one + 1 more every day it drops >={PCT}%. Benchmark = the same "
                              "yearly dollars invested lump-sum at each year's start (no dip-timing)."),
                 "seeded_through": str(c.index[-1].date()),
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates_s, "equity": eq_s, "benchmark_equity": bm_s, "trades": trades,
        "price": price_s, "shares": shares_s, "invested": inv_s2,
        "stats": stats, "recommendation": rec,
    }


def _stats(value, bench, inv_series, c, n_buys):
    invested = inv_series[-1]
    val = value[-1]
    bval = bench[-1]
    profit = val - invested
    bprofit = bval - invested
    roi = (profit / invested * 100) if invested else 0.0
    broi = (bprofit / invested * 100) if invested else 0.0
    peak, dd = float(c.iloc[0]), 0.0
    for p in c:
        peak = max(peak, float(p)); dd = min(dd, float(p) / peak - 1.0)
    yrs = len(c) / 252.0
    dips = n_buys - 1
    return {"days": len(c), "years": round(yrs, 1), "shares": int(round(value[-1] / float(c.iloc[-1]))) if c.iloc[-1] else 0,
            "n_buys": n_buys, "dip_buys": dips, "avg_dips_per_month": round(dips / max(1, len(c) / 21.0), 1),
            "invested": round(invested, 2), "value": round(val, 2), "current_equity": round(val, 2),
            "profit": round(profit, 2), "roi_pct": round(roi, 1),
            "benchmark_equity": round(bval, 2), "benchmark_profit": round(bprofit, 2), "benchmark_roi_pct": round(broi, 1),
            "voo_drawdown_pct": round(dd * 100, 1)}


def _recommendation(c, ret, shares, invested, n_buys):
    price = float(c.iloc[-1])
    today_chg = float(ret.iloc[-1]) * 100 if len(c) >= 2 else 0.0
    trig = price * (1 + DIP)
    dips = n_buys - 1
    cadence = round(dips / max(1, len(c) / 21.0), 1)
    if today_chg <= DIP * 100:
        today = {"horizon": "Today", "action": "BUY 1 SHARE", "price": round(price, 2),
                 "note": f"VOO is down {today_chg:.1f}% today — that's a {PCT}%+ dip, buy 1 share (~${price:,.0f})."}
    else:
        today = {"horizon": "Today", "action": "WAIT", "price": round(price, 2),
                 "note": f"VOO is {today_chg:+.1f}% today — no {PCT}% dip, so no buy."}
    nextday = {"horizon": "Tomorrow", "action": "BUY ON DIP", "price": round(trig, 2),
               "note": f"Buy 1 share only if VOO closes below ~${trig:,.0f} (a {PCT}% drop from today)."}
    nextmonth = {"horizon": "Next month", "action": "ACCUMULATE", "price": round(price, 2),
                 "note": f"Historically ~{cadence} down-≥{PCT}% days per month — keep adding 1 share on each."}
    return [today, nextday, nextmonth], {"price": round(price, 2), "dip_trigger": round(trig, 2),
                                         "shares": int(shares), "invested": round(invested, 2)}


def _empty(reason):
    return {"meta": {"benchmark": TICKER, "strategy": "", "seeded_through": None, "note": reason, "levels": {},
                     "start_capital": 0, "dip_pct": PCT, "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "dates": [], "equity": [], "benchmark_equity": [], "trades": [], "stats": {}, "recommendation": []}


def load_state():
    try:
        with open(VOO_STATE) as f:
            return json.load(f)
    except Exception:
        return None


def save_state(s):
    try:
        with open(VOO_STATE, "w") as f:
            json.dump(s, f)
    except Exception as e:
        print(f"[warn] voo state save failed: {e}", flush=True)


def ensure(daily):
    latest = None
    for probe in ("VOO", "AAPL", "MSFT", "SPY"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    if state and state.get("dates") and latest and state["meta"].get("seeded_through") == latest \
            and state["meta"].get("dip_pct") == PCT and state["meta"].get("schema") == 2:
        return state
    new = backtest(_fetch())
    if new.get("dates"):
        save_state(new)
        return new
    return state or new


# --- end of voo_sim.py ---
