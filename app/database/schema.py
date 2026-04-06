"""SQLite database schema and connection management for finance-agent.

This module provides the database schema for storing historical OHLC data, news
articles, and multi-layer pipeline results for the Magnificent Seven stocks.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_TICKER_CATALOG = [
    ("AAPL", "Apple Inc.", "consumer_ecosystem"),
    ("MSFT", "Microsoft Corporation", "cloud_enterprise_ai"),
    ("GOOGL", "Alphabet Inc.", "internet_ad_platform"),
    ("AMZN", "Amazon.com Inc.", "cloud_enterprise_ai"),
    ("META", "Meta Platforms Inc.", "internet_ad_platform"),
    ("NVDA", "NVIDIA Corporation", "ai_compute_semis"),
    ("TSLA", "Tesla Inc.", "ev_autonomy_high_beta"),
]

# Database schema with alignment and pipeline tables
SCHEMA = """
CREATE TABLE IF NOT EXISTS tickers (
    symbol        TEXT PRIMARY KEY,
    name          TEXT,
    peer_group    TEXT,
    last_ohlc_fetch   TEXT,
    last_news_fetch   TEXT
);

CREATE TABLE IF NOT EXISTS ohlc (
    symbol        TEXT NOT NULL,
    date          TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    volume        REAL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_date ON ohlc(symbol, date DESC);

CREATE TABLE IF NOT EXISTS crypto_ohlc (
    symbol        TEXT NOT NULL,
    timestamp     INTEGER NOT NULL,
    date          TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    volume        REAL,
    bar           TEXT NOT NULL,
    PRIMARY KEY (symbol, timestamp, bar)
);
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_symbol_date ON crypto_ohlc(symbol, date DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_ohlc_symbol_bar_date ON crypto_ohlc(symbol, bar, date DESC);

CREATE TABLE IF NOT EXISTS crypto_metadata (
    symbol        TEXT NOT NULL,
    bar           TEXT NOT NULL,
    last_update   TEXT,
    data_start    TEXT,
    data_end      TEXT,
    total_records INTEGER,
    PRIMARY KEY (symbol, bar)
);

CREATE TABLE IF NOT EXISTS news (
    id            TEXT PRIMARY KEY,
    symbol        TEXT NOT NULL,
    published_utc TEXT NOT NULL,
    title         TEXT,
    description   TEXT,
    article_url   TEXT,
    publisher     TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news(symbol, published_utc DESC);

-- News-to-trading-day alignment with forward returns
CREATE TABLE IF NOT EXISTS news_aligned (
    news_id       TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    published_utc TEXT,
    ret_t0        REAL,
    ret_t1        REAL,
    ret_t3        REAL,
    ret_t5        REAL,
    ret_t10       REAL,
    PRIMARY KEY (news_id, symbol)
);
CREATE INDEX IF NOT EXISTS idx_news_aligned_symbol_date ON news_aligned(symbol, trade_date);

-- Layer 0: Rule-based filter results
CREATE TABLE IF NOT EXISTS layer0_results (
    news_id       TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    passed        INTEGER NOT NULL,
    reason        TEXT,
    PRIMARY KEY (news_id, symbol)
);

-- Layer 1: LLM semantic extraction results
CREATE TABLE IF NOT EXISTS layer1_results (
    news_id       TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    relevance     TEXT,
    key_discussion      TEXT,
    sentiment           TEXT,
    reason_growth       TEXT,
    reason_decrease     TEXT,
    PRIMARY KEY (news_id, symbol)
);

-- Batch API job tracking
CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id      TEXT PRIMARY KEY,
    symbol        TEXT,
    status        TEXT,
    total         INTEGER,
    completed     INTEGER DEFAULT 0,
    created_at    TEXT,
    finished_at   TEXT
);
"""

# Default database path
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "finance_data.db"


def _is_sqlite_uri(path: Path) -> bool:
    string = str(path)
    return string == ":memory:" or string.startswith("file:")


def _ensure_parent_dir(path: Path) -> None:
    if _is_sqlite_uri(path):
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def get_conn(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a database connection with optimized settings.

    Args:
        db_path: Path to the SQLite database file. If None, uses default path.

    Returns:
        A configured SQLite connection with Row factory enabled.
    """
    path = db_path or DEFAULT_DB_PATH
    _ensure_parent_dir(path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the database schema.

    Args:
        db_path: Path to the SQLite database file. If None, uses default path.
    """
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    _ensure_ticker_peer_group_column(conn)
    _seed_default_tickers(conn)

    conn.commit()
    conn.close()

    path = db_path or DEFAULT_DB_PATH
    print(f"Database initialized at {path}")


def _table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Return whether a SQLite table currently contains the named column."""

    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(str(row["name"]) == column_name for row in rows)


def _ensure_ticker_peer_group_column(conn: sqlite3.Connection) -> None:
    """Apply a lightweight migration for older databases missing peer_group."""

    if not _table_has_column(conn, "tickers", "peer_group"):
        conn.execute("ALTER TABLE tickers ADD COLUMN peer_group TEXT")


def _seed_default_tickers(conn: sqlite3.Connection) -> None:
    """Seed or backfill the default ticker catalog and peer-group metadata."""

    for symbol, name, peer_group in DEFAULT_TICKER_CATALOG:
        conn.execute(
            "INSERT OR IGNORE INTO tickers (symbol, name, peer_group) VALUES (?, ?, ?)",
            (symbol, name, peer_group),
        )
        conn.execute(
            """
            UPDATE tickers
            SET name = CASE
                    WHEN name IS NULL OR TRIM(name) = '' THEN ?
                    ELSE name
                END,
                peer_group = CASE
                    WHEN peer_group IS NULL OR TRIM(peer_group) = '' THEN ?
                    ELSE peer_group
                END
            WHERE symbol = ?
            """,
            (name, peer_group, symbol),
        )


def get_ticker_peer_groups(db_path: Optional[Path] = None) -> dict[str, str]:
    """Return ticker -> peer_group mappings from the metadata table."""

    conn = get_conn(db_path)
    try:
        if not _table_has_column(conn, "tickers", "peer_group"):
            return {}

        rows = conn.execute(
            """
            SELECT symbol, peer_group
            FROM tickers
            WHERE symbol IS NOT NULL
              AND peer_group IS NOT NULL
              AND TRIM(peer_group) <> ''
            """
        ).fetchall()
        return {
            str(row["symbol"]).strip().upper(): str(row["peer_group"]).strip()
            for row in rows
            if row["symbol"] and row["peer_group"]
        }
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
