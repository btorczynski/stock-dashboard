"""
Build a STATIC snapshot of the dashboard for free, permanent-URL hosting
(Cloudflare Pages / GitHub Pages).

The live app is a Flask server whose page polls /api/data. Serverless/static hosts
can't run that server, so instead we run the exact same data build ONCE here, dump it
to public/data.json, and emit a public/index.html that is the real dashboard UI with
its data source repointed from the live endpoint to that static file.

A scheduled GitHub Action runs this every few minutes during market hours and publishes
public/ to Cloudflare Pages — so the link never changes and the data stays fresh, free.

Run locally:  python build_snapshot_static.py     (writes ./public/)
"""

import json
import os
import sys
import time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")


def _write(path, text, binary=False):
    mode = "wb" if binary else "w"
    with open(path, mode) as f:
        f.write(text)


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    # Import here so a failure prints a clear message in the Action log.
    import stock_dashboard as sd
    from dashboard_ui import INDEX_HTML

    # 1) Build the snapshot — identical payload to what /api/data serves live.
    print("building snapshot (fetching quotes + running backtests)…", flush=True)
    data = sd.build_snapshot()
    data["_static"] = {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "build_seconds": round(time.time() - t0, 1)}
    payload = json.dumps(data, separators=(",", ":"))
    _write(os.path.join(OUT, "data.json"), payload)

    # 2) Static page = the real UI, with its data source repointed and the
    #    server-only refresh call turned into a plain re-fetch of the file.
    html = INDEX_HTML.replace("/api/data", "./data.json")
    html = html.replace("await fetch('/api/refresh',{method:'POST'});",
                        "await fetch('./data.json',{cache:'no-store'});")
    _write(os.path.join(OUT, "index.html"), html)

    # 3) Tell Cloudflare Pages never to edge-cache the data file, so a new
    #    deploy is visible immediately (the HTML/JS can cache normally).
    _write(os.path.join(OUT, "_headers"),
           "/data.json\n  Cache-Control: no-cache, no-store, must-revalidate\n")

    kb = len(payload) / 1024
    keys = [k for k in data.keys() if not k.startswith("_")]
    print(f"OK  public/data.json {kb:,.0f} KB · {len(keys)} sections · "
          f"updated {data.get('updated_at_str','?')} · built in {data['_static']['build_seconds']}s", flush=True)
    print("    sections:", ", ".join(keys), flush=True)
    # Fail the build (non-zero exit) if the snapshot is obviously empty, so the
    # Action doesn't publish a broken page over a good one.
    if not data.get("watchlist") and not data.get("sectors"):
        print("ERROR: snapshot looks empty (no watchlist/sectors) — not publishing.", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
