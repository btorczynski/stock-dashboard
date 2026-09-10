"""Deterministic regression checks. No downloads or saved portfolio changes."""
import unittest
import copy
import json
import tempfile
from pathlib import Path
from datetime import datetime, date
from contextlib import ExitStack
from unittest.mock import patch

import numpy as np
import pandas as pd
import stock_dashboard as sd
import signal_calibration as calibration
import top_calls
import entry_rules as rules
import forever_hold
import simulator
import strategy


def bars(values, end="2026-09-08"):
    return pd.DataFrame({"Close": values, "Volume": 1000},
                        index=pd.bdate_range(end=end, periods=len(values)))


class SignalRegressions(unittest.TestCase):
    def test_flat_prices_have_neutral_rsi(self):
        self.assertEqual(sd._rsi(pd.Series([100.] * 50)).iloc[-1], 50)

    def test_short_history_cannot_buy(self):
        sig = sd.compute_signal(bars(np.linspace(90, 120, 20)), {})
        self.assertNotEqual(sig["action"], "BUY")

    def test_quality_cannot_undo_200_day_guard(self):
        sig = {"action": "HOLD", "score": 24, "vs200_pct": -1,
               "buy_blockers": ["below 200-day average"], "reasons": []}
        sd.apply_lt_discipline({"signal": sig, "drift": {"tag": "strong"},
                                "levels": {"lt_up": 70}})
        self.assertNotEqual(sig["action"], "BUY")

    def test_quality_cannot_undo_sector_guard_in_correction(self):
        sig = {"action": "HOLD", "score": 24, "crash_flag": "correction",
               "buy_blockers": ["sector drawdown"], "reasons": []}
        sd.apply_lt_discipline({"signal": sig, "drift": {"tag": "strong"}})
        self.assertNotEqual(sig["action"], "BUY")

    def test_top_buys_empty_when_all_names_sell(self):
        frame = bars(np.linspace(120, 60, 252))
        with patch.object(sd, "PICKS_UNIVERSE", ["AAPL"]):
            picks = sd.rank_picks(datetime.now(sd.ET), lambda _: {},
                                 {"AAPL": frame}, 0, {}, 0)
        self.assertEqual(picks, [])

    def test_infinite_values_rejected(self):
        self.assertIsNone(sd._safe_float(float("inf")))

    def test_sell_boundary_uses_sell_calibration(self):
        self.assertEqual(calibration.band_of(-25), "sell")

    def test_top_calls_keep_watchlist_discipline(self):
        picks = [{"symbol": "AAPL", "action": "BUY", "score": 90, "price": 100}]
        wl = [{"ticker": "AAPL", "signal": {"action": "HOLD", "score": 10, "price": 100}}]
        self.assertEqual(top_calls._candidates(picks, wl)[0]["action"], "HOLD")

    def test_bear_rebound_still_cannot_buy(self):
        frame = bars(np.r_[200, np.linspace(90, 95, 180), np.linspace(95, 150, 71)])
        s = sd.compute_signal(frame, {"data_status": "close"}, ext_bias=1)
        self.assertLess(s["score"], 25)
        self.assertEqual(s["entry_action"], "AVOID")

    def test_history_minimum_boundary(self):
        for n in (50, 179, 180, 199):
            with self.subTest(n=n):
                s = sd.compute_signal(bars(np.linspace(100, 120, n)), {"data_status": "close"})
                self.assertNotEqual(s["action"], "BUY")
                self.assertEqual(s["entry_action"], "WAIT")
        s = sd.compute_signal(bars(np.linspace(100, 120, 200)), {"data_status": "close"})
        self.assertEqual(s["entry_action"], "BUY")

    def test_live_price_only_scores_match_historical_scores(self):
        rng = np.random.default_rng(42)
        frame = bars(100 * np.exp(np.cumsum(rng.normal(.001, .025, 420))))
        historical = calibration.hist_scores(frame.Close)
        for n in (200, 201, 250, 310, 420):
            with self.subTest(n=n):
                sig = sd.compute_signal(frame.iloc[:n], {})
                self.assertEqual(sig["score"], historical.iloc[n - 1])

    def test_historical_scores_do_not_see_future_prices(self):
        frame = bars(100 + np.arange(400) * .1 + np.sin(np.arange(400)))
        original = calibration.hist_scores(frame.Close)
        frame.iloc[300:, 0] *= 10
        changed = calibration.hist_scores(frame.Close)
        pd.testing.assert_series_equal(original.iloc[:300], changed.iloc[:300])

    def test_crash_is_not_softened_by_events(self):
        frame = bars(np.r_[np.full(230, 100.), np.linspace(100, 70, 22)])
        for risk in (0, 1):
            sig = sd.compute_signal(frame, {"data_status": "close"}, event_risk=risk)
            self.assertLessEqual(sig["score"], -40)
            self.assertEqual(sig["entry_action"], "AVOID")

    def test_unsorted_duplicate_history_counts_unique_days(self):
        frame = bars(np.linspace(100, 120, 199))
        duplicated = pd.concat([frame.iloc[::-1], frame.iloc[-1:]])
        sig = sd.compute_signal(duplicated, {})
        self.assertEqual(sig["history_days"], 199)
        self.assertNotEqual(sig["action"], "BUY")


class DataRegressions(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 9, 11, 0, tzinfo=sd.ET)
        self.daily = bars(np.linspace(100, 120, 252))

    def intra(self, stamp):
        return pd.DataFrame({"Close": [121.], "Volume": [500]}, index=pd.DatetimeIndex([stamp]))

    def test_fresh_regular_quote_can_buy(self):
        metrics = sd.compute_metrics(self.intra("2026-09-09 10:59-04:00"), self.daily, self.now)
        self.assertEqual(metrics["data_status"], "current")
        self.assertEqual(sd.compute_signal(self.daily, metrics)["entry_action"], "BUY")

    def test_stale_regular_quote_pauses_purchase(self):
        metrics = sd.compute_metrics(self.intra("2026-09-09 10:00-04:00"), self.daily, self.now)
        sig = sd.compute_signal(self.daily, metrics)
        self.assertEqual(sig["entry_action"], "WAIT")

    def test_daily_only_during_regular_session_waits(self):
        metrics = sd.compute_metrics(None, self.daily, self.now)
        self.assertEqual(sd.compute_signal(self.daily, metrics)["entry_action"], "WAIT")

    def test_holiday_weekend_close_is_not_stale(self):
        daily = bars(np.linspace(100, 120, 252), end="2026-09-04")
        for day in (5, 6, 7, 8):
            now = datetime(2026, 9, day, 8, tzinfo=sd.ET)
            with self.subTest(day=day):
                self.assertEqual(sd.compute_metrics(None, daily, now)["data_status"], "close")

    def test_stale_daily_history_blocks_fresh_intraday(self):
        self.daily.index -= pd.Timedelta(days=10)
        metrics = sd.compute_metrics(self.intra("2026-09-09 10:59-04:00"), self.daily, self.now)
        self.assertEqual(metrics["data_status"], "stale")

    def test_newer_daily_close_beats_old_intraday_price(self):
        metrics = sd.compute_metrics(self.intra("2026-09-04 15:59-04:00"), self.daily,
                                     datetime(2026, 9, 8, 21, tzinfo=sd.ET))
        self.assertEqual(metrics["price"], 120)
        self.assertEqual(metrics["quote_as_of"], "2026-09-08")

    def test_invalid_latest_quote_waits(self):
        for price in (float("inf"), float("nan"), 0, -1):
            with self.subTest(price=price):
                frame = self.intra("2026-09-09 10:59-04:00")
                frame.iloc[0, 0] = price
                metrics = sd.compute_metrics(frame, self.daily, self.now)
                self.assertEqual(metrics["data_status"], "invalid")
                self.assertEqual(sd.compute_signal(self.daily, metrics)["entry_action"], "WAIT")

    def test_future_quote_or_history_waits(self):
        for frame, daily in ((self.intra("2026-09-10 10:59-04:00"), self.daily),
                              (self.intra("2026-09-09 10:59-04:00"), self.daily.set_axis(self.daily.index + pd.Timedelta(days=3)))):
            self.assertEqual(sd.compute_metrics(frame, daily, self.now)["data_status"], "invalid")

    def test_nan_json_and_empty_shells_rejected(self):
        for data in ({"watchlist": [{"signal": {}}], "sectors": [{}]},
                     {"watchlist": [{"signal": {"price": float("nan")}}]}):
            with self.assertRaises(ValueError):
                rules.validate_snapshot(data)

    def test_api_retains_error_and_disables_cache(self):
        data = {"updated_at": sd.time.time(), "session": {"state": "regular"}}
        with patch.dict(sd._cache, {"data": data, "error": "Provider unavailable"}):
            response = sd.app.test_client().get("/api/data")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["feed_status"]["stale"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertNotIn("feed_status", data)

    def test_api_loading_returns_503(self):
        with patch.dict(sd._cache, {"data": None, "error": None}):
            self.assertEqual(sd.app.test_client().get("/api/data").status_code, 503)


class ScorecardRegressions(unittest.TestCase):
    def test_weekend_does_not_log_duplicate_calls(self):
        state = top_calls._blank()
        picks = [{"symbol": "AAPL", "action": "BUY", "score": 40, "price": 100}]
        with patch.object(top_calls, "load_state", return_value=state), patch.object(top_calls, "save_state"):
            top_calls.compute(picks, [], {"AAPL": bars([100.], end="2026-09-04")},
                              as_of=datetime(2026, 9, 5, 12, tzinfo=sd.ET))
        self.assertEqual(state["log"], {})

    def test_intraday_call_is_not_backdated_to_yesterday(self):
        state = top_calls._blank()
        picks = [{"symbol": "AAPL", "action": "BUY", "score": 40, "price": 100,
                  "quote_as_of": "2026-09-09T10:59:00-04:00"}]
        with patch.object(top_calls, "load_state", return_value=state), patch.object(top_calls, "save_state"):
            top_calls.compute(picks, [], {"AAPL": bars([100.])},
                              as_of=datetime(2026, 9, 9, 11, tzinfo=sd.ET))
        self.assertIn("2026-09-09", state["log"])
        self.assertNotIn("2026-09-08", state["log"])

    def test_grade_uses_due_date_instead_of_latest_close(self):
        daily = {"AAPL": bars([110., 50.], end="2026-09-09")}
        state = top_calls._blank()
        state["log"]["2026-08-25"] = [{"symbol": "AAPL", "action": "BUY", "price": 100}]
        with patch.object(top_calls, "load_state", return_value=state), patch.object(top_calls, "save_state"):
            result = top_calls.compute([], [], daily)
        self.assertEqual(result["scorecard"]["hit_rate"], 100)
        self.assertEqual(state["log"]["2026-08-25"][0]["evaluated_on"], "2026-09-08")

    def test_missing_horizon_price_stays_pending(self):
        state = top_calls._blank()
        state["log"]["2026-08-01"] = [{"symbol": "AAPL", "action": "BUY", "price": 100}]
        with patch.object(top_calls, "load_state", return_value=state), patch.object(top_calls, "save_state"):
            result = top_calls.compute([], [], {"AAPL": bars([100., 110.])})
        self.assertEqual(result["scorecard"]["graded"], 0)
        self.assertEqual(result["scorecard"]["open"], 1)

    def test_legacy_calibration_is_not_used_on_download_failure(self):
        with patch.object(calibration, "load_state", return_value={"meta": {"schema": 1}}), patch.object(calibration, "compute", side_effect=RuntimeError("offline")):
            self.assertIsNone(calibration.ensure({}, ["AAPL"]))

    def test_forever_sleeve_cannot_override_entry_guard(self):
        for verdict in ("WAIT", "AVOID"):
            state = {"entry": {"holdings": [{"symbol": "AAPL", "dip_score": 100}], "overall": {}}}
            wl = [{"ticker": "AAPL", "signal": {"action": "BUY", "strength": 90,
                     "entry_action": verdict, "entry_reason": "blocked"}}]
            forever_hold.refresh_entry(state, wl)
            self.assertEqual(state["entry"]["holdings"][0]["verdict"], verdict)
            self.assertEqual(state["entry"]["overall"]["n_accumulate"], 0)

    def test_simulator_does_not_trade_on_future_prices(self):
        frame = bars(100 + np.arange(320) * .1 + np.sin(np.arange(320)))
        C = pd.DataFrame({"AAPL": frame.Close})
        first = simulator._run_rule(C, frame.Close, True, 5000)
        C.iloc[280:] *= 5
        second = simulator._run_rule(C, frame.Close, True, 5000)
        self.assertEqual(first[1][:79], second[1][:79])
        self.assertEqual(first[3][:79], second[3][:79])

    def test_strategy_signal_uses_prior_day(self):
        C = pd.DataFrame({"AAPL": np.arange(100) + 100.})
        first = strategy.signals(C)
        C.iloc[-1, 0] = 1
        self.assertEqual(first.iloc[-1, 0], strategy.signals(C).iloc[-1, 0])


def offline_snapshot():
    """Full assembly with synthetic quotes and external services stubbed."""
    now = datetime(2026, 9, 9, 11, tzinfo=sd.ET)
    daily, intra = {}, {}
    for i, sym in enumerate(sd.UNIVERSE):
        values = 100 + np.arange(420) * (.08 if i % 3 else -.08) + 2 * np.sin(np.arange(420) * .3)
        daily[sym] = bars(values)
        intra[sym] = pd.DataFrame({"Close": [values[-1]], "Volume": [500]},
                                 index=pd.DatetimeIndex(["2026-09-09 10:59-04:00"]))
    with ExitStack() as stack:
        stack.enter_context(patch.object(sd, "datetime", wraps=datetime)).now.return_value = now
        stack.enter_context(patch.object(sd, "fetch_all", return_value=(daily, intra)))
        stack.enter_context(patch.object(sd, "_download_one", return_value=("daily", {})))
        stack.enter_context(patch.object(sd.factors, "fetch_news", return_value={"headlines": [], "geo_risk": 0}))
        for module, method in ((sd.drift, "ensure"), (sd.watchlist_levels, "ensure"),
                               (sd.signal_calibration, "ensure"), (sd.fundamentals, "ensure"),
                               (sd.sim, "ensure_and_update"), (sd.insider, "ensure"),
                               (sd.forever_hold, "ensure"), (sd.crash_radar, "ensure"),
                               (sd.crash_radar, "load_state")):
            stack.enter_context(patch.object(module, method, return_value={}))
        stack.enter_context(patch.object(top_calls, "load_state", side_effect=top_calls._blank))
        stack.enter_context(patch.object(top_calls, "save_state"))
        return sd.build_snapshot()


class IntegrationRegressions(unittest.TestCase):
    def test_offline_snapshot_api_and_html(self):
        data = rules.validate_snapshot(offline_snapshot())
        self.assertEqual(len(data["watchlist"]), len(sd.WATCHLIST))
        self.assertTrue(data["picks"])
        self.assertTrue(all(p["entry_action"] == "BUY" for p in data["picks"]))
        with patch.dict(sd._cache, {"data": data, "error": None}):
            client = sd.app.test_client()
            self.assertEqual(client.get("/api/data").status_code, 200)
            self.assertIn(b"Before you buy", client.get("/").data)
            self.assertEqual(client.post("/api/refresh").status_code, 200)
            self.assertTrue(sd._force.is_set())
            sd._force.clear()

    def test_static_failure_preserves_existing_snapshot(self):
        import build_snapshot_static as export
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text('previous valid snapshot', encoding='utf-8')
            with patch.object(export, "OUT", folder), patch.object(sd, "build_snapshot", return_value={}), patch("yf_retry.install"):
                with self.assertRaises(ValueError):
                    export.main()
            self.assertEqual(path.read_text(), 'previous valid snapshot')

    def test_static_export_is_valid_utf8_json_and_html(self):
        import build_snapshot_static as export
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(export, "OUT", folder), patch.object(sd, "build_snapshot", return_value=offline_snapshot()), patch("yf_retry.install"):
                export.main()
            data = json.loads((Path(folder) / 'data.json').read_text(encoding='utf-8'))
            self.assertIn('_static', data)
            self.assertIn('Before you buy', (Path(folder) / 'index.html').read_text(encoding='utf-8'))

    def test_selfcheck_fails_for_empty_prices(self):
        import selfcheck
        with patch.object(sd, "build_snapshot", return_value={}):
            self.assertEqual(selfcheck.main(), 1)


if __name__ == "__main__":
    unittest.main()
