"""Fix timezone offset by re-downloading affected data.

Strategy:
1. Delete all data from 2020-2024 (affected by timezone bug)
2. Keep 2025-2026 data (downloaded with correct timezone)
3. Re-download 2020-2024 data using fixed script

This is safer than trying to fix timestamps in-place.
"""

import sqlite3
from pathlib import Path

db_path = Path("data/finance_data.db")
conn = sqlite3.connect(str(db_path))

print("="*80)
print("清理受时区bug影响的历史数据")
print("="*80)

# 检查当前数据
cursor = conn.execute("""
    SELECT symbol, bar,
           COUNT(*) as total,
           COUNT(CASE WHEN date < '2025-01-01' THEN 1 END) as before_2025,
           COUNT(CASE WHEN date >= '2025-01-01' THEN 1 END) as from_2025
    FROM crypto_ohlc
    GROUP BY symbol, bar
""")

print("\n当前数据统计:")
print(f"{'Symbol':<15} {'Bar':<10} {'Total':>10} {'<2025':>10} {'>=2025':>10}")
print("-"*70)

for row in cursor.fetchall():
    symbol, bar, total, before_2025, from_2025 = row
    print(f"{symbol:<15} {bar:<10} {total:>10} {before_2025:>10} {from_2025:>10}")

print("\n⚠️  将删除2025年之前的所有数据（受时区bug影响）")
print("   2025年及之后的数据将保留（时区正确）")

response = input("\n确认删除? (yes/no): ")

if response.lower() != 'yes':
    print("取消操作")
    conn.close()
    exit(0)

# 删除2025年之前的数据
print("\n删除受影响的数据...")
cursor = conn.execute("""
    DELETE FROM crypto_ohlc
    WHERE date < '2025-01-01'
""")

deleted = cursor.rowcount
conn.commit()

print(f"✓ 删除了 {deleted:,} 条记录")

# 验证结果
cursor = conn.execute("""
    SELECT symbol, bar,
           COUNT(*) as count,
           MIN(date) as min_date,
           MAX(date) as max_date
    FROM crypto_ohlc
    GROUP BY symbol, bar
""")

print("\n清理后的数据:")
print(f"{'Symbol':<15} {'Bar':<10} {'Records':>10} {'From':<25} {'To':<25}")
print("-"*90)

for row in cursor.fetchall():
    symbol, bar, count, min_date, max_date = row
    print(f"{symbol:<15} {bar:<10} {count:>10} {min_date:<25} {max_date:<25}")

conn.close()

print("\n✓ 清理完成!")
print("\n下一步: 运行 'uv run python scripts/download_crypto_data.py' 重新下载历史数据")
