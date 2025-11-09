"""Minimal SQLite helper for the trading bot.

This module currently handles only two things:
1. Ensuring the SQLite database file exists in the desired location.
2. Creating the base tables (ohlcv, pivots, opportunities).

We'll add read/write helpers later once the schema is locked in.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .models import Opportunity, PivotPoint, Trade
from .utils import to_milliseconds


def _ensure_parent(path: Path) -> None:
    """Create the parent directory for the database file if required."""

    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


class SQLiteDataStore:
    """Very small wrapper around sqlite3 connections."""

    def __init__(self, db_path: str | Path = Path("data/trading.db")) -> None:
        self.db_path = Path(db_path)
        _ensure_parent(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        """Return a live sqlite3 connection."""

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self) -> None:
        """Create base tables if they do not already exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS pivots (
            coin TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            price REAL NOT NULL,
            pivot_type TEXT NOT NULL CHECK (pivot_type IN ('high', 'low')),
            is_supported INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (coin, timestamp, pivot_type)
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            coin TEXT NOT NULL,
            support_line REAL NOT NULL,
            minimum REAL NOT NULL,
            maximum REAL NOT NULL,
            relative_pivot REAL NOT NULL,
            action TEXT DEFAULT '',
            start_time INTEGER,
            end_time INTEGER,
            PRIMARY KEY (coin, start_time, support_line)
        );
        
        CREATE TABLE IF NOT EXISTS trades (
            coin TEXT NOT NULL,
            quantity REAL NOT NULL,
            order_id INTEGER NOT NULL,
            support_line REAL NOT NULL,
            minimum REAL NOT NULL,
            maximum REAL NOT NULL,
            stop_loss REAL NOT NULL,
            profit_level REAL NOT NULL,
            PRIMARY KEY (order_id)
        );
        """

        with self._connect() as conn:
            try:
                conn.execute(
                    "DROP TABLE IF EXISTS ohlcv;"
                )
            except sqlite3.OperationalError:
                # Column already exists; ignore error.
                pass
            conn.executescript(schema)

    def fetch_pivots(
        self,
        coin: str,
        *,
        since: Optional[int | str] = None,
        until: Optional[int | str] = None,
    ) -> List[PivotPoint]:
        """Return PivotPoint objects for a coin within an optional time window."""

        clauses = ["coin = ?"]
        params: List[object] = [coin]

        if since is not None:
            since_ts = to_milliseconds(since)
            if since_ts is not None:
                clauses.append("timestamp >= ?")
                params.append(since_ts)

        if until is not None:
            until_ts = to_milliseconds(until)
            if until_ts is not None:
                clauses.append("timestamp <= ?")
                params.append(until_ts)

        query = (
            "SELECT timestamp, price, pivot_type, is_supported FROM pivots WHERE "
            + " AND ".join(clauses)
            + " ORDER BY timestamp ASC"
        )

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        pivots: List[PivotPoint] = []
        for row in rows:
            timestamp = int(row[0])
            price = float(row[1])
            pivot_type = str(row[2])
            is_supported = bool(row[3])
            pivots.append(
                PivotPoint(
                    timestamp=timestamp,
                    price=price,
                    position=0,
                    type=pivot_type,
                    is_supported=is_supported,
                )
            )

        return pivots

    def fetch_opportunities(
        self,
        coin: str,
        *,
        since: Optional[int | str] = None,
        until: Optional[int | str] = None,
        limit: Optional[int] = None,
    ) -> List[Opportunity]:
        """Return opportunity rows converted into Opportunity dataclasses."""

        clauses = ["coin = ?"]
        params: List[object] = [coin]

        if since is not None:
            since_ts = to_milliseconds(since)
            if since_ts is not None:
                clauses.append("(start_time IS NULL OR start_time >= ?)")
                params.append(since_ts)

        if until is not None:
            until_ts = to_milliseconds(until)
            if until_ts is not None:
                clauses.append("(end_time IS NULL OR end_time <= ?)")
                params.append(until_ts)

        query_parts = [
            "SELECT support_line, minimum, maximum, relative_pivot, action, start_time, end_time"
            " FROM opportunities WHERE",
            " AND ".join(clauses),
            "ORDER BY COALESCE(start_time, end_time) ASC",
        ]

        if limit is not None:
            query_parts.append("LIMIT ?")
            params.append(int(limit))

        query = " ".join(query_parts)

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        opportunities: List[Opportunity] = []
        for row in rows:
            start_dt = int(row[5]) if row[5] is not None else None
            end_dt = int(row[6]) if row[6] is not None else None
            opportunities.append(
                Opportunity(
                    support_line=float(row[0]),
                    minimum=float(row[1]),
                    maximum=float(row[2]),
                    relative_pivot=float(row[3]),
                    action=str(row[4]),
                    start=start_dt,
                    end=end_dt,
                )
            )

        return opportunities

    def fetch_trades(self) -> List[Trade]:
        """
        Fetch all Trade objects where `quantity > 0`.

        Returns:
            A list of Trade objects.
        """
        query = (
            "SELECT order_id, quantity, support_line, minimum, maximum, stop_loss, profit_level "
            "FROM trades WHERE quantity > 0 "
            "ORDER BY order_id ASC"
        )

        with self._connect() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()

        trades: List[Trade] = []
        for row in rows:
            trades.append(
                Trade(
                    order_id=int(row[0]),
                    quantity=float(row[1]),
                    support_line=float(row[2]),
                    minimum=float(row[3]),
                    maximum=float(row[4]),
                    stop_loss=float(row[5]),
                    profit_level=float(row[6]),
                )
            )

        return trades

    def insert_pivots(self, coin: str, pivots: list[PivotPoint]) -> bool:
        """
        Insert or update a list of pivot points for ``coin``.

        Args:
            coin: The cryptocurrency symbol (e.g., "BTC").
            pivots: List of PivotPoint objects.

        Returns:
            True if all pivot points are successfully inserted or updated, False otherwise.
        """
        if not pivots:
            return False

        sql = (
            "INSERT INTO pivots (coin, timestamp, price, pivot_type, is_supported) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(coin, timestamp, pivot_type) DO UPDATE SET "
            "price=excluded.price, is_supported=excluded.is_supported"
        )

        try:
            with self._connect() as conn:
                for pivot in pivots:
                    # Convert pivot attributes to database-friendly values
                    timestamp = to_milliseconds(getattr(pivot, "timestamp", None))
                    if timestamp is None:
                        continue  # Skip invalid pivot points

                    try:
                        price = float(pivot.price)
                    except (TypeError, ValueError):
                        continue  # Skip invalid pivot points

                    pivot_type = getattr(pivot, "type", None)
                    if pivot_type not in {"high", "low"}:
                        continue  # Skip invalid pivot points

                    is_supported = int(bool(getattr(pivot, "is_supported", False)))

                    # Insert or update the pivot point in the database
                    conn.execute(sql, (coin, timestamp, price, pivot_type, is_supported))

            return True
        except Exception as e:
            print(f"Error inserting pivots: {e}")
            return False

    def insert_opportunities(self, coin: str, opportunities: list[Opportunity]) -> bool:
        """
        Insert a list of opportunities into the database.

        Args:
            coin: The cryptocurrency symbol (e.g., "BTC").
            opportunities: List of Opportunity objects.

        Returns:
            True if all opportunities are successfully inserted, False otherwise.
        """
        if not opportunities:
            return False

        sql = (
            "INSERT INTO opportunities "
            "(coin, support_line, minimum, maximum, relative_pivot, action, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )

        try:
            with self._connect() as conn:
                for opportunity in opportunities:
                    try:
                        # Convert opportunity attributes to database-friendly values
                        support_line = float(opportunity.support_line)
                        minimum = float(opportunity.minimum)
                        maximum = float(opportunity.maximum)
                        relative_pivot = float(getattr(opportunity, "relative_pivot", 0.0))
                        action = str(getattr(opportunity, "action", ""))
                    except (TypeError, ValueError):
                        continue  # Skip invalid opportunities

                    start_ts = to_milliseconds(getattr(opportunity, "start", None))
                    end_ts = to_milliseconds(getattr(opportunity, "end", None))

                    # Insert the opportunity into the database
                    conn.execute(
                        sql,
                        (
                            coin,
                            support_line,
                            minimum,
                            maximum,
                            relative_pivot,
                            action,
                            start_ts,
                            end_ts,
                        ),
                    )

            return True
        except Exception as e:
            print(f"Error inserting opportunities: {e}")
            return False
        
    def insert_trades(self, coin: str, trades: list[Trade]) -> bool:
        """
        Insert a list of trades into the database.

        Args:
            coin: The cryptocurrency symbol (e.g., "BTC").
            trades: List of Trade objects to insert.

        Returns:
            True if all trades are successfully inserted, False otherwise.
        """
        if not trades:
            return False

        sql = (
            "INSERT INTO trades "
            "(coin, quantity, order_id, support_line, minimum, maximum, stop_loss, profit_level) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(order_id) DO UPDATE SET "
            "quantity=excluded.quantity, "
            "support_line=excluded.support_line, "
            "minimum=excluded.minimum, "
            "maximum=excluded.maximum, "
            "stop_loss=excluded.stop_loss, "
            "profit_level=excluded.profit_level"
        )

        try:
            with self._connect() as conn:
                for trade in trades:
                    try:
                        # Convert trade attributes to database-friendly values
                        quantity = float(trade.quantity)
                        support_line = float(trade.support_line)
                        minimum = float(trade.minimum)
                        maximum = float(trade.maximum)
                        stop_loss = float(trade.stop_loss)
                        profit_level = float(trade.profit_level)
                    except (TypeError, ValueError):
                        continue  # Skip invalid trades

                    # Insert or update the trade in the database
                    conn.execute(
                        sql,
                        (
                            coin,
                            quantity,
                            trade.order_id,
                            support_line,
                            minimum,
                            maximum,
                            stop_loss,
                            profit_level,
                        ),
                    )

            return True
        except Exception as e:
            print(f"Error inserting trades: {e}")
            return False
    # def ingest_csv(self, coin: str, csv_path: str | Path, *, batch_size: int = 1000) -> int:
    #     """Load OHLCV rows from a CSV file into the database.

    #     The CSV must contain the columns ``timestamp``, ``open``, ``high``, ``low``,
    #     ``close`` and ``volume``. Rows with missing or invalid values are skipped.

    #     Returns the number of upserted rows.
    #     """

    #     csv_path = Path(csv_path)
    #     if not csv_path.exists():
    #         raise FileNotFoundError(f"CSV not found: {csv_path}")

    #     insert_sql = (
    #         "INSERT INTO ohlcv (coin, timestamp, open, high, low, close, volume) "
    #         "VALUES (?, ?, ?, ?, ?, ?, ?) "
    #         "ON CONFLICT(coin, timestamp) DO UPDATE SET "
    #         "open=excluded.open, high=excluded.high, low=excluded.low, "
    #         "close=excluded.close, volume=excluded.volume"
    #     )

    #     written = 0
    #     buffer: List[Tuple[str, int, float, float, float, float, float]] = []

    #     with csv_path.open("r", newline="") as handle, self._connect() as conn:
    #         reader = csv.DictReader(handle)
    #         for row in reader:
    #             timestamp = to_milliseconds(row.get("timestamp"))
    #             if timestamp is None:
    #                 continue

    #             try:
    #                 open_ = float(row["open"])
    #                 high = float(row["high"])
    #                 low = float(row["low"])
    #                 close = float(row["close"])
    #                 volume = float(row["volume"])
    #             except (KeyError, TypeError, ValueError):
    #                 continue

    #             buffer.append((coin, timestamp, open_, high, low, close, volume))

    #             if len(buffer) >= batch_size:
    #                 conn.executemany(insert_sql, buffer)
    #                 written += len(buffer)
    #                 buffer.clear()

    #         if buffer:
    #             conn.executemany(insert_sql, buffer)
    #             written += len(buffer)

    #     return written

    # def fetch_ohlcv(
    #     self,
    #     coin: str,
    #     *,
    #     since: Optional[int | str] = None,
    #     until: Optional[int | str] = None,
    #     limit: Optional[int] = None,
    #     descending: bool = True,
    # ) -> List[Tuple[int, float, float, float, float, float]]:
    #     """Return OHLCV rows with optional time filtering."""

    #     clauses = ["coin = ?"]
    #     params: List[object] = [coin]

    #     if since is not None:
    #         since_ts = to_milliseconds(since)
    #         if since_ts is not None:
    #             clauses.append("timestamp >= ?")
    #             params.append(since_ts)

    #     if until is not None:
    #         until_ts = to_milliseconds(until)
    #         if until_ts is not None:
    #             clauses.append("timestamp <= ?")
    #             params.append(until_ts)

    #     order = "DESC" if descending else "ASC"

    #     query_parts = [
    #         "SELECT timestamp, open, high, low, close, volume FROM ohlcv WHERE",
    #         " AND ".join(clauses),
    #         f"ORDER BY timestamp {order}",
    #     ]

    #     if limit is not None:
    #         query_parts.append("LIMIT ?")
    #         params.append(int(limit))

    #     query = " ".join(query_parts)

    #     with self._connect() as conn:
    #         cursor = conn.execute(query, params)
    #         return [tuple(row) for row in cursor.fetchall()]

    # def upsert_ohlcv_rows(
    #     self,
    #     coin: str,
    #     rows: Iterable[Tuple[object, object, object, object, object, object]],
    # ) -> int:
    #     """Insert or update OHLCV rows provided at runtime.

    #     Each row should contain ``(timestamp, open, high, low, close, volume)``.
    #     Timestamps may be epoch integers, floats, or ISO-8601 strings.
    #     Returns the number of rows written.
    #     """

    #     payload: List[Tuple[str, int, float, float, float, float, float]] = []

    #     for entry in rows:
    #         try:
    #             ts_raw, open_, high, low, close, volume = entry
    #         except (TypeError, ValueError):
    #             continue

    #         timestamp = to_milliseconds(ts_raw)
    #         if timestamp is None:
    #             continue

    #         try:
    #             payload.append(
    #                 (
    #                     coin,
    #                     timestamp,
    #                     float(open_),
    #                     float(high),
    #                     float(low),
    #                     float(close),
    #                     float(volume),
    #                 )
    #             )
    #         except (TypeError, ValueError):
    #             continue

    #     if not payload:
    #         return 0

    #     insert_sql = (
    #         "INSERT INTO ohlcv (coin, timestamp, open, high, low, close, volume) "
    #         "VALUES (?, ?, ?, ?, ?, ?, ?) "
    #         "ON CONFLICT(coin, timestamp) DO UPDATE SET "
    #         "open=excluded.open, high=excluded.high, low=excluded.low, "
    #         "close=excluded.close, volume=excluded.volume"
    #     )

    #     with self._connect() as conn:
    #         conn.executemany(insert_sql, payload)

    #     return len(payload)

