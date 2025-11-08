from .utils import (
    update_pivots,
    check_trend_conditions,
)
from .datastore import SQLiteDataStore


def findSignal(coin: str, executeTime: int):
    db = SQLiteDataStore()
    db.initialize()
    pivots = db.fetch_pivots(coin, since=executeTime - 7 * 24 * 60 * 60, until=executeTime)
    opportunities = db.fetch_opportunities(
        coin,
        since=executeTime - 7 * 24 * 60 * 60,
        until=executeTime,
    )

    btc_data = db.fetch_ohlcv(
        "BTC",
        since=executeTime - 15 * 50 * 60,
        until=executeTime,
        limit=50,
        descending=False,
    )
    coin_data = db.fetch_ohlcv(
        coin,
        since=executeTime - 15 * 5 * 60,
        until=executeTime,
        limit=5,
        descending=False,
    )
    print(btc_data)
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
    
    if trend != "volatile":
        match update_pivots(coin_data, pivots):
            case "high":
                # Handle high pivot
                pass
            case "low":
                # Handle low pivot
                pass
            case "both":
                # Handle both pivots
                pass
            case "none":
                # Handle no pivot
                pass
            case _:
                return "error"

    # ticker = roostoo.get_ticker("BTC/USD")
    # print("BTC data length:", len(btc_data))
    # print("Ticker sample:", ticker)

    # balance = roostoo.get_balance()
    # print("Balance:", balance)


findSignal("BTC", 1762526700)