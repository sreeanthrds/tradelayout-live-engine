#!/usr/bin/env python3
"""
Restore ClickHouse data from S3 backup parquet files
"""

import os
import glob
import pandas as pd
from datetime import datetime
import clickhouse_connect

def restore_from_backup(restore_dir="/tmp/clickhouse_restore_20251206_110204"):
    """Restore all tables from downloaded S3 backup"""
    
    print("=" * 100)
    print("🔄 RESTORING CLICKHOUSE FROM S3 BACKUP")
    print("=" * 100)
    print(f"Source: {restore_dir}")
    print(f"Time: {datetime.now()}")
    print()
    
    # Connect to ClickHouse
    print("1️⃣  Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        database='tradelayout'
    )
    print("✅ Connected")
    print()
    
    # Find all parquet files
    print("2️⃣  Scanning for parquet files...")
    parquet_files = glob.glob(os.path.join(restore_dir, "*.parquet"))
    parquet_files = [f for f in parquet_files if not os.path.basename(f).startswith('.')]
    
    print(f"✅ Found {len(parquet_files)} tables to restore")
    print()
    
    # Import each table
    total_rows = 0
    start_time = datetime.now()
    
    for idx, file_path in enumerate(sorted(parquet_files), 1):
        file_name = os.path.basename(file_path)
        table_name = file_name.replace('.parquet', '')
        
        # Skip backup tables
        if 'backup' in table_name.lower():
            print(f"[{idx}/{len(parquet_files)}] ⏭️  Skipping backup table: {table_name}")
            continue
        
        print(f"[{idx}/{len(parquet_files)}] 📦 Restoring: {table_name}")
        
        try:
            # Read parquet file
            df = pd.read_parquet(file_path)
            rows = len(df)
            
            if rows == 0:
                print(f"   ⚠️  Empty file, skipping")
                continue
            
            print(f"   📊 Rows to import: {rows:,}")
            
            # Check if table exists, if not skip
            try:
                client.command(f"EXISTS TABLE {table_name}")
            except:
                print(f"   ⚠️  Table does not exist, skipping")
                continue
            
            # Truncate existing data from the table
            print(f"   🗑️  Truncating existing data...")
            client.command(f"TRUNCATE TABLE {table_name}")
            
            # Insert data
            print(f"   ⏳ Inserting...")
            insert_start = datetime.now()
            
            client.insert_df(table_name, df)
            
            insert_duration = (datetime.now() - insert_start).total_seconds()
            rows_per_sec = rows / insert_duration if insert_duration > 0 else 0
            
            print(f"   ✅ Inserted {rows:,} rows in {insert_duration:.2f}s ({rows_per_sec:,.0f} rows/sec)")
            total_rows += rows
            
            # Verify
            count = client.command(f"SELECT COUNT(*) FROM {table_name}")
            print(f"   ✔️  Verified: {count:,} rows in table")
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
            continue
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    avg_speed = total_rows / duration if duration > 0 else 0
    
    print("=" * 100)
    print("🎉 RESTORE COMPLETE")
    print("=" * 100)
    print(f"Total rows restored: {total_rows:,}")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Average speed: {avg_speed:,.0f} rows/second")
    print("=" * 100)
    print()
    
    # Show final table stats
    print("📊 Final Table Statistics:")
    print()
    for table in ['nse_ohlcv_indices', 'nse_ohlcv_stocks', 'nse_ticks_indices', 
                  'nse_ticks_options', 'nse_ticks_stocks', 'nse_options_metadata']:
        try:
            count = client.command(f"SELECT COUNT(*) FROM {table}")
            print(f"   {table:30s}: {count:,} rows")
        except:
            print(f"   {table:30s}: ERROR")
    
    print()
    client.close()


if __name__ == "__main__":
    import sys
    
    restore_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clickhouse_restore_20251206_110204"
    
    print(f"Restoring from: {restore_dir}")
    print()
    
    if not os.path.exists(restore_dir):
        print(f"❌ Directory not found: {restore_dir}")
        sys.exit(1)
    
    restore_from_backup(restore_dir)
