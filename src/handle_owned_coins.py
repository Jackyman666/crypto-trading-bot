from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence
from .roostoo import RoostooClient
import pandas as pd
from .datastore import SQLiteDataStore
from .models import Trade


def coins_handler(data: pd.DataFrame, trades: list[Trade], roostoo_client: RoostooClient):
    
    if data is None or data.empty or "high" not in data.columns or "low" not in data.columns:
        return
    

    latest = data.sort_index().iloc[-1]
    latest_high = float(latest["high"])
    latest_low  = float(latest["low"])

    for t in trades:
        
        if t.entry == 1:
        # already finished? (both lists empty)
            if getattr(t, "profit_level", []) == [] and getattr(t, "stop_loss", []) == [] and getattr(t, "processed", False):
                continue
        
        # initialize ladders + place TPs once
        if not getattr(t, "entry", 1):

            db = SQLiteDataStore
            trades = db.fetch_trades()
            

            t.profit_level = trades.profit_level
            t.stop_loss    = trades.stop_loss
            t.tp_order_ids = []

            # split 50% / 25% / rest
            q1 = t.quantity * 0.50
            q2 = t.quantity * 0.25
            q3 = t.quantity - (q1 + q2)

            # place three LIMIT sells and store *their* order IDs
            for q, p in [(q1, tp1), (q2, tp2), (q3, tp3)]:
                placed = roostoo_client.place_order(
                    coin=t.coin, side="SELL", qty=q, price=p, order_type="LIMIT"
                )
                oid = (
                    str(placed["OrderDetail"]["OrderID"])
                    if placed and placed.get("Success") and "OrderDetail" in placed
                    else None
                )
                t.tp_order_ids.append(oid)
            t.entry = 1


        # if levels exist, evaluate this candle
        if t.profit_level and t.stop_loss:
            first_tp = t.profit_level[0]
            first_sl = t.stop_loss[0]

            # TP hit → consume first rung (and drop its order id in the same index)
            if latest_high >= first_tp:
                t.profit_level.pop(0)
                t.stop_loss.pop(0)
                if t.tp_order_ids:
                    t.tp_order_ids.pop(0)   # that TP should be filled; we no longer manage its id
                continue  # go next trade

            # SL hit → cancel ONLY this trade's remaining TP orders, then market exit remainder
            if latest_low <= first_sl:
                # cancel all still-pending TP orders for THIS trade
                for oid in (t.tp_order_ids or []):
                    if oid:  # guard for None
                        try:
                            roostoo_client.cancel_order(order_id=oid)
                        except Exception:
                            pass

                # compute remaining qty based on rungs left (100%, 50%, 25%, 0%)
                left = len(t.profit_level)  # 3/2/1/0 remaining rungs
                remain_frac = {3: 1.00, 2: 0.50, 1: 0.25, 0: 0.00}.get(left, 0.0)
                remain_qty = t.quantity * remain_frac
                if remain_qty > 0:
                    roostoo_client.place_order(
                        coin=t.coin, side="SELL", qty=remain_qty,
                        price=latest_low, order_type="MARKET"
                    )

                # clear lists → this trade ends without touching other trades
                t.profit_level.clear()
                t.stop_loss.clear()
                t.tp_order_ids.clear()


    
        
