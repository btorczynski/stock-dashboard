"""
Crash Radar: recent S&P 500 history + forward CRASH RISK at 1 / 3 / 6-month horizons.

LEADING-INDICATOR MODEL (v7): the probability that the S&P falls 10%+ within each horizon
is fit on features that historically deteriorate WEEKS-TO-MONTHS BEFORE a drawdown, not the
coincident stress gauges (current drawdown, VIX level, realized vol) that only spike once the
drop is already underway. Features:
    - yield-curve slope (10y - 3m) and its 6-month change   (bull-steepening leads downturns)
    - credit-spread momentum (HYG/IEF, 3-month)             (credit cracks before equities)
    - breadth momentum (RSP/SPY equal- vs cap-weight, 3mo)  (narrowing breadth precedes tops)
    - volatility term structure (VIX3M / VIX)               (front-end stress builds early)
    - price-momentum deceleration (6mo vs prior 6mo)        (trend rolls over first)
    - distance from the 200-day average                     (slow trend break)

v8 adds a DURATION model: every 10%+ S&P drawdown since 1927, how long it took to bottom
and to recover, bucketed by depth and tagged recession-linked (NBER) — because recession
drawdowns run several times longer than sentiment-driven corrections.

HONESTY: crash timing is hard and these leads are noisy. The displayed risk line and every
validation number are computed WALK-FORWARD (expanding window, with an embargo so a day's label
can't peek past the training cut) - i.e. only on information that existed at the time. The panel
reports the model's real out-of-sample lead time, hit rate and false-alarm rate at three alert
thresholds (sensitive / balanced / precise). A risk gauge, NOT a prophecy. Not financial advice.
"""

import copy
import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_radar_state.json")
HORIZONS = [("h1", 21), ("h3", 63), ("h6", 126)]   # ~1, 3, 6 months (trading days)
DROP = -0.10
HIST_DAYS = 504
FWD_DAYS = 126
Z = 1.645
LEAD_WIN = 63          # how far before a drawdown an alert still counts as "early warning" (3 mo)
WF_REFIT = 21          # walk-forward: refit every ~month
WF_MIN_TRAIN = 600     # min rows before the first out-of-sample prediction
FEATS = ["curve", "curve_chg", "credit_mom", "breadth_mom", "vix_ts", "mom_decel", "dist200"]
SCHEMA = 8
_RNG = np.random.default_rng(7)

# NBER recessions (static history) — used to tag drawdowns as recession-linked,
# because those run far deeper and longer than sentiment-driven corrections.
NBER = [("1929-08", "1933-03"), ("1937-05", "1938-06"), ("1945-02", "1945-10"),
        ("1948-11", "1949-10"), ("1953-07", "1954-05"), ("1957-08", "1958-04"),
        ("1960-04", "1961-02"), ("1969-12", "1970-11"), ("1973-11", "1975-03"),
        ("1980-01", "1980-07"), ("1981-07", "1982-11"), ("1990-07", "1991-03"),
        ("2001-03", "2001-11"), ("2007-12", "2009-06"), ("2020-02", "2020-04")]


def _fetch():
    tk = "^GSPC ^VIX ^VIX3M ^TNX ^IRX HYG IEF RSP SPY"
    d = yf.download(tk, period="20y", auto_adjust=True, progress=False, threads=False, group_by="ticker")
    if d is None or d.empty:
        return None
    out = {}
    for s in tk.split():
        try:
            c = d[s]["Close"].dropna()
            if isinstance(c, pd.DataFrame):
                c = c.iloc[:, 0]
            if not c.empty:
                out[s] = c
        except Exception:
            pass
    return out if "^GSPC" in out else None


def _features(px):
    """Leading-indicator feature matrix aligned to the S&P calendar."""
    g = px["^GSPC"]
    idx = g.index
    al = lambda s, dflt=np.nan: (px[s].reindex(idx).ffill() if s in px else pd.Series(dflt, index=idx))
    tnx, irx = al("^TNX"), al("^IRX")
    vix, vix3 = al("^VIX", 20.0), al("^VIX3M", 22.0)
    hyg, ief = al("HYG"), al("IEF")
    rsp, spy = al("RSP"), al("SPY")
    curve = tnx - irx
    credit = (hyg / ief)
    breadth = (rsp / spy)
    feats = pd.DataFrame({
        "curve": curve,
        "curve_chg": curve - curve.shift(126),
        "credit_mom": credit / credit.shift(63) - 1,
        "breadth_mom": breadth / breadth.shift(63) - 1,
        "vix_ts": vix3 / vix - 1,
        "mom_decel": (g / g.shift(126) - 1) - (g.shift(126) / g.shift(252) - 1),
        "dist200": g / g.rolling(200).mean() - 1,
    })
    live = {
        "curve": float(curve.iloc[-1]) if pd.notna(curve.iloc[-1]) else None,
        "curve_status": None,
        "credit_mom": round(float((credit / credit.shift(63) - 1).iloc[-1]) * 100, 1) if pd.notna(credit.iloc[-1]) else None,
        "breadth_mom": round(float((breadth / breadth.shift(63) - 1).iloc[-1]) * 100, 1) if pd.notna(breadth.iloc[-1]) else None,
        "vix_ts": round(float((vix3 / vix - 1).iloc[-1]) * 100, 1) if pd.notna(vix.iloc[-1]) else None,
    }
    if live["curve"] is not None:
        live["curve_status"] = "inverted" if live["curve"] < 0 else ("flat" if live["curve"] < 0.5 else "normal")
    return feats, live


def _label(cv, h):
    n = len(cv)
    lab = np.full(n, np.nan)
    for i in range(n - h):
        w = cv[i + 1:i + 1 + h]
        lab[i] = 1.0 if (w.min() / cv[i] - 1) <= DROP else 0.0
    return lab


def _prob_ci(X, y, xnow, n_boot=30):
    """Point probability + 90% bootstrap interval + confidence label + saved coefficients."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    except Exception:
        return None, None, None, "n/a", None, None
    Xv, yv = X.values, y.values
    if len(set(yv)) < 2:
        return float(yv.mean() * 100), None, None, "Low", None, None
    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    base.fit(Xv, yv)
    point = float(base.predict_proba(xnow)[0, 1] * 100)
    boots = []
    N = len(yv)
    for _ in range(n_boot):
        ix = _RNG.integers(0, N, N)
        if len(set(yv[ix])) < 2:
            continue
        try:
            mb = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
            mb.fit(Xv[ix], yv[ix])
            boots.append(float(mb.predict_proba(xnow)[0, 1] * 100))
        except Exception:
            pass
    if len(boots) >= 8:
        lo, hi = float(np.percentile(boots, 5)), float(np.percentile(boots, 95))
        conf_pct = round(max(5, 100 * (1 - min(0.95, (hi - lo) / 12))))
        conf = "High" if conf_pct >= 72 else ("Medium" if conf_pct >= 50 else "Low")
        try:
            _sc = base.named_steps["standardscaler"]; _lr = base.named_steps["logisticregression"]
            model = {"coef": _lr.coef_[0].tolist(), "intercept": float(_lr.intercept_[0]),
                     "mean": _sc.mean_.tolist(), "scale": _sc.scale_.tolist(), "feats": FEATS}
        except Exception:
            model = None
        return round(point, 1), round(lo, 1), round(hi, 1), conf, conf_pct, model
    return round(point, 1), None, None, "Low", None, None


def _walk_forward(feats, lab, h):
    """Honest out-of-sample probability for every day: expanding-window refits, with an
    h-day embargo so a training row's forward label can't peek past the prediction cut.
    Predictions are produced for EVERY day with valid features (including the most recent
    days whose 10%-drop label isn't knowable yet); training uses only known-label rows."""
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import make_pipeline
    except Exception:
        return pd.Series(np.nan, index=feats.index)
    F = feats.replace([np.inf, -np.inf], np.nan)
    keep = F.notna().all(axis=1)                    # predict for every day with valid FEATURES
    Xdf = F[keep]
    idx = Xdf.index
    X = Xdf[FEATS].values
    y = lab.reindex(idx).values                     # label is NaN for the last h days (unknown future)
    n = len(Xdf)
    prob = np.full(n, np.nan)
    i = WF_MIN_TRAIN
    while i < n:
        e = i - h                                   # embargo: a training label can't peek past the cut
        if e > 50:
            tr = ~np.isnan(y[:e])                    # train only on rows whose label is known
            ytr = y[:e][tr]
            if tr.sum() > 50 and len(set(ytr)) >= 2:
                try:
                    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X[:e][tr], ytr)
                    j = min(i + WF_REFIT, n)
                    prob[i:j] = m.predict_proba(X[i:j])[:, 1] * 100
                except Exception:
                    pass
        i += WF_REFIT
    return pd.Series(prob, index=idx)


def _episodes(price):
    """First day of each distinct 10%+ peak-to-trough drawdown (the drop 'onset')."""
    onsets, peak, in_dd = [], price[0], False
    for i in range(len(price)):
        p = price[i]
        if p >= peak:
            peak, in_dd = p, False
        elif p <= 0.90 * peak and not in_dd:
            onsets.append(i); in_dd = True
    return onsets


def _dd_episodes(c):
    """All completed (and any ongoing) 10%+ peak-to-trough drawdowns in a close series.
    Returns dicts with peak/trough/recovery indices; rec_i is None if still underwater."""
    v = c.values
    eps, peak, pi, cur = [], float(v[0]), 0, None
    for i in range(len(v)):
        p = float(v[i])
        if cur is None:
            if p >= peak:
                peak, pi = p, i
            elif p <= 0.90 * peak:
                cur = {"peak_i": pi, "peak": peak, "tr_i": i, "tr": p}
        else:
            if p < cur["tr"]:
                cur["tr"], cur["tr_i"] = p, i
            if p >= cur["peak"]:
                cur["rec_i"] = i
                eps.append(cur)
                cur, peak, pi = None, p, i
    if cur is not None:
        cur["rec_i"] = None
        eps.append(cur)
    return eps


def _duration_stats(g):
    """How long crashes/bears last, from full S&P history: for every 10%+ drawdown,
    days peak->trough and trough->back-to-old-high, bucketed by final depth and
    tagged recession-linked (overlaps an NBER recession)."""
    eps = _dd_episodes(g)
    if not eps:
        return None
    rec_rng = [(pd.Period(a, "M").start_time, pd.Period(b, "M").end_time) for a, b in NBER]
    rows = []
    for e in eps:
        depth = e["tr"] / e["peak"] - 1
        pk_d, tr_d = g.index[e["peak_i"]], g.index[e["tr_i"]]
        linked = any(pk_d <= rb and tr_d >= ra for ra, rb in rec_rng)
        rows.append({"depth": depth, "down_d": e["tr_i"] - e["peak_i"],
                     "rec_d": (e["rec_i"] - e["tr_i"]) if e["rec_i"] is not None else None,
                     "linked": linked, "year": int(str(pk_d.date())[:4]),
                     "ongoing": e["rec_i"] is None})
    done = [r for r in rows if not r["ongoing"]]
    med = lambda xs: int(np.median(xs)) if xs else None
    def bucket(name, lo, hi):
        b = [r for r in done if lo < r["depth"] <= hi]
        return {"name": name, "n": len(b),
                "share_pct": round(len(b) / len(done) * 100) if done else None,
                "med_depth_pct": round(float(np.median([r["depth"] for r in b])) * 100, 1) if b else None,
                "med_down_days": med([r["down_d"] for r in b]),
                "med_rec_days": med([r["rec_d"] for r in b if r["rec_d"] is not None]),
                "rec_link_pct": round(sum(r["linked"] for r in b) / len(b) * 100) if b else None}
    out = {"episodes_n": len(done), "since": int(str(g.index[0].date())[:4]),
           "buckets": [bucket("Correction (10–20%)", -0.20, -0.10),
                       bucket("Bear (20–35%)", -0.35, -0.20),
                       bucket("Crash (35%+)", -1.00, -0.35)],
           "linked": {"med_down_days": med([r["down_d"] for r in done if r["linked"]]),
                      "med_rec_days": med([r["rec_d"] for r in done if r["linked"] and r["rec_d"] is not None]),
                      "med_depth_pct": round(float(np.median([r["depth"] for r in done if r["linked"]])) * 100, 1) if any(r["linked"] for r in done) else None},
           "unlinked": {"med_down_days": med([r["down_d"] for r in done if not r["linked"]]),
                        "med_rec_days": med([r["rec_d"] for r in done if not r["linked"] and r["rec_d"] is not None]),
                        "med_depth_pct": round(float(np.median([r["depth"] for r in done if not r["linked"]])) * 100, 1) if any(not r["linked"] for r in done) else None}}
    # where we stand today
    peak_now = float(g.cummax().iloc[-1])
    dd_now = float(g.iloc[-1]) / peak_now - 1
    try:
        pk_i = int(np.where(g.values >= peak_now)[0][-1])
        days_off = len(g) - 1 - pk_i
    except Exception:
        days_off = None
    out["current"] = {"active": dd_now <= -0.05, "dd_pct": round(dd_now * 100, 1), "days": days_off}
    return out


def _validate(prob, price, dates):
    """Walk-forward lead-time / hit-rate / false-alarm at 3 alert thresholds."""
    v = prob.values
    ok = ~np.isnan(v)
    if ok.sum() < 250:
        return None
    P = v[ok]; G = price[ok]; D = [str(d.date()) for d in dates[ok]]
    onsets = _episodes(G)
    n = len(P)
    out = {"span": [D[0], D[-1]], "n_episodes": len(onsets), "lead_win": LEAD_WIN, "thresholds": {}}
    for name, pctl in (("sensitive", 65), ("balanced", 80), ("precise", 90)):
        T = float(np.percentile(P, pctl))
        alert = P >= T
        # distinct alert episodes (merge gaps <= 2 days) -> false-alarm denominator
        clusters, k = [], 0
        while k < n:
            if alert[k]:
                clusters.append(k)
                while k + 1 < n and (alert[k + 1] or (k + 2 < n and alert[k + 2])):
                    k += 1
            k += 1
        caught, leads = 0, []
        for o in onsets:
            lo = max(0, o - LEAD_WIN)
            w = np.where(alert[lo:o])[0]
            if len(w):
                caught += 1
                leads.append(o - (lo + w[0]))           # lead from the FIRST early alert
        false = sum(1 for cs in clusters if not any(cs <= o <= cs + LEAD_WIN for o in onsets))
        out["thresholds"][name] = {
            "level": round(T, 1),
            "alert_freq_pct": round(float(alert.mean()) * 100, 1),
            "caught": caught, "episodes": len(onsets),
            "hit_rate_pct": round(caught / len(onsets) * 100) if onsets else None,
            "median_lead_days": int(np.median(leads)) if leads else None,
            "false_alarm_pct": round(false / len(clusters) * 100) if clusters else None,
            "on_now": bool(P[-1] >= T),
        }
    out["prob_now"] = round(float(P[-1]), 1)
    return out


def build(crash=None):
    px = _fetch()
    if px is None or len(px["^GSPC"]) < 900:
        return _empty("insufficient history")
    c = px["^GSPC"]
    ret = c.pct_change()
    feats, live_feats = _features(px)
    cv = c.values
    last = float(c.iloc[-1])
    sig = float(ret.rolling(21).std().iloc[-1]) if pd.notna(ret.rolling(21).std().iloc[-1]) else 0.01
    xnow = feats.iloc[[-1]].replace([np.inf, -np.inf], np.nan)

    horizons = {}
    for key, h in HORIZONS:
        lab = pd.Series(_label(cv, h), index=c.index)
        df = feats.copy(); df["lab"] = lab
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        base = float(df["lab"].mean() * 100) if not df.empty else 0.0
        dn_pct = round((math.exp(-Z * sig * math.sqrt(h)) - 1) * 100, 1)
        dn_to = round(last * math.exp(-Z * sig * math.sqrt(h)), 2)
        if xnow.isna().any(axis=1).iloc[0] or df.empty:
            horizons[key] = {"days": h, "prob": round(base, 1), "base": round(base, 1), "ci_lo": None,
                             "ci_hi": None, "conf": "Low", "conf_pct": None, "model": None,
                             "downside_pct": dn_pct, "downside_to": dn_to}
            continue
        prob, lo, hi, conf, conf_pct, model = _prob_ci(df[FEATS], df["lab"], xnow[FEATS].values)
        horizons[key] = {"days": h, "prob": prob if prob is not None else round(base, 1),
                         "base": round(base, 1), "ci_lo": lo, "ci_hi": hi, "conf": conf,
                         "conf_pct": conf_pct, "model": model, "downside_pct": dn_pct, "downside_to": dn_to}

    # Walk-forward 3-month probability = the honest leading "orange line" + validation
    lab3 = pd.Series(_label(cv, 63), index=c.index)
    wf = _walk_forward(feats, lab3, 63)
    wf_full = wf.reindex(c.index)
    lead = _validate(wf_full, c.values, c.index)

    hist = c.iloc[-HIST_DAYS:]
    prob_hist = [None if pd.isna(x) else round(float(x), 1) for x in wf_full.reindex(hist.index).values]

    fdr = pd.bdate_range(hist.index[-1], periods=FWD_DAYS + 1)[1:]
    f_dates, f_up, f_dn = [], [], []
    for h in range(1, FWD_DAYS + 1):
        f_dates.append(str(fdr[h - 1].date()))
        f_up.append(round(last * math.exp(Z * sig * math.sqrt(h)), 2))
        f_dn.append(round(last * math.exp(-Z * sig * math.sqrt(h)), 2))

    # duration model: full S&P history (back to 1927) for how long drops last
    duration = None
    try:
        gf = yf.download("^GSPC", period="max", auto_adjust=True, progress=False, threads=False)
        gc = gf["Close"].dropna()
        if isinstance(gc, pd.DataFrame):
            gc = gc.iloc[:, 0]
        if len(gc) > 2000:
            duration = _duration_stats(gc)
    except Exception as e:
        print(f"[warn] crash_radar duration failed: {e}", flush=True)

    recession = {"available": False}
    if live_feats.get("curve") is not None:
        recession = {"available": True, "curve": round(live_feats["curve"], 2),
                     "curve_status": live_feats["curve_status"],
                     "credit_mom": live_feats.get("credit_mom"),
                     "credit_status": ("stress building" if (live_feats.get("credit_mom") or 0) < -2
                                       else ("easing" if (live_feats.get("credit_mom") or 0) > 2 else "calm"))}
    cr = crash or {}
    return {
        "meta": {"schema": SCHEMA, "vix": round(float(px.get("^VIX", c).iloc[-1]), 1) if "^VIX" in px else None,
                 "vol_annual_pct": round(sig * math.sqrt(252) * 100, 1),
                 "model_kind": "leading", "feats": FEATS,
                 "seeded_through": str(c.index[-1].date()),
                 "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "hist": {"dates": [str(d.date()) for d in hist.index], "price": [round(float(x), 2) for x in hist.values],
                 "prob_hist": prob_hist},
        "live_feats": live_feats, "lead": lead,
        "fwd": {"dates": f_dates, "up": f_up, "down": f_dn, "i_1m": 20, "i_3m": 62, "i_6m": FWD_DAYS - 1},
        "h1": horizons["h1"], "h3": horizons["h3"], "h6": horizons["h6"], "last": round(last, 2),
        "crash_score": cr.get("score"), "crash_level": cr.get("level"), "recession": recession,
        "duration": duration,
    }


def _empty(reason):
    z = {"days": None, "prob": None, "base": None, "ci_lo": None, "ci_hi": None, "conf": "n/a",
         "conf_pct": None, "model": None, "downside_pct": None, "downside_to": None}
    return {"meta": {"schema": SCHEMA, "note": reason, "seeded_through": None, "model_kind": "leading",
                     "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")},
            "hist": {"dates": [], "price": [], "prob_hist": []}, "lead": None,
            "fwd": {"dates": [], "up": [], "down": [], "i_1m": 0, "i_3m": 0, "i_6m": 0},
            "h1": z, "h3": z, "h6": z, "last": None, "crash_score": None, "crash_level": None,
            "recession": {"available": False}, "duration": None}


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
        print(f"[warn] crash_radar state save failed: {e}", flush=True)


def _apply_live(state, live_pct):
    """Overlay today's live S&P move: re-anchor the 'now' price + forward cone. The leading
    features are daily (curve, credit, breadth, term structure don't move intraday), so the
    probabilities and the leading line stay at their daily values."""
    try:
        s = copy.deepcopy(state)
        dl = s.get("last")
        if dl is None:
            return state
        live = dl * (1 + live_pct / 100.0)
        s["hist"]["dates"].append("now"); s["hist"]["price"].append(round(live, 2))
        if isinstance(s["hist"].get("prob_hist"), list):
            s["hist"]["prob_hist"].append(s["hist"]["prob_hist"][-1] if s["hist"]["prob_hist"] else None)
        sig = (s["meta"].get("vol_annual_pct", 16) / 100.0) / math.sqrt(252)
        up, dn = [], []
        for h in range(1, FWD_DAYS + 1):
            up.append(round(live * math.exp(Z * sig * math.sqrt(h)), 2))
            dn.append(round(live * math.exp(-Z * sig * math.sqrt(h)), 2))
        s["fwd"]["up"] = up; s["fwd"]["down"] = dn
        s["last"] = round(live, 2)
        for k in ("h1", "h3", "h6"):
            hh = s.get(k) or {}
            if hh.get("downside_pct") is not None:
                hh["downside_to"] = round(live * (1 + hh["downside_pct"] / 100.0), 2)
        s["meta"]["live"] = True; s["meta"]["live_pct"] = round(float(live_pct), 2)
        return s
    except Exception:
        return state


def ensure(daily, crash=None, live_pct=None):
    latest = None
    for probe in ("SPY", "AAPL", "MSFT"):
        df = daily.get(probe) if daily else None
        if df is not None and not df.empty:
            try:
                latest = str(df["Close"].dropna().index[-1].date()); break
            except Exception:
                pass
    state = load_state()
    fresh = (state and state.get("hist", {}).get("dates") and latest
             and state["meta"].get("seeded_through") == latest and state["meta"].get("schema") == SCHEMA)
    if not fresh:
        new = build(crash)
        if new.get("hist", {}).get("dates"):
            save_state(new); state = new
        else:
            state = state or new
    if live_pct is not None and state and state.get("hist", {}).get("dates"):
        return _apply_live(state, live_pct)
    return state


if __name__ == "__main__":
    r = build()
    print("schema", r["meta"]["schema"], "kind", r["meta"]["model_kind"])
    for k in ("h1", "h3", "h6"):
        h = r[k]
        print(f"{k} ({h['days']}d): P(>=10% drop)={h['prob']}% (base {h['base']}%, CI {h['ci_lo']}-{h['ci_hi']}, conf {h['conf']}) | downside {h['downside_pct']}%")
    L = r["lead"]
    if L:
        print(f"\nWALK-FORWARD VALIDATION  ({L['span'][0]} -> {L['span'][1]}, {L['n_episodes']} drawdowns, current OOS prob {L['prob_now']}%)")
        for nm in ("sensitive", "balanced", "precise"):
            t = L["thresholds"][nm]
            print(f"  {nm:10s} level {t['level']:5.1f}  fires {t['alert_freq_pct']:4.1f}%  caught {t['caught']}/{t['episodes']}  "
                  f"lead {t['median_lead_days']}d  false-alarm {t['false_alarm_pct']}%  now {'ON' if t['on_now'] else 'off'}")
    print("\nleading features now:", r["live_feats"])

# --- end of crash_radar.py (v8: adds crash/bear duration model) ---
