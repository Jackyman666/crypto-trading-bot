from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict, Optional
from .config import RETRIES, BACK_OFF_FACTOR
import requests
from dotenv import load_dotenv


class RoostooClient:
    """Thin API client for the Roostoo mock exchange."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> None:
        load_dotenv()

        self.base_url = base_url or os.getenv("ROOSTOO_BASE_URL")
        self.api_key = api_key or os.getenv("ROOSTOO_TEST_API_KEY")
        self.secret = secret or os.getenv("ROOSTOO_TEST_SECRET_KEY")

        if not all([self.base_url, self.api_key, self.secret]):
            raise ValueError("Missing required environment variables. Please check your .env file.")

        self.retry = 0

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None,
                data: Optional[Dict[str, Any]] = None, auth: bool = False) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        payload = params if params is not None else data
        headers = {}

        if auth and payload is not None:
            signature = self._generate_signature(payload)
            headers = {
                "RST-API-KEY": self.api_key,
                "MSG-SIGNATURE": signature,
            }

        retry = 0
        while retry < RETRIES:
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers if headers else None,
                )
                response.raise_for_status()  # Raise exception for HTTP errors (4xx, 5xx)

                # Log and return successful response
                if not path == "/v3/exchangeInfo":
                    print(f"Status: {response.status_code}, Response: {response.text}")
                return response.json()

            except requests.exceptions.HTTPError as exc:
                # Handle 429 Too Many Requests
                if exc.response.status_code == 429:
                    retry += 1
                    retry_after = int(exc.response.headers.get("Retry-After", 1))  # Use Retry-After if provided
                    wait_time = BACK_OFF_FACTOR ** retry if "Retry-After" not in exc.response.headers else retry_after
                    print(f"Rate limit exceeded (429). Retrying in {wait_time} seconds... (Attempt {retry}/{RETRIES})")
                    time.sleep(wait_time)
                else:
                    # Log and re-raise for non-retryable HTTP errors
                    print(f"HTTPError: {exc}. No retry for status {exc.response.status_code}.")
                    break

            except requests.exceptions.RequestException as exc:
                # Handle generic request errors with retries
                retry += 1
                wait_time = BACK_OFF_FACTOR ** retry
                print(f"RequestException: {exc}. Retrying in {wait_time} seconds... (Attempt {retry}/{RETRIES})")
                time.sleep(wait_time)

        print("Max retries reached. Returning None.")
        return None

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        query_string = "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
        secret_bytes = self.secret.encode("utf-8")
        message = query_string.encode("utf-8")
        return hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()

    @staticmethod
    def _timestamp_ms() -> int:
        return int(time.time() * 1000)

    # Public endpoints -------------------------------------------------

    def get_server_time(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/v3/serverTime")

    def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/v3/exchangeInfo")

    def get_ticker(self, pair: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {"timestamp": self._timestamp_ms()}
        if pair:
            params["pair"] = pair
        return self._request("GET", "/v3/ticker", params=params)

    # Private endpoints ------------------------------------------------

    def get_balance(self) -> Optional[Dict[str, Any]]:
        params = {"timestamp": self._timestamp_ms()}
        return self._request("GET", "/v3/balance", params=params, auth=True)

    def place_order(self, coin: str, side: str, qty: float, price: Optional[float] = None,
                    order_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "timestamp": self._timestamp_ms(),
            "pair": f"{coin}/USD",
            "side": side,
            "quantity": qty,
        }

        if order_type:
            payload["type"] = order_type.upper()
        elif price is None:
            payload["type"] = "MARKET"
        else:
            payload["type"] = "LIMIT"
        if price is not None:
            payload["price"] = price

        return self._request("POST", "/v3/place_order", data=payload, auth=True)

    def cancel_order(self, order_id: Optional[int] = None, pair: Optional[str] = None) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"timestamp": self._timestamp_ms()}
        if order_id is not None:
            payload["order_id"] = order_id
        if pair is not None:
            payload["pair"] = pair
        return self._request("POST", "/v3/cancel_order", data=payload, auth=True)

    def query_order(
        self,
        order_id: Optional[int] = None,
        pair: Optional[str] = None,
        pending_only: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"timestamp": self._timestamp_ms()}
        if order_id is not None:
            payload["order_id"] = order_id
        if pair is not None:
            payload["pair"] = pair
        if pending_only is not None:
            payload["pending_only"] = pending_only
        return self._request("POST", "/v3/query_order", data=payload, auth=True)

    def pending_count(self) -> Optional[Dict[str, Any]]:
        params = {"timestamp": self._timestamp_ms()}
        return self._request("GET", "/v3/pending_count", params=params, auth=True)


if __name__ == "__main__":
    client = RoostooClient()
    client.get_server_time()
    # client.get_exchange_info()
    # client.get_ticker("DOGE/USD")
    # client.get_balance()
    # client.place_order("DOGE", "BUY", 10, price=0.177816)
    # x = client.place_order("DOGE", "SELL", 10, price=0.19504)
    # print(x["OrderDetail"]["OrderID"])
    # print(x["Success"] == True)
    # client.cancel_order(order_id=x["OrderDetail"]["OrderID"])
    # x = client.query_order()
    # client.pending_count()