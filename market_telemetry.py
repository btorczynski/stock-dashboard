"""Compact chart data for the Live Desk, drawn from the same quote snapshot."""
import math
from datetime import datetime, timedelta, timezone
from entry_rules import clean_bars


def candles(frame, limit=126):
    frame = clean_bars(frame)
    if frame is None or frame.empty:
        return []
    rows = []
    for stamp, row in frame.tail(limit).iterrows():
        values = [row.get(k) for k in ('Open', 'High', 'Low', 'Close')]
        try:
            o, h, l, c = [float(value) for value in values]
        except (ValueError, TypeError):
            continue
        if not all(math.isfinite(v) and v > 0 for v in (o,h,l,c)) or h < max(o,c) or l > min(o,c) or l > h:
            continue
        # Daily bars retain their exchange date; intraday bars carry UTC offsets.
        label = stamp.isoformat() if stamp.tzinfo else str(stamp.date())
        rows.append({'t':label, 'o':round(o,4), 'h':round(h,4), 'l':round(l,4),
                     'c':round(c,4), 'v':int(row.get('Volume',0))})
    return rows


def network_activity(intra, nodes, now):
    """Recent completed one-minute bars; Yahoo does not supply trade prints here."""
    events = []
    for node in nodes:
        for bar in candles(intra.get(node['symbol']), 7):
            stamp = datetime.fromisoformat(bar['t'])
            if stamp.tzinfo is None or stamp + timedelta(minutes=1) > now or bar['v'] <= 0:
                continue
            events.append({'symbol':node['symbol'], 't':bar['t'], 'open':bar['o'],
                           'close':bar['c'], 'volume':bar['v']})
    return {'kind':'volume_bars', 'interval_seconds':60, 'individual_trades':False,
            'events':sorted(events, key=lambda e:(e['t'],e['symbol']))}


def build(daily, intra, watchlist, sectors, now):
    symbols = {w['ticker'] for w in watchlist if w.get('ticker')}
    symbols.update(s['symbol'] for s in sectors)
    histories = {}
    for sym in sorted(symbols):
        histories[sym] = {'intraday':candles(intra.get(sym),180), 'daily':candles(daily.get(sym),126)}
    nodes = []
    seen = set()
    for sector in sectors:
        for stock in sector.get('stocks',[]):
            sym, metrics = stock['symbol'], stock.get('metrics') or {}
            if sym in seen:
                continue
            seen.add(sym)
            nodes.append({'symbol':sym, 'sector':sector['name'], 'price':metrics.get('price'),
                          'change_pct':metrics.get('change_pct'), 'rvol':metrics.get('rvol'),
                          'data_status':metrics.get('data_status'), 'quote_as_of':metrics.get('quote_as_of')})
    return {'as_of':now.astimezone(timezone.utc).isoformat(), 'provider':'Yahoo Finance',
            'series':histories, 'nodes':nodes, 'activity':network_activity(intra,nodes,now),
            'intraday_interval':'1 minute',
            'note':'Quotes may be delayed. Graphics refresh with the dashboard snapshot.'}
