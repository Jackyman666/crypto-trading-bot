"""Project data models for pivot detection and trade candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Literal


@dataclass
class PivotPoint:
    """A pivot/fractal point in price time-series.

    Attributes:
        timestamp: when the pivot occurred (UTC-naive or timezone-aware)
        price: price value at pivot
        type: 'high' | 'low'

    """
    timestamp: int
    price: float
    position: int
    type: Literal["high", "low"]
    is_supported: Optional[bool] = False

@dataclass
class Opportunity:
    """Simplified opportunity window bound to pivot extremes."""
    support_line: float
    minimum: float
    maximum: float
    relative_pivot: float
    action: str
    start: Optional[int] = None
    end: Optional[int] = None

@dataclass
class Trade:
    order_id: int
    quantity: float
    support_line: float
    minimum: float
    maximum: float
    stop_loss: float
    profit_level: float