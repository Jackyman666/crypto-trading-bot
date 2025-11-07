"""Project data models for pivot detection and trade candidates.

Provides lightweight, typed dataclasses for:
- PivotPoint: a detected pivot (high/low) with timestamp and price
- SupportLine: a simple linear fit across pivot timestamps/prices
- PotentialTrade: a candidate trade tied to a pivot and support/resistance
- TradeCollection: container for PotentialTrade objects

These are intentionally dependency-free (no pandas/numpy) so they are
easy to serialize and test. Small helper methods (to_dict/from_dict,
price_at) are provided.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal



def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
	return dt.isoformat() if dt is not None else None


def _iso_to_dt(s: Optional[str]) -> Optional[datetime]:
	return datetime.fromisoformat(s) if s is not None else None


@dataclass
class PivotPoint:
    """A pivot/fractal point in price time-series.

    Attributes:
        timestamp: when the pivot occurred (UTC-naive or timezone-aware)
        price: price value at pivot
        type: 'high' | 'low'

    """
    timestamp: datetime
    price: float
    position: int
    type: Literal["high", "low"]
    is_supported: Optional[bool] = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": _dt_to_iso(self.timestamp),
            "price": self.price,
            "type": self.type,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> PivotPoint:
        return PivotPoint(
            timestamp=_iso_to_dt(d["timestamp"]),
            price=float(d["price"]),
            type=d.get("type", "both"),
        )


@dataclass
class Opportunity:
	"""A simple linear support/resistance line fit to pivot points.

	The line is represented as: price = slope * t + intercept
	where t is a float unix timestamp. Use `price_at(dt)` to evaluate.
	If today is bullish, pivot_low = -1 (the pivot_low is minimum)
	If today is bearish, pivot_high = -1 (the pivot_high is maximum)
	"""

	support_line: float
	minimum: float
	maximum: float
	pivot_low: float
	pivot_high: float
	start: Optional[datetime] = None
	end: Optional[datetime] = None
	pivots: List[PivotPoint] = field(default_factory=list)
