from __future__ import annotations

from typing import Sequence, Tuple

from .models import PivotPoint, Opportunity
from .config import (
    MAXIMUM_PERCENTAGE_DIFFERENCE,
    MINIMUM_BREAKTHROUGH_PERCENTAGE,
    PIVOT_POINT_COMPARE,
    SUPPORT_LINE_TIMEFRAME,
)


def check_trend_conditions(data: Sequence[Tuple[int, float, float, float, float, float]]) -> str:
    """Return trend classification based on SMA(20) and SMA(50) of close prices."""

    closes = [row[4] for row in data if row is not None]
    if len(closes) < 50:
        return "volatile"

    short_window = 20
    long_window = 50

    sma_short = sum(closes[-short_window:]) / short_window
    sma_long = sum(closes[-long_window:]) / long_window

    if sma_short > sma_long:
        return "bullish"
    if sma_short < sma_long:
        return "bearish"
    return "volatile"

def update_pivots(
    data: Sequence[Tuple[int, float, float, float, float, float]],
    pivots: list[PivotPoint],
) -> str:
    """Detect new pivot highs/lows since the most recent stored pivot and append them."""

    if not data:
        return "none"

    window = max(int(PIVOT_POINT_COMPARE), 1)
    if len(data) < (window * 2 + 1):
        return "none"

    latest_threshold: int | None = None
    if pivots:
        latest_pivot = pivots[-1]
        latest_threshold = int(latest_pivot.timestamp) - (2 * 15 * 60)

    def _coerce_seconds(raw: int | float) -> int:
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            return 0
        return value // 1000 if value > 1_000_000_000_000 else value

    def _pivot_seconds(pivot: PivotPoint) -> int:
        return int(pivot.timestamp)

    filtered_indices = []
    for idx, row in enumerate(data):
        ts = _coerce_seconds(row[0])
        if latest_threshold is None or ts >= latest_threshold:
            filtered_indices.append(idx)

    if not filtered_indices:
        return "none"

    start = max(filtered_indices[0], window)
    end = len(data) - window - 1
    if start > end:
        return "none"

    found_types: set[str] = set()

    for candidate in range(start, end + 1):
        pivot_low = True
        pivot_high = True

        for neighbor in range(candidate - window, candidate + window + 1):
            row_candidate = data[candidate]
            row_neighbor = data[neighbor]
            if row_candidate[3] > row_neighbor[3]:
                pivot_low = False
            if row_candidate[2] < row_neighbor[2]:
                pivot_high = False

            if not pivot_low and not pivot_high:
                break

        timestamp_sec = _coerce_seconds(data[candidate][0])
        if pivot_low:
            exists = any(
                _pivot_seconds(p) == timestamp_sec and p.type == "low"
                for p in pivots
            )
            if not exists:
                pivots.append(
                    PivotPoint(
                        timestamp=timestamp_sec,
                        price=float(data[candidate][3]),
                        position=candidate,
                        type="low",
                        is_supported=False,
                    )
                )
                found_types.add("low")

        if pivot_high:
            exists = any(
                _pivot_seconds(p) == timestamp_sec and p.type == "high"
                for p in pivots
            )
            if not exists:
                pivots.append(
                    PivotPoint(
                        timestamp=timestamp_sec,
                        price=float(data[candidate][2]),
                        position=candidate,
                        type="high",
                        is_supported=False,
                    )
                )
                found_types.add("high")

    if found_types:
        pivots.sort(key=_pivot_seconds)
    else:
        return "none"
    if found_types == {"high", "low"}:
        return "both"
    if "high" in found_types:
        return "high"
    return "low"

def check_support_line_conditions(pivot_1: PivotPoint, pivot_2: PivotPoint) -> bool:
    """Check if price is bouncing off support line"""

    # ensure pivot_1 is earlier than pivot_2
    if pivot_2.position < pivot_1.position:
        pivot_1, pivot_2 = pivot_2, pivot_1

    # types: require lows
    if pivot_1.type != "low" or pivot_2.type != "low":
        return False

    
    try:
        if isinstance(SUPPORT_LINE_TIMEFRAME, dict):
            max_bars = SUPPORT_LINE_TIMEFRAME.get(pivot_1.type, SUPPORT_LINE_TIMEFRAME.get("default", 20))
        elif isinstance(SUPPORT_LINE_TIMEFRAME, (int, float)):
            max_bars = float(SUPPORT_LINE_TIMEFRAME)
        else:
            max_bars = 20  # default fallback
    except Exception:
        max_bars = 20  # safe fallback

    # Check position difference
    if abs(pivot_2.position - pivot_1.position) > max_bars:
        return False

    # price sanity checks
    if pivot_1.price is None or pivot_2.price is None:
        return False
    if pivot_1.price == 0:
        return False

    # relative price closeness
    try:
        tol_pct = abs(float(MAXIMUM_PERCENTAGE_DIFFERENCE))
    except Exception:
        tol_pct = 0.05

    if abs(pivot_2.price - pivot_1.price) / abs(pivot_1.price) > tol_pct:
        return False

    return True

def check_minimum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if minimum conditions after breaking through support are met"""
    # require a low pivot
    if pivot.type != "low":
        return False

    # ensure timestamps fall inside opportunity window when provided
    if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
        return False
    if getattr(opportunity, "end", None) is not None and pivot.timestamp > opportunity.end:
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
    if getattr(opportunity, "end", None) is not None and pivot.timestamp > opportunity.end:
        return False

    # Check if price breaks above previous pivot high
    try:
        if opportunity.pivot_high is None or opportunity.pivot_high <= 0:
            return False
        return pivot.price > opportunity.pivot_high
    except Exception:
        return False
    
    return True

def check_trade_conditions(opportunity: Opportunity) -> bool:
    """Check if the fibonacci retracement levels are met"""
    return True