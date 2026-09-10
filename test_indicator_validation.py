"""Tests for the validation machinery, with no network or saved-state writes."""
import unittest
import numpy as np
import pandas as pd
import validate_indicators as v
import stock_dashboard as sd


def frame(opens):
    return pd.DataFrame({'Open':opens, 'High':opens, 'Low':opens, 'Close':opens, 'Volume':1000},
                        index=pd.bdate_range('2022-01-03', periods=len(opens)))


class ValidationMathTests(unittest.TestCase):
    def test_trade_starts_next_open(self):
        f = frame([100., 200., 210., 220., 240.])
        r = v.future_return(f, 2, cost=0)
        self.assertAlmostEqual(r.iloc[0], 220/200 - 1)
        self.assertTrue(r.iloc[-3:].isna().all())

    def test_two_sided_trading_cost(self):
        f = frame([100.] * 10)
        result = v.future_return(f, 5)
        self.assertAlmostEqual(result.iloc[0], (1-v.FEE)/(1+v.FEE)-1)

    def test_forward_drawdown_excludes_signal_day_and_exit_day(self):
        f = frame([1., 100., 80., 120., 10.])
        result = v.future_drawdown(f, 3)
        self.assertAlmostEqual(result.iloc[0], -.20)

    def test_probability_training_excludes_unmatured_labels(self):
        f = frame(np.linspace(100, 200, 400))
        cut = f.index[300]
        scores = v.cal.hist_scores(f.Close)
        train = v.close_label_training(f.Close, scores, cut)
        self.assertEqual(train.index[-1], f.index[278])
        changed = f.Close.copy()
        changed.iloc[300:] *= 5
        pd.testing.assert_frame_equal(train, v.close_label_training(changed, scores, cut))

    def test_no_future_price_leakage_in_features(self):
        f = frame(100 + np.arange(500)*.1 + np.sin(np.arange(500)))
        base = v.features(f)
        f.iloc[300:, f.columns.get_loc('Close')] *= 5
        pd.testing.assert_frame_equal(base.iloc[:300], v.features(f).iloc[:300])

    def test_entry_matches_live_sector_guards(self):
        f = frame(100 + np.arange(260)*.1 + np.sin(np.arange(260)))
        sector = frame(np.linspace(100, 60, 260))
        h = v.features(f, sector)
        s = sd.compute_signal(f, {'data_status':'close'}, sector_dd=h.sector_dd.iloc[-1]*100)
        self.assertEqual(h.entry.iloc[-1], s['entry_action'])

    def test_bootstrap_constant_has_constant_interval(self):
        for bound in v.bootstrap_mean([.02]*100, n_boot=30):
            self.assertAlmostEqual(bound, .02)

    def test_monthly_portfolio_charges_all_round_trips(self):
        f = frame(np.full(300, 100.))
        features = pd.DataFrame({'score':40., 'entry':'BUY', 'above200':True},index=f.index)
        nav, stats = v.monthly_portfolio({'SPY':f,'AAPL':f}, {'AAPL':features}, ['AAPL'], 'buy', '2022-02-01')
        expected = ((1-v.FEE)/(1+v.FEE)) ** stats['months']
        self.assertAlmostEqual(nav.iloc[-1], expected)

    def test_cash_does_not_earn_stock_returns(self):
        f = frame(np.linspace(100, 200, 300))
        features = pd.DataFrame({'score':-40., 'entry':'AVOID', 'above200':False},index=f.index)
        nav, stats = v.monthly_portfolio({'SPY':f,'AAPL':f}, {'AAPL':features}, ['AAPL'], 'buy', '2022-02-01')
        self.assertTrue((nav == 1).all())
        self.assertEqual(stats['invested_month_pct'], 0)

    def test_monthly_portfolio_uses_prior_close_signal(self):
        f = frame(np.linspace(100, 200, 300))
        fs = pd.DataFrame({'score':40., 'entry':'BUY', 'above200':True},index=f.index)
        nav, _ = v.monthly_portfolio({'SPY':f,'AAPL':f}, {'AAPL':fs}, ['AAPL'], 'buy', '2022-02-01')
        # Changing the signal on the execution day cannot affect February's position.
        fs.loc['2022-02-01','entry'] = 'AVOID'
        changed, _ = v.monthly_portfolio({'SPY':f,'AAPL':f}, {'AAPL':fs}, ['AAPL'], 'buy', '2022-02-01')
        pd.testing.assert_series_equal(nav, changed)

    def test_matched_spread_compares_same_dates(self):
        fwd = pd.DataFrame({'A':[.1,-.1], 'B':[.2,-.2]})
        mask = pd.DataFrame({'A':[True,False], 'B':[False,False]})
        result = v.summarize(fwd,mask,fwd,bootstrap=False)
        self.assertAlmostEqual(result['matched_spread_pct'], -5.)
        self.assertEqual(result['observations'], 1)


if __name__ == '__main__':
    unittest.main()
