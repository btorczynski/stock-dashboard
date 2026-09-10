# Fixed validation plan

Written before inspecting predictive backtest results. Do not tune thresholds to
these test results.

- Historical data: Yahoo adjusted daily OHLCV, 2000-01-01 through 2026-09-09.
- Primary cohort: current US-listed dashboard watchlist. Exclude MDA.TO from the
  US comparison to avoid mixing CAD returns and US calendar execution.
- Control: the nine original sector ETFs (XLK, XLF, XLV, XLY, XLI, XLP, XLE, XLB,
  XLU). Current constituent stock lists are not reconstructed.
- Primary evaluation period: 2023 onward. Earlier results (2010–2022) and yearly
  slices are robustness diagnostics. Existing rules may have been designed using
  these years; this is a fixed-rules retrospective holdout, not a pristine prospective test.
- Primary outcome: 21-session return from the NEXT open following the signal,
  after 10bp each side. Secondary horizons: 5, 63 and 252 sessions. Report hit
  rate, mean/median return, probability of losing at least 5%, and within-holding
  drawdown. Exclude unmatured horizons, and report sample sizes/coverage.
- Compare BUY, WAIT, AVOID and unconditional entries; use a matched-date average
  eligible-universe return to measure selection spread. Confidence intervals
  resample whole date blocks (63 sessions for the primary horizon), retaining
  cross-stock dependence and overlapping-window dependence within blocks.
- Test individual trend, momentum, RSI and downside filters diagnostically.
  Do not select or retune a winning filter after examining the holdout.
- Monthly portfolio illustration: observe prior close, buy at next open,
  hold to next monthly rebalance; idle cash earns zero, with 10bp per side.
  Compare the BUY basket, all eligible names on the same dates, a 200-day-only
  rule, and SPY buy-and-hold. No leverage, tax assumptions, or shorts.
- Refit historical band probabilities each January using only labels whose
  21-session outcomes had already occurred. Compare Brier error against each
  ticker's trailing unconditional up frequency.
- Independently verify no future-price leakage, next-open execution, fees,
  training-label maturity, and parity with the live scoring function.
- Current macro releases, news, analyst consensus, fundamentals and intraday
  events cannot be tested faithfully without timestamped historical snapshots.
  Do not describe the price-only validation as proof for these overlays.

Pass standard for a *demonstrated entry edge*: positive primary BUY-vs-universe
spread with a block interval above zero, stability across years and the ETF
control, and a practical benefit after costs. Otherwise report mixed or
unproven performance, regardless of a high raw win rate.
