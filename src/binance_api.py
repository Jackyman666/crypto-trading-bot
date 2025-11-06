from dotenv import load_dotenv
from typing import Literal
import requests
import hashlib
import hmac
import time
import os
import pandas as pd
import numpy as np
from datetime import datetime
import io
from tqdm import tqdm
from datetime import datetime,timedelta
from binance.client import Client
from binance.enums import HistoricalKlinesType
from multiprocessing import Pool
from functools import partial

load_dotenv()

def parse_symbol(
    symbol: Literal["BTC","ETH","XRP","BNB","SOL","DOGE","TRX","ADA","XLM","WBTC","SUI","HBAR","LINK","BCH","WBETH","UNI","AVAX","SHIB","TON","LTC","DOT","PEPE","AAVE","ONDO","TAO","WLD","APT","NEAR","ARB","ICP","ETC","FIL","TRUMP","OP","ALGO","POL","BONK","ENA","ENS","VET","SEI","RENDER","FET","ATOM","VIRTUAL","SKY","BNSOL","RAY","TIA","JTO","JUP","QNT","FORM","INJ","STX"]
) -> str:
    symbol = symbol+"USDT"
    return symbol

def to_timedelta(
    interval: Literal["1d","1h","1m","5m","15m","30m"], 
) -> timedelta:
    if interval == '1d':
        return timedelta(days=1)
    elif interval == '1h':
        return timedelta(hours=1)
    elif interval == '1m':
        return timedelta(minutes=1)
    elif interval == '5m':
        return timedelta(minutes=5)
    elif interval == '15m':
        return timedelta(minutes=15)
    elif interval == '30m':
        return timedelta(minutes=30)

def time_chunk(
    start: datetime,
    end: datetime,
    interval: Literal["1d","1h","1m","5m","15m","30m"], 
    limit: int = 1000,
    buffer: int = 50
) -> list:
    sep = to_timedelta(interval) * (limit-buffer)
    dt_rng = pd.date_range(
        start = start,
        end = end,
        freq = sep
    )
    start_end = pd.DataFrame({
        'start': dt_rng,
        'end': dt_rng.shift(1)
    }).dropna()
    start_end.iloc[-1,1] = min(end,start_end.iloc[-1,1])
    start_end = [(start.to_pydatetime(),end.to_pydatetime()) for start,end in start_end.itertuples(index=False)]
    return start_end

def download_bars(start_end,ohlcv_only,**kwargs):
    start,end = start_end
    client = Client()
    res = client.get_historical_klines(
        start_str=str(start.timestamp()),
        end_str=str(end.timestamp()),
        **kwargs
    )
    if len(res) == 0:
        arr = np.ndarray(shape=(1,12))
    else:
        arr = np.array(res)
    if ohlcv_only:
        arr = arr[:,:6]
    return arr

def get_price_data(
    symbol: Literal["BTC","ETH","XRP","BNB","SOL","DOGE","TRX","ADA","XLM","WBTC","SUI","HBAR","LINK","BCH","WBETH","UNI","AVAX","SHIB","TON","LTC","DOT","PEPE","AAVE","ONDO","TAO","WLD","APT","NEAR","ARB","ICP","ETC","FIL","TRUMP","OP","ALGO","POL","BONK","ENA","ENS","VET","SEI","RENDER","FET","ATOM","VIRTUAL","SKY","BNSOL","RAY","TIA","JTO","JUP","QNT","FORM","INJ","STX"], 
    interval: Literal["1d","1h","1m","5m","15m","30m"], 
    start: datetime, 
    end: datetime,
    ohlcv_only: bool = False,
) -> pd.DataFrame:
    symbol = parse_symbol(symbol)
    limit = 1000
    buffer = 50
    chunks = time_chunk(start,end,interval,limit=limit,buffer=buffer)
    dl_bars_part = partial(
        download_bars,
        ohlcv_only=ohlcv_only,
        symbol=symbol,
        interval=interval,
        limit=1000,
        klines_type=HistoricalKlinesType.SPOT
    )
    try:
        with Pool(min(len(chunks),25)) as p:
            dfs = p.map(func=dl_bars_part,iterable=chunks)
        if ohlcv_only: 
            columns = ['timestamp','open','high','low','close','volume']
        else:
            columns = ['timestamp','open','high','low','close','volume','close_time','quote_volume','num_trades','buy_base_volume','buy_quote_volume','unused']
        df = pd.DataFrame(
            np.vstack(dfs),
            columns=columns,
        ).set_index('timestamp')
        # Drop duplicated rows in buffers
        df = df.loc[~df.index.duplicated(keep='first')]
        return df
    except Exception as e:
        print(f"Error getting price data: {e}")
        return pd.DataFrame()
    
if __name__ == "__main__":
    # symbols are from roostoo tradable universe
    symbols = ["BTC","ETH","XRP","BNB","SOL","DOGE","TRX","ADA","XLM","WBTC","SUI","HBAR","LINK","BCH","WBETH","UNI","AVAX","SHIB","TON","LTC","DOT","PEPE","AAVE","ONDO","TAO","WLD","APT","NEAR","ARB","ICP","ETC","FIL","TRUMP","OP","ALGO","POL","BONK","ENA","ENS","VET","SEI","RENDER","FET","ATOM","VIRTUAL","SKY","BNSOL","RAY","TIA","JTO","JUP","QNT","FORM","INJ","STX"]
    for symbol in tqdm(symbols):
        # change the interval ["1d","1h","1m","5m","15m","30m"]
        interval = "1h"
        df = get_price_data(symbol, interval, datetime(2020,1,1), datetime.today(), ohlcv_only=True)
        df.to_csv(f"data/{symbol}_{interval}.csv")