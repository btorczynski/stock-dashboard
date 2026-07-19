#!/usr/bin/env python3
"""
After-close market summary. Run once a day (the scheduled task uses this):

    python daily_summary.py

It pulls fresh data, prints a concise summary (macro regime, top-5 buy signals,
notable watchlist calls, and the strategy simulator's latest result), and writes
daily_summary.md. Running it also advances the simulator by one day.

NOT financial advice — mechanical, rules-based signals only.
"""

import os
from datetime import datetime


def format_summary(snap):
    L = []
    L.append(f"# Market Summary — {snap['updated_at_str']}")
    L.append(f"_Session: {snap['session']['label']}_\n")

    mc = snap.get("macro", {})
    L.append(f"**Macro backdrop: {mc.get('label','?')}** (bias {mc.get('bias',0):+.2f}) — "
             f"10Y {mc.get('tnx','?')}%, VIX {mc.get('vix','?')}, "
             f"CAPE {mc.get('cape','?')} (vs {mc.get('cape_mean','?')} avg), CPI {mc.get('cpi','?')}%.")
    if mc.get("drivers"):
        L.append("Drivers: " + "; ".join(mc["drivers"]) + ".\n")

    cr = snap.get("crash_risk") or {}
    if cr.get("score") is not None:
        L.append(f"\n**Crash-risk gauge: {cr['level']} — {cr['score']}/100.** "
                 f"Flags: {', '.join(cr.get('drivers', [])) or 'none at High'}.")
        L.append(f"{cr.get('scale_note', '')}")
        L.append(f"_{cr.get('timing_note', '')}_")

    sh = snap.get("sector_health") or {}
    warn = [v for v in sh.values() if v.get("status") not in (None, "ok", "pullback")]
    if warn:
        L.append("\n**Sector crash watch:** "
                 + " · ".join(f"{v['name']} {v['off_high_pct']}% off high ({v['status']})" for v in warn))

    L.append("\n## Top 5 buy signals")
    if snap.get("picks"):
        for i, p in enumerate(snap["picks"], 1):
            L.append(f"{i}. **{p['symbol']}** ({p['sector'] or '—'}) — {p['action']} {p['strength']}% · "
                     f"${p['price']} · 1mo {p['mom1m']:+}% · RSI {p['rsi']}")
    else:
        L.append("_No candidates available._")

    buys = [w for w in snap.get("watchlist", []) if w["signal"].get("action") == "BUY"]
    sells = [w for w in snap.get("watchlist", []) if w["signal"].get("action") == "SELL"]

    def fmt(w):
        return f"{w['label']} ({w['ticker'] or w.get('proxy')}) {w['signal'].get('strength')}%"
    L.append("\n## Watchlist")
    L.append("**Buy-leaning:** " + (", ".join(fmt(w) for w in buys) or "none"))
    L.append("**Sell-leaning:** " + (", ".join(fmt(w) for w in sells) or "none"))

    sm = snap.get("sim", {})
    stats = sm.get("stats", {})
    if stats:
        L.append("\n## Strategy simulator (hold up-trend basket, rebalance at close)")
        L.append(f"Strategy {stats.get('total_return_pct')}% vs {sm.get('meta',{}).get('benchmark','SPY')} "
                 f"{stats.get('benchmark_return_pct')}% (alpha {stats.get('alpha_pct')}%) over "
                 f"{stats.get('days')} days · win rate {stats.get('win_rate_pct')}% · "
                 f"max drawdown {stats.get('max_drawdown_pct')}%.")
        if sm.get("trades"):
            t = sm["trades"][-1]
            L.append(f"Latest day {t['date']}: {t['n']} names, {t['ret_pct']:+}% — {', '.join(t.get('names', [])[:8])}")

    L.append("\n_Mechanical, rules-based signals — not financial advice. Past results don't predict the future._")
    return "\n".join(L)


def main():
    import stock_dashboard as sd
    print("Fetching data and computing summary (this can take ~20-40s)...", flush=True)
    snap = sd.build_snapshot()
    text = format_summary(snap)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_summary.md")
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception as e:
        print(f"[warn] could not write daily_summary.md: {e}", flush=True)
    print("\n" + text)


if __name__ == "__main__":
    main()

# --- end of daily_summary.py ---
