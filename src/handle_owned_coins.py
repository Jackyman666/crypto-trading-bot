from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from .config import TRADE_INTERVAL, TRADING_FREQUENCY_MS, SALES_RATIO
from.binance import BinanceClient
from .roostoo import RoostooClient
import pandas as pd
from .datastore import SQLiteDataStore
from .models import Trade


def coins_handler(execute_time: int, market_info: dict[str, Any]) -> None:
    db = SQLiteDataStore()
    bianance_client = BinanceClient()
    roostoo_client = RoostooClient()

    

    trades = db.fetch_trades()
    for t in trades:
        
        if t.entry == 1 and not sum(bool(x) for x in t.profit_level):
            continue

        order = roostoo_client.query_order(order_id=t.order_id)
        if t.entry == 0 and order["OrderMatched"][0]["Status"] != "FILLED":
            continue
        
        print(f"Handling owned coins for {t.coin}...")
        price_precision = market_info["TradePairs"][f"{t.coin}/USD"]["PricePrecision"]
        amount_precision = market_info["TradePairs"][f"{t.coin}/USD"]["AmountPrecision"]
        if t.entry == 0:
            # place three LIMIT sells and store *their* order IDs
            for i in range(len(SALES_RATIO)):
                
                placed = roostoo_client.place_order(
                    coin=t.coin,
                    side="SELL",
                    qty=round(t.quantity * SALES_RATIO[i], amount_precision),
                    price=round(t.profit_level[i], price_precision), 
                    order_type="LIMIT"
                )
                print(f"TRADE: {t}")
                print(f"LIMIT SELL: {placed}")
                print(f"Order: {order}")
                if not placed["Success"]:
                    break
                t.tp_order_ids.append(placed["OrderDetail"]["OrderID"])
        t.entry = 1

        data = bianance_client.get_historical_klines(
            symbol=f"{t.coin.upper()}USDT",
            interval=TRADE_INTERVAL,
            start_time=execute_time - TRADING_FREQUENCY_MS,
            end_time=execute_time,
            limit=1,
        )

        if data is None or data.empty or "high" not in data.columns or "low" not in data.columns:
            continue

        latest = data.sort_index().iloc[-1]
        latest_low  = float(latest["low"])

        for i in range(len(t.tp_order_ids)):
            sell_order = roostoo_client.query_order(order_id=t.tp_order_ids[i])
            if sell_order["OrderMatched"][0]["Status"] == "FILLED":
                # this TP rung was filled; remove it and corresponding SL/TP levels
                t.profit_level[i] = 0.0
                t.stop_loss[i] = 0.0

        remaining = sum(bool(x) for x in t.profit_level)
        if latest_low <= t.stop_loss[len(t.stop_loss) - remaining]:
            for oid in (t.tp_order_ids or []):
                roostoo_client.cancel_order(order_id=oid)
        remain_frac = {3: 1.00, 2: 0.50, 1: 0.25, 0: 0.00}.get(remaining, 0.0)
        remain_qty = t.quantity * remain_frac
        if remain_qty > 0:
            roostoo_client.place_order(
                coin=t.coin,
                side="SELL",
                qty=round(remain_qty, amount_precision),
                order_type="MARKET"
            )
        
    db.insert_trades(trades)
    
        # # if levels exist, evaluate this candle
        # if t.profit_level and t.stop_loss:
        #     first_tp = t.profit_level[0]
        #     first_sl = t.stop_loss[0]

        #     # TP hit → consume first rung (and drop its order id in the same index)
        #     sell_order = roostoo_client.query_order(order_id=t.tp_order_ids[0])
        #     if latest_high >= first_tp:
        #         t.profit_level.pop(0)
        #         t.stop_loss.pop(0)
        #         if t.tp_order_ids:
        #             t.tp_order_ids.pop(0)   # that TP should be filled; we no longer manage its id
        #         continue  # go next trade

        #     # SL hit → cancel ONLY this trade's remaining TP orders, then market exit remainder
        #     if latest_low <= first_sl:
        #         # cancel all still-pending TP orders for THIS trade
        #         for oid in (t.tp_order_ids or []):
        #             if oid:  # guard for None
        #                 try:
        #                     roostoo_client.cancel_order(order_id=oid)
        #                 except Exception:
        #                     pass

        #         # compute remaining qty based on rungs left (100%, 50%, 25%, 0%)
        #         left = len(t.profit_level)  # 3/2/1/0 remaining rungs
        #         remain_frac = {3: 1.00, 2: 0.50, 1: 0.25, 0: 0.00}.get(left, 0.0)
        #         remain_qty = t.quantity * remain_frac
        #         if remain_qty > 0:
        #             roostoo_client.place_order(
        #                 coin=t.coin, side="SELL", qty=remain_qty,
        #                 price=latest_low, order_type="MARKET"
        #             )

        #         # clear lists → this trade ends without touching other trades
        #         t.profit_level.clear()
        #         t.stop_loss.clear()
        #         t.tp_order_ids.clear()


    
        
