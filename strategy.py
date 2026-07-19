"""
Strategy research / validation engine.

Compares candidate trading rules against the S&P 500 (VOO) and validates them
walk-forward (rolling windows) so we can report HOW OFTEN a rule beats the index
and with what confidence — not just one lucky number.

Rules compared:
  oc        Buy at open, sell at close (intraday, flat overnight)  [the old default]
  co        Buy at close, sell at next open (overnight only)
  cc        Hold the up-trend basket overnight (rebalance at close) [dividends incl.]
  cc_regime cc, but in cash when the S&P is below its 200-day average
  hold1     Low-turnover trader: <=1 trade/day, up to K positions held for days,
            dividends collected, short-term capital-gains tax on sales held <1yr

Dividends are captured via Yahoo's adjusted close. Run:  python strategy.py
NOT financial advice; a backtest is not a guarantee.
"""

import numpy as np
import pandas as pd
import yfinance as yf

PERIOD = "3y"
TAX_RATE = 0.30          # short-term capital-gains drag on gains realized < 1yr
LT_DAYS = 252            # trading days that count as "long term"
MAX_POS = 5              # max simultaneous positions for the low-turnover trader
WINDOW = 21             # walk-forward window length (trading days)

DEFAULT_UNIVERSE = ["AAPL","MSFT","NVDA","AVGO","AMD","GOOGL","META","AMZN","TSLA","NFLX",
    "ORCL","CRM","JPM","V","MA","BAC","GS","UNH","LLY","JNJ","MRK","ABBV","XOM","CVX","COP",
    "CAT","GE","HON","RTX","COST","WMT","PG","KO","NEE","KEYS","MU","PANW","NOK"]


def load(universe, benchmark="VOO", period=PERIOD):
    syms = sorted(set(universe) | {benchmark})
    adj = yf.download(" ".join(syms), period=period, interval="1d", auto_adjust=True,
                      group_by="ticker", progress=False, threads=False)
    raw = yf.download(" ".join(syms), period=period, interval="1d", auto_adjust=False,
                      group_by="ticker", progress=False, threads=False)
    A = pd.DataFrame({s: adj[s]["Close"] for s in syms if s in adj}).dropna(how="all")
    O = pd.DataFrame({s: raw[s]["Open"] for s in syms if s in raw}).reindex(A.index)
    C = pd.DataFrame({s: raw[s]["Close"] for s in syms if s in raw}).reindex(A.index)
    return A, O, C, benchmark


def signals(A):
    sma20, sma50 = A.rolling(20).mean(), A.rolling(50).mean()
    return ((A > sma50) & (sma20 > sma50)).shift(1).fillna(False)


def basket_returns(A, O, C, sig, kind, voo, voo200=None):
    U = [c for c in A.columns if c != voo]
    sel = sig[U].astype(float)
    n = sel.sum(axis=1)
    if kind == "oc":
        ret = (C[U] / O[U] - 1)
    elif kind == "co":
        ret = (O[U] / C[U].shift(1) - 1)
    else:  # cc (dividends included via adjusted A)
        ret = (A[U] / A[U].shift(1) - 1)
    port = (ret * sel).sum(axis=1) / n.replace(0, np.nan)
    port = port.fillna(0.0)
    if voo200 is not None:
        on = (A[voo] > voo200).shift(1).fillna(False)
        port = port.where(on, 0.0)
    return port


def hold1_equity(A, sig, voo, start=5000.0, k=MAX_POS, tax=TAX_RATE):
    """Low-turnover trader: <=1 trade/day, hold for days, dividends via adjusted
    prices, short-term tax on sales held < LT_DAYS. Returns a daily equity Series."""
    U = [c for c in A.columns if c != voo]
    mom = A / A.shift(21) - 1
    idx = A.index
    cash = start
    pos = {}   # sym -> {"val":dollars, "basis":dollars, "entry":i}
    eq = []
    start_i = 50
    for i in range(len(idx)):
        if i > 0:
            for s in list(pos):
                r = A[s].iloc[i] / A[s].iloc[i - 1]
                if not np.isnan(r):
                    pos[s]["val"] *= r
        if i >= start_i:
            row = sig.iloc[i]
            # one action/day: prefer selling a broken position, else buy one
            sells = [s for s in pos if not bool(row.get(s, False))]
            if sells:
                s = sells[0]
                gain = pos[s]["val"] - pos[s]["basis"]
                if gain > 0 and (i - pos[s]["entry"]) < LT_DAYS:
                    pos[s]["val"] -= gain * tax
                cash += pos[s]["val"]
                del pos[s]
            elif len(pos) < k and cash > start * 0.05:
                cand = [s for s in U if bool(row.get(s, False)) and s not in pos and not np.isnan(mom[s].iloc[i])]
                if cand:
                    s = max(cand, key=lambda x: mom[x].iloc[i])
                    spend = min(cash, eq_val(cash, pos) / k) if pos else cash / k
                    spend = min(cash, spend if spend > 0 else cash / k)
                    pos[s] = {"val": spend, "basis": spend, "entry": i}
                    cash -= spend
        eq.append(cash + sum(p["val"] for p in pos.values()))
    return pd.Series(eq, index=idx)


def eq_val(cash, pos):
    return cash + sum(p["val"] for p in pos.values())


def to_equity(daily_ret, start=5000.0):
    return start * (1 + daily_ret).cumprod()


def stats(eq):
    eq = eq.dropna()
    tot = eq.iloc[-1] / eq.iloc[0] - 1
    dd = (eq / eq.cummax() - 1).min()
    return tot, dd


def walkforward_winrate(eq, voo_eq, window=WINDOW):
    """Fraction of non-overlapping windows where the strategy beats VOO."""
    e = eq.dropna(); v = voo_eq.reindex(e.index)
    wins = tot = 0
    for a in range(0, len(e) - window, window):
        b = a + window
        sr = e.iloc[b] / e.iloc[a] - 1
        vr = v.iloc[b] / v.iloc[a] - 1
        tot += 1
        wins += (sr > vr)
    p = wins / tot if tot else 0.0
    se = (0.25 / tot) ** 0.5 if tot else 0.0
    z = (p - 0.5) / se if se else 0.0          # one-sided: is win-rate > 50%?
    return wins, tot, p, z


def run(universe=DEFAULT_UNIVERSE, start=5000.0):
    A, O, C, voo = load(universe)
    sig = signals(A)
    voo200 = A[voo].rolling(200).mean()
    voo_eq = to_equity((A[voo] / A[voo].shift(1) - 1).fillna(0.0), start)

    series = {
        "oc  (buy open/sell close, flat o/n)": to_equity(basket_returns(A, O, C, sig, "oc", voo), start),
        "co  (overnight only)":                to_equity(basket_returns(A, O, C, sig, "co", voo), start),
        "cc  (hold overnight, +divs)":         to_equity(basket_returns(A, O, C, sig, "cc", voo), start),
        "cc_regime (cash<200d)":               to_equity(basket_returns(A, O, C, sig, "cc", voo, voo200), start),
        "hold1 (<=1 trade/day, after-tax)":    hold1_equity(A, sig, voo, start),
        "VOO buy & hold":                      voo_eq,
    }
    vtot, vdd = stats(voo_eq)
    print(f"\nUniverse {len([c for c in A.columns if c!=voo])} stocks · {len(A)} days "
          f"({A.index[0].date()}→{A.index[-1].date()})  | window={WINDOW}d")
    print(f"{'strategy':40}{'total':>9}{'maxDD':>8}{'beatS&P windows':>20}{'conf(z)':>9}")
    best = None
    for name, eq in series.items():
        tot, dd = stats(eq)
        if name.startswith("VOO"):
            print(f"{name:40}{tot*100:8.1f}%{dd*100:7.1f}%{'(benchmark)':>20}")
            continue
        w, t, p, z = walkforward_winrate(eq, voo_eq)
        print(f"{name:40}{tot*100:8.1f}%{dd*100:7.1f}%{f'{w}/{t} = {p*100:.0f}%':>20}{z:8.1f}")
        cand = (p, tot)
        if best is None or cand > best[0]:
            best = (cand, name, p, tot)
    print(f"\nVOO: total {vtot*100:.1f}%, maxDD {vdd*100:.1f}%")
    print(f"Most robust beat-the-S&P rule: {best[1]} — wins {best[2]*100:.0f}% of {WINDOW}d windows, total {best[3]*100:.1f}%")
    return series


if __name__ == "__main__":
    run()

# --- end of strategy.py ---
