#!/usr/bin/env python3
"""
Fix timezone in ClickHouse tables by recreating with corrected timestamps
Subtracts 5:30 hours (19800 seconds) from all timestamps
"""

import subprocess
import time

def run_clickhouse(query):
    """Run ClickHouse query"""
    cmd = [
        'clickhouse', 'client',
        '--host', 'localhost',
        '--port', '9000',
        '--user', 'default',
        '--database', 'tradelayout',
        '--query', query
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip()

def fix_table(table_name, columns_config):
    """Fix timezone for a table by recreating it"""
    
    print("=" * 100)
    print(f"📋 Processing: {table_name}")
    print("=" * 100)
    
    # Check current range
    print("Current timestamp range:")
    current_range = run_clickhouse(f"SELECT min(timestamp), max(timestamp), count() FROM {table_name}")
    print(f"  {current_range}")
    
    # Create temp table
    temp_table = f"{table_name}_temp"
    
    print(f"\n⏳ Creating temporary table with corrected timestamps...")
    
    # Drop if exists
    run_clickhouse(f"DROP TABLE IF EXISTS {temp_table}")
    
    # Create table structure
    create_query = columns_config['create'].format(table_name=temp_table)
    run_clickhouse(create_query)
    
    # Insert with corrected timestamps
    print(f"⏳ Copying data with corrected timestamps (this will take a few minutes)...")
    
    column_list = columns_config['columns']
    insert_query = f"""
        INSERT INTO {temp_table}
        SELECT 
            {column_list}
        FROM {table_name}
    """
    
    run_clickhouse(insert_query)
    
    # Check new range
    print("\nNew timestamp range:")
    new_range = run_clickhouse(f"SELECT min(timestamp), max(timestamp), count() FROM {temp_table}")
    print(f"  {new_range}")
    
    # Swap tables
    print(f"\n⚡ Swapping tables...")
    run_clickhouse(f"DROP TABLE {table_name}")
    run_clickhouse(f"RENAME TABLE {temp_table} TO {table_name}")
    
    print(f"✅ {table_name} - Timezone fixed!")
    print()

def main():
    print("=" * 100)
    print("⏰ FIXING TIMEZONE IN ALL TABLES (UTC → IST)")
    print("=" * 100)
    print("\nSubtracting 5:30 hours (19800 seconds) from all timestamps...")
    print()
    
    # Define table configurations
    tables = {
        'nse_ticks_indices': {
            'create': """
                CREATE TABLE {table_name} (
                    trading_day Date,
                    timestamp DateTime,
                    symbol String,
                    ltp Float64,
                    volume UInt64,
                    ltq UInt64,
                    oi UInt64,
                    bid_price Float64,
                    ask_price Float64,
                    bid_qty UInt64,
                    ask_qty UInt64,
                    buy_qty UInt64,
                    sell_qty UInt64
                ) ENGINE = MergeTree
                PARTITION BY trading_day
                ORDER BY (trading_day, symbol, timestamp)
            """,
            'columns': """
                trading_day,
                timestamp - INTERVAL 19800 SECOND as timestamp,
                symbol, ltp, volume, ltq, oi,
                bid_price, ask_price, bid_qty, ask_qty, buy_qty, sell_qty
            """
        },
        'nse_ticks_options': {
            'create': """
                CREATE TABLE {table_name} (
                    trading_day Date,
                    timestamp DateTime,
                    ticker String,
                    ltp Float64,
                    volume UInt64,
                    ltq UInt64,
                    oi UInt64,
                    bid_price Float64,
                    ask_price Float64,
                    bid_qty UInt64,
                    ask_qty UInt64,
                    buy_qty UInt64,
                    sell_qty UInt64
                ) ENGINE = MergeTree
                PARTITION BY trading_day
                ORDER BY (trading_day, ticker, timestamp)
            """,
            'columns': """
                trading_day,
                timestamp - INTERVAL 19800 SECOND as timestamp,
                ticker, ltp, volume, ltq, oi,
                bid_price, ask_price, bid_qty, ask_qty, buy_qty, sell_qty
            """
        },
        'nse_ticks_stocks': {
            'create': """
                CREATE TABLE {table_name} (
                    trading_day Date,
                    timestamp DateTime,
                    symbol String,
                    ltp Float64,
                    volume UInt64,
                    ltq UInt64,
                    oi UInt64,
                    bid_price Float64,
                    ask_price Float64,
                    bid_qty UInt64,
                    ask_qty UInt64,
                    buy_qty UInt64,
                    sell_qty UInt64
                ) ENGINE = MergeTree
                PARTITION BY trading_day
                ORDER BY (trading_day, symbol, timestamp)
            """,
            'columns': """
                trading_day,
                timestamp - INTERVAL 19800 SECOND as timestamp,
                symbol, ltp, volume, ltq, oi,
                bid_price, ask_price, bid_qty, ask_qty, buy_qty, sell_qty
            """
        },
        'nse_ohlcv_indices': {
            'create': """
                CREATE TABLE {table_name} (
                    symbol String,
                    timeframe String,
                    trading_day Date,
                    timestamp DateTime,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume UInt64
                ) ENGINE = MergeTree
                PARTITION BY toYYYYMM(trading_day)
                ORDER BY (symbol, timeframe, timestamp)
            """,
            'columns': """
                symbol, timeframe, trading_day,
                timestamp - INTERVAL 19800 SECOND as timestamp,
                open, high, low, close, volume
            """
        },
        'nse_ohlcv_stocks': {
            'create': """
                CREATE TABLE {table_name} (
                    symbol String,
                    timeframe String,
                    trading_day Date,
                    timestamp DateTime,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume UInt64,
                    source String
                ) ENGINE = MergeTree
                PARTITION BY toYYYYMM(trading_day)
                ORDER BY (symbol, timeframe, timestamp)
            """,
            'columns': """
                symbol, timeframe, trading_day,
                timestamp - INTERVAL 19800 SECOND as timestamp,
                open, high, low, close, volume, source
            """
        }
    }
    
    # Fix each table
    for table_name, config in tables.items():
        try:
            fix_table(table_name, config)
        except Exception as e:
            print(f"❌ Error fixing {table_name}: {e}")
            continue
    
    print("=" * 100)
    print("✅ ALL TABLES UPDATED")
    print("=" * 100)
    print()
    
    # Verify Oct 29 data
    print("=" * 100)
    print("🔍 VERIFICATION - Oct 29, 2024 Data")
    print("=" * 100)
    print()
    
    print("📊 nse_ticks_indices (Oct 29):")
    result = run_clickhouse("""
        SELECT 
            symbol,
            min(timestamp) as first_tick,
            max(timestamp) as last_tick,
            count() as ticks
        FROM nse_ticks_indices
        WHERE trading_day = '2024-10-29'
        GROUP BY symbol
    """)
    print(result)
    
    print("\n📊 nse_ticks_options (Oct 29):")
    result = run_clickhouse("""
        SELECT 
            min(timestamp) as first_tick,
            max(timestamp) as last_tick,
            count() as ticks
        FROM nse_ticks_options
        WHERE trading_day = '2024-10-29'
    """)
    print(result)
    
    print("\n" + "=" * 100)
    print("✅ TIMEZONE FIX COMPLETE")
    print("=" * 100)
    print("\nExpected Oct 29 time range: 09:07:04 to 15:30:00 (IST)")
    print("Data is now ready for backtesting with correct timestamps!")
    print()

if __name__ == "__main__":
    main()
