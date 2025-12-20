#!/usr/bin/env python3
"""
Fix Oct 28 options timezone - process in chunks to avoid OOM
"""

import pandas as pd
import clickhouse_connect
import pyarrow.parquet as pq
from datetime import datetime

def fix_options_timezone():
    print('=' * 80)
    print('FIXING OCT 28 OPTIONS DATA - TIMEZONE (Chunked Processing)')
    print('=' * 80)
    print()
    
    # Connect
    print('Step 1: Connecting to ClickHouse...')
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        database='tradelayout'
    )
    print('✅ Connected')
    print()
    
    # Check current data
    print('Step 2: Checking current options data...')
    result = client.query("""
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM nse_ticks_options
        WHERE trading_day = '2024-10-28'
    """)
    row = result.result_rows[0]
    print(f'  Current: {row[0]} to {row[1]}')
    print(f'  Rows: {row[2]:,}')
    print('  ❌ Wrong times (14:45 - 21:00) - missing morning session')
    print()
    
    # Delete existing Oct 28 data first
    print('Step 3: Deleting existing Oct 28 options data...')
    client.command("ALTER TABLE nse_ticks_options DELETE WHERE trading_day = '2024-10-28'")
    print('✅ Deleted')
    print()
    
    # Process parquet in chunks
    print('Step 4: Reading and fixing parquet in chunks...')
    file = '/tmp/clickhouse_restore_20251206_110204/nse_ticks_options.parquet'
    pf = pq.ParquetFile(file)
    
    print(f'  Total row groups: {pf.num_row_groups:,}')
    print(f'  Processing in batches...')
    print()
    
    total_inserted = 0
    oct28_count = 0
    start_time = datetime.now()
    
    # Process 10 row groups at a time
    batch_size = 10
    for batch_start in range(0, pf.num_row_groups, batch_size):
        batch_end = min(batch_start + batch_size, pf.num_row_groups)
        
        print(f'  Processing row groups {batch_start}-{batch_end}...', end=' ', flush=True)
        
        # Read batch
        tables = [pf.read_row_group(i) for i in range(batch_start, batch_end)]
        batch_df = pd.concat([t.to_pandas() for t in tables], ignore_index=True)
        
        # Filter for Oct 28
        batch_df['trading_day'] = pd.to_datetime(batch_df['trading_day'])
        oct28_batch = batch_df[batch_df['trading_day'] == '2024-10-28'].copy()
        
        if len(oct28_batch) > 0:
            # Fix timezone
            oct28_batch['timestamp'] = oct28_batch['timestamp'].dt.tz_localize(None)
            oct28_batch['timestamp'] = pd.to_datetime(oct28_batch['timestamp']).dt.tz_localize('Asia/Kolkata')
            
            # Insert
            client.insert_df('nse_ticks_options', oct28_batch)
            oct28_count += len(oct28_batch)
            print(f'✅ {len(oct28_batch):,} Oct 28 rows inserted')
        else:
            print('(no Oct 28 data)')
        
        total_inserted += len(batch_df)
        
        # Progress update every 50 batches
        if (batch_start // batch_size) % 5 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            progress = (batch_end / pf.num_row_groups) * 100
            print(f'    Progress: {progress:.1f}% ({elapsed:.0f}s elapsed, {oct28_count:,} Oct 28 rows so far)')
    
    print()
    print(f'✅ Processed {total_inserted:,} total rows')
    print(f'✅ Inserted {oct28_count:,} Oct 28 rows with corrected timezone')
    print()
    
    # Verify
    print('Step 5: Verifying corrected data...')
    result = client.query("""
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM nse_ticks_options
        WHERE trading_day = '2024-10-28'
    """)
    row = result.result_rows[0]
    print(f'  Verified: {row[0]} to {row[1]}')
    print(f'  Total ticks: {row[2]:,}')
    
    if '09:' in str(row[0]) or '10:' in str(row[0]):
        print('  ✅ SUCCESS! Options data now starts in morning session')
    else:
        print(f'  ⚠️  Still showing: {row[0]}')
    
    client.close()
    
    duration = (datetime.now() - start_time).total_seconds()
    print()
    print('=' * 80)
    print(f'DONE in {duration:.0f} seconds!')
    print('=' * 80)

if __name__ == '__main__':
    fix_options_timezone()
