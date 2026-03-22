"""Realtime agent for hot cache warmup and updates."""
from datetime import datetime, timezone, timedelta
from typing import List
import asyncio
import logging

from app.services.binance_client import fetch_binance_klines
from app.services.hot_cache import append_to_hot_cache, cleanup_hot_cache

logger = logging.getLogger(__name__)

# Configuration
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVALS = ["1m", "1d"]
WARMUP_HOURS = 48
UPDATE_HOURS = 1


async def warmup_hot_cache() -> None:
    """
    Warmup hot cache with last 48 hours of data for all symbols and intervals.

    This function is called on application startup to populate the hot cache
    with recent historical data.
    """
    logger.info("Starting hot cache warmup...")

    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(hours=WARMUP_HOURS)).timestamp() * 1000)

    for symbol in SYMBOLS:
        for interval in INTERVALS:
            try:
                logger.info(f"Warming up {symbol} {interval}...")
                klines = await fetch_binance_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000
                )

                if klines:
                    append_to_hot_cache(symbol, interval, klines)
                    logger.info(f"Warmed up {symbol} {interval} with {len(klines)} records")
                else:
                    logger.warning(f"No data returned for {symbol} {interval}")

            except Exception as e:
                logger.error(f"Failed to warmup {symbol} {interval}: {e}")

    logger.info("Hot cache warmup completed")


async def update_hot_cache() -> None:
    """
    Update hot cache with latest data and cleanup old data.

    This function is called periodically (e.g., every minute) to:
    1. Fetch the latest data from Binance API
    2. Append new data to hot cache
    3. Remove data older than 48 hours
    """
    logger.debug("Updating hot cache...")

    now = datetime.now(timezone.utc)
    end_time = int(now.timestamp() * 1000)
    start_time = int((now - timedelta(hours=UPDATE_HOURS)).timestamp() * 1000)
    cutoff_time = now - timedelta(hours=WARMUP_HOURS)

    for symbol in SYMBOLS:
        for interval in INTERVALS:
            try:
                # Fetch latest data
                klines = await fetch_binance_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000
                )

                if klines:
                    append_to_hot_cache(symbol, interval, klines)
                    logger.debug(f"Updated {symbol} {interval} with {len(klines)} records")

                # Cleanup old data
                cleanup_hot_cache(symbol, interval, cutoff_time)

            except Exception as e:
                logger.error(f"Failed to update {symbol} {interval}: {e}")

    logger.debug("Hot cache update completed")


async def update_hot_cache_loop() -> None:
    """
    Continuous loop that updates hot cache every 60 seconds.

    This function runs as a background task and periodically fetches
    the latest data from Binance API to keep the hot cache fresh.
    """
    logger.info("Starting hot cache update loop...")

    while True:
        try:
            await asyncio.sleep(60)  # Wait 60 seconds between updates
            await update_hot_cache()
        except Exception as e:
            logger.error(f"Error in hot cache update loop: {e}")
            # Continue running even if one update fails
            await asyncio.sleep(60)
