"""
Watchlist Confidence Backtest — "what we predicted" vs "what actually happened."

The watchlist on the dashboard shows a BUY / SELL / HOLD call for each name plus a
**confidence %** (the signal strength, 0-100, = |score|). This module turns those
calls into an honest, mechanical paper-trade so you can SEE whether acting on the
confidence-weighted signals would have beaten just buying the S&P 500.

HOW IT WORKS
  • Each trading day, for every watchlist ticker, we reconstruct the SAME technical
    signal score the live dashboard uses (compute_signal), from daily closes only:
        tech = 30·(price>50d) + 20·(20d>50d) + 25·clamp(1mo mom) + 15·clamp(RSI)
               + 10·clamp(today)            →  score = clamp(tech, -100..100)
    A name is a BUY when score ≥ +25; confidence = |score|.
    (The live signal also adds a macro/event overlay that isn't reconstructable from
     price history, so this backtest is the price-only core of that same signal.)
  • YOU ARE NOT A COMPUTER — 1-DAY EXECUTION LAG: a machine could act on the signal
    at the very close it fires. You can't. So every trade waits ONE trading day: the
    signal is read at a day's close, but the position isn't entered until the next
    day's close, missing the first-day pop. (A faint "perfect (instant)" line shows
    what a zero-lag computer would have made, so you can see the cost of being human.)
  • WALK-FORWARD CALIBRATION — the model gets better with time: raw confidence here is
    signal STRENGTH, not a probability. So we keep a live track record and, at each
    point in time, recalibrate each confidence band into the probability it ACTUALLY
    hit — using only outcomes that had already matured by that date (no look-ahead).
    Positions are then sized by the CALIBRATED EDGE (calibrated win-prob − 50%), so the
    model leans harder on the confidence levels that have earned it and fades the ones
    that haven't. Early on it knows little and bets evenly; as outcomes accumulate the
    mapping sharpens and the sizing improves. LONG ONLY; cash when no name has an edge.
  • The strategy equity (what the predictions earned, after the 1-day wait) is charted
    against $5,000 left in SPY (what the market actually did).

SEED + KEEP LOGGING: the curve is reconstructed from ~3 years of history on first run
and re-extended every new trading day, and each refresh appends that day's live
confidence calls to a forward log so the real-time track record accumulates too.

NOT financial advice. A backtest is not a promise; past results don't predict the future.
"""

import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist_sim_state.json")
BENCHMARK = "SPY"
BASE = 5000.0            # starting dollars, echoes the $5k strategy theme
PERIOD = "3y"            # history pulled; ~50d warms up the averages, rest is the curve
SIGNAL_BUY = 25         # score >= this is a BUY (matches stock_dashboard.SIGNAL_BUY)
CONF_HORIZON = 10       # trading days used to grade a call as right/wrong (calibration)
EXEC_LAG = 1            # trading days you wait before executing (you're not a computer)
CAL_K = 25.0           # shrinkage pseudocount: how much a band leans on the prior early
CAL_MIN = 60           # matured outcomes before the running base rate is trusted as prior
BASE_PRIOR = 0.55      # bull-market base hit rate used as the prior until data accrues
LOG_KEEP = 400          # cap on forward-log rows persisted
SCHEMA = 3             # bumped: yearly reset to the S&P baseline (fresh race each year)

# Confidence bands the calibration learns over. (lo, hi) on the 0-100 strength scale.
BANDS = [(25, 40), (40, 55), (55, 70), (70, 85), (85, 101)]


def _band_index(c):
    for k, (lo, hi) in enumerate(BANDS):
        if lo <= c < hi:
            return k
    return len(BANDS) - 1 if c >= BANDS[-1][0] else -1


def _band_label(k):
    lo, hi = BANDS[k]
    return f"{lo}-{min(hi, 100)}%"

# Fallback list (kept in sync with stock_dashboard.WATCHLIST); ensure() prefers the
# tickers passed in from the live dashboard so the two never drift apart.
_FALLBACK_TICKERS = [
    "XLK", "SMH", "URA", "UNG", "GLD", "SLV", "VOO", "CVX", "NVDA", "UNH", "IONQ",
    "RDW", "PL", "MDA.TO", "RKLB", "TSLA", "CSCO", "KLAC", "RGTI", "SOXX", "SNDK",
    "STX", "AAPL", "PLTR", "XOM", "SNOW", "AMZN", "BE", "KEYS", "PANW", "MU", "WDC",
    "NOK", "SPCX",
]


def _clamp_df(x, lo, hi):
    return x.clip(lo, hi)


def _rsi(closes, period=14):
    """Wilder RSI, vectorized over a Series or a whole DataFrame of closes.
    Identical formula to stock_dashboard._rsi so the backtest matches the live signal."""
    delta = closes.diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    ru = up.ewm(alpha=1 / period, adjust=False).mean()
    rd = down.ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd.replace(0, 1e-9))


def _scores(C):
    """Reconstruct the daily signal score (-100..100) for every column of closes C,
    using the price-only core of stock_dashboard.compute_signal. NaN where there is
    not yet enough history (needs the 50-day average + 1-month momentum)."""
    sma20 = C.rolling(20).mean()
    sma50 = C.rolling(50, min_periods=50).mean()
    rsi = _rsi(C)
    mom1m = (C / C.shift(21) - 1) * 100.0
    today = C.pct_change() * 100.0
    c_trend = (C > sma50).astype(float) * 2 - 1            # +1 above 50d, -1 below
    c_cross = (sma20 > sma50).astype(float) * 2 - 1        # +1 if 20d>50d
    c_mom = _clamp_df(mom1m / 10.0, -1, 1)
    c_rsi = _clamp_df((rsi - 50.0) / 20.0, -1, 1)
    c_today = _clamp_df(today / 3.0, -1, 1)
    tech = 30 * c_trend + 20 * c_cross + 25 * c_mom + 15 * c_rsi + 10 * c_today
    score = _clamp_df(tech, -100, 100)
    valid = sma50.notna() & C.notna() & mom1m.notna()
    return score.where(valid)


def _fetch(tickers):
    syms = sorted(set(t for t in tickers if t) | {BENCHMARK})
    d = yf.download(" ".join(syms), period=PERIOD, interval="1d", auto_adjust=True,
                    group_by="ticker", progress=False, threads=False)
    out = {}
    for s in syms:
        try:
            df = d[s].dropna(how="all")
            if not df.empty and "Close" in df:
                out[s] = df
        except Exception:
            pass
    return out


def _band_table(tally, ov):
    """Turn the final walk-forward tally into the display table: per confidence band,
    the probability it ACTUALLY hit and its average matured move."""
    rows = []
    for k in range(len(BANDS)):
        t = tally[k]
        if t["n"]:
            rows.append({"band": _band_label(k), "n": t["n"],
                         "hit_rate": round(t["h"] / t["n"] * 100),
                         "avg_fwd_pct": round(t["sf"] / t["n"] * 100, 2)})
        else:
            rows.append({"band": _band_label(k), "n": 0, "hit_rate": None, "avg_fwd_pct": None})
    overall = {"n": ov["n"], "hit_rate": (round(ov["h"] / ov["n"] * 100) if ov["n"] else None),
               "avg_fwd_pct": (round(ov["sf"] / ov["n"] * 100, 2) if ov["n"] else None),
               "horizon_days": CONF_HORIZON, "exec_lag": EXEC_LAG, "applied": "walk-forward"}
    return {"bands": rows, "overall": overall}


def _cal_prob(tally, ov, k):
    """Calibrated win-probability for band k, shrunk toward the running base rate so it
    is stable when the band has few matured samples. Pure function of PAST outcomes."""
    base = ov["h"] / ov["n"] if ov["n"] >= CAL_MIN else BASE_PRIOR
    t = tally[k]
    return (t["h"] + CAL_K * base) / (t["n"] + CAL_K)


def backtest(prices, tickers):
    if BENCHMARK not in prices or prices[BENCHMARK].empty:
        return _empty("benchmark (SPY) data unavailable")
    spy = prices[BENCHMARK]["Close"].dropna()
    if len(spy) < 80:
        return _empty("insufficient benchmark history")
    idx = spy.index

    closes = {}
    for s in tickers:
        df = prices.get(s)
        if df is None or df.empty or "Close" not in df:
            continue
        c = df["Close"].dropna()
        if len(c) >= 60:
            closes[s] = c
    if not closes:
        return _empty("no watchlist history")

    C = pd.DataFrame(closes).reindex(idx)
    Cv = C.values
    score = _scores(C)
    conf = score.where(score >= SIGNAL_BUY)        # raw confidence (strength) on BUY days
    rets = C.pct_change()
    spy_ret = spy.pct_change()

    cols = list(C.columns)
    conf_v = conf.values
    rets_v = rets.values
    spy_v = spy_ret.values
    score_valid = score.notna().any(axis=1).values
    T = len(idx)

    first_valid = next((i for i in range(T) if score_valid[i]), None)
    if first_valid is None:
        return _empty("signals never warmed up")
    start_i = max(first_valid + 1 + EXEC_LAG, 51)
    if start_i >= T:
        return _empty("not enough history after warmup")

    # Pre-compute, for each signal day, the matured outcome of every BUY: you execute
    # EXEC_LAG days later and the call is graded CONF_HORIZON days after THAT. The result
    # only becomes known (usable for calibration) at the outcome day's close.
    H = CONF_HORIZON
    events_by_outcome = {}
    for s in range(T):
        crow_s = conf_v[s]
        execi, outi = s + EXEC_LAG, s + EXEC_LAG + H
        if outi >= T:
            continue
        sb = np.where(~np.isnan(crow_s))[0]
        if not len(sb):
            continue
        bucket = events_by_outcome.setdefault(outi, [])
        for j in sb:
            p0, p1 = Cv[execi, j], Cv[outi, j]
            if np.isnan(p0) or np.isnan(p1) or p0 <= 0:
                continue
            k = _band_index(crow_s[j])
            if k >= 0:
                bucket.append((k, p1 / p0 - 1.0))

    tally = [{"n": 0, "h": 0.0, "sf": 0.0} for _ in BANDS]
    ov = {"n": 0, "h": 0.0, "sf": 0.0}
    flushed = -1

    def _flush(upto):
        nonlocal flushed
        for od in range(flushed + 1, upto + 1):
            for (k, fwd) in events_by_outcome.get(od, ()):  # only outcomes known by `upto`
                hit = 1.0 if fwd > 0 else 0.0
                tally[k]["n"] += 1; tally[k]["h"] += hit; tally[k]["sf"] += fwd
                ov["n"] += 1; ov["h"] += hit; ov["sf"] += fwd
        flushed = max(flushed, upto)

    real_eq = bench = perfect_eq = BASE
    dates, equity, bequity, perfect = [], [], [], []
    trades, daily_ret = [], []
    prev_buys = set()
    invested_days = name_count = entered_total = 0

    for i in range(start_i, T):
        _flush(i - 1)                       # calibration may use only outcomes known by yesterday
        # YEARLY RESET: each new calendar year the strategy (and its "perfect" twin)
        # restarts from the S&P baseline — capital = wherever $5k-in-SPY stands at the
        # year's open — so every year is a fresh, apples-to-apples race vs the index.
        reset = i > start_i and idx[i].year != idx[i - 1].year
        if reset:
            real_eq = bench
            perfect_eq = bench
        rrow = rets_v[i]

        # ---- realistic line: act on the LAGGED signal, size by CALIBRATED edge ----
        sig = i - 1 - EXEC_LAG              # signal read EXEC_LAG days before execution (close i-1)
        names, weights, day_ret = [], {}, 0.0
        if sig >= 0:
            crow = conf_v[sig]
            edges = []
            for j in np.where(~np.isnan(crow))[0]:
                k = _band_index(crow[j])
                if k < 0:
                    continue
                edge = _cal_prob(tally, ov, k) - 0.5      # calibrated win-prob over coin-flip
                if edge > 1e-9:
                    edges.append((j, edge))
            tote = sum(e for _, e in edges)
            if tote > 0:
                for j, e in edges:
                    wj = e / tote
                    weights[cols[j]] = wj
                    r = rrow[j]
                    if not np.isnan(r):
                        day_ret += wj * float(r)
                names = [cols[j] for j, _ in edges]
                invested_days += 1
                name_count += len(names)
        real_eq *= (1 + day_ret)

        # ---- "perfect (instant)" line: a computer, zero lag, raw strength-weighted ----
        craw = conf_v[i - 1]
        pmask = ~np.isnan(craw)
        if pmask.any():
            pw = np.where(pmask, craw, 0.0); pw = pw / pw.sum()
            pr = np.where(np.isnan(rrow), 0.0, rrow)
            perfect_eq *= (1 + float((pw * pr).sum()))

        br = spy_v[i]
        if not np.isnan(br):
            bench *= (1 + float(br))

        cur = set(names)
        entered = sorted(cur - prev_buys); exited = sorted(prev_buys - cur)
        entered_total += len(entered)
        top = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:6]
        hold = [f"{s} {round(wt * 100)}%" for s, wt in top]

        dates.append(str(idx[i].date()))
        equity.append(round(real_eq, 2))
        bequity.append(round(bench, 2))
        perfect.append(round(perfect_eq, 2))
        daily_ret.append(day_ret)
        trades.append({"date": str(idx[i].date()), "entered": entered[:10], "exited": exited[:10],
                       "hold": hold, "n": len(names), "ret_pct": round(day_ret * 100, 3),
                       "reset": bool(reset)})
        prev_buys = cur

    _flush(T - 1)                          # fold in the last matured outcomes for the learned table
    calib = _band_table(tally, ov)

    # today's basket: act on the latest actionable signal (1 day old) with all we've learned
    basket = []
    sigT = T - 1 - EXEC_LAG
    if sigT >= 0:
        crow = conf_v[sigT]
        edges = []
        for j in np.where(~np.isnan(crow))[0]:
            k = _band_index(crow[j])
            if k < 0:
                continue
            cp = _cal_prob(tally, ov, k)
            if cp - 0.5 > 1e-9:
                edges.append((j, cp - 0.5, cp, float(crow[j])))
        tote = sum(e for _, e, _, _ in edges) or 1.0
        for j, e, cp, rawc in edges:
            basket.append({"symbol": cols[j], "confidence": int(round(rawc)),
                           "calibrated": round(cp * 100), "weight_pct": round(e / tote * 100, 1)})
        basket.sort(key=lambda x: x["weight_pct"], reverse=True)

    stats = _stats(equity, bequity, dates, daily_ret, invested_days, name_count, entered_total)
    stats["perfect_value"] = round(perfect[-1], 2)
    stats["perfect_total_pct"] = round((perfect[-1] / BASE - 1) * 100, 1)
    stats["realism_drag_pct"] = round(stats["perfect_total_pct"] - stats["total_return_pct"], 1)
    stats["calib_events"] = ov["n"]

    state = {
        "meta": {"strategy": ("Each day, act on the watchlist's BUY signals — but wait 1 trading day "
                              "before executing (you're not a computer) and size each position by its "
                              "WALK-FORWARD CALIBRATED edge, not its raw confidence. Long-only; cash when "
                              "nothing has an edge. Charted vs $5,000 left in the S&P 500 (SPY). "
                              "EACH CALENDAR YEAR the strategy resets to the S&P baseline — its starting "
                              "capital becomes whatever the SPY line is worth at that year's open — so "
                              "every year is a fresh head-to-head race against the index."),
                 "start_capital": BASE, "benchmark": BENCHMARK, "schema": SCHEMA,
                 "universe_size": len(closes), "signal_buy": SIGNAL_BUY, "exec_lag": EXEC_LAG,
                 "since": dates[0], "seeded_through": str(idx[-1].date()),
                 "current_basket": basket,
                 "note": ("Price-only core of the live signal (no macro/event overlay). Executes 1 day "
                          "late; positions sized by calibrated win-probability learned walk-forward from "
                          "matured outcomes only — so the sizing improves as the track record grows."),
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates, "equity": equity, "benchmark_equity": bequity, "perfect_equity": perfect,
        "trades": trades, "stats": stats, "calibration": calib,
    }
    return state


def _stats(eq, bm, dates, drets, invested_days, name_count, entered_total):
    n = len(eq)
    yrs = max(1e-6, (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25)

    def cagr(a):
        return (a[-1] / a[0]) ** (1 / yrs) - 1 if a[0] > 0 and a[-1] > 0 else 0.0

    def mdd(a):
        pk, d = a[0], 0.0
        for v in a:
            pk = max(pk, v); d = min(d, v / pk - 1)
        return d

    sret = pd.Series(eq).pct_change().dropna()
    bret = pd.Series(bm).pct_change().dropna()

    def sharpe(r):
        return (r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else 0.0

    si = pd.Series(eq, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    bi = pd.Series(bm, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
    years_beat = int((si > bi).sum())
    years_total = int(len(si))

    traded = [r for r in drets if r != 0.0]
    wins = sum(1 for r in traded if r > 0)
    total_ret = (eq[-1] / eq[0] - 1) * 100
    bench_ret = (bm[-1] / bm[0] - 1) * 100
    return {"days": n, "years": round(yrs, 1), "value": round(eq[-1], 2),
            "benchmark_value": round(bm[-1], 2),
            "total_return_pct": round(total_ret, 1), "benchmark_total_pct": round(bench_ret, 1),
            "alpha_pct": round(total_ret - bench_ret, 1),
            "cagr_pct": round(cagr(eq) * 100, 1), "benchmark_cagr_pct": round(cagr(bm) * 100, 1),
            "max_drawdown_pct": round(mdd(eq) * 100, 1), "benchmark_dd_pct": round(mdd(bm) * 100, 1),
            "sharpe": round(sharpe(sret), 2), "benchmark_sharpe": round(sharpe(bret), 2),
            "win_rate_pct": round(wins / len(traded) * 100, 1) if traded else 0.0,
            "exposure_pct": round(invested_days / n * 100) if n else 0,
            "avg_names": round(name_count / invested_days, 1) if invested_days else 0.0,
            "rebalances_per_yr": round(entered_total / yrs) if yrs else 0,
            "years_beat": years_beat, "years_total": years_total}


def _empty(reason):
    return {"meta": {"strategy": "", "benchmark": BENCHMARK, "schema": SCHEMA, "start_capital": BASE,
                     "seeded_through": None, "current_basket": [], "note": reason,
                     "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "dates": [], "equity": [], "benchmark_equity": [], "perfect_equity": [],
            "trades": [], "stats": {}, "calibration": {"bands": [], "overall": {}}}


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
        print(f"[warn] watchlist_sim state save failed: {e}", flush=True)


def _append_live_log(state, watchlist):
    """Keep a forward record of the live confidence calls the dashboard actually
    showed today (real-time predictions, which include the macro/event overlay the
    backtest can't reconstruct). Grows over time alongside the seeded backtest."""
    if not watchlist:
        return
    day = state["meta"].get("seeded_through")
    if not day:
        return
    log = state.get("live_log") or {}
    if day in log:
        return
    row = []
    for w in watchlist:
        sig = (w or {}).get("signal") or {}
        t = w.get("ticker")
        if t and sig.get("action") in ("BUY", "SELL", "HOLD") and sig.get("price"):
            row.append({"symbol": t, "action": sig["action"],
                        "confidence": int(sig.get("strength", 0)), "price": round(sig["price"], 2)})
    if row:
        log[day] = row
        for k in sorted(log.keys())[:-LOG_KEEP]:
            log.pop(k, None)
        state["live_log"] = log


def ensure(daily, tickers=None, watchlist=None):
    """Rebuild the backtest when there's new daily data, else reuse the cache; then
    append today's live confidence calls to the forward log. `tickers` should be the
    live WATCHLIST tickers so this stays in sync with the dashboard."""
    tickers = [t for t in (tickers or _FALLBACK_TICKERS) if t]
    latest = None
    for probe in (BENCHMARK, "AAPL", "MSFT", "NVDA"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass

    state = load_state()
    fresh = (state and state.get("dates") and latest
             and state["meta"].get("seeded_through") == latest
             and state["meta"].get("schema") == SCHEMA)
    if not fresh:
        new = backtest(_fetch(tickers), tickers)
        if new.get("dates"):
            if state and state.get("live_log"):
                new["live_log"] = state["live_log"]   # preserve forward log across rebuilds
            state = new
        elif not state:
            state = new
    if state and state.get("dates"):
        _append_live_log(state, watchlist)
        save_state(state)
    return state


if __name__ == "__main__":
    st = ensure({}, _FALLBACK_TICKERS)
    s = st.get("stats", {})
    if not s:
        print("EMPTY:", st["meta"].get("note")); raise SystemExit
    print(f"points     : {len(st['dates'])}  {st['dates'][0]} -> {st['dates'][-1]}")
    for k in ("years", "value", "benchmark_value", "perfect_value", "total_return_pct",
              "benchmark_total_pct", "perfect_total_pct", "realism_drag_pct", "alpha_pct",
              "cagr_pct", "benchmark_cagr_pct", "max_drawdown_pct", "benchmark_dd_pct",
              "sharpe", "benchmark_sharpe", "win_rate_pct", "exposure_pct", "avg_names",
              "rebalances_per_yr", "calib_events", "years_beat", "years_total"):
        print(f"  {k:20s}: {s.get(k)}")
    print("realistic (1d lag + calibrated) ${:,.0f}  vs  perfect/instant ${:,.0f}  vs  SPY ${:,.0f}"
          .format(s["value"], s["perfect_value"], s["benchmark_value"]))
    print("today's basket (raw conf -> calibrated -> weight):")
    for b in st["meta"]["current_basket"][:8]:
        print(f"  {b['symbol']:6s} raw {b['confidence']:>3}%  ->  cal {b.get('calibrated','?')}%  ->  {b['weight_pct']}%")
    print("LEARNED calibration (walk-forward; band -> actual hit rate over",
          st["calibration"]["overall"].get("horizon_days"), "days, exec lag",
          st["calibration"]["overall"].get("exec_lag"), "):")
    for b in st["calibration"]["bands"]:
        print(f"  {b['band']:8s} n={b['n']:5d}  hit={b['hit_rate']}  avg_fwd={b['avg_fwd_pct']}")
    o = st["calibration"]["overall"]
    print(f"  overall  n={o['n']}  hit={o['hit_rate']}  avg_fwd={o['avg_fwd_pct']}")

# --- end of watchlist_sim.py ---
