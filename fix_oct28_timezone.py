#!/usr/bin/env python3
"""
Fix Oct 28 timezone issue - restore data with correct IST times
"""

import pandas as pd
import clickhouse_connect
from datetime import datetime

def fix_timezone_and_restore():
    """
    The backup has IST times mislabeled as UTC.
    We need to:
    1. Read the parquet (times show as UTC but are actually IST)
    2. Strip UTC label and apply IST timezone
    3. Delete existing corrupted Oct 28 data
    4. Insert corrected data
    """
    
    print('=' * 80)
    print('FIXING OCT 28 TIMEZONE ISSUE')
    print('=' * 80)
    print()
    
    # Connect to ClickHouse
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
    print('Step 2: Checking current Oct 28 data...')
    result = client.query("""
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM nse_ticks_indices
        WHERE trading_day = '2024-10-28' AND symbol = 'NIFTY'
    """)
    row = result.result_rows[0]
    print(f'  Current: {row[0]} to {row[1]} ({row[2]:,} ticks)')
    print(f'  ❌ Wrong times (14:37 - 21:51) - missing morning session')
    print()
    
    # Read parquet backup
    print('Step 3: Reading parquet backup...')
    file = '/tmp/clickhouse_restore_20251206_110204/nse_ticks_indices.parquet'
    df = pd.read_parquet(file)
    df['trading_day'] = pd.to_datetime(df['trading_day'])
    
    # Filter for Oct 28
    oct28 = df[df['trading_day'] == '2024-10-28'].copy()
    print(f'  Rows in backup: {len(oct28):,}')
    print(f'  Backup times (labeled UTC): {oct28["timestamp"].min()} to {oct28["timestamp"].max()}')
    print()
    
    # FIX: Convert UTC-labeled times to IST
    print('Step 4: Fixing timezone...')
    print('  Converting: UTC label → IST (no time change, just relabel)')
    
    # Remove UTC timezone and apply IST
    oct28['timestamp'] = oct28['timestamp'].dt.tz_localize(None)  # Remove UTC label
    oct28['timestamp'] = pd.to_datetime(oct28['timestamp']).dt.tz_localize('Asia/Kolkata')  # Apply IST
    
    print(f'  Corrected times: {oct28["timestamp"].min()} to {oct28["timestamp"].max()}')
    print(f'  ✅ Now shows correct market hours (09:07 - 16:21 IST)')
    print()
    
    # Fix column names: parquet has buy_price/sell_price, table has bid_price/ask_price
    print('Step 4b: Fixing column names...')
    oct28 = oct28.rename(columns={
        'buy_price': 'bid_price',
        'sell_price': 'ask_price',
        'buy_qty': 'bid_qty',
        'sell_qty': 'ask_qty'
    })
    
    # Add missing columns
    oct28['volume'] = oct28['ltq']  # Map ltq to volume
    
    # Ensure all required columns exist in correct order
    required_cols = ['trading_day', 'timestamp', 'symbol', 'ltp', 'volume', 'ltq', 'oi',
                     'bid_price', 'ask_price', 'bid_qty', 'ask_qty']
    oct28 = oct28[required_cols]
    print(f'  ✅ Columns mapped: buy/sell → bid/ask, ltq → volume')
    print()
    
    # Delete existing Oct 28 data
    print('Step 5: Deleting existing Oct 28 data...')
    client.command("ALTER TABLE nse_ticks_indices DELETE WHERE trading_day = '2024-10-28'")
    print('✅ Deleted')
    print()
    
    # Insert corrected data
    print('Step 6: Inserting corrected data...')
    start = datetime.now()
    client.insert_df('nse_ticks_indices', oct28)
    duration = (datetime.now() - start).total_seconds()
    print(f'✅ Inserted {len(oct28):,} rows in {duration:.2f}s')
    print()
    
    # Verify
    print('Step 7: Verifying corrected data...')
    result = client.query("""
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM nse_ticks_indices
        WHERE trading_day = '2024-10-28' AND symbol = 'NIFTY'
    """)
    row = result.result_rows[0]
    print(f'  New times: {row[0]} to {row[1]}')
    print(f'  Total ticks: {row[2]:,}')
    
    if '09:' in str(row[0]) or '10:' in str(row[0]):
        print('  ✅ SUCCESS! Data now starts in morning session')
    else:
        print(f'  ⚠️  Still wrong: starts at {row[0]}')
    
    client.close()
    print()
    print('=' * 80)
    print('DONE - Oct 28 timezone fixed!')
    print('=' * 80)

if __name__ == '__main__':
    fix_timezone_and_restore()
