#!/bin/bash

# Fix timezone issue - subtract 5:30 hours (19800 seconds) from all timestamps
# This converts UTC timestamps to IST

set -e

echo "======================================================================================================"
echo "⏰ FIXING TIMEZONE IN ALL TABLES (UTC → IST)"
echo "======================================================================================================"
echo ""
echo "This will subtract 5:30 hours from all timestamps"
echo ""

# Configuration
CLICKHOUSE_CLIENT="clickhouse client --host localhost --port 9000 --user default --database tradelayout"

# Tables to fix
TABLES=(
    "nse_ticks_indices"
    "nse_ticks_options"
    "nse_ticks_stocks"
    "nse_ohlcv_indices"
    "nse_ohlcv_stocks"
)

for TABLE in "${TABLES[@]}"; do
    echo "======================================================================================================"
    echo "📋 Processing: $TABLE"
    echo "======================================================================================================"
    
    # Check current timestamp range
    echo "Current timestamp range:"
    $CLICKHOUSE_CLIENT --query "
        SELECT 
            min(timestamp) as first_ts,
            max(timestamp) as last_ts,
            count() as total_rows
        FROM $TABLE
    " 2>&1
    
    echo ""
    echo "⏳ Creating new table with corrected timestamps..."
    
    # Create temporary table with corrected timestamps
    TEMP_TABLE="${TABLE}_temp"
    
    # Drop temp table if exists
    $CLICKHOUSE_CLIENT --query "DROP TABLE IF EXISTS $TEMP_TABLE" 2>&1
    
    # Get table schema
    echo "Creating temporary table structure..."
    $CLICKHOUSE_CLIENT --query "CREATE TABLE $TEMP_TABLE AS $TABLE" 2>&1
    
    # Copy data with corrected timestamps (subtract 19800 seconds = 5:30 hours)
    echo "Copying data with corrected timestamps (this may take a few minutes)..."
    
    $CLICKHOUSE_CLIENT --query "
        INSERT INTO $TEMP_TABLE
        SELECT 
            ${TABLE}.* EXCEPT timestamp,
            timestamp - INTERVAL 19800 SECOND as timestamp
        FROM $TABLE
    " 2>&1
    
    # Verify new timestamp range
    echo ""
    echo "New timestamp range in temporary table:"
    $CLICKHOUSE_CLIENT --query "
        SELECT 
            min(timestamp) as first_ts,
            max(timestamp) as last_ts,
            count() as total_rows
        FROM $TEMP_TABLE
    " 2>&1
    
    # Swap tables
    echo ""
    echo "⚡ Swapping tables..."
    $CLICKHOUSE_CLIENT --query "DROP TABLE $TABLE" 2>&1
    $CLICKHOUSE_CLIENT --query "RENAME TABLE $TEMP_TABLE TO $TABLE" 2>&1
    
    echo "✅ $TABLE - Timezone fixed!"
    echo ""
done

echo "======================================================================================================"
echo "✅ ALL TABLES UPDATED"
echo "======================================================================================================"
echo ""

# Verify Oct 29 data
echo "======================================================================================================"
echo "🔍 VERIFICATION - Oct 29, 2024 Data"
echo "======================================================================================================"
echo ""

echo "📊 nse_ticks_indices (Oct 29):"
$CLICKHOUSE_CLIENT --query "
    SELECT 
        symbol,
        min(timestamp) as first_tick,
        max(timestamp) as last_tick,
        count() as ticks
    FROM nse_ticks_indices
    WHERE trading_day = '2024-10-29'
    GROUP BY symbol
    FORMAT PrettyCompact
"

echo ""
echo "📊 nse_ticks_options (Oct 29):"
$CLICKHOUSE_CLIENT --query "
    SELECT 
        min(timestamp) as first_tick,
        max(timestamp) as last_tick,
        count() as ticks
    FROM nse_ticks_options
    WHERE trading_day = '2024-10-29'
    FORMAT PrettyCompact
"

echo ""
echo "======================================================================================================"
echo "✅ TIMEZONE FIX COMPLETE"
echo "======================================================================================================"
echo ""
echo "Expected time range: 09:15:00 to 15:30:00 (IST)"
echo "You can now re-run your backtest and should get all 11 positions!"
echo ""
