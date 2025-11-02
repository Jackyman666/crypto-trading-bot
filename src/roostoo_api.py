from dotenv import load_dotenv
import requests
import hashlib
import hmac
import time
import os

load_dotenv()

# Load environment variables
BASE_URL = os.getenv('ROOSTOO_BASE_URL')
API_KEY = os.getenv('ROOSTOO_API_KEY')
SECRET = os.getenv('ROOSTOO_SECRET_KEY')

if not all([BASE_URL, API_KEY, SECRET]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

def generate_signature(params):
    query_string = '&'.join(["{}={}".format(k, params[k])
                             for k in sorted(params.keys())])
    us = SECRET.encode('utf-8')
    m = hmac.new(us, query_string.encode('utf-8'), hashlib.sha256)
    return m.hexdigest()


def get_server_time():
    try:
        r = requests.get(
            BASE_URL + "/v3/serverTime",
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting server time: {e}")
        return None


def get_ex_info():
    try:
        r = requests.get(
            BASE_URL + "/v3/exchangeInfo",
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting exchange info: {e}")
        return None


def get_ticker(pair=None):
    try:
        payload = {
            "timestamp": int(time.time() * 1000),  # Consistent timestamp in milliseconds
        }
        if pair:
            payload["pair"] = pair

        r = requests.get(
            BASE_URL + "/v3/ticker",
            params=payload,
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting ticker: {e}")
        return None


def get_balance():
    try:
        payload = {
            "timestamp": int(time.time() * 1000),
        }

        r = requests.get(
            BASE_URL + "/v3/balance",
            params=payload,
            headers={"RST-API-KEY": API_KEY,
                     "MSG-SIGNATURE": generate_signature(payload)}
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting balance: {e}")
        return None


def place_order(coin, side, qty, price=None):
    try:
        payload = {
            "timestamp": int(time.time() * 1000),
            "pair": coin + "/USD",
            "side": side,
            "quantity": qty,
        }

        if not price:
            payload['type'] = "MARKET"
        else:
            payload['type'] = "LIMIT"
            payload['price'] = price

        r = requests.post(
            BASE_URL + "/v3/place_order",
            data=payload,
            headers={"RST-API-KEY": API_KEY,
                     "MSG-SIGNATURE": generate_signature(payload)}
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error placing order: {e}")
        return None


def cancel_order(order_id=None, pair=None):
    try:
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        if order_id:
            payload["order_id"] = order_id
        if pair:
            payload["pair"] = pair

        r = requests.post(
            BASE_URL + "/v3/cancel_order",
            data=payload,
            headers={"RST-API-KEY": API_KEY,
                     "MSG-SIGNATURE": generate_signature(payload)}
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error canceling order: {e}")
        return None


def query_order(order_id=None, pair=None, pending_only=None):
    try:
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        if order_id:
            payload["order_id"] = order_id
        if pair:
            payload["pair"] = pair
        if pending_only is not None:
            payload["pending_only"] = pending_only

        r = requests.post(
            BASE_URL + "/v3/query_order",
            data=payload,
            headers={"RST-API-KEY": API_KEY,
                     "MSG-SIGNATURE": generate_signature(payload)}
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying order: {e}")
        return None


def pending_count():
    try:
        payload = {
            "timestamp": int(time.time() * 1000),
        }

        r = requests.get(
            BASE_URL + "/v3/pending_count",
            params=payload,
            headers={"RST-API-KEY": API_KEY,
                     "MSG-SIGNATURE": generate_signature(payload)}
        )
        r.raise_for_status()
        print(f"Status: {r.status_code}, Response: {r.text}")
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting pending count: {e}")
        return None


if __name__ == '__main__':
    get_server_time()
    # get_ex_info()
    # get_ticker("DOGE/USD")
    # get_balance()
    # place_order("DOGE", "BUY", 10)
    # place_order("DOGE", "BUY", 10, 0.18504)
    # cancel_order(2329966)
    # query_order()
    # pending_count()