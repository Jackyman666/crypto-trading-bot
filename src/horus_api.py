from dotenv import load_dotenv
from typing import Literal
import requests
import hashlib
import hmac
import time
import os
import pandas as pd
from datetime import datetime
import io
from tqdm import tqdm

load_dotenv()

# Load environment variables
BASE_URL = os.getenv('HORUS_BASE_URL')
API_KEY = os.getenv('HORUS_API_KEY')

if not all([BASE_URL, API_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

def get_price_data(
        symbol: Literal["BTC","ETH","XRP","BNB","SOL","DOGE","TRX","ADA","XLM","WBTC","SUI","HBAR","LINK","BCH","WBETH","UNI","AVAX","SHIB","TON","LTC","DOT","PEPE","AAVE","ONDO","TAO","WLD","APT","NEAR","ARB","ICP","ETC","FIL","TRUMP","OP","ALGO","POL","BONK","ENA","ENS","VET","SEI","RENDER","FET","ATOM","VIRTUAL","SKY","BNSOL","RAY","TIA","JTO","JUP","QNT","FORM","INJ","STX"], 
        interval: Literal["1d","1h","15m"], 
        start: int | datetime, 
        end: int | datetime
) -> pd.DataFrame:
    try:
        payload = {
            "asset": symbol,
            "interval": interval,
            "start": start if isinstance(start, int) else int(start.timestamp()),
            "end": end if isinstance(end, int) else int(end.timestamp()),
            "format": "csv"
        }
        headers = {
            "X-API-KEY": API_KEY,
            "Accept": "application/json"
        }
        r = requests.get(
            BASE_URL + "/market/price",
            params=payload,
            headers=headers
        )
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text), index_col='timestamp')
        df.index = pd.to_datetime(df.index, unit='s')
        return df
    except requests.exceptions.RequestException as e:
        print(f"Error getting price data: {e}")
        return pd.DataFrame()
    
if __name__ == "__main__":
    symbols = ["BTC","ETH","XRP","BNB","SOL","DOGE","TRX","ADA","XLM","WBTC","SUI","HBAR","LINK","BCH","WBETH","UNI","AVAX","SHIB","TON","LTC","DOT","PEPE","AAVE","ONDO","TAO","WLD","APT","NEAR","ARB","ICP","ETC","FIL","TRUMP","OP","ALGO","POL","BONK","ENA","ENS","VET","SEI","RENDER","FET","ATOM","VIRTUAL","SKY","BNSOL","RAY","TIA","JTO","JUP","QNT","FORM","INJ","STX"]
    for symbol in tqdm(symbols):
        interval = "1d"
        df = get_price_data(symbol, interval, datetime(2020,1,1), datetime.today())
        df.to_csv(f"data/{symbol}_{interval}.csv")