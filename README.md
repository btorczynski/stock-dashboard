# Real-Time Market Bubbles + Signals + Strategy Simulator

A live, browser-based market dashboard that runs on your own machine:

- **Live Desk** — an API-driven trading-terminal view with candlesticks, volume bars, a sector heatmap, a quote strip, and a rotating stock network. It opens by default; the detailed purchase list remains on Signals.
- **Sector bubbles** — the 11 S&P sectors as circles whose **size scales with the size of the move** and whose color shows direction. Click a bubble to drill into its member stocks (also bubbles).
- **Top 5 losers & gainers** across all tracked stocks.
- **Unusual activity** flags for abnormal price moves and volume; **pre-market / after-hours** monitoring.
- **Purchase timing: BUY / WAIT / AVOID**, with reasons, source quote times and a filterable watchlist. Trend signals and adjusted ratings are shown separately from historical hit rates. The top-buy list only contains qualifying BUY entries.
- **Live futures** (S&P/Nasdaq/Dow, crude, gas, gold, silver, copper), a **commodity supply/demand** read, an **event calendar** (FOMC, CPI, jobs, share-issuance/lockups), and a **best-effort news + war/geopolitical** flag.
- **A $5,000 strategy simulator** that paper-trades the signals (holds the up-trend basket, rebalancing at each close), charting after-tax, after-slippage (10 bps per dollar traded) profit/loss vs **$5,000 left in the S&P 500 (SPY)**, with hover details showing exactly **what was bought and sold each day**. A dashed **control line** runs the identical rule on the 9 S&P sector ETFs — a fixed universe nobody cherry-picked — so you can see how much of the edge is hindsight stock-picking rather than the rule itself. Backtests with hand-picked universes carry **hindsight-selection warnings** in the UI.

Data: **Yahoo Finance** via `yfinance` (free, no API key).

## Live Desk and measured indicator performance

Select a watchlist symbol or sector to view its last 180 available one-minute
bars or 126 daily bars. Hover a bar for its actual OHLC and volume. Network
colors show price change, dot sizes show relative volume, and links group stocks
by sector; its rotation is a visual layout, not an additional trading signal.
The same `/api/data` snapshot powers every panel through its `telemetry` field.
No separate data service or browser charting dependency is required.

The network now shows incoming volume streaks that fly toward the corresponding
stock node and create a landing pulse. Each streak is one completed one-minute
OHLCV bar, labeled with its reported share volume. Green/red reflects that bar's
price direction; this API does not expose individual trades or aggressor side.
Repeated snapshots and revised bars do not create duplicate arrivals. The queue
waits until the sphere is on-screen, and pauses playback while scrolled away or
in a hidden tab. Fresh arrivals resume when visible; expired live records are
discarded. Live batches are spread over roughly 50 seconds between refreshes.
Stale data and closed markets pause live flow. **Replay recent activity** plays a finite,
clearly labeled sequence of recorded bars, including while markets are closed.
Reduced-motion preferences retain the recorded activity text without moving streaks.

The local server refreshes about every 60 seconds during active sessions and
every five minutes while closed; the browser polls every 15 seconds. Yahoo
quotes may be delayed. Each chart shows its source bar time. Missing bars remain
blank, stale quotes are marked, and a stale snapshot pauses purchase guidance.
Static hosting refreshes when the existing build publishes a new snapshot.

**The September 9 performance study did not establish a dependable timing edge.**
Across the recent holdout, BUY's matched-date 21-session return spread was
−0.64 percentage points on the current watchlist and −0.34 points on the sector
ETF control. The watchlist interval included zero; the ETF interval was negative.
BUY therefore means entry checks pass, not a demonstrated probability of profit.
The Live Desk displays this finding next to its entry readout.

See [the full results and limitations](INDICATOR_VALIDATION.md),
[the frozen evaluation plan](VALIDATION_PLAN.md), and
`indicator_validation_results.json` for coverage and reproducibility hashes.
The study tests the price/sector kernel, not the full historical live overlays.

```sh
python validate_indicators.py --download --output validation
python validate_indicators.py --output validation
node --test test_network_flow.js  # optional local JS regression check; also runs in CI
```

The second command replays cached inputs. Downloads and intermediate results
stay in `validation/`; these commands do not write simulator state. The offline
Python suite below now contains 60 regression, evaluation-harness and chart-data
checks; the JavaScript suite adds 13 activity-deduplication, visibility and playback checks.

## Entry checks and regression testing (September 2026)

The **Before you buy** panel answers whether the model's conditions support a
**new purchase**. BUY means trend/momentum pass its checks; WAIT means mixed
signals or insufficient/currently unavailable data; AVOID means downside guards
or negative long-term drift reject the entry. AVOID is not an instruction to
liquidate an existing position.

- Signals need 50 distinct daily closes to calculate the core indicators and
  **200 closes before any new BUY**. Long-term quality boosts cannot override a
  below-200-day trend, 20% drawdown, sector drawdown, or rapid-decline restriction.
- Regular-session purchases require an intraday quote no more than 20 minutes
  old and daily history through the previous completed session. Outside regular
  hours the latest available session is used; weekends and configured holidays
  do not themselves make Friday's close stale. The calendar is US-focused and
  currently lists 2026–2027 holidays; early closes and other exchange calendars
  are not modeled.
- Failed refreshes retain the last snapshot with a visible warning. The browser
  pauses purchase labels when the snapshot is stale: 3 minutes in active live
  sessions, 15 minutes while closed, or 20 minutes for static exports. The existing
  30-minute static publishing schedule can therefore show WAIT between builds.
- Ratings such as **72/100** are adjusted model scores, not success probabilities.
  The separate historical band hit rate uses a price-only model and overlapping
  observations; it does not validate the complete live model or establish an edge
  over buy-and-hold. CPI/CAPE inputs and some calendar events remain manually
  maintained, as labeled in the dashboard.
- Daily prices now use Yahoo's adjusted series, consistent with historical
  calibration. RSI treats unchanged prices as neutral. Calibration and forever
  caches rebuild once under the new schema; saved files are not deleted.
- New scorecard outcomes use the first available close at/just after the 14-day
  horizon, not the most recent price after an outage. Missing horizon prices
  remain pending. Already-graded legacy outcomes are preserved.

Run deterministic offline tests from the project directory after installing
`requirements.txt`:

```sh
python -m unittest discover -p "test_*.py" -v
```

The suite checks entry guards, quote freshness, historical/live score parity,
future-data leakage, scorecard grading, API responses, and static exports without
network requests or saved-state writes. The scheduled build runs it before
publishing. `python selfcheck.py` is a separate **live** integration check that
downloads data, updates caches, validates actual prices and exits nonzero on
failure; an empty BUY list is a valid outcome.

> **Not financial advice.** Everything is mechanical and rules-based, from public price data, futures, commodities, and slow-moving macro/event inputs. Quotes may be delayed. Past results do not predict the future.

---

## Quick start

**Windows:** double-click `run_dashboard.bat`.
**Mac / Linux:** double-click `run_dashboard.command` (first time: right-click → Open to clear Gatekeeper), or run `python3 stock_dashboard.py`.
Then open **http://localhost:8765**. First load takes ~20–40s while it pulls ~110 symbols + futures + macro.

**View on your iPhone:** run `run_phone.bat` (Windows) or `run_phone.command` (Mac). The console prints an address like `http://192.168.1.23:8765` — open it in Safari on the **same Wi-Fi** (Add to Home Screen for an app icon). LAN mode only; use on a trusted network.

---

## What's on screen

- **Top movers** (top of main column) — the 5 biggest losers and 5 biggest gainers.
- **Sector bubbles** — bigger bubble = bigger % move; green up / red down; `⚡` = unusual. Click to drill into member-stock bubbles.
- **Macro Backdrop** — 10Y yield, VIX, CPI, Shiller CAPE + a regime label. The header chip shows the combined **market bias** that tilts every signal.
- **Futures (live)** — index, energy, and metals futures (trade nearly 24h, so useful overnight/pre-market). Index futures feed the market bias.
- **Upcoming Events** — next FOMC rate decisions, CPI reports, jobs reports, and any share-issuance/lockup dates, with countdowns. Conviction is automatically reduced 1–2 days before Fed/CPI.
- **News · War/Geo Risk** — best-effort market headlines and a geopolitical-risk score that nudges the bias risk-off when conflict headlines spike.
- **Resources · Supply/Demand** — commodity-futures momentum (crude, gas, copper, gold) that tilts Energy and Materials signals.
- **Top 5 Buy Signals**, **Signals (Buy/Sell/Hold)** watchlist, and **Unusual Activity**.
- **Strategy Simulator** (bottom) — $5,000 P/L curve vs the S&P, with 🟢 new-buy / 🔴 sold-off markers; hover the chart to see each day's bought/sold names.

## How the signal is computed (transparent)

Composite score, −100…+100:

| Factor | Weight | Bullish when… |
|---|---|---|
| Price vs 50-day average | 30 | above |
| 20-day vs 50-day average | 20 | 20d above 50d |
| 1-month momentum | 25 | positive |
| RSI(14) | 15 | above 50 |
| Today's move | 10 | positive |
| **Market bias** (macro + index-futures + geopolitical) | ±20 | risk-on |
| **Commodity tilt** (Energy / Materials only) | ±~8 | rising crude/gas / metals |
| **Event dampener** | ×(1−0.35·risk) | — pulls scores toward Hold near Fed/CPI |

`score ≥ +25 → BUY`, `≤ −25 → SELL`, else `HOLD`. Strength % = |score|.

**Crash guards (signal v2, added after the Jul 2026 memory-stock crash slipped through):**

| Guard | Rule | Industry basis |
|---|---|---|
| 200-day trend filter | price < 200d avg → no BUY, −10 pts | Faber timing model / trend following |
| 52-week-high drawdown | ≥10% off high −12 pts · ≥20% off −25 pts + BUY cap | absolute momentum (Antonacci) |
| Fast-crash override | −12% in 10d or −18% in 1mo → forced SELL | crisis momentum / stop discipline |
| Volatility spike | 10d vol ≥ 1.8× 3-mo vol → bullish score ×0.6 | volatility targeting |
| Sector crash overlay | own sector/industry ETF ≥15% off high → no BUY, −10 pts | crashes cluster by industry |
| Event dampener fix | dampener now shrinks only bullish scores — a crashing name is no longer pulled back to HOLD | — |

The **Sector Crash Watch** strip in the Crash Radar tab tracks all 11 sector ETFs plus SMH/SOXX vs their 52-week highs — sector-level bears (like memory, Jul 2026) now alarm even when the S&P itself looks calm.

**Watchlist long-term discipline** (applied on top, watchlist only): durable compounders
(≥20%/yr 10-yr drift, high historical 1-yr up-odds) get a boost; a name with **negative
long-term drift is capped at HOLD**. A **pullback guard** damps BUY strength on
short-term overextension — overbought RSI ≥ 75, a ≥6% one-day spike, a ≥30% parabolic
month, weak historical 1-month up-odds, or a price above its own typical 3-month
target. Flags stack multiplicatively, so several at once force HOLD: the model buys
dips in long-term winners, not spikes.

## Data sources & keeping them current (edit in code)

- **Macro** live: `^TNX` (10Y), `^VIX`, `DX-Y.NYB` (dollar). Slow figures in `stock_dashboard.py → MACRO_CONSTANTS`: **CPI** 4.2% / core 2.9% (BLS, May 2026) and **Shiller CAPE** ~41 (June 2026, vs ~17 long-run). Update when new data prints.
- **Event calendar** in `factors.py`: `FOMC_2026` (next decision **Jul 28–29, 2026**), `CPI_2026` (June data prints **Jul 14**; later dates are estimates — replace with the official BLS schedule), jobs = first Friday auto-computed.
- **Share issuance / lockup expirations** (`factors.py → SUPPLY_EVENTS`): there is **no reliable free feed**, so this is a **manual, editable list** — add rows (ticker, date, type, note) as you learn of IPO-lockup expiries, secondary offerings, or big insider unlocks, and they'll appear in the calendar and flag the ticker.
- **News / war risk** (`factors.py → fetch_news`): best-effort free headlines; degrades gracefully if the feed is unavailable. **Real-time news sentiment and Trump/X posts were not included** — there's no reliable free source; that would need a paid news/X API key.

## Tuning (`stock_dashboard.py`)

```python
PRICE_PCT_THRESHOLD, RVOL_THRESHOLD   # unusual-activity flags
INTRA_INTERVAL = "1m"                 # "2m"/"5m" if rate-limited
MACRO_WEIGHT   = 20                   # how hard the bias tilts signals
PICKS_UNIVERSE, WATCHLIST             # what gets scored / listed
```
Simulator capital is `START_CAPITAL = 5000.0` in `simulator.py`.

## Files

| File | Purpose |
|------|---------|
| `stock_dashboard.py` | Backend: data, metrics, macro, signals, picks, movers, server |
| `factors.py` | Futures, commodity supply/demand, event calendar, news/geo risk |
| `dashboard_ui.py` | The dashboard web page (bubbles, panels, P/L chart) |
| `telemetry_ui.py`, `market_telemetry.py` | Live Desk graphics and bounded OHLCV/network API payload |
| `validate_indicators.py` | Historical next-open evaluation, annual calibration refits and baseline comparisons |
| `INDICATOR_VALIDATION.md`, `indicator_validation_results.json` | Measured performance, limitations and reproducibility metadata |
| `simulator.py` | $5,000 backtest + daily open→close paper-trading engine |
| `daily_summary.py` | After-close text summary (used by the scheduled task) |
| `strategy.py` | Shared signal/strategy helpers |
| `forever_hold.py` | **The strategy**: buy durable leaders + core ETFs, never sell (lump-sum & DCA variants, with entry "Buy now?" signals). The former sleeves (voo/momentum/basket/watchlist/dip/penny) are in `archive/` |
| `top_calls.py`, `drift.py`, `watchlist_levels.py`, `insider.py`, `crash_radar.py` | Top-calls scorecard, drift tags, support/resistance levels, insider flags, crash radar |
| `sim_state.json` (and other `*_state.json`) | Saved simulator history (created on first run) |
| `build_snapshot_static.py` | Builds a static `public/` snapshot for Cloudflare/GitHub Pages (see `DEPLOY_CLOUDFLARE.md`) |
| `selfcheck.py` | One-shot end-to-end health check (`python selfcheck.py`) |
| `requirements.txt` | Python dependencies |
| `run_dashboard.bat` / `.command` | One-click launchers (localhost) |
| `run_phone.bat` / `.command` | Launch in LAN mode to view on your iPhone |

All data is fetched on your own machine; nothing is sent anywhere else.
