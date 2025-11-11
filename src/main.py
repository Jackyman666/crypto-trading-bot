from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime

import pandas as pd

from src.roostoo import RoostooClient
from src.find_signal import findSignal
from src.handle_owned_coins import coins_handler
from src.config import TRADING_FREQUENCY_MS, TRADE_COINS
from src.utils import to_milliseconds, check_trend_conditions


def run_find_signal(coin: str, trend: str, amount_precision: int, price_precision: int, execute_time: int):
    """
    Worker function to run findSignal for a single coin in a thread.
    """
    try:
        print(f"Starting signal analysis for {coin}...")
        findSignal(coin, execute_time, trend, amount_precision, price_precision)
        print(f"Completed signal analysis for {coin}.")
    except Exception as e:
        print(f"Error processing {coin}: {e}")


def main_loop():
    """
    Main loop to run the trading bot.
    """
    roostoo_client = RoostooClient()

    while True:
        execute_time = to_milliseconds(datetime.now())
        print(f"\n--- Starting new trading cycle at {datetime.now()} ---")

        trend = check_trend_conditions(execute_time)
        print(f"Market Trend: {trend}")
        if trend == "volatile":  # Placeholder for market condition check
            print("Market conditions not met. Skipping this cycle.")
            time.sleep(TRADING_FREQUENCY_MS / 1000)
            continue
        
        try:
            market_info = roostoo_client.get_exchange_info()
            if not market_info["IsRunning"]:
                print("Failed to get market info. Retrying in the next cycle.")
                time.sleep(TRADING_FREQUENCY_MS / 1000)
                continue

            coins_to_process = []
            for coin in TRADE_COINS:
                if f"{coin}/USD" in market_info.get("TradePairs", {}):
                    details = market_info["TradePairs"][f"{coin}/USD"]
                    coins_to_process.append({
                        "name": coin,
                        "amount_precision": details.get("AmountPrecision"),
                        "price_precision": details.get("PricePrecision")
                    })

            if not coins_to_process:
                print("No coins found to process.")
                time.sleep(TRADING_FREQUENCY_MS / 1000)
                continue
            print(f"Processing {len(coins_to_process)} coins: {[coin['name'] for coin in coins_to_process]}")
            # Use ThreadPoolExecutor to process coins concurrently
            max_threads = 10  # Number of threads to run at a time
            with ThreadPoolExecutor(max_threads) as executor:
                futures = []
                for coin_info in coins_to_process:
                    futures.append(
                        executor.submit(
                            run_find_signal,
                            coin_info["name"],
                            trend,
                            coin_info["amount_precision"],
                            coin_info["price_precision"],
                            execute_time
                        )
                    )

                # Optionally: Wait for all futures to complete
                for future in futures:
                    try:
                        future.result()  # This will raise any exceptions that occurred in the thread
                    except Exception as e:
                        print(f"Error in thread: {e}")

            print("\n--- All coin signals processed. Handling owned coins. ---")
            coins_handler(execute_time, market_info)

        except Exception as e:
            print(f"An error occurred in the main loop: {e}")

        print(f"--- Cycle finished. Waiting for {TRADING_FREQUENCY_MS / 1000} seconds... ---")
        time.sleep(TRADING_FREQUENCY_MS / 1000)


if __name__ == "__main__":
    main_loop()

