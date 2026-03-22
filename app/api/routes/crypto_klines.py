"""Crypto K-lines API endpoint."""
from typing import List, Optional
from fastapi import APIRouter, Query
import pandas as pd

from app.database.crypto_ohlc import get_crypto_ohlc
from app.services.hot_cache import get_hot_cache

router = APIRouter()


@router.get("/crypto/klines")
async def get_crypto_klines(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTCUSDT)"),
    interval: str = Query(..., description="K-line interval (e.g., 1m, 1d)"),
    start: Optional[str] = Query(None, description="Start date in ISO format"),
    end: Optional[str] = Query(None, description="End date in ISO format")
) -> List[dict]:
    """
    Get crypto K-line data by merging cold (database) and hot (cache) data.

    This endpoint implements the Lambda architecture pattern:
    1. Fetch historical data from cold storage (SQLite)
    2. Fetch recent data from hot cache (in-memory)
    3. Merge and deduplicate (hot data takes precedence)
    4. Return sorted by timestamp

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        interval: K-line interval (e.g., "1m", "1d")
        start: Optional start date filter
        end: Optional end date filter

    Returns:
        List of K-line records with keys: timestamp, date, open, high, low, close, volume
    """
    # Fetch cold data from database
    cold_data = get_crypto_ohlc(
        symbol=symbol,
        bar=interval,
        start=start,
        end=end
    )

    # Fetch hot data from cache
    hot_df = get_hot_cache(symbol, interval)

    # Convert cold data to DataFrame
    if cold_data:
        cold_df = pd.DataFrame(cold_data)
        # Remove 'symbol' and 'bar' columns to match hot data format
        cold_df = cold_df[['timestamp', 'date', 'open', 'high', 'low', 'close', 'volume']]
    else:
        cold_df = pd.DataFrame(columns=['timestamp', 'date', 'open', 'high', 'low', 'close', 'volume'])

    # Merge cold and hot data
    if not hot_df.empty:
        merged_df = pd.concat([cold_df, hot_df], ignore_index=True)
    else:
        merged_df = cold_df

    # Deduplicate by timestamp (keep last, which prioritizes hot data)
    if not merged_df.empty:
        merged_df = merged_df.drop_duplicates(subset=['timestamp'], keep='last')
        merged_df = merged_df.sort_values('timestamp')

    # Convert to list of dicts
    result = merged_df.to_dict('records')

    return result
