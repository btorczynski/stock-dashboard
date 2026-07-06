"""
Strategy simulator — $5,000, backtested to 2005, after-tax P/L, and next-day
suggestions whose **confidence is the historical 1-year-forward hit rate**.

HOW CONFIDENCE IS DEFINED (this is the honest part):
  A suggestion's confidence is NOT a made-up signal strength. It is the empirical
  frequency, measured over 2005-2026, that a stock in this same trend state was
  actually higher (for a BUY) or lower (for a SELL) **one year (252 trading days)
  later**. We compute it per-stock when there's enough history (>=100 prior cases),
  otherwise we fall back to the pooled rate across all stocks. Because 2005-2026
  was largely a bull market, the unconditional "up in a year" base rate is high
  (~70%+), so read confidence relative to that base rate, and remember a historical
  frequency is NOT a guarantee.

  The suggestion's BUY/SELL/HOLD itself leans LONG-HORIZON (price vs the 200-day
  average + 6- and 12-month momentum), i.e. "is this likely up or down over the
  next year," not a one-day call.

STRATEGY P/L: hold the up-trend basket overnight, rebalance at the close, on
dividend-adjusted prices; benchmark = $5,000 in SPY, never sold. P/L is AFTER the
~43.2% short-term tax for a single Colorado filer at ~$350k (see below) and AFTER
a 10 bps slippage/cost charge on every dollar traded (daily rebalancing turns the
portfolio over a lot; pretending that's free would inflate the curve).

HONESTY NOTES (also shown in the UI):
  * HINDSIGHT UNIVERSE: PICKS_UNIVERSE is a list of names chosen TODAY — including
    two decades of known winners — backtested to 2005. That selection, not the trend
    rule, is likely most of the edge vs SPY. To show this, the SAME rule is also run
    on a NEUTRAL universe (the 9 long-history S&P sector ETFs, a fixed list nobody
    cherry-picked) and charted alongside.
  * Delisted/bankrupt stocks never appear in Yahoo data, so any stock universe is
    survivorship-biased on top of that.

NOT financial advice; a backtest is not a promise of future results.
"""

import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

SIM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_state.json")
START_CAPITAL = 5000.0
BENCHMARK = "SPY"
START_DATE = "2005-01-01"
REGIME_FILTER = False
MAX_POINTS = 1400
FWD_DAYS = 252                       # "next year" horizon for confidence
MIN_CASES = 100                      # min per-stock samples before we trust its own rate
SLIPPAGE_BPS = 10                    # cost per dollar traded (10 bps each rebalance)
SLIP = SLIPPAGE_BPS / 10000.0
SCHEMA = 2                           # bumped: slippage + neutral-universe line
# Fixed, un-cherry-picked control group: the 9 S&P sector ETFs with history to 2005.
# Same rule, no stock-picking — if the main curve's alpha vanishes here, the alpha
# came from the hand-picked stock list, not the rule.
NEUTRAL_UNIVERSE = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLB"]

STCG_FED, NIIT, CO_RATE = 0.35, 0.038, 0.044
STCG_RATE = round(STCG_FED + NIIT + CO_RATE, 4)
LTCG_RATE = round(0.15 + NIIT + CO_RATE, 4)
TAX_PROFILE = "single filer ~$350k, Colorado, 2026"


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _fetch_history(universe):
    syms = sorted(set(universe) | {BENCHMARK})
    d = yf.download(" ".join(syms), start=START_DATE, interval="1d",
                    auto_adjust=True, group_by="ticker", progress=False, threads=False)
    out = {}
    for s in syms:
        try:
            df = d[s].dropna(how="all")
            if not df.empty:
                out[s] = df
        except Exception:
            pass
    return out


def _after_tax(f_dates, f_ret, start, rate=STCG_RATE):
    eq, year_start, carry, tax_paid = start, start, 0.0, 0.0
    out = []
    for i in range(len(f_dates)):
        eq *= (1 + f_ret[i])
        year_end = (i == len(f_dates) - 1) or (f_dates[i + 1].year != f_dates[i].year)
        if year_end:
            taxable = (eq - year_start) - carry
            if taxable > 0:
                tax = rate * taxable
                eq -= tax
                tax_paid += tax
                carry = 0.0
            else:
                carry = -taxable
            year_start = eq
        out.append(eq)
    return out, tax_paid


def _forward_hit_rates(C, sma20, sma50):
    """Per-stock + pooled probability of being higher/lower FWD_DAYS later, given
    the current trend state. Returns dict used to set suggestion confidence."""
    fwd_up = (C.shift(-FWD_DAYS) / C - 1) > 0
    valid = (C.shift(-FWD_DAYS) / C).notna()
    uptrend = (C > sma50) & (sma20 > sma50)
    per_up, per_down = {}, {}
    for s in C.columns:
        um = (uptrend[s] & valid[s])
        nu = int(um.sum())
        if nu >= MIN_CASES:
            per_up[s] = round(float((fwd_up[s] & um).sum()) / nu, 3)
        dm = ((~uptrend[s]) & valid[s])
        nd = int(dm.sum())
        if nd >= MIN_CASES:
            per_down[s] = round(float(((~fwd_up[s]) & dm).sum()) / nd, 3)
    um = (uptrend & valid)
    dm = ((~uptrend) & valid)
    pooled_up = float((fwd_up & um).values.sum()) / max(1, int(um.values.sum()))
    pooled_down = float(((~fwd_up) & dm).values.sum()) / max(1, int(dm.values.sum()))
    base_up = float((fwd_up & valid).values.sum()) / max(1, int(valid.values.sum()))
    return {"per_up": per_up, "per_down": per_down,
            "pooled_up": round(pooled_up, 3), "pooled_down": round(pooled_down, 3),
            "base_up": round(base_up, 3)}


def _suggestions(C, sma20, sma50, sma200, hr, last, top=3):
    out = []
    for s in C.columns:
        cl = C[s].dropna()
        if len(cl) < 30 or pd.isna(C[s].iloc[last]) or pd.isna(sma50[s].iloc[last]):
            continue
        price = float(C[s].iloc[last])
        a200 = (not pd.isna(sma200[s].iloc[last])) and price > sma200[s].iloc[last]
        a50 = price > sma50[s].iloc[last]
        mom6 = (price / cl.iloc[-127] - 1) * 100 if len(cl) >= 127 else 0.0
        mom12 = (price / cl.iloc[-253] - 1) * 100 if len(cl) >= 253 else mom6
        # long-horizon score: 200-day trend + 6/12-month momentum
        score = (35 * (1 if a200 else -1) + 20 * (1 if a50 else -1)
                 + 25 * _clamp(mom6 / 20, -1, 1) + 20 * _clamp(mom12 / 40, -1, 1))
        action = "BUY" if score >= 25 else "SELL" if score <= -25 else "HOLD"
        if score >= 0:
            rate = hr["per_up"].get(s, hr["pooled_up"])
        else:
            rate = hr["per_down"].get(s, hr["pooled_down"])
        out.append({"symbol": s, "action": action, "confidence": int(round(rate * 100)),
                    "price": round(price, 2), "score": round(float(score)),
                    "basis": "own history" if (s in hr["per_up"] or s in hr["per_down"]) else "pooled",
                    "reason": f"{'above' if a200 else 'below'} 200d · 6mo {mom6:+.0f}% · 12mo {mom12:+.0f}%"})
    out.sort(key=lambda x: abs(x["score"]), reverse=True)
    return out[:top]


def _run_rule(C, spx, regime, start_capital):
    """The daily up-trend-basket engine, charged SLIPPAGE_BPS on every dollar traded.
    Decisions use data through close i-1; the basket earns day i's close-to-close return."""
    sma20, sma50 = C.rolling(20).mean(), C.rolling(50).mean()
    sig = (C > sma50) & (sma20 > sma50)
    spx_sma200 = spx.rolling(200).mean()
    syms = list(C.columns)
    idx = spx.index
    f_dates, f_eq, f_ret, f_basket = [], [], [], []
    eq = start_capital
    prev_held = []
    for i in range(201, len(idx)):
        prev = sig.iloc[i - 1]
        basket = [s for s in syms if bool(prev.get(s, False))]
        if regime:
            v2 = spx_sma200.iloc[i - 1]
            regime_on = True if pd.isna(v2) else (spx.iloc[i - 1] > v2)
        else:
            regime_on = True
        held = basket if regime_on else []
        rets = [C[s].iloc[i] / C[s].iloc[i - 1] - 1.0 for s in held
                if not pd.isna(C[s].iloc[i]) and not pd.isna(C[s].iloc[i - 1]) and C[s].iloc[i - 1] > 0]
        day_ret = sum(rets) / len(rets) if rets else 0.0
        # Slippage: rebalancing from yesterday's equal-weight basket to today's
        # trades sum(|w_new - w_old|) of the portfolio; each traded dollar pays SLIP.
        wo = (1.0 / len(prev_held)) if prev_held else 0.0
        wn = (1.0 / len(held)) if held else 0.0
        hs, ps = set(held), set(prev_held)
        traded = sum(abs((s in hs) * wn - (s in ps) * wo) for s in (hs | ps))
        day_ret -= SLIP * traded
        eq *= (1.0 + day_ret)
        f_dates.append(idx[i]); f_eq.append(eq)
        f_ret.append(day_ret); f_basket.append(held)
        prev_held = held
    return f_dates, f_eq, f_ret, f_basket


def backtest(daily, universe, benchmark=BENCHMARK, start_capital=START_CAPITAL, regime=REGIME_FILTER):
    closes = {}
    for s in universe:
        df = daily.get(s)
        if df is None or df.empty or "Close" not in df:
            continue
        c = df["Close"].dropna()
        if len(c) >= 210:
            closes[s] = c
    if benchmark not in daily or daily[benchmark] is None or daily[benchmark].empty:
        return _empty_state(start_capital, benchmark, "benchmark data unavailable")
    spx = daily[benchmark]["Close"].dropna()
    if not closes or len(spx) < 210:
        return _empty_state(start_capital, benchmark, "insufficient history")

    idx = spx.index
    C = pd.DataFrame({s: closes[s] for s in closes}).reindex(idx)
    sma20, sma50, sma200 = C.rolling(20).mean(), C.rolling(50).mean(), C.rolling(200).mean()

    f_dates, f_eq, f_ret, f_basket = _run_rule(C, spx, regime, start_capital)
    if not f_dates:
        return _empty_state(start_capital, benchmark, "no backtest days")

    # benchmark: $5k in SPY, never sold
    f_bench, beq = [], start_capital
    for i in range(201, len(idx)):
        bcl, bpr = spx.iloc[i], spx.iloc[i - 1]
        if not pd.isna(bcl) and not pd.isna(bpr) and bpr > 0:
            beq *= (bcl / bpr)
        f_bench.append(beq)

    # CONTROL GROUP: identical rule + slippage + tax on the fixed 9-sector-ETF
    # universe nobody cherry-picked. Gap between the two lines ≈ hindsight bias.
    n_at = []
    neutral_closes = {}
    for s in NEUTRAL_UNIVERSE:
        df = daily.get(s)
        if df is not None and not df.empty and "Close" in df:
            c = df["Close"].dropna()
            if len(c) >= 210:
                neutral_closes[s] = c
    if len(neutral_closes) >= 6:
        CN = pd.DataFrame(neutral_closes).reindex(idx)
        _, _, n_ret, _ = _run_rule(CN, spx, regime, start_capital)
        n_at, _ = _after_tax(f_dates, n_ret, start_capital)

    at_eq, tax_paid = _after_tax(f_dates, f_ret, start_capital)
    stats = _stats(at_eq, f_eq, f_bench, f_ret, start_capital, tax_paid)
    hr = _forward_hit_rates(C, sma20, sma50)
    suggestion = _suggestions(C, sma20, sma50, sma200, hr, len(idx) - 1)

    n = len(f_dates)
    stride = max(1, math.ceil(n / MAX_POINTS))
    sel = list(range(0, n, stride))
    if sel[-1] != n - 1:
        sel.append(n - 1)
    dates, equity, bench_eq, neutral_eq, trades = [], [], [], [], []
    prev_set = set()
    for k, j in enumerate(sel):
        prev_j = sel[k - 1] if k > 0 else j
        step_ret = (at_eq[j] / at_eq[prev_j] - 1.0) * 100 if at_eq[prev_j] else 0.0
        cur = set(f_basket[j])
        entered, exited = sorted(cur - prev_set), sorted(prev_set - cur)
        prev_set = cur
        dates.append(str(f_dates[j].date()))
        equity.append(round(at_eq[j], 2))
        bench_eq.append(round(f_bench[j], 2))
        if n_at:
            neutral_eq.append(round(n_at[j], 2))
        trades.append({"date": str(f_dates[j].date()), "n": len(f_basket[j]),
                       "names": sorted(f_basket[j])[:14], "entered": entered[:10], "exited": exited[:10],
                       "ret_pct": round(step_ret, 3), "equity": round(at_eq[j], 2)})

    conf_basis = {"horizon": "1 year (252 trading days)",
                  "p_up_given_uptrend": round(hr["pooled_up"] * 100, 1),
                  "p_down_given_downtrend": round(hr["pooled_down"] * 100, 1),
                  "p_up_unconditional": round(hr["base_up"] * 100, 1),
                  "history": f"{f_dates[0].date()} to {f_dates[-1].date()}"}

    if n_at:
        stats["neutral_equity"] = round(n_at[-1], 2)
        stats["neutral_return_pct"] = round((n_at[-1] / start_capital - 1) * 100, 2)
        stats["neutral_alpha_pct"] = round(((n_at[-1] - f_bench[-1]) / start_capital) * 100, 2)

    return {
        "meta": {"start_capital": start_capital, "benchmark": benchmark, "universe_size": len(closes),
                 "regime_filter": regime, "since": str(f_dates[0].date()), "tax_profile": TAX_PROFILE,
                 "stcg_rate": STCG_RATE, "confidence_basis": conf_basis,
                 "schema": SCHEMA, "slippage_bps": SLIPPAGE_BPS,
                 "strategy": (f"Hold the up-trend basket overnight, rebalancing at the close, since "
                              f"{f_dates[0].date()}. P/L is AFTER ~{STCG_RATE*100:.1f}% short-term tax "
                              f"({TAX_PROFILE}) and {SLIPPAGE_BPS} bps slippage per dollar traded; "
                              f"pre-tax ${f_eq[-1]:,.0f}, ~${tax_paid:,.0f} tax. "
                              f"Benchmark SPY never sold (untaxed)."),
                 "hindsight_note": ("The stock universe was hand-picked recently, with full knowledge of "
                                    "which names won over the backtest years — and delisted losers can't "
                                    "even appear in the data. The dashed control line runs the SAME rule "
                                    "on the 9 S&P sector ETFs (a fixed list nobody cherry-picked): the gap "
                                    "between the lines is roughly what hindsight stock-picking added."),
                 "neutral_universe": (NEUTRAL_UNIVERSE if n_at else []),
                 "seeded_through": str(f_dates[-1].date()),
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "dates": dates, "equity": equity, "benchmark_equity": bench_eq,
        "neutral_equity": neutral_eq,
        "stats": stats, "trades": trades, "suggestion": suggestion,
    }


def _stats(at_eq, pre_eq, bench_eq, daily_rets, start_capital, tax_paid):
    if not at_eq:
        return {}
    total = at_eq[-1] / start_capital - 1.0
    pre_total = pre_eq[-1] / start_capital - 1.0
    bench_total = bench_eq[-1] / start_capital - 1.0
    wins = sum(1 for r in daily_rets if r > 0)
    traded = sum(1 for r in daily_rets if r != 0)
    peak, max_dd = at_eq[0], 0.0
    for v in at_eq:
        peak = max(peak, v)
        max_dd = min(max_dd, v / peak - 1.0)
    yrs = len(at_eq) / 252.0
    cagr = (at_eq[-1] / start_capital) ** (1 / yrs) - 1 if yrs > 0 and at_eq[-1] > 0 else 0.0
    bcagr = (bench_eq[-1] / start_capital) ** (1 / yrs) - 1 if yrs > 0 else 0.0
    return {"days": len(at_eq), "years": round(yrs, 1), "start_capital": start_capital,
            "current_equity": round(at_eq[-1], 2), "profit": round(at_eq[-1] - start_capital, 2),
            "total_return_pct": round(total * 100, 2), "cagr_pct": round(cagr * 100, 2),
            "pretax_equity": round(pre_eq[-1], 2), "pretax_return_pct": round(pre_total * 100, 2),
            "tax_paid": round(tax_paid, 2),
            "benchmark_equity": round(bench_eq[-1], 2), "benchmark_profit": round(bench_eq[-1] - start_capital, 2),
            "benchmark_return_pct": round(bench_total * 100, 2), "benchmark_cagr_pct": round(bcagr * 100, 2),
            "alpha_pct": round((total - bench_total) * 100, 2),
            "win_rate_pct": round(100.0 * wins / traded, 1) if traded else 0.0,
            "max_drawdown_pct": round(max_dd * 100, 2)}


def _empty_state(start_capital, benchmark, reason):
    return {"meta": {"start_capital": start_capital, "benchmark": benchmark, "universe_size": 0,
                     "regime_filter": REGIME_FILTER, "strategy": "", "seeded_through": None,
                     "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": reason},
            "dates": [], "equity": [], "benchmark_equity": [], "stats": {}, "trades": [], "suggestion": []}


def load_state():
    try:
        with open(SIM_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_state(state):
    try:
        with open(SIM_PATH, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[warn] could not save sim state: {e}", flush=True)


def _latest_date(daily):
    for probe in ("VOO", "AAPL", "MSFT", "SPY", "NVDA"):
        df = daily.get(probe)
        if df is not None and not df.empty:
            try:
                return str(df["Close"].dropna().index[-1].date())
            except Exception:
                pass
    return None


def ensure_and_update(daily, universe):
    state = load_state()
    latest = _latest_date(daily)
    if state and state.get("dates"):
        same_day = latest and state["meta"].get("seeded_through") == latest
        same_cap = abs(state["meta"].get("start_capital", -1) - START_CAPITAL) < 1e-6
        same_strat = state["meta"].get("regime_filter") == REGIME_FILTER
        same_schema = state["meta"].get("schema") == SCHEMA
        if same_day and same_cap and same_strat and same_schema:
            return state
    new_state = backtest(_fetch_history(list(universe) + NEUTRAL_UNIVERSE), universe)
    if new_state.get("dates"):
        save_state(new_state)
        return new_state
    return state or new_state


# --- end of simulator.py ---
