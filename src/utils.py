from .models import PivotPoint, Opportunity
from .config import SUPPORT_LINE_TIMEFRAME


def check_trend_conditions() -> bool:
    """Check if the trend SMA20>SMA50 on BIN or ETH occur"""
    return True

def check_pivot_conditions() -> bool:
    """Check if pivot points are"""
    return True

def check_support_line_conditions(pivot_1: PivotPoint, pivot_2: PivotPoint) -> bool:
    """Check if price is bouncing off support line"""
    return True

def check_minimum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if minimum conditions are met"""
    return True

def check_maximum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
    """Check if maximum conditions are met"""
    return True

def check_trade_conditions(opportunity: Opportunity) -> bool:
    """Check if the fibonacci retracement levels are met"""
    return True