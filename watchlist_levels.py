"""
Watchlist forward odds + backtested buy/sell levels.

For every watchlist ticker this turns the signal into a FORWARD, backtested read — the
same "what actually happened next" machinery behind the Watchlist Confidence Backtest:

  • FORWARD ODDS (the honest confidence): the historical probability the stock was HIGHER
    a given horizon later, measured from THIS ticker's own ~10 years and conditioned on its
    current trend state (price vs 50-day, 20- vs 50-day). Two horizons:
        ST = 21 trading days  (~1 month)   — near-term, more discriminating
        LT = 252 trading days (~1 year)    — long-term (note: 2008-2026 was mostly a bull
                                              market, so read LT odds relative to the ~70%
                                              base rate shown in the panel).
    Per-ticker when there are >=150 same-state samples, otherwise the pooled watchlist rate.

  • BACKTESTED BUY / SELL LEVELS, from the ticker's own forward-return distribution:
        buy  = price x (1 + 25th-percentile 1-month return)  — a TYPICAL pullback entry
        sell = price x (1 + median 3-month return)           — a TYPICAL 3-month target
    i.e. "it usually dips about this far before resuming (buy there); it has typically
    risen about this much over three months (sell there)." Bounded to sane ranges.

These are mechanical, history-based references — NOT financial advice, and the future need
not rhyme with the past. A high LT win-rate is partly just the long bull market.
"""

import json
import os

import numpy as np
import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist_levels_state.json")
PERIOD = "10y"
ST_H = 21          # ~1 month
LT_H = 252         # ~1 year
TGT_H = 63         # ~3 months (sell target)
MIN_PER = 150      # min same-state samples before trusting a ticker's own rate
SCHEMA = 1

_FALLBACK = ["XLK", "SMH", "URA", "UNG", "GLD", "SLV", "VOO", "CVX", "NVDA", "UNH", "IONQ",
             "RDW", "PL", "MDA.TO", "RKLB", "TSLA", "CSCO", "KLAC", "RGTI", "SOXX", "SNDK",
             "STX", "AAPL", "PLTR", "XOM", "SNOW", "AMZN", "BE", "KEYS", "PANW", "MU", "WDC",
             "NOK", "SPCX"]


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
            if len(c) >= 60:
                out[s] = c
        except Exception:
            pass
    return out


def compute(tickers):
    px = _fetch(tickers)
    data = {}
    for t, c in px.items():
        sma20, sma50 = c.rolling(20).mean(), c.rolling(50).mean()
        up = (c > sma50) & (sma20 > sma50)
        data[t] = {"c": c, "up": up, "sma50": sma50,
                   "fwd_st": c.shift(-ST_H) / c - 1,
                   "fwd_lt": c.shift(-LT_H) / c - 1,
                   "fwd_tg": c.shift(-TGT_H) / c - 1}

    # pooled win-rates by state/horizon (fallback for thin-history tickers)
    def pool(key):
        up_l, dn_l = [], []
        for d in data.values():
            f, up = d[key], d["up"]
            up_l += list((f[up & f.notna()] > 0).astype(float))
            dn_l += list((f[(~up) & f.notna()] > 0).astype(float))
        return (float(np.mean(up_l)) if up_l else 0.5), (float(np.mean(dn_l)) if dn_l else 0.5)

    pst_up, pst_dn = pool("fwd_st")
    plt_up, plt_dn = pool("fwd_lt")

    out = {}
    for t, d in data.items():
        c = d["c"]
        price = float(c.iloc[-1])
        s50 = d["sma50"].iloc[-1]
        up_now = bool(d["up"].iloc[-1]) if pd.notna(d["up"].iloc[-1]) else (price > float(s50) if pd.notna(s50) else True)

        def wr(fwd, p_up, p_dn):
            m = (d["up"] if up_now else ~d["up"]) & fwd.notna()
            v = fwd[m]
            n = int(len(v))
            if n >= MIN_PER:
                return float((v > 0).mean()), n, "own"
            return (p_up if up_now else p_dn), n, "pooled"

        st_p, st_n, st_b = wr(d["fwd_st"], pst_up, pst_dn)
        lt_p, lt_n, lt_b = wr(d["fwd_lt"], plt_up, plt_dn)

        st_all, tg_all = d["fwd_st"].dropna(), d["fwd_tg"].dropna()
        dip = float(st_all.quantile(0.25)) if len(st_all) > 30 else -0.04
        dip = max(-0.30, min(-0.01, dip))
        tgt = float(tg_all.median()) if len(tg_all) > 30 else 0.05
        tgt = max(0.02, min(0.40, tgt))

        out[t] = {"price": round(price, 2), "up_now": up_now,
                  "st_up": round(st_p * 100), "lt_up": round(lt_p * 100),
                  "st_n": st_n, "lt_n": lt_n, "st_basis": st_b, "lt_basis": lt_b,
                  "buy": round(price * (1 + dip), 2), "sell": round(price * (1 + tgt), 2),
                  "dip_pct": round(dip * 100, 1), "tgt_pct": round(tgt * 100, 1),
                  "support": round(float(c.tail(63).min()), 2),
                  "resistance": round(float(c.tail(252).max()), 2),
                  "st_h": ST_H, "lt_h": LT_H, "tgt_h": TGT_H, "hist_days": int(len(c))}

    return {"meta": {"schema": SCHEMA,
                     "pooled": {"st_up": round(pst_up * 100), "st_dn": round(pst_dn * 100),
                                "lt_up": round(plt_up * 100), "lt_dn": round(plt_dn * 100)}},
            "tickers": out}


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
        print(f"[warn] watchlist_levels state save failed: {e}", flush=True)


def ensure(daily, tickers=None):
    """Recompute once per trading day (10y fetch is slow); reuse the cache otherwise."""
    tickers = [t for t in (tickers or _FALLBACK) if t]
    latest = None
    for probe in ("SPY", "AAPL", "MSFT", "NVDA"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    fresh = (state and state.get("tickers") and latest
             and state["meta"].get("seeded_through") == latest
             and state["meta"].get("schema") == SCHEMA)
    if fresh:
        return state
    try:
        new = compute(tickers)
    except Exception as e:
        print(f"[warn] watchlist_levels compute failed: {e}", flush=True)
        return state or {"meta": {"schema": SCHEMA}, "tickers": {}}
    new["meta"]["seeded_through"] = latest
    if new.get("tickers"):
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    r = compute(_FALLBACK)
    print("pooled base rates:", r["meta"]["pooled"])
    print(f"{'tkr':7s}{'price':>9s}{'st↑':>5s}{'lt↑':>5s}{'buy':>9s}{'sell':>9s}{'dip%':>6s}{'tgt%':>6s}  basis   trend")
    for t in sorted(r["tickers"]):
        x = r["tickers"][t]
        print(f"{t:7s}{x['price']:9.2f}{x['st_up']:5d}{x['lt_up']:5d}{x['buy']:9.2f}{x['sell']:9.2f}"
              f"{x['dip_pct']:6.1f}{x['tgt_pct']:6.1f}  {x['st_basis'][:4]}/{x['lt_basis'][:4]} {'UP' if x['up_now'] else 'DN':>4s}")

# --- end of watchlist_levels.py ---
