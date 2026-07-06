"""
Long-term drift tag per watchlist name. Slow-moving (recomputed daily, but it barely
changes): each ticker's long-run CAGR over up to ~10 years of dividend-adjusted history.

Tags:
  avoid  -> negative long-term drift (buy-and-hold has lost money; e.g. UNG)
  long   -> positive drift (normal long-bias)
  strong -> >= 20%/yr long-term compounder
  new    -> too little history to judge

This is the "should I even hold this for the long run?" filter from the short-analysis,
surfaced next to each watchlist signal. NOT financial advice.
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drift_state.json")
SCHEMA = 1


def build(tickers):
    tickers = [t for t in tickers if t]
    if not tickers:
        return {"tags": {}, "schema": SCHEMA}
    d = yf.download(tickers, period="10y", auto_adjust=True, progress=False,
                    threads=False, group_by="ticker")
    out = {}
    for t in tickers:
        try:
            c = d[t]["Close"].dropna() if len(tickers) > 1 else d["Close"].dropna()
        except Exception:
            continue
        if len(c) < 60:
            out[t] = {"tag": "new", "cagr_pct": None, "years": round(len(c) / 252, 1)}
            continue
        yrs = len(c) / 252.0
        cagr = (float(c.iloc[-1]) / float(c.iloc[0])) ** (1 / yrs) - 1
        tag = "avoid" if cagr <= 0 else ("strong" if cagr >= 0.20 else "long")
        out[t] = {"tag": tag, "cagr_pct": round(cagr * 100, 1), "years": round(yrs, 1)}
    return {"tags": out, "schema": SCHEMA,
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}


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
        print(f"[warn] drift state save failed: {e}", flush=True)


def ensure(tickers, daily):
    latest = None
    for p in ("SPY", "AAPL", "MSFT", "NVDA"):
        df = daily.get(p) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    if state and state.get("tags") and latest and state.get("seeded_through") == latest \
            and state.get("schema") == SCHEMA:
        return state
    new = build(tickers)
    new["seeded_through"] = latest
    if new["tags"]:
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    r = build(["SPY", "NVDA", "AAPL", "UNG", "PLUG", "GLD", "KGC"])
    for t, d in r["tags"].items():
        print(f"{t:6s} {d['tag']:7s} CAGR={d['cagr_pct']}% ({d['years']}y)")

# --- end of drift.py ---
