"""Purchase eligibility and data checks shared by the dashboard and tests."""
import math
from datetime import timedelta, time

import pandas as pd


def rsi(closes, period=14):
    delta = closes.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    result = 100 - 100 / (1 + up / down.replace(0, float("nan")))
    return result.mask((down == 0) & (up > 0), 100).mask((down == 0) & (up == 0), 50)


def clean_bars(frame):
    if frame is None or frame.empty or "Close" not in frame:
        return None
    frame = frame.sort_index().loc[lambda x: ~x.index.duplicated(keep="last")].copy()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame = frame.loc[frame["Close"].map(lambda x: math.isfinite(x) and x > 0)]
    volume = frame["Volume"] if "Volume" in frame else pd.Series(0, index=frame.index)
    frame["Volume"] = pd.to_numeric(volume, errors="coerce").replace([float("inf"), -float("inf")], 0).fillna(0).clip(lower=0)
    return frame


def quote_quality(intra, daily, now, holidays):
    """Require recent intraday quotes during regular hours; otherwise the last
    completed US trading session. A weekend/holiday is not itself stale data.
    The exchange calendar supplied by the caller defines supported holidays.
    """
    invalid_close = False
    for frame in (daily, intra):
        if frame is not None and not frame.empty and "Close" in frame:
            try:
                value = float(frame.sort_index()["Close"].iloc[-1])
                invalid_close |= not math.isfinite(value) or value <= 0
            except (ValueError, TypeError):
                invalid_close = True
    di, it = clean_bars(daily), clean_bars(intra)
    latest_daily = di.index[-1].date() if di is not None and not di.empty else None
    stamp = None
    if it is not None and not it.empty:
        stamp = pd.Timestamp(it.index[-1])
        stamp = stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp
        stamp = stamp.tz_convert(now.tzinfo)
        if latest_daily and stamp.date() < latest_daily:
            stamp = None  # metrics use the newer daily close too
    result = {"data_status": "missing", "quote_as_of": None,
              "data_reason": "No valid price data", "history_as_of": str(latest_daily) if latest_daily else None}
    if invalid_close:
        result.update(data_status="invalid", data_reason="Latest price is missing, non-finite or non-positive")
        return result
    if stamp is None and latest_daily is None:
        return result
    result["quote_as_of"] = stamp.isoformat() if stamp is not None else str(latest_daily)
    quote_day = stamp.date() if stamp is not None else latest_daily
    trading_today = now.weekday() < 5 and now.date() not in holidays
    expected = now.date()
    # Give the daily provider a 30-minute closing-data grace period.
    if not trading_today or now.time() < time(16, 30):
        expected -= timedelta(days=1)
    while expected.weekday() >= 5 or expected in holidays:
        expected -= timedelta(days=1)
    if (latest_daily and latest_daily > now.date()) or quote_day > now.date() or (stamp is not None and (stamp - now).total_seconds() > 120):
        result.update(data_status="invalid", data_reason="Quote timestamp is in the future")
    elif latest_daily is None or latest_daily < expected:
        result.update(data_status="stale", data_reason="Daily history is older than the last completed session")
    elif trading_today and time(9, 30) <= now.time() < time(16):
        if stamp is None or not 0 <= (now - stamp).total_seconds() <= 20 * 60:
            result.update(data_status="stale", data_reason="Waiting for an intraday quote less than 20 minutes old")
        else:
            result.update(data_status="current", data_reason="Recent intraday quote")
    elif quote_day < expected:
        result.update(data_status="stale", data_reason="Quote is older than the last completed session")
    else:
        result.update(data_status="close", data_reason="Latest available quote; regular session is closed")
    return result


def entry_verdict(signal):
    """A new purchase decision, separate from a trend/position exit signal."""
    blockers = signal.get("buy_blockers") or []
    status = signal.get("data_status")
    if status not in ("current", "close"):
        action, reason = "WAIT", signal.get("data_reason") or "Quote freshness has not been verified"
    elif signal.get("action") == "N/A" or signal.get("history_days", 200) < 200:
        action, reason = "WAIT", signal.get("note") or "Need 200 daily closes to check the long-term trend"
    elif blockers or signal.get("action") == "SELL":
        action, reason = "AVOID", "; ".join(blockers) or "Negative trend and momentum; conditions do not support a new purchase"
    elif signal.get("action") == "BUY":
        action, reason = "BUY", "Trend and momentum pass the model's entry checks"
    else:
        action, reason = "WAIT", "Mixed signals or an extended price; wait for a stronger setup"
    signal.update(entry_action=action, entry_reason=reason)
    return signal


def validate_snapshot(data):
    """Reject empty shells and inconsistent purchase signals before publishing."""
    import json
    json.dumps(data, allow_nan=False)
    prices = [w.get("signal") or {} for w in data.get("watchlist", [])]
    prices += [s.get("metrics") or {} for s in data.get("sectors", [])]
    if not any(isinstance(p.get("price"), (int, float)) and p["price"] > 0 for p in prices):
        raise ValueError("Snapshot has no valid watchlist or sector prices")
    for sig in [w.get("signal") or {} for w in data.get("watchlist", [])] + data.get("picks", []):
        if sig.get("entry_action") == "BUY" and (sig.get("action") != "BUY" or sig.get("buy_blockers") or sig.get("data_status") not in ("current", "close")):
            raise ValueError("Snapshot contains a BUY that fails entry checks")
    return data
