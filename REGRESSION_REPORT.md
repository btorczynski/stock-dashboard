# Dashboard review — September 9, 2026

The dashboard now presents BUY / WAIT / AVOID decisions for new purchases, with
reasons and quote timestamps. A score remains a mechanical model output; these
changes fix correctness and presentation rather than establish investment returns.

## Confirmed and fixed

- Eight initial regression cases failed against the original code: insufficient
  history producing BUY; quality boosts overriding the 200-day and sector guards;
  HOLD/SELL entries appearing under Top BUY; conflicting watchlist/top-call
  decisions; flat-price RSI returning zero; infinity accepted as a number; and the
  -25 SELL boundary being calibrated as HOLD. All now pass.
- Bear-market rebound scores and all later overlays retain purchase restrictions.
  The forever-hold entry panel also respects the final watchlist decision.
- Intraday freshness, completed daily history, invalid/future timestamps,
  missing prices and duplicate history are checked. Old intraday data cannot
  replace a newer daily close. Failed refreshes remain visible to the browser.
- Historical price-only scores match live price-only scores at tested boundaries.
  Adjusted ratings are labeled /100, separately from historical hit rates.
- Calls are graded near their intended 14-calendar-day horizon even after an
  outage. Missing horizon prices remain pending; intraday calls are not backdated
  to yesterday, and weekends do not create duplicate daily calls.
- Static exports validate actual prices and finite JSON before replacing output,
  and write UTF-8. Live self-checks fail with a nonzero status for empty prices.
- Offline regression tests run before the existing scheduled publishing step.

## Validation performed

- **37 deterministic regression tests passed**, including full snapshot assembly,
  Flask routes, static export and failure handling. Tests stub external services
  and state writes. Run `python -m unittest discover -p "test_*.py" -v`.
- Syntax checks passed for project Python scripts and the embedded JavaScript.
- A synthetic 600-session forever-hold backtest produced finite, correctly sized
  lump-sum, benchmark and DCA series. Future-price perturbation tests cover the
  historical scoring kernel and the daily simulator's earlier decisions/results.
- Live Yahoo daily downloads succeeded for AAPL and VOO (251 rows each).
- **Full live self-check passed in 82 seconds**, with 11 sector panels, 34 watchlist
  rows, 5 qualifying picks, populated strategy/radar/context sections and zero
  stale or unavailable watchlist quotes at that check. Yahoo returned expected
  missing-fundamentals responses for several ETFs; these optional inputs did not
  prevent the snapshot from building.
- Browser verification covered desktop and a 390px phone viewport, BUY/WAIT/AVOID
  filtering, the empty-filter state, the signal and strategy panels, stale-feed
  purchase suppression, provider errors and recovery. No JavaScript console errors
  were observed in these flows. Browser fixtures were clearly labeled synthetic.

## Remaining model limitations

CPI/CAPE and some events are manually maintained, not a live economic release feed.
The market calendar covers configured US holidays in 2026–2027, not exchange-specific
holidays or early closes. Static publishing currently runs every 30 minutes, so its
20-minute freshness limit can deliberately show WAIT between builds.

Historical baskets contain selection/survivorship bias. Some confidence-weighted
backtests estimate band odds over the full sample; they are descriptive research,
not independent out-of-sample proof. Legacy graded scorecard outcomes are retained.
The full live model still needs a sustained forward record before claims about
predictive accuracy or improved returns would be justified.

Tests and live rebuilds ran in an isolated working copy. Installation copies only
the reviewed source, tests, documentation and workflow; existing `*_state.json`
files are preserved. New cache schemas will rebuild through the app's normal flow.
