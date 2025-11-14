from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

import pandas as pd
import requests
from dotenv import load_dotenv


class BinanceClient:
    """API client for Binance exchange with focus on historical data."""

    # API Endpoints
    BASE_URL = "https://api.binance.us"
    KLINES_PATH = "/api/v3/klines"
    EXCHANGE_INFO_PATH = "/api/v3/exchangeInfo"
    TICKER_PATH = "/api/v3/ticker/24hr"

    def __init__(
        self,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url or self.BASE_URL
        self.session = session or requests.Session()

    def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Binance API."""
        url = f"{self.base_url}{path}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            print(f"Error calling {path}: {exc}")
            return None


    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical klines/candlestick data.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSD')
            interval: Kline interval ('1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M')
            start_time: Start time as epoch seconds, milliseconds, or datetime (optional)
            end_time: End time as epoch seconds, milliseconds, or datetime (optional)
            limit: Number of klines to fetch (max 1000)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume, etc.
        """
        params: Dict[str, Any] = {
            "symbol": f"{symbol.upper()}USD",
            "interval": interval,
            "limit": limit
        }

        params["startTime"] = start_time if start_time is not None else None
        params["endTime"] = end_time if end_time is not None else None

        result = self._request("GET", self.KLINES_PATH, params=params)
        
        if not result:
            return pd.DataFrame()

        # Convert to DataFrame with epoch-millisecond timestamps
        df = pd.DataFrame(result, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # Convert types
        df['timestamp'] = (
            pd.to_numeric(df['timestamp'], errors='coerce')
            .fillna(0)
            .astype('int64')
        )
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df.set_index('timestamp')

    def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange trading rules and symbol information."""
        return self._request("GET", self.EXCHANGE_INFO_PATH)

    def get_ticker(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get 24hr ticker price change statistics."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", self.TICKER_PATH, params=params)


if __name__ == "__main__":
    from datetime import datetime, timedelta
    import pytz

    # Create UTC datetime explicitly
    utc_now = datetime.now(pytz.UTC)                 # Current time in UTC
    local_now = datetime.now()                       # Current time in your local timezone
    
    print(f"UTC time: {utc_now}")
    print(f"Local time: {local_now}")
    
    # Example with both
    client = BinanceClient()
    df = client.get_historical_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_time=utc_now - timedelta(hours=24),    # Last 24h in UTC
        end_time=utc_now
    )
    print("\nHistorical Data:")
    print(df)
    
    # Get current ticker
    ticker = client.get_ticker("BTCUSDT")
    if ticker:
        print("\nCurrent Ticker:")
        print(f"Price: {ticker.get('lastPrice')}")
        print(f"24h Change: {ticker.get('priceChangePercent')}%")