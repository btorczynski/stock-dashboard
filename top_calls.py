"""
Top-2 Calls + self-grading scorecard.

Each refresh it surfaces the 2 highest-conviction calls (BUY / HOLD / SELL) from the
signal engine. Each trading day it LOGS those calls, and once a call is ~10 trading days
old it GRADES it against the actual move (BUY right if up, SELL right if down, HOLD right
if roughly flat). Those grades accumulate into a live, out-of-sample report card.

This is the honest "continually improve the model" loop: it does NOT secretly retrain a
model (that would overfit). It builds a real forward track record so we can SEE which call
types actually work and tune the signal weights deliberately. NOT financial advice.
"""

import json
import os
from datetime import datetime, timezone, date, timedelta
import math

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "top_calls_state.json")
HORIZON_DAYS = 14   # calendar days ~ 10 trading days
SCHEMA = 1


def _blank():
    return {"log": {}, "schema": SCHEMA,
            "stats": {"n": 0, "hits": 0, "sum_fwd": 0.0,
                      "BUY": {"n": 0, "hits": 0}, "SELL": {"n": 0, "hits": 0}, "HOLD": {"n": 0, "hits": 0}}}


def load_state():
    try:
        with open(STATE) as f:
            s = json.load(f)
        return s if s.get("schema") == SCHEMA else _blank()
    except Exception:
        return _blank()


def save_state(s):
    try:
        with open(STATE, "w") as f:
            json.dump(s, f)
    except Exception as e:
        print(f"[warn] top_calls state save failed: {e}", flush=True)


def _latest_date(daily):
    for p in ("SPY", "AAPL", "MSFT"):
        df = daily.get(p) if daily else None
        if df is not None and not df.empty:
            try:
                return str(df["Close"].dropna().index[-1].date())
            except Exception:
                pass
    return None


def _price(daily, sym):
    df = daily.get(sym) if daily else None
    if df is None or df.empty:
        return None
    try:
        c = df["Close"].dropna()
        return float(c.iloc[-1]) if len(c) else None
    except Exception:
        return None


def _entry(src):
    return {"symbol": src.get("symbol") or src.get("ticker"), "action": src["action"],
            "score": src.get("score", 0), "price": src["price"], "change_pct": src.get("change_pct"),
            "conf": src.get("conf_pct"), "conf_basis": src.get("conf_basis"),
            "entry_action": src.get("entry_action"), "quote_as_of": src.get("quote_as_of")}


def _candidates(picks, watchlist):
    pool = {}
    for p in (picks or []):
        if p.get("price") and p.get("action") in ("BUY", "SELL", "HOLD"):
            pool[p["symbol"]] = _entry(p)
    for w in (watchlist or []):
        s = dict(w.get("signal") or {})
        t = w.get("ticker")
        if t:
            pool.pop(t, None)  # the final watchlist decision is authoritative
        if s.get("data_status") in ("stale", "missing", "invalid"):
            continue
        if t and s.get("price") and s.get("action") in ("BUY", "SELL", "HOLD"):
            s["symbol"] = t
            pool[t] = _entry(s)
    cands = list(pool.values())
    # conviction ranks; the CALIBRATED hit-rate (historical odds the band's call
    # was right — see signal_calibration.py) breaks ties and is what we report
    cands.sort(key=lambda c: (abs(c["score"]), c.get("conf") or 0), reverse=True)
    return cands


def _horizon_price(daily, symbol, called_on, latest):
    """Grade at the promised horizon, even when the app was offline afterwards.
    Missing bars around the due date remain ungraded instead of using a later price.
    """
    frame = daily.get(symbol)
    if frame is None or frame.empty:
        return None
    due = date.fromisoformat(called_on) + timedelta(days=HORIZON_DAYS)
    c = frame["Close"].dropna().sort_index()
    rows = c[[due <= stamp.date() <= min(latest, due + timedelta(days=4)) for stamp in c.index]]
    if rows.empty:
        return None
    value = float(rows.iloc[0])
    return (value, str(rows.index[0].date())) if math.isfinite(value) and value > 0 else None


def compute(picks, watchlist, daily, as_of=None):
    cands = _candidates(picks, watchlist)
    top = [{"symbol": c["symbol"], "action": c["action"],
            "confidence": (int(c["conf"]) if c.get("conf") is not None else abs(int(c["score"]))),
            "conf_basis": ("adjusted" if c.get("conf") is not None else "score"),
            "entry_action": c.get("entry_action"),
            "price": round(c["price"], 2), "change_pct": c["change_pct"]} for c in cands[:2]]
    st = load_state()
    latest = _latest_date(daily)
    if latest:
        ld = date.fromisoformat(latest)
        S = st["stats"]
        for d, calls in list(st["log"].items()):
            try:
                age = (ld - date.fromisoformat(d)).days
            except Exception:
                continue
            if age < HORIZON_DAYS:
                continue
            for c in calls:
                if c.get("graded"):
                    continue
                result = _horizon_price(daily, c["symbol"], d, ld)
                if result is None or not c.get("price"):
                    continue
                cur, evaluated_on = result
                fwd = cur / c["price"] - 1
                act = c["action"]
                correct = (fwd > 0) if act == "BUY" else ((fwd < 0) if act == "SELL" else abs(fwd) < 0.03)
                aligned = fwd if act != "SELL" else -fwd
                S["n"] += 1
                S["sum_fwd"] += aligned
                S[act]["n"] += 1
                if correct:
                    S["hits"] += 1
                    S[act]["hits"] += 1
                c["graded"] = True
                c["evaluated_on"] = evaluated_on
                c["forward_return_pct"] = round(fwd * 100, 4)
        call_date = str(as_of.date()) if as_of is not None else latest
        can_log = as_of is None or (as_of.weekday() < 5 and
            (call_date == latest or any((c.get("quote_as_of") or "").startswith(call_date) for c in cands)))
        if can_log and call_date not in st["log"] and top:
            st["log"][call_date] = [{"symbol": t["symbol"], "action": t["action"], "price": t["price"]} for t in top]
        save_state(st)
    S = st["stats"]
    n = S["n"]
    by = {a: {"n": S[a]["n"], "hit_rate": (round(S[a]["hits"] / S[a]["n"] * 100) if S[a]["n"] else None)}
          for a in ("BUY", "SELL", "HOLD")}
    open_calls = sum(1 for _, cs in st["log"].items() for c in cs if not c.get("graded"))
    sc = {"graded": n, "hit_rate": (round(S["hits"] / n * 100) if n else None),
          "avg_aligned_return": (round(S["sum_fwd"] / n * 100, 1) if n else None),
          "open": open_calls, "by_action": by, "horizon_days": HORIZON_DAYS}
    return {"top": top, "scorecard": sc, "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# --- end of top_calls.py ---
