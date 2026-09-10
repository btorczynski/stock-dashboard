"""Reproducible, fixed-rules historical validation; never writes app state.

python validate_indicators.py --download --output validation
python validate_indicators.py --output validation   # replay cached downloads
"""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
import stock_dashboard as sd
import signal_calibration as cal
from entry_rules import rsi

START = '2000-01-01'
END = '2026-09-10'  # exclusive; frozen to the requested review date
EVAL = '2010-01-01'
HOLDOUT = '2023-01-01'
HORIZONS = (5, 21, 63, 252)
FEE = .001
SEED = 20260909
CONTROL = ['XLK', 'XLF', 'XLV', 'XLY', 'XLI', 'XLP', 'XLE', 'XLB', 'XLU']
WATCHLIST = [w['ticker'] for w in sd.WATCHLIST if w.get('ticker') and '.' not in w['ticker']]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def fetch_history(folder, download=False):
    raw = folder / 'prices'
    raw.mkdir(parents=True, exist_ok=True)
    syms = sorted(set(WATCHLIST + CONTROL + ['SPY'] + list(sd.SECTORS) + list(sd.INDUSTRY_ETF.values())))
    if download:
        yf.set_tz_cache_location(str(folder / 'yf-cache'))
        for start in range(0, len(syms), 8):
            group = syms[start:start + 8]
            data = yf.download(group, start=START, end=END, interval='1d', auto_adjust=True,
                               group_by='ticker', threads=False, progress=False, timeout=30)
            for sym in group:
                try:
                    frame = data[sym].dropna(subset=['Open', 'Close']).sort_index()
                    frame = frame.loc[~frame.index.duplicated(keep='last')]
                    frame = frame.loc[(frame.Open > 0) & (frame.Close > 0)]
                    if frame.empty:
                        continue
                    frame.to_json(raw / (sym + '.json'), orient='table', date_format='iso')
                    print(f'{sym}: {len(frame)} daily bars', flush=True)
                except (KeyError, ValueError) as exc:
                    print(f'{sym}: missing data ({exc})', flush=True)
    frames, coverage = {}, {}
    for sym in syms:
        path = raw / (sym + '.json')
        if not path.exists():
            coverage[sym] = {'rows': 0, 'status': 'missing'}
            continue
        frame = pd.read_json(path, orient='table')
        frame.index = pd.DatetimeIndex(frame.index).tz_localize(None)
        frame = frame.loc[(frame.index >= START) & (frame.index < END)]
        frames[sym] = frame
        coverage[sym] = {'rows': len(frame), 'first': str(frame.index[0].date()),
                         'last': str(frame.index[-1].date()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if 'SPY' not in frames:
        raise ValueError('SPY history is required. Run with --download first.')
    return frames, coverage


def features(frame, sector=None):
    c = frame.Close.dropna()
    f = pd.DataFrame(index=c.index)
    f['score'] = cal.hist_scores(c)
    f['rsi'] = rsi(c)
    f['mom21'] = c / c.shift(21) - 1
    f['ret10'] = c / c.shift(10) - 1
    f['today'] = c.pct_change(fill_method=None)
    f['above50'] = c > c.rolling(50).mean()
    f['cross'] = c.rolling(20).mean() > c.rolling(50).mean()
    f['above200'] = c >= c.rolling(200).mean()
    f['offhigh'] = c / c.rolling(252, min_periods=200).max() - 1
    ret = c.pct_change(fill_method=None)
    f['vol_spike'] = ret.rolling(10).std() / ret.rolling(63).std() >= 1.8
    f['sector_dd'] = np.nan if sector is None else (sector.Close / sector.Close.rolling(252, min_periods=60).max() - 1).reindex(f.index)
    f['sector_known'] = True if sector is None else f.sector_dd.notna()
    f['blocked'] = (~f.above200) | (f.offhigh <= -.20) | (f.ret10 <= -.12) | (f.mom21 <= -.18) | (f.sector_dd <= -.15)
    f['entry'] = np.where(f.blocked | (f.score <= -25), 'AVOID', np.where(f.score >= 25, 'BUY', 'WAIT'))
    f.loc[f.score.isna() | ~f.sector_known, 'entry'] = 'UNAVAILABLE'
    return f


def future_return(frame, horizon, cost=FEE):
    # At close t, buy open t+1; exit open t+1+h. Never execute at close t.
    return frame.Open.shift(-(horizon + 1)) / frame.Open.shift(-1) * (1 - cost) / (1 + cost) - 1


def future_drawdown(frame, horizon):
    low = frame.Low.shift(-1).iloc[::-1].rolling(horizon, min_periods=horizon).min().iloc[::-1]
    return (low / frame.Open.shift(-1) - 1).clip(upper=0)


def bootstrap_mean(values, block=63, n_boot=2000):
    # Resample full date blocks, not individual ticker/day observations.
    # Preserve NaNs (dates without BUYs) inside blocks until computing each mean.
    x = np.asarray(values, dtype=float)
    n = len(x)
    if np.isfinite(x).sum() < 30:
        return [None, None]
    block = min(block, max(1, n // 3))
    rng = np.random.default_rng(SEED)
    means = []
    for _ in range(n_boot):
        starts = rng.integers(0, n, int(np.ceil(n / block)))
        ix = ((starts[:, None] + np.arange(block)) % n).ravel()[:n]
        sample = x[ix]
        if np.isfinite(sample).any():
            means.append(float(np.nanmean(sample)))
    return [float(v) for v in np.percentile(means, [2.5, 97.5])]


def summarize(fwd, mask, baseline, drawdown=None, block=63, bootstrap=True):
    chosen = fwd.where(mask)
    vals = chosen.to_numpy().ravel()
    vals = vals[np.isfinite(vals)]
    spread = chosen.mean(axis=1) - baseline.mean(axis=1)
    ci = bootstrap_mean(spread, block) if bootstrap else [None, None]
    dd = drawdown.where(mask & fwd.notna()).to_numpy().ravel() if drawdown is not None else np.array([])
    dd = dd[np.isfinite(dd)]
    return {'observations': len(vals), 'dates': int(chosen.notna().any(axis=1).sum()),
            'win_pct': float((vals > 0).mean() * 100) if len(vals) else None,
            'mean_pct': float(vals.mean() * 100) if len(vals) else None,
            'median_pct': float(np.median(vals) * 100) if len(vals) else None,
            'loss5_pct': float((vals <= -.05).mean() * 100) if len(vals) else None,
            'intraperiod_loss10_pct': float((dd <= -.10).mean() * 100) if len(dd) else None,
            'matched_spread_pct': float(spread.mean() * 100) if spread.notna().any() else None,
            'spread_95ci_pct': [v * 100 if v is not None else None for v in ci]}


def close_label_training(c, scores, cutoff, horizon=21):
    # Physically truncate before creating labels, so outcomes after cutoff cannot enter.
    past = c.loc[c.index < cutoff].tail(2520)
    forward = past.shift(-horizon) / past - 1
    train = pd.DataFrame({'score': scores.reindex(past.index), 'outcome': forward}).dropna()
    train['band'] = train.score.map(cal.band_of)
    return train


def probability_validation(frames, fs, tickers):
    rows = []
    for year in range(2016, 2027):
        cutoff = pd.Timestamp(f'{year}-01-01')
        train = {s: close_label_training(frames[s].Close, fs[s].score, cutoff) for s in tickers}
        pool = pd.concat([v for v in train.values() if not v.empty])
        prior = pool.groupby('band').outcome.apply(lambda x: (x > 0).mean())
        for sym in tickers:
            tr = train[sym]
            if len(tr) < 120:
                continue
            own = tr.groupby('band').outcome.agg(n='size', hits=lambda x: (x > 0).sum())
            unconditional = float((tr.outcome > 0).mean())
            c = frames[sym].Close
            target = c.shift(-21) / c - 1
            for stamp, score in fs[sym].score.loc[fs[sym].index.year == year].dropna().items():
                out = target.get(stamp)
                if pd.isna(out):
                    continue
                band = cal.band_of(score)
                n = own.loc[band, 'n'] if band in own.index else 0
                hits = own.loc[band, 'hits'] if band in own.index else 0
                p = float((hits + 60 * prior.get(band, unconditional)) / (n + 60))
                rows.append({'date': stamp, 'symbol': sym, 'p': p, 'base': unconditional,
                             'y': int(out > 0), 'band': band})
    detail = pd.DataFrame(rows)
    out = {}
    for label, lo in [('all_walk_forward', '2016-01-01'), ('holdout', HOLDOUT)]:
        df = detail.loc[detail.date >= lo].copy()
        df['brier'] = (df.p - df.y) ** 2
        df['baseline_brier'] = (df.base - df.y) ** 2
        skill = 1 - df.brier.mean() / df.baseline_brier.mean()
        diff = df.assign(diff=df.baseline_brier - df.brier).groupby('date')['diff'].mean()
        out[label] = {'n': len(df), 'brier': float(df.brier.mean()), 'baseline_brier': float(df.baseline_brier.mean()),
                      'skill_pct': float(skill * 100), 'error_improvement_95ci': bootstrap_mean(diff),
                      'reliability': []}
        for band, d in df.groupby('band'):
            out[label]['reliability'].append({'band': band, 'n': len(d),
                'predicted_up_pct': float(d.p.mean() * 100), 'actual_up_pct': float(d.y.mean() * 100)})
    return out


def monthly_portfolio(frames, fs, tickers, mode, start):
    index = frames['SPY'].index
    index = index[index >= start]
    opens = pd.DataFrame({s: frames[s].Open for s in tickers}).reindex(index)
    closeindex = frames['SPY'].index
    rebalance = [i for i in range(len(index)) if i == 0 or index[i].month != index[i-1].month]
    nav = pd.Series(np.nan, index=index)
    capital, invested, periods = 1., 0, 0
    for k, begin in enumerate(rebalance):
        end = rebalance[k+1] if k+1 < len(rebalance) else len(index)-1
        if end <= begin:
            continue
        stamp = index[begin]
        before = closeindex[closeindex < stamp]
        if before.empty:
            continue
        prev = before[-1]
        held = []
        for sym in tickers:
            if prev not in fs[sym].index or pd.isna(opens[sym].iloc[begin]):
                continue
            f = fs[sym].loc[prev]
            eligible = pd.notna(f.score)
            allow = eligible and (mode == 'all' or (mode == 'buy' and f.entry == 'BUY') or (mode == 'sma200' and f.above200))
            if allow:
                held.append(sym)
        periods += 1
        if held:
            invested += 1
            path = opens[held].iloc[begin:end+1]
            if path.isna().any().any():
                raise ValueError('Missing holding prices; cannot silently omit a selected security')
            ratios = path.div(path.iloc[0]).mean(axis=1)
            values = capital / (1 + FEE) * ratios
            nav.iloc[begin:end+1] = values.to_numpy()
            capital = float(values.iloc[-1] * (1 - FEE))
            nav.iloc[end] = capital
        else:
            nav.iloc[begin:end+1] = capital
    nav = nav.ffill().fillna(1.)
    return nav, {'invested_month_pct': 100 * invested / periods if periods else 0, 'months': periods}


def nav_stats(nav, start_value=1.):
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    high = nav.cummax().clip(lower=start_value)
    return {'cagr_pct': float(((nav.iloc[-1] / start_value) ** (1 / years) - 1) * 100),
            'total_pct': float((nav.iloc[-1] / start_value - 1) * 100),
            'max_drawdown_pct': float((nav / high - 1).min() * 100)}


def run(folder, download=False):
    folder.mkdir(parents=True, exist_ok=True)
    frames, coverage = fetch_history(folder, download)
    features_by_sym = {}
    for sym, frame in frames.items():
        etf = sd.INDUSTRY_ETF.get(sym) or sd.SECTOR_ETF_OF.get(sd.sector_of(sym))
        features_by_sym[sym] = features(frame, frames.get(etf) if etf else None)
    results = {'run_utc': datetime.now(timezone.utc).isoformat(), 'data_start': START, 'data_end_exclusive': END,
               'holdout': HOLDOUT, 'fee_bps_per_side': FEE * 10000, 'coverage': coverage,
               'cohorts': {}, 'sources': {'Yahoo': 'https://finance.yahoo.com/',
               'backtest_limits': 'https://www.finra.org/investors/insights/smart-beta-what-you-need-know'}}
    for cohort, universe in [('watchlist_us', WATCHLIST), ('sector_control', CONTROL)]:
        print('Evaluating', cohort, flush=True)
        tickers = [s for s in universe if s in frames and features_by_sym[s].score.notna().any()]
        fs = {s: features_by_sym[s] for s in tickers}
        scores = pd.DataFrame({s: fs[s].score for s in tickers})
        eligible = scores.notna()
        entries = pd.DataFrame({s: fs[s].entry for s in tickers})
        result = {'tickers': tickers, 'excluded_no_200_bars': [s for s in universe if s not in tickers],
                  'horizons': {}, 'yearly': {}, 'individual_filters': {}, 'portfolios': {}}
        for horizon in HORIZONS:
            fwd = pd.DataFrame({s: future_return(frames[s], horizon) for s in tickers}).where(eligible)
            dd = pd.DataFrame({s: future_drawdown(frames[s], horizon) for s in tickers}).where(eligible)
            hrows = {}
            for period, lo, hi in [('earlier', EVAL, HOLDOUT), ('holdout', HOLDOUT, END)]:
                f = fwd.loc[(fwd.index >= lo) & (fwd.index < hi)]
                d = dd.reindex(f.index)
                hrows[period] = {a: summarize(f, entries.reindex(f.index).eq(a) if a != 'ALL' else f.notna(), f, d,
                                             block=max(63,horizon), bootstrap=horizon==21)
                                for a in ['ALL','BUY','WAIT','AVOID']}
            result['horizons'][str(horizon)] = hrows
            if horizon != 21:
                continue
            for year in range(2010, 2027):
                f = fwd.loc[fwd.index.year == year]
                result['yearly'][str(year)] = {a: summarize(f, entries.reindex(f.index).eq(a), f, bootstrap=False)
                                               for a in ['BUY','WAIT','AVOID']}
            masks = {
                'above_50_day': pd.DataFrame({s: fs[s].above50 for s in tickers}),
                '20_above_50_day': pd.DataFrame({s: fs[s].cross for s in tickers}),
                'positive_21_day_momentum': pd.DataFrame({s: fs[s].mom21 > 0 for s in tickers}),
                'rsi_above_50': pd.DataFrame({s: fs[s].rsi > 50 for s in tickers}),
                'rsi_oversold_below_30': pd.DataFrame({s: fs[s].rsi < 30 for s in tickers}),
                'above_200_day': pd.DataFrame({s: fs[s].above200 for s in tickers}),
                'within_20pct_of_high': pd.DataFrame({s: fs[s].offhigh > -.20 for s in tickers}),
                'no_fast_crash': pd.DataFrame({s: (fs[s].ret10 > -.12) & (fs[s].mom21 > -.18) for s in tickers}),
                'no_volatility_spike': pd.DataFrame({s: ~fs[s].vol_spike for s in tickers}),
                'core_buy_without_sector': scores >= 25}
            f = fwd.loc[fwd.index >= HOLDOUT]
            for name, mask in masks.items():
                result['individual_filters'][name] = summarize(f, mask.reindex(f.index), f, dd.reindex(f.index), bootstrap=False)
        for period, begin in [('earlier_and_recent', EVAL), ('holdout', HOLDOUT)]:
            portfolio = {}
            for mode in ['all','buy','sma200']:
                nav, exposure = monthly_portfolio(frames, fs, tickers, mode, begin)
                portfolio[mode] = {**nav_stats(nav), **exposure}
                nav.to_json(folder / f'{cohort}_{period}_{mode}_nav.json', date_format='iso')
            spy = frames['SPY'].Open.loc[frames['SPY'].index >= begin]
            spy_nav = spy / spy.iloc[0] / (1+FEE)
            spy_nav.iloc[-1] *= (1-FEE)
            portfolio['spy_buy_hold'] = nav_stats(spy_nav)
            result['portfolios'][period] = portfolio
        result['probability_validation'] = probability_validation(frames, fs, tickers)
        results['cohorts'][cohort] = result
        write_json(folder / 'results.json', results)
    # Independent, no-overlay real-data parity against the live engine.
    count = 0
    for sym in results['cohorts']['watchlist_us']['tickers']:
        frame, f = frames[sym], features_by_sym[sym]
        for n in [200, min(1000,len(frame)),len(frame)]:
            sig = sd.compute_signal(frame.iloc[:n], {'data_status':'close'})
            if sig['score'] != f.score.iloc[n-1]:
                raise AssertionError((sym,n,sig['score'],f.score.iloc[n-1]))
            sector_dd = f.sector_dd.iloc[n-1]
            guarded = sd.compute_signal(frame.iloc[:n], {'data_status':'close'},
                                        sector_dd=float(sector_dd)*100 if pd.notna(sector_dd) else None)
            if guarded['entry_action'] != f.entry.iloc[n-1]:
                raise AssertionError((sym,n,guarded['entry_action'],f.entry.iloc[n-1]))
            count += 1
    results['real_data_score_parity_checks'] = count
    results['real_data_entry_parity_checks'] = count
    write_json(folder / 'results.json', results)
    print('Results written:', folder / 'results.json', flush=True)
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('validation'))
    args = parser.parse_args()
    run(args.output, args.download)
