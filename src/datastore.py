"""Minimal SQLite helper for the trading bot.

This module currently handles only two things:
1. Ensuring the SQLite database file exists in the desired location.
2. Creating the base tables (ohlcv, pivots, opportunities).

We'll add read/write helpers later once the schema is locked in.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .models import Opportunity, PivotPoint


def _ensure_parent(path: Path) -> None:
    """Create the parent directory for the database file if required."""

    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _coerce_timestamp(value) -> Optional[int]:
    """Convert assorted timestamp representations to epoch seconds."""

    if value is None:
        return None

    try:
        ts = int(float(value))
        return ts if ts > 0 else None
    except (TypeError, ValueError):
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
        return int(dt.timestamp()) if dt.timestamp() > 0 else None


def _to_datetime(seconds: int) -> datetime:
    """Return a UTC datetime from epoch seconds."""

    return datetime.fromtimestamp(int(seconds), tz=timezone.utc)


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
        CREATE TABLE IF NOT EXISTS ohlcv (
            coin TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (coin, timestamp)
        );

        CREATE TABLE IF NOT EXISTS pivots (
            coin TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            price REAL NOT NULL,
            pivot_type TEXT NOT NULL CHECK (pivot_type IN ('high', 'low')),
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
            PRIMARY KEY (coin, timestamp, pivot_type)
        );

        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin TEXT NOT NULL,
            support_line REAL NOT NULL,
            minimum REAL NOT NULL,
            maximum REAL NOT NULL,
            pivot_low REAL NOT NULL,
            pivot_high REAL NOT NULL,
            start_time INTEGER,
            end_time INTEGER,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );
        """

        with self._connect() as conn:
            conn.executescript(schema)

    def ingest_csv(self, coin: str, csv_path: str | Path, *, batch_size: int = 1000) -> int:
        """Load OHLCV rows from a CSV file into the database.

        The CSV must contain the columns ``timestamp``, ``open``, ``high``, ``low``,
        ``close`` and ``volume``. Rows with missing or invalid values are skipped.

        Returns the number of upserted rows.
        """

        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        insert_sql = (
            "INSERT INTO ohlcv (coin, timestamp, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(coin, timestamp) DO UPDATE SET "
            "open=excluded.open, high=excluded.high, low=excluded.low, "
            "close=excluded.close, volume=excluded.volume"
        )

        written = 0
        buffer: List[Tuple[str, int, float, float, float, float, float]] = []

        with csv_path.open("r", newline="") as handle, self._connect() as conn:
            reader = csv.DictReader(handle)
            for row in reader:
                timestamp = _coerce_timestamp(row.get("timestamp"))
                if timestamp is None:
                    continue

                try:
                    open_ = float(row["open"])
                    high = float(row["high"])
                    low = float(row["low"])
                    close = float(row["close"])
                    volume = float(row["volume"])
                except (KeyError, TypeError, ValueError):
                    continue

                buffer.append((coin, timestamp, open_, high, low, close, volume))

                if len(buffer) >= batch_size:
                    conn.executemany(insert_sql, buffer)
                    written += len(buffer)
                    buffer.clear()

            if buffer:
                conn.executemany(insert_sql, buffer)
                written += len(buffer)

        return written



    def fetch_ohlcv(
        self,
        coin: str,
        *,
        since: Optional[int | str] = None,
        until: Optional[int | str] = None,
        limit: Optional[int] = None,
        descending: bool = True,
    ) -> List[Tuple[int, float, float, float, float, float]]:
        """Return OHLCV rows with optional time filtering."""

        clauses = ["coin = ?"]
        params: List[object] = [coin]

        if since is not None:
            since_ts = _coerce_timestamp(since)
            if since_ts is not None:
                clauses.append("timestamp >= ?")
                params.append(since_ts)

        if until is not None:
            until_ts = _coerce_timestamp(until)
            if until_ts is not None:
                clauses.append("timestamp <= ?")
                params.append(until_ts)

        order = "DESC" if descending else "ASC"

        query_parts = [
            "SELECT timestamp, open, high, low, close, volume FROM ohlcv WHERE",
            " AND ".join(clauses),
            f"ORDER BY timestamp {order}",
        ]

        if limit is not None:
            query_parts.append("LIMIT ?")
            params.append(int(limit))

        query = " ".join(query_parts)

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            return [tuple(row) for row in cursor.fetchall()]

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

        since_ts = _coerce_timestamp(since)
        if since_ts is not None:
            clauses.append("timestamp >= ?")
            params.append(since_ts)

        until_ts = _coerce_timestamp(until)
        if until_ts is not None:
            clauses.append("timestamp <= ?")
            params.append(until_ts)

        query = (
            "SELECT timestamp, price, pivot_type FROM pivots WHERE "
            + " AND ".join(clauses)
            + " ORDER BY timestamp ASC"
        )

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [
            PivotPoint(timestamp=int(row[0]), price=row[1], type=row[2])
            for row in rows
        ]

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

        since_ts = _coerce_timestamp(since)
        if since_ts is not None:
            clauses.append("(start_time IS NULL OR start_time >= ?)")
            params.append(since_ts)

        until_ts = _coerce_timestamp(until)
        if until_ts is not None:
            clauses.append("(end_time IS NULL OR end_time <= ?)")
            params.append(until_ts)

        query_parts = [
            "SELECT support_line, minimum, maximum, pivot_low, pivot_high, start_time, end_time"
            " FROM opportunities WHERE",
            " AND ".join(clauses),
            "ORDER BY COALESCE(start_time, end_time, created_at) ASC",
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
                    support_line=row[0],
                    minimum=row[1],
                    maximum=row[2],
                    pivot_low=row[3],
                    pivot_high=row[4],
                    start=start_dt,
                    end=end_dt,
                )
            )

        return opportunities
