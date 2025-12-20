#!/usr/bin/env python3
"""
Restore nse_ticks_indices from S3 backup with schema mapping
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

def restore_ticks_indices(parquet_path="/tmp/clickhouse_restore_20251206_110204/nse_ticks_indices.parquet"):
    """Restore nse_ticks_indices with proper column mapping"""
    
    print("=" * 100)
    print("🔄 RESTORING nse_ticks_indices WITH SCHEMA MAPPING")
    print("=" * 100)
    print(f"Source: {parquet_path}")
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
    
    # Read parquet file
    print("2️⃣  Reading parquet file...")
    df = pd.read_parquet(parquet_path)
    total_rows = len(df)
    print(f"✅ Read {total_rows:,} rows")
    print()
    
    print("3️⃣  Original columns:")
    for col in df.columns:
        print(f"   - {col}")
    print()
    
    # Schema mapping
    print("4️⃣  Applying schema mapping...")
    
    # Essential columns only (user clarification)
    essential_cols = ['symbol', 'trading_day', 'timestamp', 'ltp', 'ltq', 'oi']
    df_mapped = df[essential_cols].copy()
    
    # Add volume = ltq (user clarification: ltq = volume)
    df_mapped['volume'] = df_mapped['ltq']
    
    # Add missing columns with defaults (ignored columns from user)
    df_mapped['bid_price'] = 0.0
    df_mapped['ask_price'] = 0.0
    df_mapped['bid_qty'] = 0
    df_mapped['ask_qty'] = 0
    df_mapped['buy_qty'] = 0
    df_mapped['sell_qty'] = 0
    
    print("✅ Mapped columns:")
    print("   - ltq → volume (as per user: ltq = volume)")
    print("   - Ignored: buy_price, sell_price, bid_price, ask_price, bid_qty, ask_qty")
    print("   - Added default values for missing columns")
    print()
    
    # Reorder to match local table schema
    column_order = [
        'trading_day', 'timestamp', 'symbol', 'ltp', 'volume', 'ltq', 'oi',
        'bid_price', 'ask_price', 'bid_qty', 'ask_qty', 'buy_qty', 'sell_qty'
    ]
    df_final = df_mapped[column_order]
    
    print("5️⃣  Final schema:")
    for col in df_final.columns:
        print(f"   - {col:20s} ({df_final[col].dtype})")
    print()
    
    # Truncate existing data
    print("6️⃣  Truncating existing data...")
    client.command("TRUNCATE TABLE nse_ticks_indices")
    print("✅ Table truncated")
    print()
    
    # Insert in batches to avoid memory issues
    print("7️⃣  Inserting data in batches...")
    batch_size = 1_000_000
    num_batches = (len(df_final) + batch_size - 1) // batch_size
    
    start_time = datetime.now()
    
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(df_final))
        batch = df_final.iloc[start_idx:end_idx]
        
        print(f"   Batch {i+1}/{num_batches}: Inserting rows {start_idx:,} to {end_idx:,}...")
        client.insert_df('nse_ticks_indices', batch)
        print(f"   ✅ Batch {i+1} complete")
    
    duration = (datetime.now() - start_time).total_seconds()
    rows_per_sec = total_rows / duration if duration > 0 else 0
    
    print()
    print("=" * 100)
    print("🎉 RESTORE COMPLETE")
    print("=" * 100)
    print(f"Total rows inserted: {total_rows:,}")
    print(f"Total time: {duration:.2f} seconds")
    print(f"Average speed: {rows_per_sec:,.0f} rows/second")
    print("=" * 100)
    print()
    
    # Verify
    print("8️⃣  Verifying data...")
    count = client.command("SELECT COUNT(*) FROM nse_ticks_indices")
    print(f"✅ Verified: {count:,} rows in table")
    print()
    
    # Sample data
    result = client.query("SELECT * FROM nse_ticks_indices LIMIT 3")
    print("Sample data (first 3 rows):")
    for row in result.result_rows:
        print(f"   {row}")
    print()
    
    client.close()


if __name__ == "__main__":
    import sys
    
    parquet_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clickhouse_restore_20251206_110204/nse_ticks_indices.parquet"
    
    restore_ticks_indices(parquet_path)
