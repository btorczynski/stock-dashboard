"""
One-shot end-to-end check. Run this in the project folder:

    python selfcheck.py

It imports the app, builds one full snapshot (pulls live data — can take 30-90s the
first time), and reports whether every panel populated, plus any error. Paste the output
back if something says EMPTY or ERROR and it can be fixed quickly.
"""
import time, traceback


def main():
    t0 = time.time()
    try:
        import stock_dashboard as s
    except Exception:
        print("IMPORT FAILED:\n"); traceback.print_exc(); return
    print("import OK — building snapshot (fetching live data, please wait)...")
    try:
        snap = s.build_snapshot()
    except Exception:
        print("build_snapshot FAILED:\n"); traceback.print_exc(); return
    print(f"BUILD OK in {time.time()-t0:.0f}s\n")
    checks = ["top_calls", "sectors", "movers", "watchlist", "picks", "sim", "voo_sim",
              "momentum_sim", "momentum_basket", "penny_hold", "insiders", "crash_risk", "macro"]
    for k in checks:
        v = snap.get(k)
        if isinstance(v, dict):
            status = ("ok (" + str(len(v)) + " keys)") if v else "EMPTY"
        elif isinstance(v, list):
            status = (str(len(v)) + " items") if v else "EMPTY"
        else:
            status = "present" if v is not None else "MISSING"
        print(f"  {k:16s}: {status}")
    tc = snap.get("top_calls", {}) or {}
    print("\n  Top calls:", [(t.get("symbol"), t.get("action"), str(t.get("confidence")) + "%") for t in tc.get("top", [])])
    sc = tc.get("scorecard", {}) or {}
    print("  Scorecard:", "graded", sc.get("graded"), "| open", sc.get("open"), "| hit_rate", sc.get("hit_rate"))
    wl = snap.get("watchlist", []) or []
    print("  Drift tags:", [(w.get("ticker"), (w.get("drift") or {}).get("tag")) for w in wl if w.get("drift")][:8])
    for name in ("momentum_sim", "momentum_basket", "penny_hold"):
        st = (snap.get(name) or {}).get("stats", {})
        if st:
            print(f"  {name}: value={st.get('value')} CAGR={st.get('cagr_pct')}% vsSPY={st.get('benchmark_cagr_pct')}%")
    print("\nIf everything above is non-EMPTY, the dashboard is healthy. Run run_dashboard.bat to view it.")


if __name__ == "__main__":
    main()
