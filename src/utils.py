from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

import pandas as pd

from .models import PivotPoint, Opportunity
from .config import (
    MAXIMUM_PERCENTAGE_DIFFERENCE,
    MINIMUM_BREAKTHROUGH_PERCENTAGE,
    PIVOT_POINT_COMPARE,
    SUPPORT_LINE_TIMEFRAME,
    TRADING_FREQUENCY_MS
)


def to_milliseconds(value: Any) -> int | None:
    """Normalize assorted timestamp-like inputs to epoch milliseconds."""

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, pd.Timestamp):
        return int(value.value // 1_000_000)

    if isinstance(value, datetime):
        ts = value.timestamp()
        return int(ts * 1000) if ts > 0 else None

    if hasattr(value, "timestamp"):
        try:
            ts = value.timestamp()
        except (TypeError, ValueError, OSError, OverflowError):
            ts = None
        if ts is not None and ts > 0:
            return int(ts * 1000)

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
        ts = dt.timestamp()
        return int(ts * 1000) if ts > 0 else None

    if numeric <= 0:
        return None
    if numeric >= 1_000_000_000_000:
        return int(numeric)
    return int(numeric * 1000)


def check_trend_conditions(data: pd.DataFrame) -> str:
    """Return trend classification from SMA(20) and SMA(50) on closing prices."""

    if data is None or data.empty:
        return "volatile"

    if "close" not in data.columns:
        return "volatile"

    closes = data.sort_index()["close"].dropna()
    short_window = 20
    long_window = 50

    if closes.size < long_window:
        return "volatile"

    sma_short = closes.tail(short_window).mean()
    sma_long = closes.tail(long_window).mean()

    if sma_short > sma_long:
        return "bullish"
    if sma_short < sma_long:
        return "bearish"
    return "volatile"


def update_pivots(data: pd.DataFrame, pivots: list[PivotPoint]):
    """Detect new pivot highs/lows since the most recent stored pivot and append them."""

    if data is None or data.empty:
        return "none"

    window = max(int(PIVOT_POINT_COMPARE), 1)
    if len(data) < (window * 2 + 1):
        return "none"

    df = data.sort_index()
    if not {"high", "low"}.issubset(df.columns):
        return "none"

    latest_threshold: int | None = None
    if pivots:
        try:
            latest_ts = int(pivots[-1].timestamp)
        except (TypeError, ValueError, AttributeError):
            latest_ts = 0
        if latest_ts > 0:
            latest_threshold = latest_ts - (2 * 15 * 60 * 1000)

    filtered_indices = []
    timestamps = [idx for idx in df.index]
    for idx, ts in enumerate(timestamps):
        if latest_threshold is None or ts >= latest_threshold:
            filtered_indices.append(idx)

    if not filtered_indices:
        return "none"

    start = max(filtered_indices[0], window)
    end = len(df) - window - 1
    if start > end:
        return "none"


    for candidate in range(start, end + 1):
        pivot_low = True
        pivot_high = True

        for neighbor in range(candidate - window, candidate + window + 1):
            row_candidate = df.iloc[candidate]
            row_neighbor = df.iloc[neighbor]
            if row_candidate["low"] > row_neighbor["low"]:
                pivot_low = False
            if row_candidate["high"] < row_neighbor["high"]:
                pivot_high = False

            if not pivot_low and not pivot_high:
                break

        timestamp_ms = timestamps[candidate]
        if timestamp_ms <= 0:
            continue
        if pivot_low:
            exists = any(
                p.timestamp == timestamp_ms and p.type == "low"
                for p in pivots
            )
            if not exists:
                pivots.append(
                    PivotPoint(
                        timestamp=timestamp_ms,
                        price=float(df.iloc[candidate]["low"]),
                        position=candidate,
                        type="low",
                        is_supported=False,
                    )
                )

        if pivot_high:
            exists = any(
                p.timestamp == timestamp_ms and p.type == "high"
                for p in pivots
            )
            if not exists:
                pivots.append(
                    PivotPoint(
                        timestamp=timestamp_ms,
                        price=float(df.iloc[candidate]["high"]),
                        position=candidate,
                        type="high",
                        is_supported=False,
                    )
                )


def update_support_resistance(pivots: list[PivotPoint], opportunities: list[Opportunity]):
    """Identify a support or resistance line and enqueue a new opportunity."""

    if len(pivots) < 2:
        return None

    # Configuration values
    tolerance_pct = abs(float(MAXIMUM_PERCENTAGE_DIFFERENCE))
    timeframe_limit_ms = SUPPORT_LINE_TIMEFRAME

    # Define both target types (support and resistance)
    target_types = ["low", "high"]

    for target_type in target_types:
        for i in range(len(pivots) - 1):
            pivot_1 = pivots[i]
            # Skip invalid or already used pivots
            if pivot_1.type != target_type or pivot_1.price is None or pivot_1.is_supported:
                continue

            for j in range(i + 1, len(pivots)):
                pivot_2 = pivots[j]
                # Skip invalid or already used pivots
                if pivot_2.type != target_type or pivot_2.price is None or pivot_2.is_supported:
                    continue

                # Check if pivots are within the timeframe limit
                time_gap = abs(pivot_2.timestamp - pivot_1.timestamp)
                if time_gap > timeframe_limit_ms:
                    break

                # Check price difference tolerance
                base_price = float(pivot_1.price)
                if base_price == 0:
                    continue

                diff_pct = abs(pivot_2.price - pivot_1.price) / base_price
                if diff_pct > tolerance_pct:
                    continue

                # A valid support/resistance line is found
                pivot_1.is_supported = True
                pivot_2.is_supported = True

                support_price = (pivot_1.price + pivot_2.price) / 2.0
                new_opportunity = Opportunity(
                    support_line=support_price,
                    minimum=0.0,
                    maximum=0.0,
                    pivot_low=0.0,
                    pivot_high=0.0,
                    start=pivot_2.timestamp,
                    end=None,
                )
                opportunities.append(new_opportunity)

def check_minimum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if minimum conditions after breaking through support are met"""
    # require a low pivot
    if pivot.type != "low":
        return False

    # ensure timestamps fall inside opportunity window when provided
    if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
        return False


    # threshold: pivot must be lower than avg by the configured percentage
    try:
        pct = float(MINIMUM_BREAKTHROUGH_PERCENTAGE)
    except Exception:
        return False
    
    avg = opportunity.support_line
    threshold = avg * (1.0 - pct)
    if pivot.price >= threshold:
        return False

    return True

def check_maximum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if maximum conditions after breaking out the previous high are met"""
    # require a high pivot
    if pivot.type != "high":
        return False

    # ensure timestamps fall inside opportunity window when provided
    if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
        return False
    

    # Check if price breaks above previous pivot high
    try:
        if opportunity.pivot_high is None or opportunity.pivot_high <= 0:
            return False
        
    except Exception:
        return False
    
    return True

def check_trade_conditions(
    data: pd.DataFrame | Sequence[Sequence[float]],
    opportunity: Opportunity,
) -> bool:
    """Check if the fibonacci retracement levels are met."""

    if opportunity is None:
        return False

    if isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        try:
            df = pd.DataFrame(
                data,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
        except Exception:
            return False

    if df.empty or not {"low", "high"}.issubset(df.columns):
        return False

    df = df.sort_index()
    last = df.iloc[-1]

    try:
        pl1 = float(getattr(opportunity, "minimum"))
        ph2 = float(getattr(opportunity, "maximum"))
    except (TypeError, ValueError):
        return False

    if not (ph2 > pl1):
        return False

    buy_price = pl1 + 0.618 * (ph2 - pl1)

    try:
        low = float(last["low"])
        high = float(last["high"])
    except (TypeError, ValueError, KeyError):
        return False

    return low <= buy_price <= high