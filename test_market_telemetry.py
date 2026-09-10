import unittest
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
import market_telemetry as mt
import dashboard_ui


def data():
    return pd.DataFrame({'Open':[100.,101.], 'High':[102.,103.], 'Low':[99.,100.],
                         'Close':[101.,102.], 'Volume':[1000,1200]},
                        index=pd.date_range('2026-09-09 14:30',periods=2,freq='min',tz='UTC'))


class TelemetryTests(unittest.TestCase):
    def test_ohlcv_matches_source(self):
        bars = mt.candles(data())
        self.assertEqual(bars[0], {'t':'2026-09-09T14:30:00+00:00','o':100.,'h':102.,'l':99.,'c':101.,'v':1000})

    def test_latest_bars_are_bounded_and_ordered(self):
        frame = data().iloc[::-1]
        self.assertEqual(mt.candles(frame,1)[0]['c'],102.)

    def test_missing_ohlc_is_not_invented(self):
        self.assertEqual(mt.candles(data()[['Close','Volume']]), [])

    def test_nonfinite_and_impossible_candles_are_removed(self):
        frame = data()
        frame.iloc[0,frame.columns.get_loc('High')] = 10
        frame.iloc[1,frame.columns.get_loc('Close')] = np.inf
        self.assertEqual(mt.candles(frame), [])

    def test_empty_series_are_explicit(self):
        result = mt.build({}, {}, [{'ticker':'AAPL'}], [], datetime.now(timezone.utc))
        self.assertEqual(result['series']['AAPL'],{'intraday':[],'daily':[]})

    def test_daily_dates_remain_exchange_dates(self):
        frame = data()
        frame.index = pd.date_range('2026-09-08',periods=2)
        self.assertEqual(mt.candles(frame)[0]['t'],'2026-09-08')

    def test_activity_uses_only_completed_bars(self):
        now = datetime(2026,9,9,14,31,30,tzinfo=timezone.utc)
        activity=mt.network_activity({'AAPL':data()},[{'symbol':'AAPL'}],now)
        self.assertEqual(len(activity['events']),1)
        self.assertEqual(activity['events'][0]['volume'],1000)
        self.assertEqual(activity['events'][0]['t'],'2026-09-09T14:30:00+00:00')
        self.assertFalse(activity['individual_trades'])

    def test_activity_skips_zero_volume_and_future_bars(self):
        frame=data(); frame.iloc[0,frame.columns.get_loc('Volume')]=0
        now=datetime(2026,9,9,14,31,tzinfo=timezone.utc)
        self.assertEqual(mt.network_activity({'AAPL':frame},[{'symbol':'AAPL'}],now)['events'],[])

    def test_activity_does_not_treat_daily_bars_as_trade_events(self):
        frame=data(); frame.index=pd.date_range('2026-09-08',periods=2)
        self.assertEqual(mt.network_activity({'AAPL':frame},[{'symbol':'AAPL'}],datetime.now(timezone.utc))['events'],[])

    def test_network_activity_includes_sector_stocks_outside_chart_watchlist(self):
        metric={'price':102.,'data_status':'current'}
        sector={'symbol':'XLK','name':'Technology','stocks':[{'symbol':'AAPL','metrics':metric}]}
        snapshot=mt.build({}, {'AAPL':data()}, [], [sector],datetime(2026,9,9,15,tzinfo=timezone.utc))
        self.assertNotIn('AAPL',snapshot['series'])
        self.assertEqual(len(snapshot['activity']['events']),2)

    def test_live_nodes_use_metrics_and_deduplicate(self):
        metric = {'price':123.45,'change_pct':-2.,'rvol':3.,'data_status':'current'}
        sector = {'symbol':'XLK','name':'Technology','stocks':[{'symbol':'AAPL','metrics':metric}]*2}
        result=mt.build({'AAPL':data()}, {}, [{'ticker':'AAPL'}], [sector], datetime.now(timezone.utc))
        self.assertEqual(len(result['nodes']),1)
        self.assertEqual(result['nodes'][0]['price'],123.45)
        self.assertEqual(result['nodes'][0]['change_pct'],-2.)
        json.dumps(result,allow_nan=False)

    def test_default_desk_and_purchase_panel_each_exist_once(self):
        h=dashboard_ui.INDEX_HTML
        self.assertEqual(h.count('id="tab-live"'),1)
        self.assertEqual(h.count('id="entryCards"'),1)
        self.assertEqual(h.count('id="liveSymbol"'),1)
        self.assertIn('class="tabbtn on" data-tab="tab-live"',h)
        self.assertLess(h.index('id="tab-signals"'),h.index('id="entryCards"'))


if __name__ == '__main__':
    unittest.main()
