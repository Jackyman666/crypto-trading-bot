from .models import PivotPoint, Opportunity
from .config import PIVOT_POINT_COMPARE, PIVOT_POINT_INTERVAL_MIN, MAXIMUM_PERCENTAGE_DIFFERENCE, MINIMUM_BREAKTHROUGH_PERCENTAGE, SUPPORT_LINE_TIMEFRAME


def check_trend_conditions() -> bool:
    """Check if the trend SMA20>SMA50 on BIN or ETH occur"""

    return True

def check_pivot_conditions() -> bool:
    """Check if pivot points are"""

    return True

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