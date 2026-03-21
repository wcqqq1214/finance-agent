"""Fetch crypto OHLC data from OKX and store to database."""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from time import sleep

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.okx import get_okx_client
from app.database.crypto_ohlc import upsert_crypto_ohlc, update_crypto_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CRYPTO_SYMBOLS = ["BTC-USDT", "ETH-USDT"]
TIME_BARS = ["15m", "1H", "4H", "1D", "1W", "1M"]


async def fetch_and_store(symbol: str, bar: str, limit: int = 300) -> None:
    """Fetch OHLC data from OKX and store to database.

    Args:
        symbol: Cryptocurrency symbol (e.g., 'BTC-USDT')
        bar: Timeframe bar (e.g., '15m', '1H', '4H', '1D', '1W', '1M')
        limit: Number of records to fetch (default: 300)
    """
    try:
        logger.info(f"Fetching {symbol} {bar} data (limit={limit})...")

        # Get OKX client in demo mode
        client = get_okx_client("demo")

        # Fetch candles from OKX
        candles = await client.get_candles(
            inst_id=symbol,
            bar=bar,
            limit=limit
        )

        if not candles:
            logger.warning(f"No data returned for {symbol} {bar}")
            return

        # Transform data for database
        records = []
        for candle in candles:
            # Convert timestamp from milliseconds to datetime string
            timestamp_ms = int(candle["ts"])
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            date_str = dt.isoformat()

            records.append({
                "timestamp": timestamp_ms,
                "date": date_str,
                "open": float(candle["o"]),
                "high": float(candle["h"]),
                "low": float(candle["l"]),
                "close": float(candle["c"]),
                "volume": float(candle["vol"])
            })

        # Store to database
        count = upsert_crypto_ohlc(symbol, bar, records)
        logger.info(f"Stored {count} records for {symbol} {bar}")

        # Update metadata
        if records:
            # Records are sorted by timestamp descending from OKX
            start_date = records[-1]["date"]  # Oldest
            end_date = records[0]["date"]     # Newest
            update_crypto_metadata(
                symbol=symbol,
                bar=bar,
                start=start_date,
                end=end_date,
                total_records=count
            )
            logger.info(f"Updated metadata for {symbol} {bar}: {start_date} to {end_date}")

    except Exception as e:
        logger.error(f"Error fetching {symbol} {bar}: {e}", exc_info=True)


async def fetch_all() -> None:
    """Fetch all symbols and bars with rate limiting."""
    logger.info("Starting crypto OHLC data fetch...")
    logger.info(f"Symbols: {CRYPTO_SYMBOLS}")
    logger.info(f"Time bars: {TIME_BARS}")

    total_tasks = len(CRYPTO_SYMBOLS) * len(TIME_BARS)
    completed = 0

    for symbol in CRYPTO_SYMBOLS:
        for bar in TIME_BARS:
            await fetch_and_store(symbol, bar)
            completed += 1
            logger.info(f"Progress: {completed}/{total_tasks}")

            # Sleep to avoid rate limits (0.5 seconds between requests)
            if completed < total_tasks:
                sleep(0.5)

    logger.info("Crypto OHLC data fetch completed!")


if __name__ == "__main__":
    asyncio.run(fetch_all())
