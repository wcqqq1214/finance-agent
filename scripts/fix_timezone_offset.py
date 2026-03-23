"""Fix timezone offset in historical crypto data.

This script fixes the 8-hour timezone offset issue in data downloaded
before the timezone fix was applied.

The issue: pandas to_datetime() without utc=True creates timezone-naive
timestamps, which are then interpreted as local time (UTC+8) when converted
back to Unix timestamps, causing an 8-hour shift.

This script identifies and fixes affected records.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

db_path = Path("data/finance_data.db")
conn = sqlite3.connect(str(db_path))

print("="*80)
print("修复历史数据时区偏移问题")
print("="*80)

# 检查受影响的数据范围
# 2024年及之前的数据可能受影响（使用旧脚本下载）
# 2025年的数据应该是正确的（使用新脚本下载）

cursor = conn.execute("""
    SELECT symbol, bar,
           MIN(timestamp) as min_ts,
           MAX(timestamp) as max_ts,
           COUNT(*) as count
    FROM crypto_ohlc
    WHERE date < '2025-01-01'
    GROUP BY symbol, bar
""")

print("\n2025年之前的数据统计:")
print(f"{'Symbol':<15} {'Bar':<10} {'Records':>10} {'Min Timestamp':<20} {'Max Timestamp':<20}")
print("-"*90)

affected_data = []
for row in cursor.fetchall():
    symbol, bar, min_ts, max_ts, count = row
    min_dt = datetime.fromtimestamp(min_ts / 1000, tz=timezone.utc)
    max_dt = datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc)
    print(f"{symbol:<15} {bar:<10} {count:>10} {str(min_dt):<20} {str(max_dt):<20}")
    affected_data.append((symbol, bar, count))

print(f"\n检测到需要修复的数据组: {len(affected_data)}")

# 修复策略：将所有2025年之前的时间戳增加8小时（28800000毫秒）
print("\n开始修复...")

for symbol, bar, count in affected_data:
    print(f"\n修复 {symbol} {bar} ({count} 条记录)...")

    # 更新时间戳：增加8小时
    cursor = conn.execute("""
        UPDATE crypto_ohlc
        SET timestamp = timestamp + 28800000,
            date = datetime((timestamp + 28800000) / 1000, 'unixepoch')
        WHERE symbol = ? AND bar = ? AND date < '2025-01-01'
    """, (symbol, bar))

    updated = cursor.rowcount
    print(f"  更新了 {updated} 条记录")

conn.commit()

# 验证修复结果
print("\n" + "="*80)
print("验证修复结果")
print("="*80)

cursor = conn.execute("""
    SELECT symbol, bar,
           MIN(timestamp) as min_ts,
           MAX(timestamp) as max_ts,
           COUNT(*) as count
    FROM crypto_ohlc
    WHERE date < '2025-01-01'
    GROUP BY symbol, bar
""")

print("\n修复后的数据:")
print(f"{'Symbol':<15} {'Bar':<10} {'Records':>10} {'Min Timestamp':<20} {'Max Timestamp':<20}")
print("-"*90)

for row in cursor.fetchall():
    symbol, bar, min_ts, max_ts, count = row
    min_dt = datetime.fromtimestamp(min_ts / 1000, tz=timezone.utc)
    max_dt = datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc)
    print(f"{symbol:<15} {bar:<10} {count:>10} {str(min_dt):<20} {str(max_dt):<20}")

# 检查跨年gap是否修复
print("\n检查跨年连续性:")
cursor = conn.execute("""
    SELECT symbol, bar,
           MAX(CASE WHEN date LIKE '2024-12-31%' THEN timestamp END) as last_2024,
           MIN(CASE WHEN date LIKE '2025-01-01%' THEN timestamp END) as first_2025
    FROM crypto_ohlc
    GROUP BY symbol, bar
""")

for row in cursor.fetchall():
    symbol, bar, last_2024, first_2025 = row
    if last_2024 and first_2025:
        gap_ms = first_2025 - last_2024
        gap_minutes = gap_ms / 1000 / 60

        last_dt = datetime.fromtimestamp(last_2024 / 1000, tz=timezone.utc)
        first_dt = datetime.fromtimestamp(first_2025 / 1000, tz=timezone.utc)

        print(f"\n{symbol} {bar}:")
        print(f"  2024最后: {last_dt}")
        print(f"  2025最早: {first_dt}")
        print(f"  Gap: {gap_minutes:.1f} 分钟")

        if gap_minutes <= 1:
            print(f"  ✅ 连续")
        else:
            print(f"  ⚠️  仍有gap")

conn.close()

print("\n✓ 修复完成!")
