"""
Buy-and-Hold-FOREVER sleeve — the patient cousin of the Watchlist Confidence Backtest.

Where the signal-trading sleeves traded the BUY/SELL/HOLD signal every day, THIS module
(the sole surviving strategy) does the opposite: it buys a basket of durable names, then sits
on its hands. No signals, no timing, no churn — just "own good things and wait."

WHAT IT HOLDS (a hand-picked "forever" subset of the dashboard watchlist — edit HOLDINGS):
  • Core ETFs ...... VOO, XLK, SMH, SOXX, GLD
  • Durable leaders . AAPL, NVDA, AMZN, CSCO, KLAC, MU, UNH, XOM, CVX, PANW
  Speculative watchlist names (IONQ, RGTI, RDW, PL, RKLB, SPCX, BE, …) are deliberately
  LEFT OUT — "hold forever" only makes sense for businesses you expect to still be here.

FOUR HONEST VARIANTS (because you asked to see them all):
  LUMP SUM ($5,000 invested once, equal weight, at the common start date)
     • drift ............ never sell, never rebalance; winners are allowed to dominate.
     • annual rebalance . each January, trim winners / top up laggards back to equal weight.
  DOLLAR-COST AVERAGING ($250 added every month, split equally across the basket)
     • drift ............ buy a little each month, otherwise never touch it.
     • annual rebalance . same monthly buys, plus a yearly reset to equal weight.
  Each is charted against the SAME money going into the S&P 500 (SPY), so the comparison is
  apples-to-apples: lump vs $5k-in-SPY, and DCA vs the-identical-schedule-in-SPY.

WHY TWO CHARTS: lump sum puts in $5,000 on day one; DCA keeps adding cash, so its ending
balance is bigger simply because more money went in. Plotting them on one axis would lie.
Instead each gets its own chart, and DCA is scored by its MONEY-WEIGHTED return (XIRR) — the
true annualized rate on the dollars actually invested — so the two are comparable as RATES.

HONEST CAVEATS (also shown in the UI):
  • SURVIVORSHIP: this basket is today's known winners. A "forever" list drawn up years ago
    would have looked different. Real forward results will very likely be more muted.
  • The basket HOLDS VOO (the S&P 500 itself), so "beating the S&P" is partly built-in — the
    point here isn't to beat it, it's to see how patient ownership of quality compares.
  • Rebalancing is modeled cost-free and tax-free. In a taxable account, trimming winners
    triggers tax; in reality the drift line is the cheapest to actually run.

NOT financial advice. A backtest is not a promise; past results don't predict the future.
"""

import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forever_state.json")

# Curated "forever" subset of the dashboard WATCHLIST. Edit to taste.
HOLDINGS = [
    "VOO", "XLK", "SMH", "SOXX", "GLD",                       # core / diversified ETFs
    "AAPL", "NVDA", "AMZN", "CSCO", "KLAC", "MU", "UNH", "XOM", "CVX", "PANW",  # durable leaders
]
BENCHMARK = "SPY"
BASE = 5000.0          # lump-sum dollars (echoes the $5k theme)
DCA_MONTHLY = 250.0    # dollars added every month in the DCA variant
PERIOD = "max"         # pull full history; the basket starts when the LAST name is available
SCHEMA = 2             # bumped: added per-holding "Buy now?" entry signals

# --- "Buy now?" entry signal ------------------------------------------------
# Even a forever holding has better and worse moments to deploy new cash. The
# entry-DIP score (0-100, price-only, so it's reconstructable through history)
# rewards buying when a name is cheap relative to ITS OWN trend; the live macro
# signal is then blended in. History grades each band by the return that buying
# at that valuation ACTUALLY produced over the next year.
FWD_DAYS = 252         # trading days ahead used to grade an entry (≈ 1 year)
DIP_ACC = 60           # entry score ≥ this -> "Accumulate"; < DIP_EXP -> "Expensive"
DIP_EXP = 45
W_DIP, W_LIVE = 0.60, 0.40   # blend weights: cheapness vs live macro-aware signal


def _clip01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def _rsi(s, period=14):
    """Wilder RSI on a Series (matches the dashboard's RSI)."""
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    ru = up.ewm(alpha=1 / period, adjust=False).mean()
    rd = dn.ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd.replace(0, 1e-9))


def _dip_from(vs200, offhigh, rsi):
    """Entry-dip score 0-100 (higher = more 'on sale'): below 200-day trend,
    far off the 52-week high, and a low RSI all make for a better entry."""
    c200 = _clip01(0.5 - vs200 / 0.40)        # -20% vs 200d -> 1.0, flat -> 0.5, +20% -> 0
    chigh = _clip01(-offhigh / 0.40)          # at the high -> 0, 40% below -> 1.0
    crsi = _clip01((70.0 - rsi) / 40.0)       # RSI 70 -> 0, RSI 30 -> 1.0
    return 100.0 * (c200 + chigh + crsi) / 3.0


def _band(score):
    return "Accumulate" if score >= DIP_ACC else ("Expensive" if score < DIP_EXP else "Fair")


# --------------------------------------------------------------------------- data
def _fetch(tickers):
    syms = sorted(set(t for t in tickers if t) | {BENCHMARK})
    d = yf.download(" ".join(syms), period=PERIOD, interval="1d", auto_adjust=True,
                    group_by="ticker", progress=False, threads=False)
    out = {}
    for s in syms:
        try:
            c = d[s]["Close"].dropna()
            if len(c) > 50:
                out[s] = c
        except Exception:
            pass
    return out


def _xirr(cashflows):
    """Money-weighted annualized return. cashflows = [(date, amount), ...] with
    contributions negative and the final value positive. Bisection on NPV(rate)."""
    if len(cashflows) < 2:
        return None
    t0 = cashflows[0][0]
    yrs = [(d - t0).days / 365.25 for d, _ in cashflows]
    amts = [a for _, a in cashflows]

    def npv(r):
        return sum(a / (1.0 + r) ** y for a, y in zip(amts, yrs))

    lo, hi = -0.9999, 10.0
    flo, fhi = npv(lo), npv(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        fm = npv(mid)
        if abs(fm) < 1e-7:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2.0


# --------------------------------------------------------------------------- engine
def backtest(closes):
    if BENCHMARK not in closes:
        return _empty("benchmark (SPY) data unavailable")
    held = [t for t in HOLDINGS if t in closes]
    if len(held) < 3:
        return _empty("not enough holdings have history")

    # Align every holding on a common calendar; the basket can only start once the
    # NEWEST name exists. Forward-fill minor gaps, then drop the leading warm-up.
    C = pd.concat({t: closes[t] for t in held}, axis=1).sort_index()
    start = max(closes[t].dropna().index[0] for t in held)
    C = C[C.index >= start].ffill().dropna(how="any")
    if len(C) < 60:
        return _empty("insufficient overlapping history")
    spy = closes[BENCHMARK].reindex(C.index).ffill()
    idx = C.index
    dates = [str(d.date()) for d in idx]
    N = len(held)
    P = C.values                         # (T, N) prices
    spv = spy.values
    T = len(idx)

    # Rebalance on the first trading day of each new YEAR; contribute on the first
    # trading day of each MONTH. Precompute those day indices.
    years = idx.year.values
    months = idx.month.values
    rebal_days = [i for i in range(1, T) if years[i] != years[i - 1]]
    contrib_days = [0] + [i for i in range(1, T) if months[i] != months[i - 1]]
    rebal_set = set(rebal_days)

    p0 = P[0]
    # ---- LUMP SUM ---------------------------------------------------------------
    sh_drift = (BASE / N) / p0                       # buy once, never touch
    eq_drift = (P * sh_drift).sum(axis=1)

    sh_re = (BASE / N) / p0                           # buy once, reset each January
    eq_rebal = np.empty(T)
    for i in range(T):
        if i in rebal_set:
            val = float((sh_re * P[i]).sum())
            sh_re = (val / N) / P[i]
        eq_rebal[i] = float((sh_re * P[i]).sum())

    spy_sh = BASE / spv[0]                            # $5k into SPY, held
    bench = spv * spy_sh

    # ---- DOLLAR-COST AVERAGING --------------------------------------------------
    per_name = DCA_MONTHLY / N
    contrib_set = set(contrib_days)
    dsh = np.zeros(N)                                 # DCA drift shares
    dsh_re = np.zeros(N)                              # DCA + annual rebalance shares
    spy_dsh = 0.0
    contributed = 0.0
    dca_val = np.empty(T)
    dca_val_re = np.empty(T)
    dca_contrib = np.empty(T)
    dca_bench = np.empty(T)
    cashflows = []                                    # for XIRR (basket, drift)
    cashflows_spy = []
    for i in range(T):
        if i in contrib_set:
            dsh += per_name / P[i]
            dsh_re += per_name / P[i]
            spy_dsh += DCA_MONTHLY / spv[i]
            contributed += DCA_MONTHLY
            cashflows.append((idx[i].to_pydatetime(), -DCA_MONTHLY))
            cashflows_spy.append((idx[i].to_pydatetime(), -DCA_MONTHLY))
        if i in rebal_set:                            # yearly reset to equal weight
            val = float((dsh_re * P[i]).sum())
            dsh_re = (val / N) / P[i]
        dca_val[i] = float((dsh * P[i]).sum())
        dca_val_re[i] = float((dsh_re * P[i]).sum())
        dca_contrib[i] = contributed
        dca_bench[i] = spy_dsh * spv[i]

    # money-weighted (XIRR) returns on the DCA dollars actually invested
    end_dt = idx[-1].to_pydatetime()
    mwr_basket = _xirr(cashflows + [(end_dt, float(dca_val[-1]))])
    mwr_rebal = _xirr(cashflows + [(end_dt, float(dca_val_re[-1]))])
    mwr_spy = _xirr(cashflows_spy + [(end_dt, float(dca_bench[-1]))])

    # ---- per-holding total return + final drifted weights (lump drift) ----------
    final_val = float(eq_drift[-1])
    holdings_perf = []
    drift_weights = []
    for j, t in enumerate(held):
        ret = (P[-1, j] / P[0, j] - 1.0) * 100.0
        wj = (sh_drift[j] * P[-1, j]) / final_val * 100.0
        holdings_perf.append({"symbol": t, "ret_pct": round(ret, 1),
                              "start_price": round(float(P[0, j]), 2),
                              "last_price": round(float(P[-1, j]), 2),
                              "weight_now_pct": round(wj, 1)})
        drift_weights.append({"symbol": t, "weight_pct": round(wj, 1)})
    holdings_perf.sort(key=lambda x: x["ret_pct"], reverse=True)
    drift_weights.sort(key=lambda x: x["weight_pct"], reverse=True)

    # hover rows: holdings are constant, so just a short label; flag January rebalances
    trades = [{"date": dates[i], "hold": "%d names · equal-weight target" % N,
               "rebalance": (i in rebal_set)} for i in range(T)]

    yrs = max(1e-6, (idx[-1] - idx[0]).days / 365.25)
    nxt = idx[-1].year + 1
    state = {
        "meta": {
            "strategy": ("Buy a curated 'forever' subset of the watchlist (durable leaders + core "
                         "ETFs), equal weight, and just hold — no signals, no timing. Shown four ways: "
                         "$5,000 lump sum and $%d/mo dollar-cost averaging, each with and without a "
                         "yearly rebalance, vs the same money in the S&P 500." % int(DCA_MONTHLY)),
            "holdings": held, "benchmark": BENCHMARK, "base": BASE, "dca_monthly": DCA_MONTHLY,
            "schema": SCHEMA, "since": dates[0], "seeded_through": dates[-1], "years": round(yrs, 1),
            "current_basket": [{"symbol": t, "target_pct": round(100.0 / N, 1)} for t in held],
            "drift_weights": drift_weights, "next_rebalance": "Jan %d (first trading day)" % nxt,
            "note": ("Common start = when the newest holding (%s) began trading. The basket holds VOO, "
                     "so it overlaps the benchmark by design. Rebalancing is modeled cost- and tax-free."
                     % held[int(np.argmin([closes[t].dropna().index[0].value for t in held]))]),
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "dates": dates,
        # lump sum (all start at $5,000 -> directly comparable)
        "equity": [round(float(v), 2) for v in eq_drift],          # primary: buy & hold, drift
        "equity_rebal": [round(float(v), 2) for v in eq_rebal],    # annual rebalance
        "benchmark_equity": [round(float(v), 2) for v in bench],   # $5k in SPY
        "trades": trades,
        # dollar-cost averaging (own scale; compare via money-weighted return)
        "dca_value": [round(float(v), 2) for v in dca_val],
        "dca_value_rebal": [round(float(v), 2) for v in dca_val_re],
        "dca_contributed": [round(float(v), 2) for v in dca_contrib],
        "dca_benchmark": [round(float(v), 2) for v in dca_bench],
        "holdings_perf": holdings_perf,
        "entry": _entry_signals(C, held),
        "stats": _stats(eq_drift, eq_rebal, bench, dca_val, dca_val_re, dca_contrib, dca_bench,
                        dates, mwr_basket, mwr_rebal, mwr_spy, N),
    }
    return state


def _stats(eqd, eqr, bm, dcav, dcar, dcac, dcab, dates, mwr_b, mwr_r, mwr_s, n_names):
    yrs = max(1e-6, (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365.25)

    def cagr(a):
        return (a[-1] / a[0]) ** (1 / yrs) - 1 if a[0] > 0 and a[-1] > 0 else 0.0

    def mdd(a):
        pk, d = a[0], 0.0
        for v in a:
            pk = max(pk, v)
            d = min(d, v / pk - 1)
        return d * 100.0

    def sharpe(a):
        r = pd.Series(a).pct_change().dropna()
        return (r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else 0.0

    def ann_yrs(a):
        si = pd.Series(a, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
        bi = pd.Series(bm, index=pd.to_datetime(dates)).resample("YE").last().pct_change().dropna()
        m = min(len(si), len(bi))
        return int((si.values[:m] > bi.values[:m]).sum()), int(m)

    yb_d, yt = ann_yrs(eqd)
    yb_r, _ = ann_yrs(eqr)
    contributed = float(dcac[-1])
    return {
        "names": n_names, "years": round(yrs, 1),
        # lump sum — drift (primary)
        "value": round(float(eqd[-1]), 2), "total_return_pct": round((eqd[-1] / eqd[0] - 1) * 100, 1),
        "cagr_pct": round(cagr(eqd) * 100, 1), "max_drawdown_pct": round(mdd(eqd), 1),
        "sharpe": round(sharpe(eqd), 2),
        # lump sum — annual rebalance
        "value_rebal": round(float(eqr[-1]), 2), "total_return_rebal_pct": round((eqr[-1] / eqr[0] - 1) * 100, 1),
        "cagr_rebal_pct": round(cagr(eqr) * 100, 1), "max_drawdown_rebal_pct": round(mdd(eqr), 1),
        # benchmark (lump $5k in SPY)
        "benchmark_value": round(float(bm[-1]), 2), "benchmark_total_pct": round((bm[-1] / bm[0] - 1) * 100, 1),
        "benchmark_cagr_pct": round(cagr(bm) * 100, 1), "benchmark_dd_pct": round(mdd(bm), 1),
        "benchmark_sharpe": round(sharpe(bm), 2),
        "alpha_pct": round((eqd[-1] / eqd[0] - 1) * 100 - (bm[-1] / bm[0] - 1) * 100, 1),
        "years_beat": yb_d, "years_beat_rebal": yb_r, "years_total": yt,
        # dollar-cost averaging
        "dca_contributed": round(contributed, 2),
        "dca_value": round(float(dcav[-1]), 2), "dca_value_rebal": round(float(dcar[-1]), 2),
        "dca_benchmark_value": round(float(dcab[-1]), 2),
        "dca_gain_pct": round((dcav[-1] / contributed - 1) * 100, 1) if contributed else 0.0,
        "dca_gain_rebal_pct": round((dcar[-1] / contributed - 1) * 100, 1) if contributed else 0.0,
        "dca_benchmark_gain_pct": round((dcab[-1] / contributed - 1) * 100, 1) if contributed else 0.0,
        "dca_mwr_pct": round(mwr_b * 100, 1) if mwr_b is not None else None,
        "dca_mwr_rebal_pct": round(mwr_r * 100, 1) if mwr_r is not None else None,
        "dca_benchmark_mwr_pct": round(mwr_s * 100, 1) if mwr_s is not None else None,
        "dca_max_drawdown_pct": round(mdd(dcav), 1),
    }


def _bucket(dip, fwd):
    """Grade matured entries: for each valuation band, how the next-year return
    actually turned out. `dip` and `fwd` are aligned Series; rows with no matured
    forward return are dropped (no look-ahead)."""
    valid = dip.notna() & fwd.notna()
    dv, fv = dip[valid], fwd[valid]
    out = {}
    for b in ("Accumulate", "Fair", "Expensive"):
        if b == "Accumulate":
            m = dv >= DIP_ACC
        elif b == "Expensive":
            m = dv < DIP_EXP
        else:
            m = (dv >= DIP_EXP) & (dv < DIP_ACC)
        n = int(m.sum())
        if n:
            f = fv[m]
            out[b] = {"n": n, "fwd_avg_pct": round(float(f.mean()) * 100, 1),
                      "hit_pct": round(float((f > 0).mean()) * 100)}
        else:
            out[b] = {"n": 0, "fwd_avg_pct": None, "hit_pct": None}
    return out


def _entry_signals(C, held):
    """Price-only entry read for every holding, cacheable daily. Per name: today's
    dip metrics + the historical next-year outcome of buying at each valuation band.
    The live macro signal is layered on later in refresh_entry()."""
    fwd_all = C.shift(-FWD_DAYS) / C - 1.0          # next-year return from each day
    basket_dip = {}
    rows = []
    for t in held:
        c = C[t]
        sma200 = c.rolling(200, min_periods=200).mean()
        hi52 = c.rolling(252, min_periods=60).max()
        rsi = _rsi(c)
        vs200 = c / sma200 - 1.0
        offh = c / hi52 - 1.0
        dip = (100.0 * ((0.5 - vs200 / 0.40).clip(0, 1)
                        + (-offh / 0.40).clip(0, 1)
                        + ((70.0 - rsi) / 40.0).clip(0, 1)) / 3.0)
        basket_dip[t] = dip
        bands = _bucket(dip, fwd_all[t])
        i = dip.last_valid_index()
        d0 = float(dip.loc[i])
        b0 = _band(d0)
        rows.append({
            "symbol": t, "price": round(float(c.loc[i]), 2),
            "vs200_pct": round(float(vs200.loc[i]) * 100, 1),
            "off_high_pct": round(float(offh.loc[i]) * 100, 1),
            "rsi": round(float(rsi.loc[i])),
            "dip_score": round(d0), "dip_band": b0,
            "sma200": (round(float(sma200.loc[i]), 4) if pd.notna(sma200.loc[i]) else None),
            "hi52": round(float(hi52.loc[i]), 4),
            "hist": bands, "hist_today": bands.get(b0),
        })
    # overall basket: average dip across names vs the equal-weight forward return
    bd = pd.DataFrame(basket_dip).mean(axis=1)
    bfwd = fwd_all[held].mean(axis=1)
    obands = _bucket(bd, bfwd)
    j = bd.last_valid_index()
    ob = _band(float(bd.loc[j]))
    overall = {"dip_score": round(float(bd.loc[j])), "dip_band": ob,
               "hist": obands, "hist_today": obands.get(ob)}
    return {"holdings": rows, "overall": overall,
            "params": {"w_dip": W_DIP, "w_live": W_LIVE, "fwd_days": FWD_DAYS,
                       "acc": DIP_ACC, "exp": DIP_EXP,
                       "live_note": "live leg = calibrated 1mo/1yr band up-odds when available"}}


def refresh_entry(state, watchlist=None):
    """Overlay the LIVE macro-aware BUY/SELL signal onto the cached price-only entry
    read, producing each holding's blended 'Buy now?' verdict. Cheap (re)run every
    poll so the call stays current without rebuilding the backtest. Mutates in place."""
    e = state.get("entry") if state else None
    if not e:
        return state
    sig = {}
    for w in (watchlist or []):
        t = (w or {}).get("ticker")
        if t:
            sig[t] = (w or {}).get("signal") or {}
    scores = []
    for h in e.get("holdings", []):
        s = sig.get(h["symbol"]) or {}
        act = s.get("action")
        strg = float(s.get("strength") or 0)
        price = s.get("price")
        # Live leg v2: when the signal carries CALIBRATED band odds (historical
        # chance the name was higher 1mo / 1yr later from this signal band —
        # signal_calibration.py), use those directly; they are already on the
        # same 0-100 probability scale the blend wants. Heuristic fallback
        # (50 ± strength/2) only when calibration is unavailable.
        p1m, p1y = s.get("p_up_1m_pct"), s.get("p_up_1y_pct")
        if p1m is not None and p1y is not None:
            live = (float(p1m) + float(p1y)) / 2.0
            live_basis = "hist"
        else:
            live = 50.0 + (strg / 2 if act == "BUY" else (-strg / 2 if act == "SELL" else 0.0))
            live_basis = "score"
        dip = float(h["dip_score"])
        if price and h.get("sma200") and h.get("hi52"):      # refresh cheapness off the live price
            vs200 = price / h["sma200"] - 1.0
            offh = price / h["hi52"] - 1.0
            dip = _dip_from(vs200, offh, float(h["rsi"]))
            h["price"] = round(float(price), 2)
            h["vs200_pct"] = round(vs200 * 100, 1)
            h["off_high_pct"] = round(offh * 100, 1)
            h["dip_score"] = round(dip)
            h["dip_band"] = _band(dip)
            h["hist_today"] = h["hist"].get(h["dip_band"])
        buy = round(W_DIP * dip + W_LIVE * live)
        # Falling-knife guard: while the fast-crash override is firing (−12%/10d
        # or −18%/1mo, still in free-fall), "cheap" is not yet "on sale" — hold
        # new cash back; the verdict flips to Accumulate as the flag clears.
        if s.get("crash_flag") == "crash" and buy >= DIP_ACC:
            buy = DIP_ACC - 1
            h["capped"] = "fast-crash"
        else:
            h.pop("capped", None)
        h["live_action"] = act or "—"
        h["live_strength"] = int(round(strg))
        h["live_score"] = round(live)
        h["live_basis"] = live_basis
        h["buy_now"] = buy
        h["verdict"] = _band(buy)
        scores.append(buy)
    if scores:
        avg = round(sum(scores) / len(scores))
        e["overall"]["buy_now"] = avg
        e["overall"]["verdict"] = _band(avg)
        e["overall"]["n_accumulate"] = sum(1 for h in e["holdings"] if h.get("verdict") == "Accumulate")
        e["overall"]["n_total"] = len(scores)
    return state


def _empty(reason):
    return {"meta": {"strategy": "", "benchmark": BENCHMARK, "schema": SCHEMA, "base": BASE,
                     "dca_monthly": DCA_MONTHLY, "holdings": [], "seeded_through": None,
                     "current_basket": [], "drift_weights": [], "note": reason,
                     "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "dates": [], "equity": [], "equity_rebal": [], "benchmark_equity": [], "trades": [],
            "dca_value": [], "dca_value_rebal": [], "dca_contributed": [], "dca_benchmark": [],
            "holdings_perf": [], "entry": {"holdings": [], "overall": {}, "params": {}}, "stats": {}}


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
        print(f"[warn] forever_hold state save failed: {e}", flush=True)


def ensure(daily, watchlist=None):
    """Rebuild the backtest when there's a new trading day, else reuse the daily cache;
    then overlay the live macro-aware signal onto the entry read every call (cheap), so
    the 'Buy now?' verdicts stay current intraday. `watchlist` carries the live signals."""
    latest = None
    for probe in (BENCHMARK, "AAPL", "MSFT", "NVDA"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date())
                break
            except Exception:
                pass
    state = load_state()
    fresh = (state and state.get("dates") and latest
             and state["meta"].get("seeded_through") == latest
             and state["meta"].get("schema") == SCHEMA)
    if not fresh:
        new = backtest(_fetch(HOLDINGS))
        if new.get("dates"):
            save_state(new)
            state = new
        elif not state:
            state = new
    if state and state.get("dates"):
        refresh_entry(state, watchlist)        # live blend; not persisted (re-applied each call)
    return state


if __name__ == "__main__":
    st = ensure({})
    s = st.get("stats", {})
    if not s:
        print("EMPTY:", st["meta"].get("note"))
        raise SystemExit
    m = st["meta"]
    print(f"holdings   : {', '.join(m['holdings'])}")
    print(f"window     : {st['dates'][0]} -> {st['dates'][-1]}  ({s['years']}y, {len(st['dates'])} days)")
    print("\nLUMP SUM  $%.0f invested once -------------------------------------" % BASE)
    print(f"  buy & hold (drift) : ${s['value']:>12,.0f}   total {s['total_return_pct']:>7}%   CAGR {s['cagr_pct']}%   maxDD {s['max_drawdown_pct']}%")
    print(f"  annual rebalance   : ${s['value_rebal']:>12,.0f}   total {s['total_return_rebal_pct']:>7}%   CAGR {s['cagr_rebal_pct']}%   maxDD {s['max_drawdown_rebal_pct']}%")
    print(f"  S&P 500 ($5k held) : ${s['benchmark_value']:>12,.0f}   total {s['benchmark_total_pct']:>7}%   CAGR {s['benchmark_cagr_pct']}%   maxDD {s['benchmark_dd_pct']}%")
    print(f"  alpha vs S&P (drift): {s['alpha_pct']} pts   ·   beat S&P in {s['years_beat']}/{s['years_total']} calendar yrs")
    print("\nDOLLAR-COST AVG  $%.0f/mo, total contributed $%s ----------------" % (DCA_MONTHLY, f"{s['dca_contributed']:,.0f}"))
    print(f"  buy & hold (drift) : ${s['dca_value']:>12,.0f}   gain {s['dca_gain_pct']:>7}%   money-weighted {s['dca_mwr_pct']}%/yr")
    print(f"  annual rebalance   : ${s['dca_value_rebal']:>12,.0f}   gain {s['dca_gain_rebal_pct']:>7}%   money-weighted {s['dca_mwr_rebal_pct']}%/yr")
    print(f"  same into S&P 500  : ${s['dca_benchmark_value']:>12,.0f}   gain {s['dca_benchmark_gain_pct']:>7}%   money-weighted {s['dca_benchmark_mwr_pct']}%/yr")
    print("\nper-holding total return (lump, drift):")
    for h in st["holdings_perf"]:
        print(f"  {h['symbol']:6s} {h['ret_pct']:>9}%   now {h['weight_now_pct']:>5}% of basket")
    print("\ndrifted weights now (started equal at %.1f%% each):" % (100.0 / s["names"]))
    print("  " + " · ".join(f"{d['symbol']} {d['weight_pct']}%" for d in m["drift_weights"][:8]))

    e = st.get("entry", {})
    ov = e.get("overall", {})
    print("\nBUY NOW?  (blended dip + live signal; history = next-%dd return when in that valuation band)" % FWD_DAYS)
    print(f"  overall basket: dip {ov.get('dip_score')} ({ov.get('dip_band')}) · history {ov.get('hist_today')}")
    print(f"  {'name':6s} {'entry':>5s}  {'verdict':11s} {'vs200d':>7s} {'offHigh':>7s} {'RSI':>4s}   history when this cheap")
    for h in sorted(e.get("holdings", []), key=lambda x: x.get("dip_score", 0), reverse=True):
        ht = h.get("hist_today") or {}
        fa = ht.get("fwd_avg_pct")
        hist = f"n={ht.get('n',0):<5d} avg {('+' if (fa or 0) >= 0 else '')}{fa}%  hit {ht.get('hit_pct')}%" if ht.get("n") else "no matured history"
        print(f"  {h['symbol']:6s} {h.get('dip_score'):>5}  {h.get('dip_band','—'):11s} "
              f"{h['vs200_pct']:>6.1f}% {h['off_high_pct']:>6.1f}% {h['rsi']:>4}   {hist}")

# --- end of forever_hold.py (entry signals v2) ---
