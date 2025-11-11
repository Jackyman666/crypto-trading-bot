from __future__ import annotations
from datetime import datetime

from .models import Trade
from .utils import (
    update_pivots,
    update_support_resistance,
    to_milliseconds,
    can_trade
)
from .config import TRADING_FREQUENCY_MS, SUPPORT_LINE_TIMEFRAME, TRADE_INTERVAL
from .datastore import SQLiteDataStore
from .binance import BinanceClient
from .logger import get_logger

logger = get_logger(__name__)


def findSignal(coin: str, executeTime: int, trend: str, amount_precision: int, price_precision: int) -> None:
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

    coin_symbol = f"{coin.upper()}USDT"
    coin_start_ms = execute_ms - TRADING_FREQUENCY_MS * 25
    coin_data = datasource.get_historical_klines(
        symbol=coin_symbol,
        interval=TRADE_INTERVAL,
        start_time=coin_start_ms,
        end_time=execute_ms,
        limit=25,
    )

    if trend != "volatile":
        update_pivots(coin_data, pivots)
        update_support_resistance(pivots, opportunities)
        can_trade(coin, pivots, opportunities, trades, trend, amount_precision, price_precision)
        db.insert_pivots(coin, pivots)
        db.insert_opportunities(coin, opportunities)
        db.insert_trades(trades)

    logger.info(f"Found {len(pivots)} pivots and {len(opportunities)} opportunities for {coin}")

current_time = datetime.now()
logger.info(f"Current time: {current_time}")
current_time_ms = to_milliseconds(current_time)
logger.info(f"Current time in ms: {current_time_ms}")