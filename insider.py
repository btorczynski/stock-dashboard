"""
Insider activity tracker — LEGAL, public SEC Form 4 disclosures (via Yahoo).

Corporate insiders (officers, directors, 10%+ owners) must report their own trades
to the SEC within 2 business days. This module reads those filings for the watchlist
and turns OPEN-MARKET purchases/sales into a signal.

Key principle: BUYING is the signal, SELLING is mostly noise. Insiders buy with their
own cash for one reason (they expect a rise); they sell for many innocent reasons
(taxes, diversification, scheduled 10b5-1 plans). So clusters of open-market BUYS —
especially several insiders at once — get a bullish nudge; selling is reported but
NOT treated as bearish. Grants, gifts, and option exercises are excluded.

This is public information only. It is NOT non-public/"inside" information and cannot
predict a market crash. NOT financial advice.
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "insider_state.json")
SCHEMA = 1


def _one(ticker):
    """Return open-market insider summary for one ticker, or None if no insider data."""
    try:
        tr = yf.Ticker(ticker).insider_transactions
    except Exception:
        return None
    if tr is None or tr.empty:
        return None
    txt = tr.get("Text", pd.Series([""] * len(tr))).fillna("").astype(str).str.lower()
    val = pd.to_numeric(tr.get("Value"), errors="coerce").fillna(0)
    ins = tr.get("Insider", pd.Series([""] * len(tr))).fillna("").astype(str)
    buy = txt.str.contains("purchase")
    sell = txt.str.contains("sale")
    n_buy, n_sell = int(buy.sum()), int(sell.sum())
    buy_val, sell_val = float(val[buy].sum()), float(val[sell].sum())
    buyers = sorted({x for x in ins[buy] if x})
    if n_buy == 0 and n_sell == 0:
        return None  # only grants/gifts/exercises -> nothing to say
    if n_buy >= 3 and buy_val >= sell_val:
        label, tone, nudge = "Insider buying cluster", "bull", 12
    elif buy_val > sell_val and n_buy > 0:
        label, tone, nudge = "Net insider buying", "bull", 6
    elif n_sell >= 3 and sell_val > buy_val * 3:
        label, tone, nudge = "Insider selling (usually noise)", "soft", 0
    else:
        label, tone, nudge = "Mixed", "neutral", 0
    return {"n_buy": n_buy, "n_sell": n_sell, "buy_val": round(buy_val),
            "sell_val": round(sell_val), "buyers": len(buyers),
            "top_buyers": buyers[:3], "label": label, "tone": tone, "nudge": nudge}


def build(tickers):
    sigs = {}
    for t in tickers:
        d = _one(t)
        if d:
            sigs[t] = d
    bullish = sorted([t for t, d in sigs.items() if d["tone"] == "bull"],
                     key=lambda t: -sigs[t]["buy_val"])
    return {"signals": sigs, "bullish": bullish, "schema": SCHEMA,
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
        print(f"[warn] insider state save failed: {e}", flush=True)


def ensure(tickers, daily):
    """Cached once per trading day (insider filings update slowly)."""
    latest = None
    for probe in ("AAPL", "MSFT", "NVDA"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    if state and state.get("signals") is not None and latest \
            and state.get("seeded_through") == latest and state.get("schema") == SCHEMA:
        return state
    new = build(tickers)
    new["seeded_through"] = latest
    if new["signals"]:
        save_state(new)
        return new
    return state or new


if __name__ == "__main__":
    r = build(["NVDA", "AAPL", "UNH", "PLTR", "CVX", "TSLA"])
    print("bullish:", r["bullish"])
    for t, d in r["signals"].items():
        print(f"{t:6s} {d['label']:32s} buys={d['n_buy']} (${d['buy_val']:,}) sells={d['n_sell']} buyers={d['buyers']}")

# --- end of insider.py ---
