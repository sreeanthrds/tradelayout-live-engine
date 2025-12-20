#!/bin/bash

# Fix timezone issue - subtract 5:30 hours (19800 seconds) from all timestamps
# Using ALTER TABLE UPDATE for direct modification

set -e

echo "======================================================================================================"
echo "⏰ FIXING TIMEZONE IN ALL TABLES (UTC → IST)"
echo "======================================================================================================"
echo ""
echo "Subtracting 5:30 hours from all timestamps..."
echo ""

# Configuration
CLICKHOUSE_CLIENT="clickhouse client --host localhost --port 9000 --user default --database tradelayout"

# Tables to fix
declare -A TABLES
TABLES=(
    ["nse_ticks_indices"]="timestamp"
    ["nse_ticks_options"]="timestamp"
    ["nse_ticks_stocks"]="timestamp"
    ["nse_ohlcv_indices"]="timestamp"
    ["nse_ohlcv_stocks"]="timestamp"
)

for TABLE in "${!TABLES[@]}"; do
    TIMESTAMP_COL="${TABLES[$TABLE]}"
    
    echo "======================================================================================================"
    echo "📋 Processing: $TABLE"
    echo "======================================================================================================"
    
    # Check current timestamp range
    echo "Current timestamp range:"
    $CLICKHOUSE_CLIENT --query "
        SELECT 
            min($TIMESTAMP_COL) as first_ts,
            max($TIMESTAMP_COL) as last_ts,
            count() as total_rows
        FROM $TABLE
    "
    
    echo ""
    echo "⏳ Updating timestamps (subtracting 5:30 hours)..."
    
    # Use ALTER TABLE UPDATE to modify timestamps in place
    $CLICKHOUSE_CLIENT --query "
        ALTER TABLE $TABLE 
        UPDATE $TIMESTAMP_COL = $TIMESTAMP_COL - INTERVAL 19800 SECOND 
        WHERE 1=1
    "
    
    # Wait for mutation to complete
    echo "⏳ Waiting for update to complete..."
    sleep 2
    
    # Check if mutation is still running
    MUTATIONS_RUNNING=1
    while [ $MUTATIONS_RUNNING -gt 0 ]; do
        MUTATIONS_RUNNING=$($CLICKHOUSE_CLIENT --query "
            SELECT count() 
            FROM system.mutations 
            WHERE table = '$TABLE' 
            AND database = 'tradelayout' 
            AND is_done = 0
        ")
        
        if [ $MUTATIONS_RUNNING -gt 0 ]; then
            echo "   Still processing... (mutations running: $MUTATIONS_RUNNING)"
            sleep 5
        fi
    done
    
    # Verify new timestamp range
    echo ""
    echo "New timestamp range:"
    $CLICKHOUSE_CLIENT --query "
        SELECT 
            min($TIMESTAMP_COL) as first_ts,
            max($TIMESTAMP_COL) as last_ts,
            count() as total_rows
        FROM $TABLE
    "
    
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
echo "Data should now be ready for backtesting!"
echo ""
