"""
Resilient Yahoo/yfinance downloads.

Yahoo frequently answers shared/CI IPs (e.g. GitHub Actions runners) with HTTP 429
rate-limit errors or an empty frame. When that happens mid-build, the static snapshot
comes out empty and the publish step is (correctly) skipped — so the dashboard silently
stops refreshing until a later run happens to get through.

`install()` wraps `yfinance.download` with bounded exponential backoff + jitter, retrying
when the call raises OR returns an empty frame. It patches the shared yfinance module
object, so every caller that does `import yfinance as yf; yf.download(...)` is covered
automatically — no per-module edits needed. Idempotent and dependency-free.

Usage (once, before any download happens):
    import yf_retry; yf_retry.install()
"""

import random
import time

try:
    import pandas as pd
except Exception:  # pandas should always be present, but never crash the wrapper
    pd = None


def install(retries=5, base=2.0, cap=30.0, verbose=True):
    """Monkeypatch yfinance.download with retry/backoff. Returns the wrapper (or the
    existing one if already installed). Safe to call more than once."""
    try:
        import yfinance as yf
    except Exception as e:  # yfinance missing -> nothing to wrap
        if verbose:
            print(f"[yf_retry] yfinance not importable: {e}", flush=True)
        return None

    orig = getattr(yf, "download", None)
    if orig is None or getattr(orig, "_retry_wrapped", False):
        return orig  # nothing to do / already wrapped

    def download(*args, **kwargs):
        last_desc = "unknown error"
        result = None
        for attempt in range(retries):
            try:
                result = orig(*args, **kwargs)
                if result is not None and len(result) > 0:
                    return result
                last_desc = "empty result"
            except Exception as e:  # network error, 429, JSON decode, etc.
                result = None
                last_desc = repr(e)
            if attempt < retries - 1:
                delay = min(cap, base * (2 ** attempt)) + random.uniform(0, 1.0)
                if verbose:
                    print(f"[yf_retry] {last_desc}; retry {attempt + 1}/"
                          f"{retries - 1} in {delay:.1f}s", flush=True)
                time.sleep(delay)
        if verbose:
            print(f"[yf_retry] exhausted {retries} attempts ({last_desc})", flush=True)
        # Hand back the last result (possibly empty) so callers hit their normal
        # empty-frame handling instead of a hard crash.
        if result is not None:
            return result
        return pd.DataFrame() if pd is not None else None

    download._retry_wrapped = True
    yf.download = download
    if verbose:
        print(f"[yf_retry] installed (retries={retries}, base={base}s)", flush=True)
    return download
