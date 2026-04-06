"""Tests for database schema initialization and metadata migrations."""

from __future__ import annotations

import sqlite3

from app.database.schema import get_ticker_peer_groups, init_db


def test_init_db_seeds_peer_group_metadata(tmp_path):
    db_path = tmp_path / "finance_schema.db"

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tickers)").fetchall()]
    assert "peer_group" in columns

    rows = conn.execute(
        "SELECT symbol, peer_group FROM tickers WHERE symbol IN ('MSFT', 'AMZN', 'NVDA') ORDER BY symbol"
    ).fetchall()
    conn.close()

    peer_groups = {symbol: peer_group for symbol, peer_group in rows}
    assert peer_groups["AMZN"] == "cloud_enterprise_ai"
    assert peer_groups["MSFT"] == "cloud_enterprise_ai"
    assert peer_groups["NVDA"] == "ai_compute_semis"


def test_init_db_migrates_existing_tickers_table_with_peer_groups(tmp_path):
    db_path = tmp_path / "legacy_finance_schema.db"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE tickers (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            last_ohlc_fetch TEXT,
            last_news_fetch TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO tickers (symbol, name) VALUES (?, ?)",
        ("MSFT", "Microsoft Corporation"),
    )
    conn.commit()
    conn.close()

    init_db(db_path)

    conn = sqlite3.connect(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tickers)").fetchall()]
    row = conn.execute("SELECT peer_group FROM tickers WHERE symbol = 'MSFT'").fetchone()
    conn.close()

    assert "peer_group" in columns
    assert row is not None
    assert row[0] == "cloud_enterprise_ai"

    peer_group_map = get_ticker_peer_groups(db_path)
    assert peer_group_map["MSFT"] == "cloud_enterprise_ai"


def test_init_db_creates_nested_parent_dirs(tmp_path):
    """init_db should create missing parent directories for the target DB path."""
    db_path = tmp_path / "deep" / "layout" / "finance_schema.db"
    init_db(db_path)
    assert db_path.exists()
