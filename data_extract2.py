import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from tqdm import tqdm

BINANCE_BASE = "https://api.binance.com"
KLINES_PATH  = "/api/v3/klines"

def to_ms(dt):
    if isinstance(dt, int):
        return dt * 1000
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def fetch_binance_klines(symbol, interval, start, end):
    """
    Fetch OHLCV data from Binance and return as DataFrame with DatetimeIndex.
    """


    start_ms = to_ms(start)
    end_ms = to_ms(end)
    all_data = []
    session = requests.Session()

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1000
        }
        r = session.get(BINANCE_BASE + KLINES_PATH, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        all_data += data
        last_close = data[-1][6]
        if last_close >= end_ms:
            break
        start_ms = last_close + 1
        time.sleep(0.5)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_volume","trades","taker_buy_base",
        "taker_buy_quote","ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[["timestamp","open","high","low","close","volume"]]
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df = df.set_index("timestamp")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

        # Binance-compatible trading pairs (USDT-based)
    symbols = ["BTCUSDT", "DOGEUSDT"]
    
    interval = "15m"   # "15m", "1h", or "1d"
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end   = datetime.now(timezone.utc)

    for s in tqdm(symbols):
        try:
            df = fetch_binance_klines(s, interval, start, end)
            if df.empty:
                print(f"{s}: no data returned.")
                continue
            df.to_csv(f"Data/{s}_{interval}.csv")
            print(f"{s}: saved {len(df)} rows.")
        except Exception as e:
            print(f"{s}: error {e}")