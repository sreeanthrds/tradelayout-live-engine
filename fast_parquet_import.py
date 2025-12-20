#!/usr/bin/env python3
"""
Super Fast Parquet Import to ClickHouse
Imports millions of rows in seconds using native ClickHouse format
"""

import os
import glob
import pandas as pd
from datetime import datetime
import clickhouse_connect

def import_parquet_files_fast(parquet_dir, date_str=None):
    """
    Import parquet files to ClickHouse with maximum speed
    
    Args:
        parquet_dir: Directory containing parquet files
        date_str: Optional date filter (DDMMYYYY format, e.g., '29102024')
    """
    
    print("=" * 100)
    print("⚡ FAST PARQUET IMPORT TO CLICKHOUSE")
    print("=" * 100)
    
    # Connect to ClickHouse
    print("\n1️⃣  Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,  # HTTP port, not native TCP port
        username='default',
        database='tradelayout'
    )
    print("✅ Connected")
    
    # Find parquet files
    print(f"\n2️⃣  Scanning for parquet files in: {parquet_dir}")
    
    if date_str:
        pattern = f"*{date_str}*/**/*.parquet"
    else:
        pattern = "**/*.parquet"
    
    parquet_files = glob.glob(os.path.join(parquet_dir, pattern), recursive=True)
    
    if not parquet_files:
        print(f"❌ No parquet files found matching pattern: {pattern}")
        return
    
    print(f"✅ Found {len(parquet_files)} parquet files")
    
    # Import each file
    total_rows = 0
    start_time = datetime.now()
    
    for idx, file_path in enumerate(parquet_files, 1):
        file_name = os.path.basename(file_path)
        print(f"\n3️⃣  Processing [{idx}/{len(parquet_files)}]: {file_name}")
        
        try:
            # Read parquet file
            df = pd.read_parquet(file_path)
            rows = len(df)
            
            if rows == 0:
                print(f"   ⚠️  Skipping (empty file)")
                continue
            
            print(f"   📊 Rows: {rows:,}")
            
            # Detect table type from file path or columns
            if 'INDICES' in file_path.upper() or 'indices' in file_name.lower():
                table_name = 'nse_ticks_indices'
            elif 'OPTIONS' in file_path.upper() or 'options' in file_name.lower():
                table_name = 'nse_ticks_options'
            else:
                table_name = 'nse_ticks_stocks'
            
            print(f"   📋 Target table: {table_name}")
            
            # Prepare data for ClickHouse
            # Ensure required columns exist
            required_cols = {
                'nse_ticks_indices': ['trading_day', 'timestamp', 'symbol', 'ltp'],
                'nse_ticks_options': ['trading_day', 'timestamp', 'ticker', 'ltp'],
                'nse_ticks_stocks': ['trading_day', 'timestamp', 'symbol', 'ltp']
            }
            
            missing_cols = set(required_cols[table_name]) - set(df.columns)
            if missing_cols:
                print(f"   ⚠️  Missing columns: {missing_cols}")
                print(f"   Available columns: {list(df.columns)[:10]}")
                continue
            
            # Insert data using ClickHouse native format (super fast!)
            print(f"   ⏳ Inserting...")
            insert_start = datetime.now()
            
            client.insert_df(table_name, df)
            
            insert_duration = (datetime.now() - insert_start).total_seconds()
            rows_per_sec = rows / insert_duration if insert_duration > 0 else 0
            
            print(f"   ✅ Inserted {rows:,} rows in {insert_duration:.2f}s ({rows_per_sec:,.0f} rows/sec)")
            total_rows += rows
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    avg_speed = total_rows / duration if duration > 0 else 0
    
    print("\n" + "=" * 100)
    print("📊 IMPORT COMPLETE")
    print("=" * 100)
    print(f"Total rows imported: {total_rows:,}")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Average speed: {avg_speed:,.0f} rows/second")
    print("=" * 100)
    
    # Verify data
    print("\n4️⃣  Verifying data...")
    for table in ['nse_ticks_indices', 'nse_ticks_options', 'nse_ticks_stocks']:
        result = client.query(f"SELECT COUNT(*) FROM {table}")
        count = result.result_rows[0][0]
        print(f"   {table}: {count:,} rows")
    
    client.close()


if __name__ == "__main__":
    import sys
    
    # Usage examples:
    # python3 fast_parquet_import.py /path/to/parquet/dir
    # python3 fast_parquet_import.py /path/to/parquet/dir 29102024
    
    if len(sys.argv) < 2:
        print("Usage: python3 fast_parquet_import.py <parquet_directory> [date_DDMMYYYY]")
        print("\nExamples:")
        print("  # Import all parquet files:")
        print("  python3 fast_parquet_import.py /path/to/data/raw/")
        print("")
        print("  # Import only Oct 29, 2024 files:")
        print("  python3 fast_parquet_import.py /path/to/data/raw/ 29102024")
        sys.exit(1)
    
    parquet_dir = sys.argv[1]
    date_filter = sys.argv[2] if len(sys.argv) > 2 else None
    
    import_parquet_files_fast(parquet_dir, date_filter)
