from .utils import check_maximum_conditions, check_minimum_conditions, check_pivot_conditions, check_support_line_conditions, check_trade_conditions, check_trend_conditions
from .models import PivotPoint, Opportunity
import time
# from src.binance_api import get_coin_data, get_bitcoin_data  # Adjust import if needed
from .roostoo import RoostooClient  # Assuming you use roostoo for trading
from .datastore import SQLiteDataStore


store = SQLiteDataStore() 
store.initialize()   



def findSignal(coin: str, executeTime: int):
    roostoo = RoostooClient()
    db = SQLiteDataStore()

    pivots = db.fetch_pivots(coin, since=executeTime - 7*24*60*60, until=executeTime)
    # update db with the latest price data
    ### To be Implemented ###

    btc_data = db.fetch_ohlcv('BTC', since=executeTime - 15*50*60, until=executeTime, limit=50, descending=False)  # newest first
    coin_data = db.fetch_ohlcv(coin, since=executeTime - 15*5*60, until=executeTime, limit=5, descending=False)  # newest first
    match check_trend_conditions(btc_data):
        case "bullish":
            # Handle bullish trend
            pass
        case "bearish":
            # Handle bearish trend
            pass
        case "volatile":
            # Handle volatile trend
            return
        case _:
            return "error"

    match check_pivot_conditions(coin_data):
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