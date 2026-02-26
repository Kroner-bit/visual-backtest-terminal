"""
Data Cache — SQLite storage for OHLCV data
-------------------------------------------
Stores downloaded market data locally so the same
ticker/period/interval combination is not re-downloaded.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Tuple

import pandas as pd


DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_data.db")


def _get_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str = None):
    """Create tables if they don't exist."""
    conn = _get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL,
            period      TEXT NOT NULL,
            interval    TEXT NOT NULL,
            bars        INTEGER NOT NULL,
            start_date  TEXT,
            end_date    TEXT,
            downloaded  TEXT NOT NULL,
            UNIQUE(ticker, period, interval)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            dataset_id  INTEGER NOT NULL,
            ts          TEXT NOT NULL,
            open        REAL NOT NULL,
            high        REAL NOT NULL,
            low         REAL NOT NULL,
            close       REAL NOT NULL,
            volume      REAL,
            PRIMARY KEY (dataset_id, ts),
            FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def save_dataset(
    ticker: str,
    period: str,
    interval: str,
    df: pd.DataFrame,
    db_path: str = None,
) -> int:
    """
    Save an OHLCV DataFrame to the database.
    If the same ticker/period/interval already exists, replace it.

    Returns:
        The dataset ID.
    """
    conn = _get_connection(db_path)
    cur = conn.cursor()

    # Delete existing data for the same combination
    cur.execute(
        "SELECT id FROM datasets WHERE ticker=? AND period=? AND interval=?",
        (ticker, period, interval),
    )
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM ohlcv WHERE dataset_id=?", (row[0],))
        cur.execute("DELETE FROM datasets WHERE id=?", (row[0],))

    # Get date range
    start_date = str(df.index[0])[:19] if len(df) > 0 else ""
    end_date = str(df.index[-1])[:19] if len(df) > 0 else ""

    # Insert dataset metadata
    cur.execute(
        """INSERT INTO datasets (ticker, period, interval, bars, start_date, end_date, downloaded)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ticker, period, interval, len(df), start_date, end_date,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    dataset_id = cur.lastrowid

    # Insert OHLCV rows
    rows = []
    for ts, r in df.iterrows():
        rows.append((
            dataset_id,
            str(ts)[:19],
            float(r['Open']),
            float(r['High']),
            float(r['Low']),
            float(r['Close']),
            float(r.get('Volume', 0)) if 'Volume' in r.index else 0.0,
        ))
    cur.executemany(
        "INSERT INTO ohlcv (dataset_id, ts, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )

    conn.commit()
    conn.close()
    return dataset_id


def load_dataset(dataset_id: int, db_path: str = None) -> Optional[pd.DataFrame]:
    """
    Load an OHLCV DataFrame from the database by dataset ID.

    Returns:
        DataFrame with DatetimeIndex, or None if not found.
    """
    conn = _get_connection(db_path)
    cur = conn.cursor()

    cur.execute(
        "SELECT ts, open, high, low, close, volume FROM ohlcv WHERE dataset_id=? ORDER BY ts",
        (dataset_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df.set_index('Datetime', inplace=True)
    return df


def list_datasets(db_path: str = None) -> List[dict]:
    """
    List all cached datasets.

    Returns:
        List of dicts with keys: id, ticker, period, interval, bars,
        start_date, end_date, downloaded.
    """
    conn = _get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, ticker, period, interval, bars, start_date, end_date, downloaded "
        "FROM datasets ORDER BY downloaded DESC"
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            'id': r[0],
            'ticker': r[1],
            'period': r[2],
            'interval': r[3],
            'bars': r[4],
            'start_date': r[5],
            'end_date': r[6],
            'downloaded': r[7],
        }
        for r in rows
    ]


def delete_dataset(dataset_id: int, db_path: str = None):
    """Delete a dataset and its OHLCV data."""
    conn = _get_connection(db_path)
    conn.execute("DELETE FROM ohlcv WHERE dataset_id=?", (dataset_id,))
    conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    conn.commit()
    conn.close()


def find_dataset(ticker: str, period: str, interval: str, db_path: str = None) -> Optional[dict]:
    """Find a cached dataset by ticker/period/interval."""
    conn = _get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, ticker, period, interval, bars, start_date, end_date, downloaded "
        "FROM datasets WHERE ticker=? AND period=? AND interval=?",
        (ticker, period, interval),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'ticker': row[1],
            'period': row[2],
            'interval': row[3],
            'bars': row[4],
            'start_date': row[5],
            'end_date': row[6],
            'downloaded': row[7],
        }
    return None


# Initialize DB on import
init_db()
