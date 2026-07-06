"""
Low-priced momentum "hold, don't churn" sleeve — the ONLY penny approach that survived
honest testing. Active all-in/all-out trading of these names died after 2.5% slippage
(turnover ~5%/round-trip eats everything). This minimizes turnover instead.

RULES (checked monthly, rebalanced QUARTERLY):
  1. Rank a basket of low-priced LISTED (Robinhood-tradable) names by 12-month return.
  2. Hold the top 3 with POSITIVE 12-month momentum, equal weight.
  3. Any slot without a positive-momentum name sits in CASH (so in a broad penny
     downturn the sleeve de-risks itself).
  4. Rebalance only once a quarter -> few trades -> slippage stays small (2.5% modeled).

$500 starting stake. Prices dividend-adjusted. NOT financial advice.

HONEST CAVEATS (also shown in the UI):
  * The backtest return is inflated by HINDSIGHT universe selection (these names were
    chosen knowing some had huge runs). Real forward results will very likely be far lower.
  * Drawdowns are brutal (~-80%). This is a small, high-risk speculative sleeve, period.
  * Edit UNIVERSE to your own low-priced listed names.
"""

import json
import math
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "penny_state.json")
UNIVERSE = ["PLUG", "FCEL", "SIRI", "NOK", "RIG", "NIO", "MARA", "RIOT", "CLSK", "AMC",
            "SOFI", "CHPT", "LCID", "SOUN", "BBAI", "GRAB", "KGC", "BTG", "VTRS"]
BENCH = "SPY"
START = "2016-06-01"
LOOKBACK = 12          # months
TOPN = 3
REBAL_EVERY = 3        # months (quarterly)
BASE = 500.0
SLIP = 0.025           # 2.5% each way on traded $
SCHEMA = 2


def _fetch():
    d = yf.download(UNIVERSE + [BENCH], start=START, auto_adjust=True, progress=False,
                    threads=False, group_by="ticker")
    if d is None or d.empty:
        return None
    cols = {}
    for t in UNIVERSE + [BENCH]:
        try:
            s = d[t]["Close"].dropna()
            if len(s) > 200:
                cols[t] = s
        except Exception:
            pass
    if BENCH not in cols or len(cols) < 4:
        return None
    return pd.DataFrame(cols)


def backtest(close):
    if close is None or close.empty:
        return _empty("insufficient history")
    m = close.resample("ME").last()
    univ = [t for t in UNIVERSE if t in m.columns]
    mom = m[univ].pct_change(LOOKBACK)
    spy_ret = m[BENCH].pct_change()
    idx = m.index
    i0 = LOOKBACK
    while i0 < len(idx) and mom.iloc[i0].notna().sum() < TOPN:
        i0 += 1

    cash = BASE
    sh = {}
    bench = BASE
    dates, equity, bequity, trades = [], [], [], []
    holds = []
    n_trades = 0
    prev = set()
    for i in range(i0, len(idx)):
        dt = idx[i]
        px = m.loc[dt]
        if i > i0 and pd.notna(spy_ret.iloc[i]):
            bench *= (1 + float(spy_ret.iloc[i]))
        val = cash + sum(sh[t] * px[t] for t in sh if pd.notna(px.get(t)))
        entered, exited = [], []
        if (i - i0) % REBAL_EVERY == 0:
            mo = mom.loc[dt].dropna()
            mo = mo[mo > 0]
            picks = list(mo.sort_values(ascending=False).head(TOPN).index)
            tgt = (val / len(picks)) if picks else 0.0
            newsh = {t: tgt / px[t] for t in picks if pd.notna(px.get(t)) and px[t] > 0}
            tc = 0.0
            for t in set(list(sh) + list(newsh)):
                tc += abs(newsh.get(t, 0) * px.get(t, 0) - sh.get(t, 0) * px.get(t, 0)) * SLIP
            cur = set(newsh)
            entered = sorted(cur - prev)
            exited = sorted(prev - cur)
            if entered or exited:
                n_trades += len(entered) + len(exited)
            cash = val - sum(newsh[t] * px[t] for t in newsh) - tc
            sh = newsh
            prev = cur
            holds = picks
        eqv = cash + sum(sh[t] * px[t] for t in sh if pd.notna(px.get(t)))
        dates.append(str(dt.date()))
        equity.append(round(eqv, 2))
        bequity.append(round(bench, 2))
        trades.append({"date": str(dt.date()), "entered": entered, "exited": exited,
                       "hold": list(sh.keys())})

    stats = _stats(equity, bequity, dates, n_trades)
    stats.update(_ex_boom(equity, bequity, dates))
    rec, cur_holds = _reco(m, mom, sh)
    return {
        "meta": {"strategy": ("Hold the top 3 low-priced names by 12-month momentum (positive only; "
                              "cash otherwise), rebalanced quarterly. Low turnover by design."),
                 "lookback": LOOKBACK, "topn": TOPN, "benchmark": BENCH, "base": BASE, "schema": SCHEMA,
                 "universe": univ, "since": dates[0] if dates else None,
                 "seeded_through": str(close.index[-1].date()), "current_holds": cur_holds,
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates, "equity": equity, "benchmark_equity": bequity, "trades": trades,
        "stats": stats, "recommendation": rec,
    }


def _ex_boom(equity, bequity, dates, excl=(2019, 2020, 2021)):
    """Performance with the 2019-2021 COVID/meme window spliced out (returns chained)."""
    e = pd.Series(equity, index=pd.to_datetime(dates)).pct_change().dropna()
    b = pd.Series(bequity, index=pd.to_datetime(dates)).pct_change().dropna()
    e = e[~e.index.year.isin(excl)]
    b = b[~b.index.year.isin(excl)]
    if len(e) < 6:
        return {}
    sc = float((1 + e).prod()); bc = float((1 + b).prod()); yrs = len(e) / 12.0
    return {"ex_value": round(BASE * sc), "ex_total_pct": round((sc - 1) * 100, 1),
            "ex_cagr_pct": round((sc ** (1 / yrs) - 1) * 100, 1),
            "ex_spy_total_pct": round((bc - 1) * 100, 1), "ex_years": round(yrs, 1)}


def _stats(eq, bm, dates, n_trades):
    n = len(eq)
    yrs = max(1e-6, (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25)

    def cagr(a):
        return (a[-1] / a[0]) ** (1 / yrs) - 1 if a[0] > 0 else 0.0

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
    return {"months": n, "years": round(yrs, 1), "value": round(eq[-1], 2), "benchmark_value": round(bm[-1], 2),
            "total_return_pct": round((eq[-1] / eq[0] - 1) * 100, 1),
            "benchmark_total_pct": round((bm[-1] / bm[0] - 1) * 100, 1),
            "cagr_pct": round(cagr(eq) * 100, 1), "benchmark_cagr_pct": round(cagr(bm) * 100, 1),
            "max_drawdown_pct": round(mdd(eq) * 100, 1), "benchmark_dd_pct": round(mdd(bm) * 100, 1),
            "sharpe": round(sharpe(sret), 2), "benchmark_sharpe": round(sharpe(bret), 2),
            "trades": int(n_trades), "trades_per_yr": round(n_trades / yrs, 1),
            "years_beat": int((si > bi).sum()), "years_total": int(len(si))}


def _reco(m, mom, sh):
    i = len(m.index) - 1
    mo = mom.iloc[i].dropna()
    mo = mo[mo > 0].sort_values(ascending=False)
    holds = []
    for t in list(mo.head(TOPN).index):
        holds.append({"ticker": t, "mom_pct": round(float(mo[t]) * 100, 1),
                      "price": round(float(m[t].iloc[i]), 2)})
    names = ", ".join(h["ticker"] for h in holds) or "ALL CASH"
    cashslots = TOPN - len(holds)
    top = {"horizon": "Hold this quarter", "action": names,
           "note": f"Top {TOPN} by 12-mo momentum, equal weight." + (f" {cashslots} slot(s) in cash (too few uptrends)." if cashslots else "")}
    rb = {"horizon": "Rebalance", "action": "Quarterly only",
          "note": "Re-rank once a quarter; keep turnover low so slippage stays small."}
    risk = {"horizon": "Risk", "action": "HIGH",
            "note": "Backtest drawdown ~-80%; only money you can lose. Backtest is hindsight-biased."}
    return [top, rb, risk], holds


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
        print(f"[warn] penny state save failed: {e}", flush=True)


def ensure(daily):
    latest = None
    for probe in ("SPY", "SOFI", "AAPL", "MSFT"):
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
    for k in ("years", "value", "total_return_pct", "benchmark_total_pct", "cagr_pct",
              "benchmark_cagr_pct", "max_drawdown_pct", "trades", "trades_per_yr", "years_beat", "years_total"):
        print(f"{k:20s}: {s[k]}")
    print("holds now:", [(h["ticker"], h["mom_pct"]) for h in r["meta"]["current_holds"]])
    print("points:", len(r["dates"]), r["dates"][0], "->", r["dates"][-1])

# --- end of penny_hold.py ---
