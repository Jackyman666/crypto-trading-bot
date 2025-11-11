from __future__ import annotations

from datetime import datetime
from typing import Any
from .roostoo import RoostooClient
from .binance import BinanceClient
import pandas as pd

from .models import PivotPoint, Opportunity, Trade
from .config import (
    MAXIMUM_PERCENTAGE_DIFFERENCE,
    MINIMUM_BREAKTHROUGH_PERCENTAGE,
    PIVOT_POINT_COMPARE,
    SUPPORT_LINE_TIMEFRAME,
    TIME_EXTEND_MS,
    SET_TRADE_QUANTITY,
    TRADE_INTERVAL,
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


def check_trend_conditions(execute_ms: int) -> str:
    """Return trend classification from SMA(20) and SMA(50) on closing prices."""
    
    datasource = BinanceClient()
    btc_start_ms = execute_ms - TRADING_FREQUENCY_MS * 50
    btc_data = datasource.get_historical_klines(
        symbol="BTCUSDT",
        interval=TRADE_INTERVAL,
        start_time=btc_start_ms,
        end_time=execute_ms,
        limit=50,
    )
    
    # print(f"btc_data length: {len(btc_data)}")
    # print("btc_data details:")
    # print(btc_data)
    
    if "close" not in btc_data.columns:
        return "volatile"

    closes = btc_data.sort_index()["close"].dropna()
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

    
    # Define both target types (support and resistance)
    target_types = ["low", "high"]

    for target_type in target_types:
        for i in range(len(pivots) - 1):
            # Skip invalid or already used pivots
            if pivots[i].type != target_type or pivots[i].price is None or pivots[i].is_supported:
                continue

            for j in range(i + 1, len(pivots)):
                # Skip invalid or already used pivots
                if pivots[j].type != target_type or pivots[j].price is None or pivots[j].is_supported:
                    continue
                
                # Skip non consecutive part
                if any(pivots[k].type == target_type for k in range(i+1,j)):
                    continue  
                
                # Check if pivots are within the timeframe limit
                time_gap = abs(pivots[j].timestamp - pivots[i].timestamp)
                if time_gap > SUPPORT_LINE_TIMEFRAME:
                    break

                # Check price difference tolerance
                base_price = float(pivots[i].price)
                if base_price == 0:
                    continue

                diff_pct = abs(pivots[j].price - pivots[i].price) / base_price
                if diff_pct > MAXIMUM_PERCENTAGE_DIFFERENCE:
                    continue

                # A valid support/resistance line is found
                pivots[i].is_supported = True
                pivots[j].is_supported = True

                support_price = (pivots[i].price + pivots[j].price) / 2.0
                new_opportunity = Opportunity(
                    support_line=support_price,
                    minimum=0.0,
                    maximum=0.0,
                    relative_pivot=0.0,
                    action="N/A",
                    start=pivots[j].timestamp,
                    end=pivots[j].timestamp + SUPPORT_LINE_TIMEFRAME,
                    extrema_timestamp=0
                )
                opportunities.append(new_opportunity)

def can_trade(
    coin: str,pivots: list[PivotPoint], opportunities: list[Opportunity],
    trades: list[Trade], trend: str, amount_precision: int, price_precision: int
    ) -> None:
    """
    Determines whether a trade can be placed based on the trend, pivots, and opportunities.

    Args:
        pivots: List of PivotPoint objects.
        opportunities: List of Opportunity objects to update.
        trend: "bullish" or "bearish".
        roostoo_client: Client object to interact with Roostoo for placing orders and retrieving balances.
    """
    if not pivots or not opportunities or trend not in ["bullish", "bearish"]:
        return
    roostoo_client = RoostooClient()  # Initialize the Roostoo client
    for opportunity in opportunities:
        if opportunity.action != "N/A":
            continue

        if trend == "bullish":
            # Find the pivot high (relative_pivot)
            for i in range(len(pivots)):
                if pivots[i].timestamp < opportunity.start or pivots[i].timestamp < opportunity.extrema_timestamp:
                    continue
                if pivots[i].type == "low" and pivots[i].price < opportunity.support_line * (1 - MINIMUM_BREAKTHROUGH_PERCENTAGE):
                    opportunity.minimum = pivots[i].price
                    opportunity.end += TIME_EXTEND_MS
                    opportunity.extrema_timestamp = pivots[i].timestamp
                for j in range(i-1, -1, -1):
                    if pivots[j].type == "high":
                        opportunity.relative_pivot = pivots[j].price
                        break
                if opportunity.minimum > 0 and pivots[i].price > opportunity.relative_pivot:
                    opportunity.maximum = pivots[i].price
                    break
        
        # elif trend == "bearish":
        #     # Find the pivot low (relative_pivot)
        #     pivot_low = next((p for p in pivots if p.type == "low" and p.price < opportunity.support_line * (1 - MINIMUM_BREAKTHROUGH_PERCENTAGE)), 0)
        #     if not pivot_low:
        #         continue

        #     opportunity.relative_pivot = pivot_low.price

        #     # Find the maximum (pivot point higher than pivot low)
        #     maximum = max((p.price for p in pivots if p.price > pivot_low.price), 0)
        #     if not maximum:
        #         continue
            
        #     opportunity.end += TIME_EXTEND_MS
        #     opportunity.maximum = maximum

        #     # Find the minimum (pivot point lower than support line)
        #     minimum = min((p.price for p in pivots if p.price < opportunity.support_line * (1 - MINIMUM_BREAKTHROUGH_PERCENTAGE)), 0)
        #     if not minimum:
        #         continue

        #     opportunity.minimum = minimum
        
        # Get balance and calculate order quantity
        balance = roostoo_client.get_balance()
        if not balance["Success"]:
            continue
        
        print(balance)
        usd_balance = balance["SpotWallet"]["USD"]["Free"]
        # Calculate the order price and quantity
        order_price = opportunity.minimum + 0.618 * (opportunity.maximum - opportunity.minimum)
        order_quantity = (usd_balance * SET_TRADE_QUANTITY) / order_price
        order_quantity = round(order_quantity, amount_precision)
        order_price = round(order_price, price_precision)
        print(f"USD Balance: {usd_balance}, Order Price: {order_price}, Order Quantity: {order_quantity}")
        # Place the order
        action = "BUY"
        placed_order = roostoo_client.place_order(
            coin=coin, 
            side=action,
            qty=order_quantity,
            price=order_price,
            order_type="LIMIT",
        )
        
        if placed_order["Success"]:
            opportunity.action = action
            fib_range = opportunity.maximum - opportunity.minimum
            trades.append(Trade(
                coin=coin,
                order_id=placed_order["OrderDetail"]["OrderID"],
                quantity=order_quantity,
                stop_loss=[(opportunity.minimum + opportunity.support_line)/2, opportunity.minimum + fib_range*0.618, fib_range*1.000],
                profit_level=[fib_range*1.000, fib_range*1.618, fib_range*2.618],
                tp_order_ids=[],
                entry=0,
            ))
        else:
            opportunity.action = "N/A"

# def check_minimum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
#     """Check if minimum conditions after breaking through support are met"""
#     # require a low pivot
#     if pivot.type != "low":
#         return False

#     # ensure timestamps fall inside opportunity window when provided
#     if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
#         return False


#     # threshold: pivot must be lower than avg by the configured percentage
#     try:
#         pct = float(MINIMUM_BREAKTHROUGH_PERCENTAGE)
#     except Exception:
#         return False
    
#     avg = opportunity.support_line
#     threshold = avg * (1.0 - pct)
#     if pivot.price >= threshold:
#         return False

#     return True

# def check_maximum_conditions(pivot: PivotPoint, opportunity: Opportunity) -> bool:
#     """Check if maximum conditions after breaking out the previous high are met"""
#     # require a high pivot
#     if pivot.type != "high":
#         return False

#     # ensure timestamps fall inside opportunity window when provided
#     if getattr(opportunity, "start", None) is not None and pivot.timestamp < opportunity.start:
#         return False
    

#     # Check if price breaks above previous pivot high
#     try:
#         # Use the new `relative_pivot` field which represents the pivot
#         # level used to determine breakouts. Require a positive value.
#         rp = float(getattr(opportunity, "relative_pivot", 0.0))
#         if rp <= 0:
#             return False
        
#     except Exception:
#         return False
    
#     return True
