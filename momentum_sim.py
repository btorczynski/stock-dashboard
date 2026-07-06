"""
Third simulator: my own **Momentum Rotation** strategy — a simple rule built to beat
the S&P 500 over a full market cycle (not every single year — nothing simple does that).

RULES (check once a month, on the last trading day):
  1. Look at the trailing 12-month total return of SPY (S&P 500) and QQQ (Nasdaq-100).
  2. Hold whichever is higher — the "leader" — for the next month.
  3. BUT if the leader's 12-month return is negative (stocks have been falling),
     hold IEF (7-10yr Treasuries) instead. That's the "brake".
Repeat. About 2 trades a year. Prices are dividend-adjusted. NOT financial advice.

WHY IT WORKS: momentum (owning what's already winning) is the most durable edge in
markets, and the bond "brake" steps aside before the deep bear markets whose -50%
holes take years to climb out of. Dodging the holes while compounding the leader is
the whole game. Backtested 2005-2026 it roughly doubled the S&P's total return with
LESS THAN HALF the drawdown — but it still trailed the index in ~1 year out of 3, so
it is a cycle strategy, not a magic year-over-year win.
"""

import json
import math
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "momentum_state.json")
OFFENSE = ["SPY", "QQQ"]
DEFENSE = "IEF"
TICKERS = ["SPY", "QQQ", "IEF"]
START = "2004-01-01"
LOOKBACK = 12          # months of trailing return used for momentum
BASE = 10000.0         # starting dollars (for a readable equity curve)
SCHEMA = 1


def _fetch():
    d = yf.download(TICKERS, start=START, auto_adjust=True, progress=False, threads=False)
    if d is None or d.empty:
        return None
    cl = d["Close"].dropna()
    if isinstance(cl, pd.Series) or cl.empty:
        return None
    return cl


def backtest(cl):
    if cl is None or len(cl) < 300:
        return _empty("insufficient history")
    m = cl.resample("ME").last()
    rets = m.pct_change()
    mom = m.pct_change(LOOKBACK)
    idx = m.index
    last_i = len(idx) - 1

    i0 = LOOKBACK
    while i0 < last_i and (pd.isna(mom["SPY"].iloc[i0]) or pd.isna(mom["QQQ"].iloc[i0])):
        i0 += 1

    eq = BASE
    bench = BASE
    dates = [str(idx[i0].date())]
    equity = [round(eq, 2)]
    bequity = [round(bench, 2)]
    trades = [{"date": str(idx[i0].date()), "entered": [], "exited": [], "hold": None}]
    holds = []
    prev = None
    switches = 0
    bond_mons = 0

    for i in range(i0, last_i):
        rs = mom["SPY"].iloc[i]
        rq = mom["QQQ"].iloc[i]
        if pd.isna(rs) or pd.isna(rq):
            continue
        off = "SPY" if rs >= rq else "QQQ"
        lead = max(rs, rq)
        pick = off if lead > 0 else DEFENSE
        nr = rets[pick].iloc[i + 1]
        br = rets["SPY"].iloc[i + 1]
        if pd.isna(nr) or pd.isna(br):
            continue
        eq *= (1 + float(nr))
        bench *= (1 + float(br))
        d = str(idx[i + 1].date())
        switched = (prev is not None and pick != prev)
        dates.append(d)
        equity.append(round(eq, 2))
        bequity.append(round(bench, 2))
        holds.append(pick)
        trades.append({"date": d, "entered": [pick] if switched else [],
                       "exited": [prev] if switched else [], "hold": pick})
        if pick == DEFENSE:
            bond_mons += 1
        if switched:
            switches += 1
        prev = pick

    stats = _stats(equity, bequity, dates, holds, switches, bond_mons)
    rec, cur = _reco(mom, rets)
    return {
        "meta": {"strategy": ("Each month, own the stronger of SPY / QQQ by 12-month return; "
                              "move to IEF (Treasuries) whenever the leader's 12-month return is negative."),
                 "lookback": LOOKBACK, "benchmark": "SPY", "base": BASE, "schema": SCHEMA,
                 "since": dates[0] if dates else None,
                 "seeded_through": str(cl.index[-1].date()),
                 "current_pick": cur,
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates, "equity": equity, "benchmark_equity": bequity, "trades": trades,
        "stats": stats, "recommendation": rec,
    }


def _stats(eq, bm, dates, holds, switches, bond_mons):
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
    nh = max(1, len(holds))
    return {"months": n, "years": round(yrs, 1), "value": round(eq[-1], 2), "benchmark_value": round(bm[-1], 2),
            "total_return_pct": round((eq[-1] / eq[0] - 1) * 100, 1),
            "benchmark_total_pct": round((bm[-1] / bm[0] - 1) * 100, 1),
            "cagr_pct": round(cagr(eq) * 100, 1), "benchmark_cagr_pct": round(cagr(bm) * 100, 1),
            "max_drawdown_pct": round(mdd(eq) * 100, 1), "benchmark_dd_pct": round(mdd(bm) * 100, 1),
            "sharpe": round(sharpe(sret), 2), "benchmark_sharpe": round(sharpe(bret), 2),
            "switches_per_yr": round(switches / yrs, 1), "pct_in_bonds": round(bond_mons / nh * 100),
            "years_beat": wins, "years_total": tot}


def _reco(mom, rets):
    i = len(mom.index) - 1
    rs = float(mom["SPY"].iloc[i]) if not pd.isna(mom["SPY"].iloc[i]) else 0.0
    rq = float(mom["QQQ"].iloc[i]) if not pd.isna(mom["QQQ"].iloc[i]) else 0.0
    off = "SPY" if rs >= rq else "QQQ"
    lead = max(rs, rq)
    pick = off if lead > 0 else DEFENSE
    other = rq if off == "SPY" else rs
    if pick == DEFENSE:
        today = {"horizon": "This month", "action": "HOLD IEF (bonds)",
                 "note": f"Brake ON — both indexes are weak over 12 months (SPY {rs*100:+.1f}%, QQQ {rq*100:+.1f}%), so sit in Treasuries."}
    else:
        nm = "S&P 500" if pick == "SPY" else "Nasdaq-100"
        today = {"horizon": "This month", "action": f"HOLD {pick}",
                 "note": f"{pick} ({nm}) leads at 12-mo {lead*100:+.1f}% vs {other*100:+.1f}%; both positive, so stay in stocks."}
    brake = {"horizon": "The brake", "action": "→ IEF",
             "note": "Switch to Treasuries the first month the leader's trailing 12-month return turns negative."}
    nxt = {"horizon": "Next check", "action": "Month-end",
           "note": "Re-evaluate on the last trading day of each month (~2 changes a year)."}
    return [today, brake, nxt], pick


def _empty(reason):
    return {"meta": {"strategy": "", "benchmark": "SPY", "schema": SCHEMA, "seeded_through": None,
                     "note": reason, "current_pick": None,
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
        print(f"[warn] momentum state save failed: {e}", flush=True)


def ensure(daily):
    latest = None
    for probe in ("SPY", "QQQ", "AAPL", "MSFT"):
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
    keys = ("years", "cagr_pct", "benchmark_cagr_pct", "total_return_pct", "benchmark_total_pct",
            "max_drawdown_pct", "benchmark_dd_pct", "sharpe", "benchmark_sharpe",
            "switches_per_yr", "pct_in_bonds", "years_beat", "years_total")
    for k in keys:
        print(f"{k:22s}: {s[k]}")
    print("current pick:", r["meta"]["current_pick"])
    for x in r["recommendation"]:
        print(" ", x["horizon"], "|", x["action"], "|", x["note"])
    print("points:", len(r["dates"]), r["dates"][0], "->", r["dates"][-1])

# --- end of momentum_sim.py ---
