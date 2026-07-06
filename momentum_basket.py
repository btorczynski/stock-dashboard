"""
Fourth simulator: my **Momentum Basket** — a simple "sector rotation" strategy, the
retail-scale nod to the "many small uncorrelated bets" idea (Renaissance in spirit,
not in machinery). It spreads across a handful of winners instead of betting on one.

UNIVERSE (11 liquid, long-history funds):
  9 S&P sectors  — XLK Tech, XLF Financials, XLV Health, XLE Energy, XLI Industrials,
                   XLY Cons-Disc, XLP Cons-Staples, XLU Utilities, XLB Materials
  + SMH Semiconductors, + GLD Gold   (the offense/diversifiers that let it beat the index)

RULES (check once a month, last trading day):
  1. Rank all 11 by trailing 12-month total return.
  2. Hold the TOP 3, equal weight (~33% each), for the next month.
  3. The filter: any of those 3 whose 12-month return is negative parks in Treasuries
     (IEF) instead — so in a broad downturn the basket drifts to bonds.
Rebalance monthly. Dividend-adjusted. NOT financial advice.

WHY: cross-sectional momentum (own this month's strongest groups) is a well-documented
edge, and spreading across 3 sectors plus a bond brake cuts the single-bet risk. Backtested
2007-2026 it beat the S&P's return with under half the drawdown — but, like any momentum
system, it trails in whipsaw years, so it's a full-cycle strategy, not a yearly guarantee.
"""

import json
import math
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "basket_state.json")
SECTORS = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"]
EXTRA = ["SMH", "GLD"]
UNIVERSE = SECTORS + EXTRA
DEFENSE = "IEF"
BENCH = "SPY"
TICKERS = UNIVERSE + [BENCH, DEFENSE]
NAMES = {"XLK": "Tech", "XLF": "Financials", "XLV": "Health Care", "XLE": "Energy",
         "XLI": "Industrials", "XLY": "Cons. Disc.", "XLP": "Cons. Staples", "XLU": "Utilities",
         "XLB": "Materials", "SMH": "Semiconductors", "GLD": "Gold", "IEF": "Treasuries", "SPY": "S&P 500"}
START = "2005-01-01"
BACKTEST_START_YEAR = 2007
LOOKBACK = 12
TOPN = 3
BASE = 10000.0
SCHEMA = 1


def _fetch():
    d = yf.download(TICKERS, start=START, auto_adjust=True, progress=False, threads=False)
    if d is None or d.empty:
        return None
    cl = d["Close"]
    if isinstance(cl, pd.Series):
        return None
    return cl


def _rank(m, i):
    mom = {}
    for a in UNIVERSE:
        v0, v1 = m[a].iloc[i - LOOKBACK], m[a].iloc[i]
        if pd.notna(v0) and pd.notna(v1) and v0 > 0:
            mom[a] = v1 / v0 - 1
    rank = sorted(mom, key=mom.get, reverse=True)[:TOPN]
    picks = [a if mom[a] > 0 else DEFENSE for a in rank]
    return rank, picks, mom


def backtest(cl):
    if cl is None or len(cl) < 300:
        return _empty("insufficient history")
    m = cl.resample("ME").last()
    rets = m.pct_change()
    idx = m.index
    last_i = len(idx) - 1

    i0 = LOOKBACK
    while i0 < last_i and (idx[i0].year < BACKTEST_START_YEAR or len(_rank(m, i0)[0]) < TOPN):
        i0 += 1

    eq = BASE
    bench = BASE
    dates = [str(idx[i0].date())]
    equity = [round(eq, 2)]
    bequity = [round(bench, 2)]
    trades = [{"date": str(idx[i0].date()), "entered": [], "exited": [], "hold": []}]
    prev = None
    rebalances = 0
    cash_slots = 0
    slot_total = 0

    for i in range(i0, last_i):
        rank, picks, mom = _rank(m, i)
        if len(picks) < TOPN:
            continue
        r = sum(float(rets[p].iloc[i + 1]) for p in picks) / len(picks)
        br = rets[BENCH].iloc[i + 1]
        if pd.isna(r) or pd.isna(br):
            continue
        eq *= (1 + r)
        bench *= (1 + float(br))
        d = str(idx[i + 1].date())
        cur = set(picks)
        entered = sorted(cur - prev) if prev is not None else []
        exited = sorted(prev - cur) if prev is not None else []
        changed = (prev is not None and cur != prev)
        dates.append(d)
        equity.append(round(eq, 2))
        bequity.append(round(bench, 2))
        trades.append({"date": d, "entered": [NAMES.get(x, x) for x in entered],
                       "exited": [NAMES.get(x, x) for x in exited],
                       "hold": [NAMES.get(x, x) for x in picks]})
        if changed:
            rebalances += 1
        cash_slots += picks.count(DEFENSE)
        slot_total += len(picks)
        prev = cur

    stats = _stats(equity, bequity, dates, rebalances, cash_slots, slot_total)
    rec, holds = _reco(m)
    return {
        "meta": {"strategy": ("Each month, rank 9 S&P sectors + Semis + Gold by 12-month return, hold the top 3 "
                              "equal-weight; any pick with negative 12-month momentum parks in Treasuries (IEF)."),
                 "lookback": LOOKBACK, "topn": TOPN, "benchmark": BENCH, "base": BASE, "schema": SCHEMA,
                 "universe": [NAMES[a] for a in UNIVERSE], "since": dates[0] if dates else None,
                 "seeded_through": str(cl.index[-1].date()), "current_holds": holds,
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates, "equity": equity, "benchmark_equity": bequity, "trades": trades,
        "stats": stats, "recommendation": rec,
    }


def _stats(eq, bm, dates, rebalances, cash_slots, slot_total):
    n = len(eq)
    yrs = max(1e-6, (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25)

    def cagr(a):
        return (a[-1] / a[0]) ** (1 / yrs) - 1

    def mdd(a):
        pk, d = a[0], 0.0
        for v in a:
            pk = max(pk, v); d = min(d, v / pk - 1)
        return d

    sret = pd.Series(eq).pct_change().dropna()
    bret = pd.Series(bm).pct_change().dropna()

    def sharpe(r):
        return (r.mean() / r.std() * math.sqrt(12)) if r.std() > 0 else 0.0

    si = pd.Series(eq, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    bi = pd.Series(bm, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    wins = int((si > bi).sum())
    tot = int(len(si))
    return {"months": n, "years": round(yrs, 1), "value": round(eq[-1], 2), "benchmark_value": round(bm[-1], 2),
            "total_return_pct": round((eq[-1] / eq[0] - 1) * 100, 1),
            "benchmark_total_pct": round((bm[-1] / bm[0] - 1) * 100, 1),
            "cagr_pct": round(cagr(eq) * 100, 1), "benchmark_cagr_pct": round(cagr(bm) * 100, 1),
            "max_drawdown_pct": round(mdd(eq) * 100, 1), "benchmark_dd_pct": round(mdd(bm) * 100, 1),
            "sharpe": round(sharpe(sret), 2), "benchmark_sharpe": round(sharpe(bret), 2),
            "rebalances_per_yr": round(rebalances / yrs, 1),
            "pct_in_cash": round(cash_slots / max(1, slot_total) * 100),
            "years_beat": wins, "years_total": tot}


def _reco(m):
    i = len(m.index) - 1
    rank, picks, mom = _rank(m, i)
    holds = []
    for a in rank:
        in_cash = mom[a] <= 0
        holds.append({"ticker": DEFENSE if in_cash else a,
                      "name": NAMES["IEF"] if in_cash else NAMES.get(a, a),
                      "lead": NAMES.get(a, a), "mom_pct": round(float(mom[a]) * 100, 1), "cash": bool(in_cash)})
    names = ", ".join(h["name"] for h in holds) or "—"
    top = {"horizon": "Hold this month", "action": names,
           "note": "Equal weight across the top 3 by 12-month momentum, rebalanced monthly."}
    filt = {"horizon": "The filter", "action": "→ IEF",
            "note": "Any of the 3 whose trailing 12-month return is negative parks in Treasuries instead."}
    nxt = {"horizon": "Next check", "action": "Month-end",
           "note": "Re-rank on the last trading day of each month and rotate into the new top 3."}
    return [top, filt, nxt], holds


def _empty(reason):
    return {"meta": {"strategy": "", "benchmark": BENCH, "schema": SCHEMA, "seeded_through": None,
                     "note": reason, "current_holds": [],
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
        print(f"[warn] basket state save failed: {e}", flush=True)


def ensure(daily):
    latest = None
    for probe in ("SPY", "XLK", "AAPL", "MSFT"):
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
    new = backtest(_fetch())
    if new.get("dates"):
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    r = backtest(_fetch())
    s = r["stats"]
    for k in ("years", "cagr_pct", "benchmark_cagr_pct", "total_return_pct", "benchmark_total_pct",
              "max_drawdown_pct", "benchmark_dd_pct", "sharpe", "benchmark_sharpe",
              "rebalances_per_yr", "pct_in_cash", "years_beat", "years_total"):
        print(f"{k:22s}: {s[k]}")
    print("current holds:", [(h["name"], h["mom_pct"]) for h in r["meta"]["current_holds"]])
    print("points:", len(r["dates"]), r["dates"][0], "->", r["dates"][-1])

# --- end of momentum_basket.py ---
