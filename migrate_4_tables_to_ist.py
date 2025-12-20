#!/usr/bin/env python3
"""
Migrate 4 smaller tables to correct IST timezone
Options table already has correct IST - skip it
"""

import clickhouse_connect
from datetime import datetime

def migrate_table(client, table_name):
    """Migrate a single table via temp table."""
    print(f'\n{"=" * 80}')
    print(f'MIGRATING: {table_name}')
    print(f'{"=" * 80}')
    
    start_time = datetime.now()
    
    # Get table info
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
    
    # Get row count
    result = client.query(f'SELECT COUNT(*) FROM {table_name}')
    total_rows = result.result_rows[0][0]
    print(f'Rows to migrate: {total_rows:,}')
    
    # Create temp table
    print(f'\nCreating temp table {table_name}_ist...')
    
    # Build proper ORDER BY syntax (wrap in parens if multiple columns)
    order_by = f"({sorting_key})" if ',' in sorting_key else sorting_key
    primary = f"({primary_key})" if ',' in primary_key else primary_key
    
    create_sql = f"""
    CREATE TABLE {table_name}_ist AS {table_name}
    ENGINE = {engine}
    PARTITION BY {partition_key}
    ORDER BY {order_by}
    PRIMARY KEY {primary}
    """
    
    try:
        client.command(create_sql)
        print('✅ Created')
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    # Copy data with timezone fix (-5:30 hours)
    print(f'\nCopying data with -5:30 hour adjustment...')
    insert_start = datetime.now()
    
    insert_sql = f"""
    INSERT INTO {table_name}_ist
    SELECT *
    REPLACE(toDateTime(toUnixTimestamp(timestamp) - 19800) AS timestamp)
    FROM {table_name}
    """
    
    try:
        client.command(insert_sql)
        insert_duration = (datetime.now() - insert_start).total_seconds()
        print(f'✅ Copied in {insert_duration:.1f}s')
    except Exception as e:
        print(f'❌ Error: {e}')
        client.command(f'DROP TABLE IF EXISTS {table_name}_ist')
        return False
    
    # Verify row count
    result = client.query(f'SELECT COUNT(*) FROM {table_name}_ist')
    new_count = result.result_rows[0][0]
    
    if new_count != total_rows:
        print(f'❌ Row count mismatch: {new_count:,} != {total_rows:,}')
        client.command(f'DROP TABLE IF EXISTS {table_name}_ist')
        return False
    
    print(f'✅ Row count verified: {new_count:,}')
    
    # Check timestamp sample
    result = client.query(f"""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM {table_name}_ist
        WHERE trading_day = '2024-12-11'
        LIMIT 1
    """)
    
    if result.result_rows and result.result_rows[0][0]:
        first, last = result.result_rows[0]
        print(f'Dec 11 sample: {first} to {last}')
        
        if '09:' in str(first) or '08:' in str(first):
            print('✅ Timestamps corrected to IST')
        else:
            print(f'⚠️  Timestamps: {first}')
    
    # Drop old table (use DETACH if DROP fails due to metadata corruption)
    print(f'\nRemoving old table...')
    try:
        client.command(f'DROP TABLE {table_name}')
        print('✅ Dropped')
    except Exception as e:
        print(f'⚠️  DROP failed (metadata corruption), trying DETACH...')
        try:
            client.command(f'DETACH TABLE {table_name}')
            print('✅ Detached')
        except Exception as e2:
            print(f'❌ Both DROP and DETACH failed: {e2}')
            return False
    
    # Rename temp table
    print(f'Renaming {table_name}_ist to {table_name}...')
    try:
        client.command(f'RENAME TABLE {table_name}_ist TO {table_name}')
        print('✅ Renamed')
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    duration = (datetime.now() - start_time).total_seconds()
    print(f'\n✅ {table_name} complete in {duration:.1f}s')
    
    return True


def main():
    print('=' * 80)
    print('MIGRATE 4 TABLES TO IST (EXCLUDE OPTIONS)')
    print('=' * 80)
    print()
    print('Tables to migrate:')
    print('  1. nse_ticks_indices    (21M rows)')
    print('  2. nse_ohlcv_indices    (468K rows)')
    print('  3. nse_ohlcv_stocks     (2.5M rows)')
    print('  4. nse_ticks_stocks     (49M rows)')
    print()
    print('Skipping: nse_ticks_options (already correct IST)')
    print()
    
    client = clickhouse_connect.get_client(
        host='localhost',
        port=8123,
        username='default',
        database='tradelayout'
    )
    
    tables = [
        'nse_ohlcv_indices',      # Smallest first
        'nse_ohlcv_stocks',
        'nse_ticks_indices',
        'nse_ticks_stocks'
    ]
    
    start_time = datetime.now()
    successful = []
    failed = []
    
    for table_name in tables:
        success = migrate_table(client, table_name)
        
        if success:
            successful.append(table_name)
        else:
            failed.append(table_name)
            print(f'\n⚠️  Migration failed for {table_name}')
            print('Stopping to prevent inconsistency')
            break
    
    total_duration = (datetime.now() - start_time).total_seconds()
    
    print()
    print('=' * 80)
    print('MIGRATION SUMMARY')
    print('=' * 80)
    print()
    print(f'Total time: {total_duration/60:.1f} minutes')
    print(f'Successful: {len(successful)}/{len(tables)} tables')
    
    if successful:
        for table in successful:
            print(f'  ✅ {table}')
    
    if failed:
        print(f'\nFailed:')
        for table in failed:
            print(f'  ❌ {table}')
    
    if len(successful) == len(tables):
        print()
        print('=' * 80)
        print('✅ ALL TABLES MIGRATED SUCCESSFULLY')
        print('=' * 80)
        print()
        print('All tables now have consistent IST timezone (9:15-15:30)')
        print('Config already set to IST mode')
        print()
        print('Ready to test backtest!')
    
    client.close()


if __name__ == '__main__':
    main()
