#!/usr/bin/env python3
"""
Real-time sector bubble map + macro/futures/event-aware buy/sell signals, top
movers, top picks, and a self-testing $5,000 open/close strategy simulator.

Data: Yahoo Finance via `yfinance` (free, no API key).
Run:  pip install -r requirements.txt  &&  python stock_dashboard.py
Then open http://localhost:8765.

NOT financial advice. Signals are mechanical, rules-based indicators from public
price data, futures, commodities and slow-moving macro/event inputs.
"""

import json
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, time as dtime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from flask import Flask, Response

import simulator as sim
import factors
import insider
import top_calls
import drift
import crash_radar
import watchlist_levels
import forever_hold

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
PORT = 8765
# Set DASH_HOST=0.0.0.0 to view from your phone / another device on the same Wi-Fi.
HOST = os.environ.get("DASH_HOST", "127.0.0.1")
ET = ZoneInfo("America/New_York")

PRICE_PCT_THRESHOLD = 3.0
RVOL_THRESHOLD = 2.0
REFRESH_OPEN = 60
REFRESH_CLOSED = 300

INTRA_INTERVAL = "1m"       # "2m"/"5m" are lighter if you ever get rate-limited
CHUNK_SIZE = 25
MAX_WORKERS = 4
RETRIES = 2

SECTORS = {
    "XLK":  {"name": "Technology",            "stocks": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "CSCO", "AMD"]},
    "XLF":  {"name": "Financials",            "stocks": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "SPGI"]},
    "XLV":  {"name": "Health Care",           "stocks": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE"]},
    "XLY":  {"name": "Consumer Discretionary", "stocks": ["AMZN", "TSLA", "HD", "MCD", "BKNG", "NKE", "LOW", "SBUX"]},
    "XLC":  {"name": "Communication Svcs",    "stocks": ["META", "GOOGL", "NFLX", "DIS", "TMUS", "VZ", "T", "CMCSA"]},
    "XLI":  {"name": "Industrials",           "stocks": ["GE", "CAT", "RTX", "UNP", "HON", "BA", "UPS", "DE"]},
    "XLP":  {"name": "Consumer Staples",      "stocks": ["COST", "WMT", "PG", "KO", "PEP", "PM", "MO", "MDLZ"]},
    "XLE":  {"name": "Energy",                "stocks": ["XOM", "CVX", "COP", "WMB", "SLB", "EOG", "MPC", "PSX"]},
    "XLB":  {"name": "Materials",             "stocks": ["LIN", "SHW", "FCX", "ECL", "APD", "NEM", "DOW", "NUE"]},
    "XLRE": {"name": "Real Estate",           "stocks": ["PLD", "AMT", "EQIX", "WELL", "SPG", "PSA", "O", "CCI"]},
    "XLU":  {"name": "Utilities",             "stocks": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "EXC"]},
}

HOLIDAY_NAMES = {
    # 2026 (NYSE)
    date(2026,1,1):"New Year's Day",date(2026,1,19):"MLK Jr. Day",date(2026,2,16):"Presidents' Day",
    date(2026,4,3):"Good Friday",date(2026,5,25):"Memorial Day",date(2026,6,19):"Juneteenth",
    date(2026,7,3):"Independence Day",date(2026,9,7):"Labor Day",date(2026,11,26):"Thanksgiving",date(2026,12,25):"Christmas",
    # 2027 (NYSE; observed dates — Juneteenth, July 4 and Christmas fall on weekends)
    date(2027,1,1):"New Year's Day",date(2027,1,18):"MLK Jr. Day",date(2027,2,15):"Presidents' Day",
    date(2027,3,26):"Good Friday",date(2027,5,31):"Memorial Day",date(2027,6,18):"Juneteenth (obs.)",
    date(2027,7,5):"Independence Day (obs.)",date(2027,9,6):"Labor Day",date(2027,11,25):"Thanksgiving",date(2027,12,24):"Christmas (obs.)",
}
MARKET_HOLIDAYS = set(HOLIDAY_NAMES)

ALL_SYMBOLS = list(SECTORS.keys()) + [s for v in SECTORS.values() for s in v["stocks"]]
STOCK_SECTOR = {s: v["name"] for v in SECTORS.values() for s in v["stocks"]}
EXTRA_SECTOR = {"IONQ": "Technology", "RDW": "Industrials", "PL": "Technology",
                "KEYS": "Technology", "PANW": "Technology", "MU": "Technology",
                "WDC": "Technology", "NOK": "Technology", "MDA.TO": "Industrials", "SPCX": "Industrials",
                "RKLB": "Industrials", "RGTI": "Technology", "KLAC": "Technology",
                "SNDK": "Technology", "STX": "Technology", "PLTR": "Technology",
                "AMZN": "Consumer Discretionary", "BE": "Industrials", "SNOW": "Technology"}


def sector_of(sym):
    return STOCK_SECTOR.get(sym) or EXTRA_SECTOR.get(sym, "")


WATCHLIST = [
    {"label": "Technology",        "ticker": "XLK",  "note": "Tech sector ETF"},
    {"label": "Semiconductors",    "ticker": "SMH",  "note": "VanEck Semiconductor ETF"},
    {"label": "Nuclear / Uranium", "ticker": "URA",  "note": "Global X Uranium ETF"},
    {"label": "Natural Gas",       "ticker": "UNG",  "note": "US Natural Gas Fund"},
    {"label": "Gold",              "ticker": "GLD",  "note": "SPDR Gold Shares"},
    {"label": "Silver",            "ticker": "SLV",  "note": "iShares Silver Trust"},
    {"label": "S&P 500 (VOO)",     "ticker": "VOO",  "note": "Vanguard S&P 500 ETF"},
    {"label": "Chevron",           "ticker": "CVX",  "note": "Integrated energy"},
    {"label": "Nvidia",            "ticker": "NVDA", "note": "Semiconductors / AI"},
    {"label": "UnitedHealth",      "ticker": "UNH",  "note": "Health insurance"},
    {"label": "IonQ",              "ticker": "IONQ", "note": "Quantum computing"},
    {"label": "Redwire",           "ticker": "RDW",  "note": "Space infrastructure"},
    {"label": "Planet Labs",       "ticker": "PL",   "note": "Earth-imaging satellites"},
    {"label": "MDA Space",         "ticker": "MDA.TO", "note": "Space robotics/satellites (TSX, CAD)"},
    {"label": "Rocket Lab",        "ticker": "RKLB", "note": "Small-launch / space systems"},
    {"label": "Tesla",             "ticker": "TSLA", "note": "EV / autonomy"},
    {"label": "Cisco",             "ticker": "CSCO", "note": "Networking"},
    {"label": "KLA Corp",          "ticker": "KLAC", "note": "Semiconductor equipment"},
    {"label": "Rigetti",           "ticker": "RGTI", "note": "Quantum computing"},
    {"label": "Semis ETF (SOXX)",  "ticker": "SOXX", "note": "iShares Semiconductor ETF"},
    {"label": "SanDisk",           "ticker": "SNDK", "note": "Flash memory (WDC spinoff)"},
    {"label": "Seagate",           "ticker": "STX",  "note": "Storage / HDD"},
    {"label": "Apple",             "ticker": "AAPL", "note": "Consumer tech"},
    {"label": "Palantir",          "ticker": "PLTR", "note": "Data analytics / AI"},
    {"label": "Exxon Mobil",       "ticker": "XOM",  "note": "Integrated oil & gas"},
    {"label": "Snowflake",         "ticker": "SNOW", "note": "Cloud data / AI platform"},
    {"label": "Amazon",            "ticker": "AMZN", "note": "E-commerce / cloud (AWS)"},
    {"label": "Bloom Energy",      "ticker": "BE",   "note": "Hydrogen fuel cells / clean power"},
    {"label": "Keysight",          "ticker": "KEYS", "note": "Electronic test & measurement"},
    {"label": "Palo Alto Networks", "ticker": "PANW", "note": "Cybersecurity (replaces Pawn)"},
    {"label": "Micron (memory)",    "ticker": "MU",   "note": "DRAM / NAND memory"},
    {"label": "Western Digital",    "ticker": "WDC",  "note": "Storage / memory"},
    {"label": "Nokia",              "ticker": "NOK",  "note": "Telecom / networks"},
    {"label": "SpaceX (SPCX)",     "ticker": "SPCX", "note": "IPO'd Jun 12 2026 (NASDAQ); previously private via DXYZ"},
]
WL_TICKERS = sorted({w["ticker"] for w in WATCHLIST if w["ticker"]} | {w["proxy"] for w in WATCHLIST if w.get("proxy")})

SIGNAL_BUY = 25
SIGNAL_SELL = -25
MACRO_WEIGHT = 20

PICKS_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AVGO", "AMD", "GOOGL", "META", "AMZN", "TSLA", "NFLX",
    "ORCL", "CRM", "JPM", "V", "MA", "BAC", "GS", "UNH", "LLY", "JNJ", "MRK", "ABBV",
    "XOM", "CVX", "COP", "CAT", "GE", "HON", "RTX", "COST", "WMT", "PG", "KO", "NEE",
    "KEYS", "RDW", "PL", "PANW", "MU", "WDC", "NOK", "IONQ",
]

MACRO_TICKERS = [("^TNX", "US 10Y Yield"), ("^VIX", "VIX"), ("DX-Y.NYB", "US Dollar")]
MACRO_CONSTANTS = {"cpi_yoy": 4.2, "core_cpi_yoy": 2.9, "shiller_cape": 41.0, "cape_mean": 17.4, "as_of": "May–Jun 2026"}

UNIVERSE = sorted(set(ALL_SYMBOLS) | set(WL_TICKERS) | set(PICKS_UNIVERSE) | {"VOO"})
PRE_OPEN, REG_OPEN, REG_CLOSE, POST_CLOSE = dtime(4,0), dtime(9,30), dtime(16,0), dtime(20,0)


# --------------------------------------------------------------------------
def market_session(now_et):
    d, t, wd = now_et.date(), now_et.time(), now_et.weekday()
    if wd >= 5: return {"state":"closed","label":"Weekend · Markets Closed","is_extended":False}
    if d in MARKET_HOLIDAYS: return {"state":"closed","label":f"Closed · {HOLIDAY_NAMES.get(d,'Holiday')}","is_extended":False}
    if PRE_OPEN <= t < REG_OPEN: return {"state":"pre","label":"Pre-Market","is_extended":True}
    if REG_OPEN <= t < REG_CLOSE: return {"state":"regular","label":"Regular Session · Open","is_extended":False}
    if REG_CLOSE <= t < POST_CLOSE: return {"state":"post","label":"After-Hours","is_extended":True}
    return {"state":"closed","label":"Overnight · Markets Closed","is_extended":False}


def _download_one(kind, group, daily_period="1mo"):
    kw = dict(period=daily_period, interval="1d", prepost=False) if kind == "daily" else dict(period="1d", interval=INTRA_INTERVAL, prepost=True)
    for attempt in range(RETRIES):
        try:
            data = yf.download(tickers=" ".join(group), group_by="ticker", auto_adjust=False, progress=False, threads=False, **kw)
            out = {}
            for sym in group:
                try:
                    df = data[sym].dropna(how="all")
                    if not df.empty: out[sym] = df
                except Exception: pass
            if out: return kind, out
        except Exception as e:
            if attempt == RETRIES - 1: print(f"[warn] {kind} {group[:2]} failed: {e}", flush=True)
        time.sleep(1.5 * (attempt + 1))
    return kind, {}


def fetch_all(symbols, daily_period="6mo"):
    groups = [symbols[i:i+CHUNK_SIZE] for i in range(0, len(symbols), CHUNK_SIZE)]
    tasks = [("daily", g) for g in groups] + [("intra", g) for g in groups]
    daily, intra = {}, {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for kind, res in ex.map(lambda t: _download_one(t[0], t[1], daily_period), tasks):
            (daily if kind == "daily" else intra).update(res)
    return daily, intra


def _to_et(df):
    idx = df.index
    if idx.tz is None: df = df.tz_localize("UTC")
    return df.tz_convert(ET)


def _safe_float(x):
    try:
        v = float(x); return None if math.isnan(v) else v
    except Exception: return None


def _clamp(x, lo, hi): return max(lo, min(hi, x))


def compute_metrics(intra, daily, now_et):
    m = {"price":None,"prev_close":None,"change_pct":None,"reg_change_pct":None,"ext_change_pct":None,
         "ext_kind":None,"rvol":None,"volume":0,"avg_volume":None,"unusual":False,"reasons":[],"score":0.0}
    prev_close = avg_volume = trading_date = None
    if intra is not None and not intra.empty:
        intra = _to_et(intra); trading_date = intra.index[-1].date()
    if daily is not None and not daily.empty:
        dd = daily.copy(); dd["d"] = [ts.date() for ts in dd.index]
        if trading_date is None: trading_date = dd["d"].iloc[-1]
        prior = dd[dd["d"] < trading_date]
        if not prior.empty:
            prev_close = _safe_float(prior["Close"].iloc[-1]); avg_volume = _safe_float(prior["Volume"].tail(20).mean())
        else:
            prev_close = _safe_float(dd["Close"].iloc[-1]); avg_volume = _safe_float(dd["Volume"].tail(20).mean())
    m["prev_close"] = prev_close; m["avg_volume"] = int(avg_volume) if avg_volume else None
    if intra is None or intra.empty or trading_date is None:
        if daily is not None and not daily.empty:
            m["price"] = _safe_float(daily["Close"].iloc[-1])
            if prev_close and m["price"]:
                m["reg_change_pct"] = (m["price"]-prev_close)/prev_close*100; m["change_pct"] = m["reg_change_pct"]
        return m
    day = intra[[ts.date()==trading_date for ts in intra.index]]; times=[ts.time() for ts in day.index]
    reg = day[[(REG_OPEN<=t<REG_CLOSE) for t in times]]; pre = day[[(PRE_OPEN<=t<REG_OPEN) for t in times]]; post = day[[(REG_CLOSE<=t<POST_CLOSE) for t in times]]
    lc = day["Close"].dropna(); m["price"] = _safe_float(lc.iloc[-1]) if not lc.empty else None
    reg_close = _safe_float(reg["Close"].dropna().iloc[-1]) if not reg["Close"].dropna().empty else None
    if reg_close is not None and prev_close: m["reg_change_pct"] = (reg_close-prev_close)/prev_close*100
    if not post["Close"].dropna().empty and reg_close is not None:
        ep=_safe_float(post["Close"].dropna().iloc[-1]); m["ext_kind"],m["ext_change_pct"]="post",(ep-reg_close)/reg_close*100
    elif not pre["Close"].dropna().empty and prev_close:
        ep=_safe_float(pre["Close"].dropna().iloc[-1]); m["ext_kind"],m["ext_change_pct"]="pre",(ep-prev_close)/prev_close*100
    if m["ext_change_pct"] is not None and m["price"] and prev_close:
        m["change_pct"]=(m["price"]-prev_close)/prev_close*100   # extended hours: live move vs prior close, keeps updating pre/post
    elif m["reg_change_pct"] is not None: m["change_pct"]=m["reg_change_pct"]
    elif m["ext_change_pct"] is not None: m["change_pct"]=m["ext_change_pct"]
    reg_volume = float(reg["Volume"].fillna(0).sum()) if not reg.empty else 0.0; m["volume"]=int(reg_volume)
    fraction=1.0; live_today=(now_et.date()==trading_date); sess=market_session(now_et)
    if live_today and sess["state"]=="regular":
        elapsed=(now_et-now_et.replace(hour=9,minute=30,second=0,microsecond=0)).total_seconds()/60.0; fraction=max(0.02,min(1.0,elapsed/390.0))
    elif live_today and sess["state"]=="pre": fraction=0.0
    if avg_volume and fraction>0: m["rvol"]=reg_volume/(avg_volume*fraction)
    reasons=[]; big=max(abs(m["change_pct"] or 0),abs(m["ext_change_pct"] or 0))
    if big>=PRICE_PCT_THRESHOLD: reasons.append("price")
    if m["rvol"] is not None and m["rvol"]>=RVOL_THRESHOLD and reg_volume>0: reasons.append("volume")
    m["reasons"],m["unusual"]=reasons,len(reasons)>0
    m["score"]=round(big+0.5*abs(m["ext_change_pct"] or 0)+1.5*max(0.0,(m["rvol"] or 0)-1.0),3)
    for k in ("price","prev_close","change_pct","reg_change_pct","ext_change_pct","rvol"):
        if isinstance(m[k],float): m[k]=round(m[k],4)
    return m


def _rsi(closes, period=14):
    delta=closes.diff(); up,down=delta.clip(lower=0),-delta.clip(upper=0)
    ru=up.ewm(alpha=1/period,adjust=False).mean(); rd=down.ewm(alpha=1/period,adjust=False).mean()
    return 100-100/(1+ru/rd.replace(0,1e-9))


def compute_macro(macro_daily):
    r={"as_of":MACRO_CONSTANTS["as_of"],"cpi":MACRO_CONSTANTS["cpi_yoy"],"core_cpi":MACRO_CONSTANTS["core_cpi_yoy"],
       "cape":MACRO_CONSTANTS["shiller_cape"],"cape_mean":MACRO_CONSTANTS["cape_mean"],"tnx":None,"tnx_trend":None,"vix":None,"dxy":None}
    def lt(sym):
        df=macro_daily.get(sym)
        if df is None or df.empty: return None,None
        c=df["Close"].dropna()
        if c.empty: return None,None
        lvl=float(c.iloc[-1]); sma=float(c.tail(50).mean()) if len(c)>=20 else lvl
        return lvl, lvl-sma
    tnx,tnx_tr=lt("^TNX")
    if tnx is not None and tnx>20: tnx,tnx_tr=tnx/10.0,(tnx_tr/10.0 if tnx_tr is not None else None)
    vix,_=lt("^VIX"); dxy,dxy_tr=lt("DX-Y.NYB")
    r["tnx"]=round(tnx,2) if tnx else None; r["tnx_trend"]=round(tnx_tr,3) if tnx_tr is not None else None
    r["vix"]=round(vix,1) if vix else None; r["dxy"]=round(dxy,2) if dxy else None
    infl_c=-_clamp((MACRO_CONSTANTS["cpi_yoy"]-2.5)/3.0,0,1)
    rate_c=-_clamp((tnx-3.5)/2.0,-0.3,1) if tnx else 0.0
    rate_tr_c=-_clamp((tnx_tr or 0)/0.5,-1,1)*0.5
    vix_c=_clamp((18-(vix or 18))/15.0,-1,0.3)
    cape_c=-_clamp((MACRO_CONSTANTS["shiller_cape"]-25)/20.0,0,1)
    bias=round(_clamp(0.25*infl_c+0.20*rate_c+0.15*rate_tr_c+0.20*vix_c+0.20*cape_c,-1,1),3); r["bias"]=bias
    r["label"]="Risk-Off" if bias<=-0.4 else "Cautious" if bias<=-0.1 else "Neutral" if bias<0.1 else "Risk-On"
    drivers=[]
    if cape_c<-0.3: drivers.append(f"Valuations stretched (CAPE {MACRO_CONSTANTS['shiller_cape']:.0f} vs {MACRO_CONSTANTS['cape_mean']:.0f} avg)")
    if infl_c<-0.2: drivers.append(f"Inflation elevated (CPI {MACRO_CONSTANTS['cpi_yoy']:.1f}% YoY)")
    if tnx and rate_c<-0.2: drivers.append(f"Yields high (10Y {tnx:.2f}%)")
    if (tnx_tr or 0)>0.1: drivers.append("Yields rising")
    if vix and vix>=22: drivers.append(f"Volatility high (VIX {vix:.0f})")
    elif vix and vix<15: drivers.append(f"Volatility low (VIX {vix:.0f})")
    r["drivers"]=drivers or ["Mixed / balanced conditions"]
    return r


def compute_signal(daily, intra_m, ext_bias=0.0, event_risk=0.0, sector_dd=None):
    """Buy/Sell/Hold signal v2 — crash-aware.

    On top of the original composite (trend, cross, momentum, RSI, today's move,
    macro bias), v2 folds in the industry-standard downside guards that the July
    2026 memory-stock crash exposed as missing:
      • 200-day trend filter (Faber): no BUY below the 200-day average — the single
        best-documented crash-avoidance rule in the literature.
      • 52-week-high drawdown (absolute momentum): a name 10-20% off its high is in
        a correction (penalty), 20%+ is in a bear market (hard penalty + BUY cap).
      • Fast-crash override: a −12%/10-day or −18%/21-day slide forces SELL even
        if slower averages haven't rolled over yet — this is what a 2-3 week sector
        rout looks like in real time.
      • Volatility-spike guard (vol targeting): 10-day vol ≥ 1.8× its 3-month norm
        damps bullish conviction.
      • Sector-crash overlay: if the name's sector/industry ETF is itself 15%+ off
        its high, members can't be BUYs and lose points (crashes cluster by sector).
      • The event dampener now shrinks only BULLISH conviction — it no longer pulls
        a crashing name back toward HOLD.
    """
    out={"action":"N/A","strength":0,"score":0,"rsi":None,"sma_state":None,"mom1m":None,"reasons":[],"note":None,
         "price":None,"change_pct":None,"ext_change_pct":None,"ext_kind":None,
         "off_high_pct":None,"vs200_pct":None,"crash_flag":None}
    rvol=None
    if intra_m:
        out.update({"price":intra_m.get("price"),"change_pct":intra_m.get("change_pct"),"ext_change_pct":intra_m.get("ext_change_pct"),"ext_kind":intra_m.get("ext_kind")}); rvol=intra_m.get("rvol")
    if daily is None or daily.empty: out["note"]="No data"; return out
    closes=daily["Close"].dropna()
    if closes.empty: out["note"]="No data"; return out
    price=out["price"] or _safe_float(closes.iloc[-1]); out["price"]=round(price,2) if price else None
    if out["change_pct"] is None and len(closes)>=2: out["change_pct"]=round((closes.iloc[-1]/closes.iloc[-2]-1)*100,2)
    sma20=float(closes.tail(20).mean()); sma50=float(closes.tail(50).mean()) if len(closes)>=50 else float(closes.mean())
    sma200=float(closes.tail(200).mean()) if len(closes)>=180 else None
    hi52=float(closes.tail(252).max())
    rsi=float(_rsi(closes).iloc[-1]) if len(closes)>15 else 50.0
    n=min(21,len(closes)-1); mom1m=(price/float(closes.iloc[-1-n])-1)*100 if n>0 and price else 0.0
    n10=min(10,len(closes)-1); ret10=(price/float(closes.iloc[-1-n10])-1)*100 if n10>0 and price else 0.0
    rets=closes.pct_change().dropna()
    vol10=float(rets.tail(10).std()) if len(rets)>=10 else None
    vol63=float(rets.tail(63).std()) if len(rets)>=40 else None
    off_high=(price/hi52-1)*100 if price and hi52 else 0.0
    out["rsi"],out["mom1m"]=round(rsi,1),round(mom1m,1); out["sma_state"]="above" if price and price>sma50 else "below"
    out["off_high_pct"]=round(off_high,1)
    if sma200 and price: out["vs200_pct"]=round((price/sma200-1)*100,1)
    if len(closes)<30: out["note"]="Limited history"
    c_trend=1.0 if (price and price>sma50) else -1.0; c_cross=1.0 if sma20>sma50 else -1.0
    c_mom=_clamp(mom1m/10.0,-1,1); c_rsi=_clamp((rsi-50.0)/20.0,-1,1); c_today=_clamp((out["change_pct"] or 0)/3.0,-1,1)
    tech=30*c_trend+20*c_cross+25*c_mom+15*c_rsi+10*c_today
    raw=_clamp(tech+ext_bias*MACRO_WEIGHT,-100,100)
    reasons=[("Above" if (price and price>sma50) else "Below")+" 50-day avg","20d>50d" if sma20>sma50 else "20d<50d",f"1mo {mom1m:+.1f}%",f"RSI {rsi:.0f}"]
    # --- crash-aware guards (v2) --------------------------------------
    crash_flag=None
    if off_high<=-20:
        raw-=25; crash_flag="bear"; reasons.append(f"bear market: {off_high:.0f}% off 52w high")
    elif off_high<=-10:
        raw-=12; crash_flag="correction"; reasons.append(f"correction: {off_high:.0f}% off 52w high")
    if sma200 is not None and price and price<sma200:
        raw=min(raw-10,SIGNAL_BUY-1)            # Faber trend filter: never BUY below the 200-day
        reasons.append("below 200-day avg — no new buys")
    if vol10 and vol63 and vol63>0 and vol10/vol63>=1.8 and raw>0:
        raw*=0.6; reasons.append(f"vol spike {vol10/vol63:.1f}x")
    if sector_dd is not None and sector_dd<=-15:
        raw=min(raw-10,SIGNAL_BUY-1)
        crash_flag=crash_flag or "sector"
        reasons.append(f"sector in drawdown ({sector_dd:.0f}% off high)")
    if raw>0:
        raw=raw*(1-0.35*_clamp(event_risk,0,1))  # dampen only bullish conviction near big events
    if ret10<=-12 or mom1m<=-18:
        raw=min(raw,-40); crash_flag="crash"
        reasons.append(f"fast drawdown: {ret10:+.0f}% in 10d / {mom1m:+.0f}% in 1mo — exit signal")
    raw=_clamp(raw,-100,100)
    score=int(round(raw)); out["score"]=score; out["strength"]=abs(score); out["crash_flag"]=crash_flag
    out["action"]="BUY" if score>=SIGNAL_BUY else ("SELL" if score<=SIGNAL_SELL else "HOLD")
    if rsi>=70: reasons.append("overbought")
    elif rsi<=30: reasons.append("oversold")
    if rvol and rvol>=2: reasons.append(f"vol {rvol:.1f}x")
    if abs(ext_bias)>=0.1: reasons.append(f"macro {'+' if ext_bias>0 else '−'}")
    if event_risk>=0.4: reasons.append("event risk")
    out["reasons"]=reasons; return out


# Industry/theme ETFs used for the sector-crash overlay: crashes cluster by
# industry (July 2026: memory/semis), so each name is checked against the most
# specific ETF that covers it, not just its broad S&P sector.
INDUSTRY_ETF = {
    "NVDA":"SMH","AMD":"SMH","AVGO":"SMH","MU":"SMH","KLAC":"SMH","WDC":"SMH",
    "SNDK":"SMH","STX":"SMH","SOXX":"SMH","SMH":"SMH",
}
SECTOR_ETF_OF = {name: etf for etf, v in SECTORS.items() for name in [v["name"]]}


def sector_health(daily):
    """Drawdown/trend read for every sector + industry ETF: % off 52-week high,
    vs 200-day, 1-month return, and a status (ok / pullback / correction / bear).
    This is the sector-level crash detector the S&P-only radar was missing."""
    out={}
    for etf in list(SECTORS.keys())+["SMH","SOXX"]:
        df=daily.get(etf)
        if df is None or df.empty: continue
        c=df["Close"].dropna()
        if len(c)<60: continue
        px=float(c.iloc[-1]); hi=float(c.tail(252).max())
        off=(px/hi-1)*100
        sma200=float(c.tail(200).mean()) if len(c)>=180 else None
        n=min(21,len(c)-1); m1=(px/float(c.iloc[-1-n])-1)*100
        status="ok"
        if off<=-30: status="crash"
        elif off<=-20: status="bear"
        elif off<=-10: status="correction"
        elif off<=-5: status="pullback"
        out[etf]={"name":(SECTORS.get(etf) or {}).get("name") or {"SMH":"Semiconductors","SOXX":"Semiconductors"}.get(etf,etf),
                  "off_high_pct":round(off,1),"mom1m_pct":round(m1,1),
                  "below_200d":bool(sma200 and px<sma200),"status":status}
    return out


def _sector_dd_for(sym, sec_health):
    """Most specific ETF drawdown covering `sym` (industry first, then S&P sector)."""
    etf=INDUSTRY_ETF.get(sym) or SECTOR_ETF_OF.get(sector_of(sym))
    h=sec_health.get(etf) if etf else None
    return h["off_high_pct"] if h else None


def apply_lt_discipline(w):
    """Re-weight a watchlist signal for LONG-TERM holding.

    Two rules:
      1. Prioritize durable compounders: 'strong' long-term drift and high 1-yr
         up-odds boost the score; an 'avoid' drift tag (negative 10-yr CAGR)
         caps it — a name you shouldn't hold can never be a strong BUY.
      2. Pullback guard: a name that is short-term overextended (overbought RSI,
         a 1-day spike, a parabolic month, poor historical 1-month odds, or a
         price already above its own typical 3-month target) is statistically
         likely to give back several percent near-term — so its BUY strength is
         damped hard. Buy-the-dip, not the spike.
    """
    s = w.get("signal") or {}
    if s.get("action") not in ("BUY", "HOLD", "SELL"):
        return
    score = float(s.get("score") or 0)
    d = w.get("drift") or {}
    lv = w.get("levels") or {}
    rs = s.setdefault("reasons", [])
    # --- 1) long-term quality tilt -------------------------------------
    tag = d.get("tag")
    if tag == "strong" and score > 0:
        score *= 1.15
    elif tag == "avoid":
        if score > 10: rs.append("capped: negative LT drift")
        score = min(score, 10.0)
    lt_up = lv.get("lt_up")
    if score > 0 and lt_up is not None:
        if lt_up >= 65: score *= 1.10
        elif lt_up < 50:
            score *= 0.70; rs.append(f"1yr up-odds only {lt_up}%")
    # --- 2) short-term pullback guard ----------------------------------
    if score > 0:
        damp = 1.0
        rsi = s.get("rsi"); chg = s.get("change_pct") or 0; mom = s.get("mom1m") or 0
        st_up = lv.get("st_up"); sell_lv = lv.get("sell"); px = s.get("price")
        if rsi is not None and rsi >= 75:
            damp *= 0.55; rs.append("overbought — pullback risk")
        if chg >= 6:
            damp *= 0.55; rs.append("1-day spike — chase risk")
        if mom >= 30:
            damp *= 0.65; rs.append("parabolic month — cooling likely")
        if st_up is not None and st_up <= 45:
            damp *= 0.65; rs.append(f"1mo up-odds only {st_up}%")
        if px and sell_lv and px >= sell_lv:
            damp *= 0.75; rs.append("above typical 3-mo target — wait for dip")
        score *= max(damp, 0.20)   # flags stack; several at once forces HOLD
    # crash guard: the quality boost above must never lift a name whose own chart
    # (or sector) is in a bear/crash regime back into BUY territory
    if s.get("crash_flag") in ("bear", "crash", "sector"):
        score = min(score, SIGNAL_BUY - 1)
    sc = int(round(_clamp(score, -100, 100)))
    s["score"] = sc; s["strength"] = abs(sc)
    s["action"] = "BUY" if sc >= SIGNAL_BUY else ("SELL" if sc <= SIGNAL_SELL else "HOLD")


def build_watchlist(now_et, M, daily, market_bias, event_risk, sec_health=None):
    items=[]
    sh=sec_health or {}
    for w in WATCHLIST:
        t=w["ticker"] or w.get("proxy")
        sig=compute_signal(daily.get(t),M(t),market_bias,event_risk,_sector_dd_for(t,sh)) if t else {"action":"N/A","strength":0,"reasons":[],"note":"Not publicly traded"}
        items.append({"label":w["label"],"ticker":w["ticker"],"note":w.get("note"),"private":w["ticker"] is None,"proxy":w.get("proxy"),"signal":sig})
    return items


def rank_picks(now_et, M, daily, market_bias, commod, event_risk, sec_health=None, top=5):
    scored=[]
    sh=sec_health or {}
    for s in PICKS_UNIVERSE:
        sec=sector_of(s); ext=_clamp(market_bias+factors.sector_tilt(commod,sec),-1,1)
        sig=compute_signal(daily.get(s),M(s),ext,event_risk,_sector_dd_for(s,sh))
        if sig["action"]=="N/A" or sig["price"] is None: continue
        scored.append({"symbol":s,"sector":sec,"action":sig["action"],"score":sig["score"],"strength":sig["strength"],
                       "price":sig["price"],"change_pct":sig["change_pct"],"rsi":sig["rsi"],"mom1m":sig["mom1m"],"reasons":sig["reasons"]})
    scored.sort(key=lambda x:x["score"],reverse=True)
    return scored[:top]


def build_movers(M):
    pool = set(STOCK_SECTOR) | set(PICKS_UNIVERSE)
    rows=[]
    for s in pool:
        mm=M(s)
        if mm["change_pct"] is None: continue
        rows.append({"symbol":s,"sector":sector_of(s),"price":mm["price"],"change_pct":mm["change_pct"],
                     "rvol":mm["rvol"],"ext_change_pct":mm["ext_change_pct"],"ext_kind":mm["ext_kind"]})
    rows.sort(key=lambda x:x["change_pct"])
    return {"losers":rows[:5], "gainers":list(reversed(rows[-5:]))}


# --------------------------------------------------------------------------
def build_snapshot():
    now_et = datetime.now(ET); sess = market_session(now_et)
    # 1y history (was 6mo): the 200-day trend filter and 52-week-high drawdown
    # guards in compute_signal v2 need a full year of daily closes.
    daily, intra = fetch_all(UNIVERSE, daily_period="1y")

    _mc = {}
    def M(sym):
        if sym not in _mc:
            _mc[sym] = compute_metrics(intra.get(sym), daily.get(sym), now_et)
        return _mc[sym]

    _, macro_daily = _download_one("daily", [t[0] for t in MACRO_TICKERS], "6mo")
    macro = compute_macro(macro_daily); mbias = macro.get("bias", 0.0)
    _, fut_daily = _download_one("daily", factors.FUT_TICKERS, "3mo")
    futures = factors.fetch_futures(fut_daily)
    commod = factors.commodity_supply_demand(fut_daily)
    calendar = factors.event_calendar(now_et)
    _, crash_daily = _download_one("daily", ["^GSPC", "^VIX", "^TNX", "^IRX"], "2y")
    crash = factors.crash_risk(crash_daily, MACRO_CONSTANTS["shiller_cape"], MACRO_CONSTANTS["cape_mean"], calendar["next_fed"])
    news = factors.fetch_news()
    market_bias = round(_clamp(mbias + 0.4 * futures["bias"] - 0.5 * news.get("geo_risk", 0.0), -1, 1), 3)
    event_risk = calendar["event_risk"]

    sectors, up, down = [], 0, 0
    for etf, info in SECTORS.items():
        em = M(etf)
        if em["change_pct"] is not None:
            up += em["change_pct"] > 0; down += em["change_pct"] < 0
        stocks = [{"symbol": s, "metrics": M(s)} for s in info["stocks"]]
        sectors.append({"symbol": etf, "name": info["name"], "metrics": em, "stocks": stocks,
                        "unusual_members": sum(1 for s in stocks if s["metrics"]["unusual"])})

    unusual = []
    for sec in sectors:
        rows = [{"symbol": sec["symbol"], "metrics": sec["metrics"], "is_etf": True}] + \
               [{"symbol": s["symbol"], "metrics": s["metrics"], "is_etf": False} for s in sec["stocks"]]
        for item in rows:
            mm = item["metrics"]
            if mm["unusual"]:
                unusual.append({"symbol": item["symbol"], "sector": sec["name"], "is_etf": item["is_etf"],
                                "price": mm["price"], "change_pct": mm["change_pct"], "ext_change_pct": mm["ext_change_pct"],
                                "ext_kind": mm["ext_kind"], "rvol": mm["rvol"], "reasons": mm["reasons"], "score": mm["score"]})
    unusual.sort(key=lambda x: x["score"], reverse=True)

    movers = build_movers(M)
    sec_health = sector_health(daily)
    watchlist = build_watchlist(now_et, M, daily, market_bias, event_risk, sec_health)
    try:
        drift_tags = drift.ensure(WL_TICKERS, daily).get("tags", {})
        for w in watchlist:
            w["drift"] = drift_tags.get(w.get("ticker"))
    except Exception as e:
        print(f"[warn] drift failed: {e}", flush=True)
    try:
        _lv = (watchlist_levels.ensure(daily, WL_TICKERS).get("tickers") or {})
        for w in watchlist:
            w["levels"] = _lv.get(w.get("ticker"))
    except Exception as e:
        print(f"[warn] watchlist levels failed: {e}", flush=True)
    for w in watchlist:                       # long-term discipline: boost compounders,
        apply_lt_discipline(w)                # damp overextended names (pullback guard)
    picks = rank_picks(now_et, M, daily, market_bias, commod, event_risk, sec_health)
    try:
        top_calls_state = top_calls.compute(picks, watchlist, daily)
    except Exception as e:
        print(f"[warn] top_calls failed: {e}", flush=True); top_calls_state = top_calls.load_state() or {"top": [], "scorecard": {}}
    try:
        sim_state = sim.ensure_and_update(daily, PICKS_UNIVERSE)
    except Exception as e:
        print(f"[warn] simulator failed: {e}", flush=True); sim_state = sim.load_state() or {}
    try:
        insider_state = insider.ensure(WL_TICKERS, daily)
    except Exception as e:
        print(f"[warn] insider failed: {e}", flush=True); insider_state = insider.load_state() or {}
    try:
        forever_state = forever_hold.ensure(daily, watchlist)
    except Exception as e:
        print(f"[warn] forever-hold sim failed: {e}", flush=True); forever_state = forever_hold.load_state() or {}
    try:
        _vs = next((w["signal"] for w in watchlist if w.get("ticker") == "VOO"), {}) or {}
        _st = (sess or {}).get("state")
        _live = _vs.get("ext_change_pct") if _st == "post" else (_vs.get("change_pct") if _st in ("pre", "regular") else None)
        cradar_state = crash_radar.ensure(daily, crash, _live)
    except Exception as e:
        print(f"[warn] crash radar failed: {e}", flush=True); cradar_state = crash_radar.load_state() or {}

    return {
        "updated_at": time.time(), "updated_at_str": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
        "session": {**sess, "et_time": now_et.strftime("%H:%M:%S")},
        "thresholds": {"price_pct": PRICE_PCT_THRESHOLD, "rvol": RVOL_THRESHOLD},
        "breadth": {"up": up, "down": down, "total": len(SECTORS)},
        "macro": macro, "futures": futures, "commodities": commod, "calendar": calendar, "news": news,
        "crash_risk": crash, "crash_radar": cradar_state, "sector_health": sec_health,
        "market_bias": market_bias, "event_risk": event_risk,
        "sectors": sectors, "unusual": unusual, "movers": movers,
        "watchlist": watchlist, "picks": picks, "sim": sim_state, "top_calls": top_calls_state,
        "insiders": insider_state,
        "forever_hold": forever_state,
    }


# --------------------------------------------------------------------------
_cache = {"data": None, "error": None}
_lock = threading.Lock()
_force = threading.Event()   # set by /api/refresh to trigger an immediate rebuild


def refresh_loop():
    first = True
    while True:
        try:
            snap = build_snapshot()
            with _lock:
                _cache["data"], _cache["error"] = snap, None
            state = snap["session"]["state"]
            if first:
                print(f"  Data loaded. {snap['session']['label']} · macro {snap['macro'].get('label')} · "
                      f"{len(snap['picks'])} picks · sim ${snap['sim'].get('stats',{}).get('current_equity','?')}.", flush=True)
                first = False
        except Exception as e:
            with _lock:
                _cache["error"] = str(e)
            state = "closed"
            print(f"[error] refresh failed: {e}", flush=True)
        _force.wait(timeout=(REFRESH_OPEN if state in ("pre", "regular", "post") else REFRESH_CLOSED))
        _force.clear()   # woken either by the timeout or by a manual /api/refresh


app = Flask(__name__)


@app.route("/api/data")
def api_data():
    with _lock:
        if _cache["data"] is None:
            return Response(json.dumps({"error": _cache["error"] or "loading"}), mimetype="application/json", status=503)
        return Response(json.dumps(_cache["data"]), mimetype="application/json")


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    _force.set()   # wake refresh_loop to rebuild the snapshot immediately
    return Response(json.dumps({"ok": True}), mimetype="application/json")


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


from dashboard_ui import INDEX_HTML  # noqa: E402


def _lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return None


if __name__ == "__main__":
    threading.Thread(target=refresh_loop, daemon=True).start()
    ip = _lan_ip()
    print(f"\n  Dashboard running ->  http://localhost:{PORT}", flush=True)
    if HOST == "0.0.0.0" and ip:
        print(f"  On your phone (same Wi-Fi) ->  http://{ip}:{PORT}", flush=True)
    elif ip:
        print(f"  Phone/LAN: restart with DASH_HOST=0.0.0.0, then open http://{ip}:{PORT}", flush=True)
    print("  Market data loads in the background (~20-40s on first run). Ctrl+C to stop.\n", flush=True)
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)

# --- end of stock_dashboard.py ---
