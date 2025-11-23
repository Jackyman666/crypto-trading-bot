# Crypto Trading Bot

This repository contains the trading system we built for the HK Web3 Quant Trading Hackathon. The bot combines on-chain quality market data from Binance with order execution on the Roostoo mock exchange. The core idea is to let BTC and ETH set the higher‑timeframe context, then only take alt‑coin trades that sweep obvious liquidity and confirm a reversal before automating both the entry and the staged exit so the strategy can run unattended.

---

## Core idea at a glance

- **Dual market-regime gate** – every cycle starts by pulling the last 50 candles for BTC and ETH. A 20/50 SMA cross that slopes upward denotes a bullish regime; a cross that rolls over signals bearish. Only when both majors agree do we enable longs or shorts; otherwise the bot stands aside.
- **Alt-coin focus list** – after a bullish regime is confirmed we prioritise alt coins that recently tagged their monthly high (configurable via `TRADE_COINS`). In a bearish regime the same framework flips to spotting equal highs on overextended names, effectively mirroring the logic for shorts.
- **Liquidity + structure scan** – for each enabled coin the bot streams Binance klines, detects pivots, and looks for paired highs/lows that form equal‑liquidity pools. A sweep that runs those equal lows/highs and then closes back through the prior impulse high/low is treated as the “strong reversal” confirmation.
- **Fibonacci-based entries** – once the sweep and reversal are recorded, the bot either fires a buy/sell stop immediately or—by default—rests a limit order in the OTE zone (`0.618–0.71` retracement). Position size remains a fixed percentage of free USD balance so every entry is self‑funded.
- **Layered exits with full fib ladder** – `src/handle_owned_coins.py` manages both bullish and bearish take-profit ladders using the Fibonacci extensions {1.0, 1.618, 2.618}. When short, the negative extensions {-0.272, -0.618, -1.0} are used for partial covers. Each partial uses the sales ratios `50% / 25% / 25%` to scale out.
- **Stop-loss logic tied to liquidity** – the protective stop is anchored at the midpoint between the swept equal lows/highs and the deepest wick produced during the sweep. Once price closes beyond the final rung or violates the stop, all remaining bracket orders are cancelled and the rest of the position is flattened at market.

The result is a loop that constantly scans for liquidity-run pullbacks in trending markets and manages the entire lifecycle of both long and short trades.

P.S. Notice that since short is not allowed in this competiton, so the short-sell part is not implemented in the code but is indeed part of our strategy.

---

## How it is implemented

| Step                     | What happens                                                                                                                                                                                              | Key code                                                   |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 1. Cycle orchestration   | `src/main.py` drives the loop: fetch market mode, pull exchange metadata, and dispatch a thread per coin so signal discovery is concurrent.                                                               | `main_loop`, `run_find_signal`                             |
| 2. Data & persistence    | `findSignal` pulls recent candles from `BinanceClient`, merges them with previously stored pivots/opportunities/trades from `SQLiteDataStore`, and writes back any updates.                               | `src/find_signal.py`, `src/binance.py`, `src/datastore.py` |
| 3. Opportunity detection | `update_pivots` flags fractal highs/lows, `update_support_resistance` pairs pivots into zones, and `can_trade` promotes them into actionable trades if the trend gate is open.                            | `src/utils.py`                                             |
| 4. Execution             | The lightweight`RoostooClient` (`src/roostoo.py`) signs and sends all private API calls (balances, limit/market orders, cancellations).                                                                   | `place_order`, `query_order`, `get_balance`                |
| 5. Position management   | `coins_handler` reconciles open trades from SQLite, checks whether staged take-profits filled on Roostoo, reclocks stop losses against the latest candle, and cancels/markets out when protection is hit. | `src/handle_owned_coins.py`                                |

The datastore lives in `data/trading.db` and currently tracks three tables: `pivots`, `opportunities`, and `trades`. Lists such as stop-loss ladders are JSON-encoded before being persisted so the bot can recover state after restarts.

---

## Key configuration switches

All tunables reside in `src/config.py`.

- `TRADING_FREQUENCY_MS`: cadence of each full cycle (default 5 minutes).
- `TRADE_INTERVAL`: Binance kline interval used everywhere (default `5m`).
- `TRADE_COINS`: shortlist of symbols to scan (defaults to `["XRP","ZEC","SOL","UNI","HBAR","PAXG"]`).
- `SET_TRADE_QUANTITY`: capital allocation per trade expressed as a fraction of free USD.
- Pivot/opportunity knobs such as `PIVOT_POINT_COMPARE`, `MAXIMUM_PERCENTAGE_DIFFERENCE`, and `SUPPORT_LINE_TIMEFRAME`.
- `SALES_RATIO`: percentages for the three staged take‑profit orders.

---

## Project structure

```
src/
├── binance.py           # Historical data client for Binance US
├── roostoo.py           # Authenticated order routing client
├── config.py            # All runtime settings
├── datastore.py         # SQLite wrapper (pivots, opportunities, trades)
├── find_signal.py       # Signal discovery pipeline per coin
├── handle_owned_coins.py# Post-trade management and scaling out
├── utils.py             # Technical analysis helpers and trade sizing
└── main.py              # Threaded orchestration loop
```

Jupyter notebooks in the repo (`base.ipynb`, etc.) were used for prototyping and visualization and are not required for execution.

---

## Getting started

```bash
git clone https://github.com/Jackyman666/crypto-trading-bot.git
cd crypto-trading-bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` in the project root with your mock-exchange credentials:

```
ROOSTOO_BASE_URL=https://mock-api.roostoo.com
ROOSTOO_TEST_API_KEY=your_key
ROOSTOO_TEST_SECRET_KEY=your_secret
```

_Note:_ Binance market data does not require credentials for the endpoints used here.

---

## Running the bot

```bash
source venv/bin/activate
python -m src.main
```

By default the bot will spin forever, waking up every `TRADING_FREQUENCY_MS` milliseconds. Logs are printed to stdout so you can watch each cycle progress (trend classification, coins processed, order responses, etc.).

---
