from .utils import check_maximum_conditions, check_minimum_conditions, check_pivot_conditions, check_support_line_conditions, check_trade_conditions, check_trend_conditions
from .models import PivotPoint, Opportunity
import time
# from src.binance_api import get_coin_data, get_bitcoin_data  # Adjust import if needed
from .roostoo import RoostooClient  # Assuming you use roostoo for trading
from src.datastore import SQLiteDataStore


store = SQLiteDataStore() 
store.initialize()   


def findSignal(coin: str):
    roostoo = RoostooClient()
    coin_data = roostoo.get_ticker(pair=f"{coin}/USD")
    coin = "BNB"  # Example coin, replace as needed