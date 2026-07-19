# Strategy Deep Dive — July 19, 2026

## 1. What happened: the memory-stock crash the simulator missed

Between late June and mid-July 2026, memory stocks went from one of the year's hottest trades to a bear market. Micron, Samsung, and SK Hynix all fell 20%+ from their late-June closing highs; SK Hynix dropped ~14.6% and Samsung ~9% in a single session (July 2), heavy enough to force an emergency trading pause on the Kospi. Semiconductors as a group lost roughly $1.5 trillion in market value from June 25, with Micron alone shedding ~$350 billion. Triggers: a brokerage estimate putting SK Hynix Q2 profit 8% below consensus on slower HBM4 shipments, then TSMC-outlook and AI-capex worries spreading the rout to MU, WDC, SNDK, and STX.

The watchlist holds MU, WDC, SNDK, STX, SMH, SOXX, KLAC, and NVDA — this crash hit the portfolio squarely, and the dashboard stayed calm.

## 2. Why the old engine missed it

- **The Crash Radar only watched the S&P 500.** Its leading-indicator model (yield curve, credit, breadth, VIX term structure) is index-level. Memory fell 20-40% while the S&P slipped only modestly — no index-level alarm ever fired. Crashes cluster by industry; there was no sector-level detector.
- **The signal only saw 6 months of history.** No 200-day average, no 52-week high — the two reference points nearly every institutional trend model is built on. A stock 30% off a high it set 7 months ago looked merely "weak," not broken.
- **All inputs were slow.** 20/50-day averages, 1-month momentum, and RSI all lag a 2-3 week vertical drop; by the time they roll over, most of the damage is done.
- **The event dampener actively hid the crash.** `score × (1 − 0.35·risk)` shrank *negative* scores too — so near the Jul 14 CPI print and the Jul 28-29 FOMC (peak crash window), crashing names were pulled *back toward HOLD*.
- **The pullback guard only damped BUYs.** Nothing on the sell side was ever accelerated.

## 3. What changed: signal engine v2 (crash-aware)

Each guard is a standard, evidence-backed institutional technique:

| Guard | Rule | Industry basis |
|---|---|---|
| 200-day trend filter | price < 200d avg → no BUY possible, −10 pts | Faber's timing model; the best-documented drawdown-avoidance rule ("A Quantitative Approach to Tactical Asset Allocation"; AQR's "A Century of Evidence on Trend-Following") |
| 52-week-high drawdown | ≥10% off high → −12 pts; ≥20% → −25 pts + BUY cap | Absolute momentum (Antonacci's Dual Momentum): distance from the high is the cleanest regime tell |
| Fast-crash override | −12% in 10 days or −18% in a month → forced SELL (score ≤ −40), overrides everything | Crisis momentum / stop discipline — a 2-3 week sector rout looks exactly like this in real time |
| Volatility-spike guard | 10-day vol ≥ 1.8× 3-month vol → bullish score ×0.6 | Volatility targeting — vol clusters, and spikes precede fat left tails |
| Sector crash overlay | own sector/industry ETF ≥15% off its high → no BUY, −10 pts | Sector contagion: a healthy chart in a crashing industry usually catches down |
| Event dampener fix | dampener now shrinks only bullish conviction | A crashing name is no longer pulled back toward HOLD near Fed/CPI dates |

Supporting changes: daily history fetch went 6mo → 1y (the guards need it); a new **Sector Crash Watch** (all 11 sector ETFs + SMH/SOXX vs their 52-week highs, with ok/pullback/correction/bear/crash status) feeds the overlay and renders in the Crash Radar tab; the long-term quality boost can no longer lift a bear-regime name back into BUY.

**Verification on live data (Jul 17 close):** MU → SELL −78 (crash flag, −30% off high) · WDC → SELL −70 · SNDK → SELL −88 · STX → SELL −66 · SMH → SELL −70 · NVDA → SELL −86. Sector watch: SOXX −20.3% **bear**, SMH −16.8% **correction**, XLK −11.4% **correction**. Synthetic replay: a −14% two-week slide (still above its 200-day) already fires SELL −69 — the old engine showed HOLD at that point.

## 4. Deep dive: the surviving strategy — Buy & Hold Forever

All other sleeves (VOO timing, momentum ×2, watchlist confidence, dip-rotate, penny) are retired to `archive/`. Forever-hold was the best performer and is the only one kept.

**The record (2012-07-20 → 2026-07-17, 14.0 years, 15 names, equal weight):**

| | Forever basket | S&P 500 (SPY) |
|---|---|---|
| $5,000 lump sum → | **$374,202** | $35,600 |
| CAGR | **36.1%** | 14.9% |
| Sharpe | **1.17** | 0.92 |
| Max drawdown | −46.6% | −33.7% |
| Calendar years beating SPY | **11 of 14** | — |
| DCA $250/mo ($42,250 in) → | **$801,863** (37.1%/yr money-weighted) | 14.8%/yr |

**Why this one wins, and why the industry agrees:**
- Its edge is structural, not timing: zero turnover means zero short-term tax drag, zero slippage, and no whipsaw cost — the exact costs that killed the signal-trading sleeves after tax and slippage.
- It can't be scared out at the bottom. The backtests' worst self-inflicted wound is selling a compounder during a correction; a never-sell rule makes that impossible.
- It matches the evidence: most active rules fail to beat the index after costs; the reliable long-run outperformers are concentrated quality/momentum names *held*, not traded. Trend-following's value is in avoiding *entering* during crashes — which is where the v2 signal now does its job.

**Division of labor after this change:** forever-hold never sells; the v2 signal decides when new cash goes in. Its "Buy now?" entry read blends cheapness-vs-own-trend with the live signal, and the live signal is now crash-aware — so during a sector bear, the entry verdicts hold new cash back on names still falling fast, then flip to Accumulate as the fast-crash flags clear. Historically, buying this basket when its dip score was in today's band produced +27% average next-12-month returns with a 90% hit rate (n=2,557 days).

**Honest caveats (unchanged and important):**
- Survivorship: this basket is today's known winners; a list drawn in 2012 would have looked different. Forward results will very likely be more muted.
- The basket holds VOO/SMH/SOXX, so it overlaps its own benchmark by design.
- The deeper drawdown (−46.6% vs SPY's −33.7%) is the price of concentration in tech/semis — the current memory bear is being felt in full. Never-sell means riding it; the strategy's history says that has been the right trade 11 years out of 14, but nothing guarantees it.
- Not financial advice; a backtest is not a promise.

## 5. Calibrated confidence (July 19 upgrade)

The old "confidence" was |score| — signal strength dressed up as a percentage. It is now a four-stage probability:

1. **Calibration** (`signal_calibration.py`): the price-only v2 score is reconstructed over each name's ~10 years, every day is bucketed into a band (strong_sell → strong_buy), and each band is graded by its actual forward hit-rate (21-day headline; 1-year feeds the forever-hold entry blend). Thin bands shrink toward the pooled watchlist rate (empirical Bayes, M0=60). This immediately exposed an asymmetry the old number hid: SELL bands on long-run compounders were near coin-flips at 1 month (MU strong_sell: 54% of the time it was *higher* a month later, +57% avg the following year) while trend-aligned BUYs graded 70%+.
2. **Crash-risk weighting** (`fundamentals.py`): elevated index-level crash gauges (factors score above "Low", or Crash Radar 1-month odds above base) strip up to 12 pts from bullish confidence and add up to 8 to bearish.
3. **Fundamentals tilt**: revenue YoY growth, profit margin, earnings growth, and ROE combine into a 0-100 quality score (standard quant "quality" construction, Yahoo Finance data, cached daily); it moves confidence up to ±8 pts — good businesses damp SELL confidence, deteriorating ones damp BUYs.
4. **Street anchor**: analyst consensus (recommendation mean × coverage) maps to a 0-100 anchor; when ≥4 analysts cover a name, our confidence is blended 75/25 toward it and clamped within ±20 pts — the number can disagree with "what other places rank," but never wildly.

Verified Jul 17 close: MU SELL conf 46% → 31% (fundamentals −8, Street strong_buy ×42 → −9), AAPL BUY 62% → 68%, ETFs get the crash leg only. The forever-hold "Buy now?" live leg now uses the calibrated 1mo/1yr band up-odds, with a falling-knife cap (🔪): a name whose fast-crash flag is firing can't read Accumulate until the flag clears. The UI shows the full breakdown on hover.

## Sources

- [Yahoo Finance — Micron, Samsung, SK Hynix drag memory stocks into a bear market](https://finance.yahoo.com/markets/article/micron-samsung-sk-hynix-just-dragged-memory-stocks-into-a-bear-market-154549356.html)
- [CNBC — Samsung, SK Hynix tumble over 9% as chip rout spreads (Jul 2, 2026)](https://www.cnbc.com/2026/07/02/samsung-sk-hynix-shares-slide-kospi-tech-selloff-nasdaq.html)
- [24/7 Wall St — Micron, SanDisk, WDC fall 6% on SK Hynix outlook (Jul 13, 2026)](https://247wallst.com/investing/2026/07/13/micron-sandisk-western-digital-fall-6-as-sk-hynixs-weak-outlook-rattles-memory-stocks/)
- [Invezz — Memory stocks fall as TSMC outlook sparks chip selloff (Jul 16, 2026)](https://invezz.com/en-ae/news/2026/07/16/micron-sk-hynix-other-memory-stocks-fall-as-tsmc-outlook-sparks-chip-selloff/)
- [Hurst, Ooi & Pedersen (AQR) — A Century of Evidence on Trend-Following Investing](https://fairmodel.econ.yale.edu/ec439/hurst.pdf)
- [Alpha Architect — Avoiding the Big Drawdown with Trend-Following Investment Strategies](https://alphaarchitect.com/wp-content/uploads/2021/08/Avoiding_the_Big_Drawdown_with_Trend-Following_Investment_Strategies.pdf)
- [Newfound Research — Protect & Participate: Managing Drawdowns with Trend Following](https://blog.thinknewfound.com/2018/03/protect-participate-managing-drawdowns-with-trend-following/)
- [Man Group — Trend Following and Drawdowns](https://www.man.com/insights/is-this-time-different)
