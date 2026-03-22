"""Initialize crypto K-line data for cold-hot architecture.

This script downloads recent historical data to populate the cold storage layer.
For production, you should download more historical data.

Usage:
    uv run python scripts/init_crypto_data.py
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.batch_downloader import download_daily_data
from app.database.schema import init_db


async def main():
    """Download last 7 days of data for BTCUSDT and ETHUSDT."""
    print("初始化加密货币 K 线数据...")

    # Initialize database
    init_db()
    print("✓ 数据库已初始化")

    symbols = ["BTCUSDT", "ETHUSDT"]
    intervals = ["1m", "1d"]

    # Use 2024 data since 2026 data is not available yet
    # Download data from March 2024
    base_date = date(2024, 3, 20)
    days_to_download = 7

    print(f"\n下载 2024年3月 的数据（用于测试）...")

    total_records = 0
    for i in range(days_to_download):
        target_date = base_date - timedelta(days=i)
        print(f"\n日期: {target_date}")

        for symbol in symbols:
            for interval in intervals:
                try:
                    records = await download_daily_data(symbol, interval, target_date)
                    if records:
                        total_records += len(records)
                        print(f"  ✓ {symbol} {interval}: {len(records)} 条记录")
                    else:
                        print(f"  ✗ {symbol} {interval}: 无数据")
                except Exception as e:
                    print(f"  ✗ {symbol} {interval}: 错误 - {e}")

    print(f"\n完成！共下载 {total_records} 条记录")
    print("\n提示：")
    print("- 1m 数据用于热缓存（最近48小时）")
    print("- 1d 数据用于长期历史分析")
    print("- 生产环境建议下载更多历史数据")


if __name__ == "__main__":
    asyncio.run(main())
