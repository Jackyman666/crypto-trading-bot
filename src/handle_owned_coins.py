from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence
from .roostoo import RoostooClient
import pandas as pd

from .models import Trade

def coins_handler(data: pd.DataFrame, trades: list[Trade], roostoo_client: RoostooClient):
    """
    Long-only management:
      - Initialize per-trade TP/SL ladders and pre-place 3 TP LIMIT orders (50%, 25%, remainder).
      - On new candles, if latest high >= first TP -> pop one TP + one SL (ratchet).
      - If latest low <= first SL -> cancel all TPs, MARKET sell remaining, clear lists.
      - Trade considered finished when both lists are empty.
    """
    if data is None or data.empty or "high" not in data.columns or "low" not in data.columns:
        return

    # Latest candle values
    latest_high = data.sort_index()["high"].dropna().iloc[-1]
    latest_low  = data.sort_index()["low"].dropna().iloc[-1]

    for t in trades:
        # Skip finished trades
        if hasattr(t, "profit_level") and hasattr(t, "stop_loss"):
            if not t.profit_level and not t.stop_loss:
                # already finished (all levels consumed)
                continue

        # 1) Initialize ladder + place 3 TP LIMITs on first pass
        if not getattr(t, "processed", False):
            fib_range = t.maximum - t.minimum

            # Take-profit ladder (your spec)
            tp1 = t.support_line + fib_range * 1.000
            tp2 = t.support_line + fib_range * 1.618
            tp3 = t.support_line + fib_range * 2.618

            # Stop-loss ladder (your spec)
            sl1 = (t.minimum + t.support_line) / 2.0
            sl2 = t.minimum + t.support_line * 0.618
            sl3 = t.minimum + t.support_line * 1.000  # as specified

            t.profit_level = [tp1, tp2, tp3]
            t.stop_loss    = [sl1, sl2, sl3]

            # Pre-place 3 TP LIMIT sells: 50%, 25%, remainder
            q1 = t.quantity * 0.50
            q2 = t.quantity * 0.25
            q3 = t.quantity - (q1 + q2)

            # If your API needs "PAIR" like "BNB/USD", adapt here
            roostoo_client.place_order(
                coin=t.coin,
                side="SELL",
                qty=q1,
                price=tp1,
                order_type="LIMIT",
            )
            roostoo_client.place_order(
                coin=t.coin,
                side="SELL",
                qty=q2,
                price=tp2,
                order_type="LIMIT",
            )
            roostoo_client.place_order(
                coin=t.coin,
                side="SELL",
                qty=q3,
                price=tp3,
                order_type="LIMIT",
            )

            t.processed = True

        # 2) If still active, evaluate latest candle against first TP/SL
        if t.profit_level and t.stop_loss:
            first_tp = t.profit_level[0]
            first_sl = t.stop_loss[0]

            # TP hit: latest high breaches first TP -> consume one rung on both lists
            if latest_high >= first_tp:
                t.profit_level.pop(0)
                t.stop_loss.pop(0)   # ratchet stop to next level (SL2 or SL3)
                # nothing else to do here; the LIMIT order should have filled on venue

            # SL hit: latest low breaches first SL -> exit remainder now
            elif latest_low <= first_sl:
                # Cancel all remaining TP LIMIT orders for this coin (pair-wide)
                try:
                    roostoo_client.cancel_order(pair=f"{t.coin}/USD")
                except Exception:
                    # If your client only cancels by ID, you’d track + cancel each TP order ID instead.
                    pass

                # Compute remaining qty from how many TP levels are left:
                # 3 left -> 100% remain; 2 left -> 50%; 1 left -> 25%; 0 left -> 0
                remaining_fraction_map = {3: 1.00, 2: 0.50, 1: 0.25, 0: 0.00}
                remain_frac = remaining_fraction_map.get(len(t.profit_level), 0.0)
                remain_qty = t.quantity * remain_frac

                if remain_qty > 0:
                    roostoo_client.place_order(
                        coin=t.coin,
                        side="SELL",
                        qty=remain_qty,
                        price=latest_low,          # ignored by MARKET on most venues
                        order_type="MARKET",
                    )

                # Clear both lists -> trade over
                t.profit_level.clear()
                t.stop_loss.clear()


    
        
