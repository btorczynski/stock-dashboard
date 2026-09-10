# Indicator performance validation — September 9, 2026

**Conclusion: the tested price/sector indicators do not demonstrate a dependable entry-timing advantage.** The software calculations pass regression checks, but that does not establish investment usefulness. BUY observations showed modestly better win rates and lower loss frequencies on the current watchlist; results did not consistently exceed ordinary entries and deteriorated on the sector-ETF control.

## Primary result: 21 trading sessions, 2023 onward

Signals use the completed close; simulated entry is the following open and exit is 21 sessions after entry. Returns include 0.10% execution cost on each side. ALL means buying on every eligible day; it is a baseline, not a signal. AVOID outcomes show what happened **if someone nevertheless bought**, not a short-selling return.

| Cohort / condition | Observations | Positive return | Mean net return | Median net return | Loss of 5% or more | Intraperiod drop of 10% or more |
|---|---:|---:|---:|---:|---:|---:|
| Watchlist / ALL | 28,135 | 59.73% | 4.91% | 2.27% | 23.75% | 29.91% |
| Watchlist / BUY | 12,778 | 61.32% | 4.96% | 2.36% | 21.23% | 24.90% |
| Watchlist / WAIT | 1,227 | 60.23% | 3.28% | 1.85% | 20.70% | 22.82% |
| Watchlist / AVOID | 14,130 | 58.26% | 5.01% | 2.23% | 26.29% | 35.05% |
| Sector ETFs / ALL | 8,118 | 58.81% | 1.07% | 1.02% | 8.77% | 4.19% |
| Sector ETFs / BUY | 4,362 | 54.91% | 0.68% | 0.51% | 9.40% | 3.28% |
| Sector ETFs / WAIT | 792 | 56.31% | 0.46% | 0.60% | 9.72% | 3.16% |
| Sector ETFs / AVOID | 2,964 | 65.22% | 1.81% | 1.92% | 7.59% | 5.80% |

The observations overlap and are not independent trades. The primary comparison averages each day’s BUY basket against all eligible names **on the same date**, then averages those date-level differences. This differs from the table’s observation-weighted mean, which weights dates with more names more heavily.

| Cohort | BUY minus matched-date baseline | 95% date-block bootstrap interval | Interpretation |
|---|---:|---:|---|
| Watchlist | -0.64 percentage points | -2.01 to +0.47 | No demonstrated positive edge |
| Sector ETFs | -0.34 percentage points | -0.66 to -0.04 | Negative in this holdout |

Intervals use 2,000 circular moving-block resamples of 63-session date blocks with a fixed random seed; ticker correlations within dates are preserved. These approximate intervals do not remove universe-selection bias or past model-development hindsight.

## Stability by year

| Signal year | Watchlist BUY spread | Sector ETF BUY spread |
|---|---:|---:|
| 2020 | +0.41 pp | -0.06 pp |
| 2021 | -0.37 pp | -0.79 pp |
| 2022 | +1.78 pp | +0.15 pp |
| 2023 | -1.01 pp | -0.08 pp |
| 2024 | -0.75 pp | -0.22 pp |
| 2025 | -1.61 pp | -0.44 pp |
| 2026 | +1.77 pp | -0.79 pp |

2026 contains only outcomes that have matured by September 9. Yearly results are grouped by signal date. The recent watchlist advantage changes sign across years; the ETF control does not confirm a stable effect.

## Monthly portfolio illustration

At the first open of each month, use the preceding close’s signal, split equally across eligible names, and hold to the next monthly rebalance. Cash earns zero. Each monthly purchase/exit pays 0.10%, even when a name remains selected; this is a conservative turnover assumption. These are illustrative portfolios, not the dashboard’s complete live strategy.

| Cohort / strategy, 2023 onward | CAGR | Worst open-to-open drawdown | Months with stock exposure |
|---|---:|---:|---:|
| Watchlist / all eligible names | 71.85% | -30.44% | 100.00% |
| Watchlist / BUY basket | 68.47% | -24.87% | 100.00% |
| Watchlist / 200-day-only basket | 66.75% | -31.46% | 100.00% |
| Watchlist / SPY held | 21.92% | -19.77% | — |
| Sector ETFs / all eligible names | 12.84% | -17.19% | 100.00% |
| Sector ETFs / BUY basket | 7.87% | -18.08% | 95.56% |
| Sector ETFs / 200-day-only basket | 9.90% | -17.55% | 100.00% |
| Sector ETFs / SPY held | 21.92% | -19.77% | — |

**Do not extrapolate the large watchlist returns.** This is today’s selected list, including stocks that became major winners and speculative names. It lacks delisted losers and historical universe membership. The all-name basket also performed exceptionally, so beating SPY would not by itself demonstrate timing skill. Portfolio drawdowns use daily opens, not every intraday low.

## Individual indicator diagnostics

These are exploratory filter results at 21 sessions in the recent holdout. They are not independent experiments and were not used to change weights or select a new “winning” model.

| Condition | Watchlist win rate | Watchlist matched spread | ETF win rate | ETF matched spread |
|---|---:|---:|---:|---:|
| above 50 day | 60.32% | +0.02 pp | 56.28% | -0.30 pp |
| 20 above 50 day | 59.28% | -0.26 pp | 56.71% | -0.37 pp |
| positive 21 day momentum | 60.20% | +0.26 pp | 57.08% | -0.24 pp |
| rsi above 50 | 60.33% | -0.01 pp | 57.11% | -0.24 pp |
| rsi oversold below 30 | 69.80% | +0.03 pp | 74.17% | +0.77 pp |
| above 200 day | 59.94% | +0.03 pp | 55.87% | -0.24 pp |
| within 20pct of high | 61.14% | -0.81 pp | 58.57% | -0.06 pp |
| no fast crash | 60.16% | -0.14 pp | 58.70% | -0.01 pp |
| no volatility spike | 59.62% | -0.11 pp | 58.58% | -0.04 pp |
| core buy without sector | 61.39% | -0.53 pp | 54.91% | -0.34 pp |

A high raw win rate can come from a generally rising market. Oversold observations sometimes rebounded, but they are sparse and correlated; this is not sufficient evidence to reverse the model or disable downside guards. The guards are best understood as risk-policy choices with opportunity costs, not universal return boosters.

## Probability calibration: annual forward refits

Every January, band frequencies are estimated using only earlier observations whose 21-session **close-to-close** outcomes were already known. Ticker counts are shrunk toward the pooled band rate using the existing 60-observation prior. The baseline predicts the ticker’s unconditional historical up frequency. This tests the historical band-odds component, not the heuristically adjusted /100 rating.

| Cohort, 2023 onward | Band model Brier error | Baseline Brier error | Improvement | 95% interval for error reduction |
|---|---:|---:|---:|---:|
| Watchlist | 0.24392 | 0.24566 | +0.71% | -0.00157 to +0.00556 |
| Sector ETFs | 0.24022 | 0.23989 | -0.14% | -0.00407 to +0.00332 |

Lower Brier error is better. Both intervals include zero: neither cohort demonstrates a clear probability-forecast improvement over its unconditional baseline.

## Coverage and safeguards

- Downloaded adjusted daily OHLCV from 2000-01-01 through 2026-09-09. The watchlist evaluation includes 32 US tickers and the fixed control includes nine original sector ETFs.
- MDA.TO is excluded from the US performance comparison because its price series is in CAD and follows a different exchange calendar. It remains available in the Live Desk charts.
- SPCX has 61 bars and cannot meet the 200-bar minimum. Recent IPOs enter other tests only after sufficient history; no pre-IPO bars are invented.
- 5-, 21-, 63- and 252-session results, data coverage, file hashes, yearly results and probability reliability tables are included in `indicator_validation_results.json`.
- 96 real-data score comparisons and 96 sector-aware entry comparisons matched the live engine with macro/event inputs neutralized.
- Tests check next-open execution, two-sided fees, cash behavior, signal-day isolation, training-label maturity and future-price perturbations. The existing 37 regression checks, 11 validation-harness checks and 8 chart-data checks pass (56 total).
- The original thresholds stayed fixed. Only harness correctness issues, such as an exact floating-point assertion and a missing self-sector guard, were corrected.

## What this does not validate

The combined tests reproduce the price-only kernel plus the sector guard. They do **not** reproduce historical daily long-term-quality reweighting, fundamentals, analyst consensus, news, macro releases, event overlays, crash-radar probabilities or intraday execution. Timestamped input histories are required for a faithful end-to-end test of those components. The annual calibration exercise is separate from the daily live update schedule.

The historical periods are later than each annual calibration training cut, but the current signal design may itself have been influenced by those years. This is a retrospective fixed-rules holdout, not an untouched prospective trial. Existing live scorecard outcomes span older versions and only 26 graded calls; they do not validate the new rules.

The “dip reference” currently derives from a percentile of terminal 21-session returns; it is not a measured probability of touching an intraperiod low. It should remain context rather than an assured fill or profit target.

## Reproduce

```sh
python -m unittest discover -p "test_*.py" -v
python validate_indicators.py --download --output validation
python validate_indicators.py --output validation  # replay the same cached inputs
```

Downloaded inputs are isolated under the requested output folder; the harness never writes simulator state. Data end date and thresholds are explicit constants so this run can be repeated. Raw inputs are cached locally; the checked-in summary records their SHA-256 hashes.

The Live Desk displays real API snapshot values with provider timestamps, candlesticks, volume, sector heatmaps and a rotating stock network. It explicitly displays the unproven timing status and retains the existing stale-data purchase pause.

For context, FINRA explains that historical backtests neither predict future performance nor exactly reproduce past execution: [FINRA — Smart Beta considerations](https://www.finra.org/investors/insights/smart-beta-what-you-need-know).
