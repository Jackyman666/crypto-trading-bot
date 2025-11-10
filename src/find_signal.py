from __future__ import annotations
from datetime import datetime

import pandas as pd

from .models import Trade
from .utils import (
    update_pivots,
    update_support_resistance,
    check_trend_conditions,
    to_milliseconds,
    can_trade
)
from .config import TRADING_FREQUENCY_MS, SUPPORT_LINE_TIMEFRAME
from .datastore import SQLiteDataStore
from .binance import BinanceClient


def findSignal(coin: str, executeTime: int, btc_data: pd.DataFrame, amount_precision: int, price_precision: int) -> None:
    db = SQLiteDataStore()
    db.initialize()
    datasource = BinanceClient()
    execute_ms = to_milliseconds(executeTime)
    if execute_ms is None:
        raise ValueError("Execution time must be numeric and positive")

    pivots = db.fetch_pivots(
        coin,
        since=execute_ms - 7 * SUPPORT_LINE_TIMEFRAME,
        until=execute_ms,
    )
    opportunities = db.fetch_opportunities(
        coin,
        since=execute_ms - 7 * SUPPORT_LINE_TIMEFRAME,
        until=execute_ms,
    )
    trades: list[Trade] = []
    interval = "15m"

    btc_start_ms = execute_ms - TRADING_FREQUENCY_MS * 50
    btc_data = datasource.get_historical_klines(
        symbol="BTCUSDT",
        interval=interval,
        start_time=btc_start_ms,
        end_time=execute_ms,
        limit=50,
    )

    coin_symbol = f"{coin.upper()}USDT"
    coin_start_ms = execute_ms - TRADING_FREQUENCY_MS * 25
    coin_data = datasource.get_historical_klines(
        symbol=coin_symbol,
        interval=interval,
        start_time=coin_start_ms,
        end_time=execute_ms,
        limit=25,
    )

    trend = "volatile"
    match check_trend_conditions(btc_data):
        case "bullish":
            # Handle bullish trend
            trend = "bullish"
            pass
        case "bearish":
            # Handle bearish trend
            trend = "bearish"
            pass
        case "volatile":
            # Handle volatile trend
            return
        case _:
            return "error"
        
    print("Trend detected:", trend)

    if trend != "volatile":
        update_pivots(coin_data, pivots)
        update_support_resistance(pivots, opportunities)
        can_trade(coin, pivots, opportunities, trades, trend, amount_precision, price_precision)
        db.insert_pivots(coin, pivots)
        db.insert_opportunities(coin, opportunities)
        db.insert_trades(trades)

    # print(f"btc_data length: {len(btc_data)}")
    # print("btc_data details:")
    # print(btc_data)
    # print(f"coin_data length: {len(coin_data)}")
    # print("coin_data details:")
    # print(coin_data)
    # print(f"Total pivots for {coin}: {len(pivots)}")
    # print(f"Pivot details: {pivots}")
    # print(f"Total opportunities for {coin}: {len(opportunities)}")
    # print(f"Opportunity details: {opportunities}")
    # ticker = roostoo.get_ticker("BTC/USD")
    # print("BTC data length:", len(btc_data))
    # print("Ticker sample:", ticker)

    # balance = roostoo.get_balance()
    # print("Balance:", balance)

current_time = datetime.now()
print("Current time:", current_time)
current_time_ms = to_milliseconds(current_time)
print("Current time in ms:", current_time_ms)
findSignal("DOGE", current_time_ms)