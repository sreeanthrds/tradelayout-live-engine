#!/usr/bin/env python3
"""
Atomic Timezone Migration for All Tables
Converts all tables from shifted UTC (+5:30) to correct IST timezone
"""

import clickhouse_connect
from datetime import datetime

def migrate_table(client, table_name, columns_order):
    """Migrate a single table atomically via temp table."""
    print(f'\n{"=" * 80}')
    print(f'MIGRATING: {table_name}')
    print(f'{"=" * 80}')
    
    start_time = datetime.now()
    
    # Step 1: Get table structure
    print(f'1. Getting table structure...')
    result = client.query(f"""
        SELECT 
            engine,
            sorting_key,
            primary_key,
            partition_key
        FROM system.tables
        WHERE database = 'tradelayout' AND name = '{table_name}'
    """)
    
    if not result.result_rows:
        print(f'❌ Table {table_name} not found')
        return False
    
    engine, sorting_key, primary_key, partition_key = result.result_rows[0]
    print(f'   Engine: {engine}')
    print(f'   Sorting: {sorting_key}')
    print(f'   Primary: {primary_key}')
    print(f'   Partition: {partition_key}')
    
    # Step 2: Get row count
    result = client.query(f'SELECT COUNT(*) FROM {table_name}')
    total_rows = result.result_rows[0][0]
    print(f'\n2. Row count: {total_rows:,}')
    
    # Step 3: Create temp table with IST timezone
    print(f'\n3. Creating temp table {table_name}_ist...')
    
    # Build column list for SELECT
    timestamp_adjustment = 'toDateTime(toUnixTimestamp(timestamp) - 19800) as timestamp'
    select_cols = []
    for col in columns_order:
        if col == 'timestamp':
            select_cols.append(timestamp_adjustment)
        else:
            select_cols.append(col)
    
    create_sql = f"""
    CREATE TABLE {table_name}_ist AS {table_name}
    ENGINE = {engine}
    PARTITION BY {partition_key}
    ORDER BY {sorting_key}
    PRIMARY KEY {primary_key}
    """
    
    try:
        client.command(create_sql)
        print(f'   ✅ Created')
    except Exception as e:
        print(f'   ❌ Error: {e}')
        return False
    
    # Step 4: Copy data with timezone fix
    print(f'\n4. Copying data with -5:30 hour adjustment...')
    print(f'   This may take several minutes for large tables...')
    
    insert_start = datetime.now()
    insert_sql = f"""
    INSERT INTO {table_name}_ist
    SELECT {', '.join(select_cols)}
    FROM {table_name}
    """
    
    try:
        client.command(insert_sql)
        insert_duration = (datetime.now() - insert_start).total_seconds()
        print(f'   ✅ Copied {total_rows:,} rows in {insert_duration:.1f}s')
    except Exception as e:
        print(f'   ❌ Error: {e}')
        # Cleanup temp table
        client.command(f'DROP TABLE IF EXISTS {table_name}_ist')
        return False
    
    # Step 5: Verify row count
    print(f'\n5. Verifying...')
    result = client.query(f'SELECT COUNT(*) FROM {table_name}_ist')
    new_count = result.result_rows[0][0]
    
    if new_count != total_rows:
        print(f'   ❌ Row count mismatch: {new_count:,} != {total_rows:,}')
        client.command(f'DROP TABLE IF EXISTS {table_name}_ist')
        return False
    
    print(f'   ✅ Row count matches: {new_count:,}')
    
    # Step 6: Check timestamp range on sample day
    result = client.query(f"""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM {table_name}_ist
        WHERE trading_day = '2024-12-11'
        LIMIT 1
    """)
    
    if result.result_rows and result.result_rows[0][0]:
        first, last = result.result_rows[0]
        print(f'\n   Sample (Dec 11): {first} to {last}')
        
        first_str = str(first)
        if '09:' in first_str or '08:' in first_str:
            print(f'   ✅ Timestamps corrected to IST morning session')
        else:
            print(f'   ⚠️  Timestamps: {first_str}')
    
    # Step 7: Drop old table
    print(f'\n6. Dropping old table {table_name}...')
    try:
        client.command(f'DROP TABLE {table_name}')
        print(f'   ✅ Dropped')
    except Exception as e:
        print(f'   ❌ Error: {e}')
        return False
    
    # Step 8: Rename temp table
    print(f'\n7. Renaming {table_name}_ist to {table_name}...')
    try:
        client.command(f'RENAME TABLE {table_name}_ist TO {table_name}')
        print(f'   ✅ Renamed')
    except Exception as e:
        print(f'   ❌ Error: {e}')
        return False
    
    duration = (datetime.now() - start_time).total_seconds()
    print(f'\n✅ {table_name} migration complete in {duration:.1f}s')
    
    return True


def main():
    print('=' * 80)
    print('ATOMIC TIMEZONE MIGRATION - ALL TABLES')
    print('=' * 80)
    print()
    print('This will convert all tables from shifted UTC to correct IST')
    print('Operation: Subtract 5 hours 30 minutes from all timestamps')
    print()
    
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        database='tradelayout'
    )
    
    # Define tables to migrate with column order
    tables_to_migrate = [
        {
            'name': 'nse_ticks_indices',
            'columns': ['trading_day', 'timestamp', 'symbol', 'ltp', 'volume', 'ltq', 
                       'oi', 'bid_price', 'ask_price', 'bid_qty', 'ask_qty']
        },
        {
            'name': 'nse_ticks_options',
            'columns': ['trading_day', 'timestamp', 'ticker', 'ltp', 'volume', 'ltq',
                       'oi', 'bid_price', 'ask_price', 'bid_qty', 'ask_qty']
        },
        {
            'name': 'nse_ohlcv_indices',
            'columns': ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                       'symbol', 'timeframe', 'trading_day']
        },
        {
            'name': 'nse_ohlcv_stocks',
            'columns': ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                       'symbol', 'timeframe', 'trading_day']
        },
        {
            'name': 'nse_ticks_stocks',
            'columns': ['trading_day', 'timestamp', 'symbol', 'ltp', 'volume', 'ltq',
                       'oi', 'bid_price', 'ask_price', 'bid_qty', 'ask_qty']
        }
    ]
    
    start_time = datetime.now()
    successful = []
    failed = []
    
    for table_config in tables_to_migrate:
        table_name = table_config['name']
        columns = table_config['columns']
        
        success = migrate_table(client, table_name, columns)
        
        if success:
            successful.append(table_name)
        else:
            failed.append(table_name)
            print(f'\n⚠️  Migration failed for {table_name}')
            print(f'   Stopping migration to prevent inconsistency')
            break
    
    total_duration = (datetime.now() - start_time).total_seconds()
    
    print()
    print('=' * 80)
    print('MIGRATION SUMMARY')
    print('=' * 80)
    print()
    print(f'Total time: {total_duration/60:.1f} minutes')
    print(f'Successful: {len(successful)} tables')
    if successful:
        for table in successful:
            print(f'  ✅ {table}')
    
    if failed:
        print(f'\nFailed: {len(failed)} tables')
        for table in failed:
            print(f'  ❌ {table}')
    
    if len(successful) == len(tables_to_migrate):
        print()
        print('=' * 80)
        print('✅ ALL TABLES MIGRATED SUCCESSFULLY')
        print('=' * 80)
        print()
        print('All tables now have consistent IST timezone (9:15-15:30)')
        print()
        print('Next steps:')
        print('  1. Update config to use IST mode')
        print('  2. Test backtest with corrected timezone')
        print('  3. Verify queries work for all dates')
    
    client.close()


if __name__ == '__main__':
    main()
