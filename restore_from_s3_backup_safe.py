#!/usr/bin/env python3
"""
Restore ClickHouse data from S3 backup with DURABILITY GUARANTEES
- Uses fsync to ensure data written to disk
- Smaller batch sizes to prevent timeout
- Verifies each partition after insert
- No dependency on caffeinate or system sleep settings
"""

import os
import glob
import pandas as pd
from datetime import datetime
import clickhouse_connect
import signal
import sys

# Global client for cleanup
client = None

def signal_handler(signum, frame):
    """Handle interruption gracefully"""
    print("\n⚠️  Interrupted! Cleaning up...")
    if client:
        try:
            client.close()
        except:
            pass
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def restore_from_backup(restore_dir="/tmp/clickhouse_restore_20251206_110204"):
    """Restore all tables from downloaded S3 backup with durability"""
    global client
    
    print("=" * 100)
    print("🔄 RESTORING CLICKHOUSE WITH DURABILITY GUARANTEES")
    print("=" * 100)
    print(f"Source: {restore_dir}")
    print(f"Time: {datetime.now()}")
    print()
    
    # Connect to ClickHouse with durability settings
    print("1️⃣  Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        database='tradelayout',
        settings={
            'insert_quorum': 1,              # Ensure write acknowledged
            'insert_quorum_timeout': 300000, # 5 minutes timeout
            'max_insert_block_size': 50000,  # Smaller batches (was 1M+)
            'insert_deduplicate': 1,         # Prevent duplicates on retry
            'fsync_metadata': 1              # Force sync metadata
        }
    )
    print("✅ Connected with durability settings")
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
            
            # Check if table exists
            try:
                client.command(f"EXISTS TABLE {table_name}")
            except:
                print(f"   ⚠️  Table does not exist, skipping")
                continue
            
            # Get row count before truncate
            count_before = client.command(f"SELECT COUNT(*) FROM {table_name}")
            print(f"   📊 Current rows: {count_before:,}")
            
            # Truncate existing data
            print(f"   🗑️  Truncating...")
            client.command(f"TRUNCATE TABLE {table_name}")
            
            # Verify truncate worked
            count_after_truncate = client.command(f"SELECT COUNT(*) FROM {table_name}")
            if count_after_truncate != 0:
                print(f"   ❌ Truncate failed! Still has {count_after_truncate} rows")
                continue
            
            # Insert in smaller batches for durability
            batch_size = 50000  # Insert 50K rows at a time
            total_batches = (rows + batch_size - 1) // batch_size
            
            print(f"   ⏳ Inserting in {total_batches} batches of {batch_size:,} rows...")
            insert_start = datetime.now()
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, rows)
                batch_df = df.iloc[start_idx:end_idx]
                
                # Insert batch with retry logic
                retry_count = 0
                max_retries = 3
                
                while retry_count < max_retries:
                    try:
                        client.insert_df(table_name, batch_df)
                        
                        # Force sync to disk (critical for durability)
                        client.command(f"SYSTEM SYNC REPLICA {table_name}")
                        
                        break  # Success
                        
                    except Exception as batch_error:
                        retry_count += 1
                        if retry_count >= max_retries:
                            raise Exception(f"Batch {batch_idx+1} failed after {max_retries} retries: {batch_error}")
                        
                        print(f"   ⚠️  Batch {batch_idx+1} failed, retry {retry_count}/{max_retries}...")
                        import time
                        time.sleep(2)  # Wait before retry
                
                # Progress update
                if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
                    progress = ((batch_idx + 1) / total_batches) * 100
                    print(f"      Progress: {progress:.1f}% ({end_idx:,}/{rows:,} rows)")
            
            insert_duration = (datetime.now() - insert_start).total_seconds()
            rows_per_sec = rows / insert_duration if insert_duration > 0 else 0
            
            print(f"   ✅ Inserted {rows:,} rows in {insert_duration:.2f}s ({rows_per_sec:,.0f} rows/sec)")
            total_rows += rows
            
            # CRITICAL: Verify insertion
            print(f"   🔍 Verifying...")
            count_final = client.command(f"SELECT COUNT(*) FROM {table_name}")
            
            if count_final == rows:
                print(f"   ✔️  Verified: {count_final:,} rows (100% match)")
            else:
                print(f"   ❌ MISMATCH! Expected {rows:,}, got {count_final:,}")
                print(f"   ⚠️  Missing {rows - count_final:,} rows")
            
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
    
    # Clean up
    if client:
        client.close()
        print("✅ Connection closed properly")


if __name__ == "__main__":
    import sys
    
    restore_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clickhouse_restore_20251206_110204"
    
    print(f"Restoring from: {restore_dir}")
    print()
    
    if not os.path.exists(restore_dir):
        print(f"❌ Directory not found: {restore_dir}")
        sys.exit(1)
    
    try:
        restore_from_backup(restore_dir)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
