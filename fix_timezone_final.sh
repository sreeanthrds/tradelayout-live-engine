#!/bin/bash

# Fix timezone issue - subtract 5:30 hours (19800 seconds) from all timestamps

set -e

echo "======================================================================================================"
echo "⏰ FIXING TIMEZONE IN ALL TABLES (UTC → IST)"
echo "======================================================================================================"
echo ""
echo "Subtracting 5:30 hours (19800 seconds) from all timestamps..."
echo ""

# Configuration
CH_CMD="clickhouse client --host localhost --port 9000 --user default --database tradelayout"

# Function to fix a table
fix_table() {
    local TABLE=$1
    
    echo "======================================================================================================"
    echo "📋 Processing: $TABLE"
    echo "======================================================================================================"
    
    # Check current timestamp range
    echo "Current timestamp range:"
    $CH_CMD --query "SELECT min(timestamp) as first_ts, max(timestamp) as last_ts, count() as total_rows FROM $TABLE"
    
    echo ""
    echo "⏳ Updating timestamps (subtracting 5:30 hours)..."
    
    # Use ALTER TABLE UPDATE
    $CH_CMD --query "ALTER TABLE $TABLE UPDATE timestamp = timestamp - INTERVAL 19800 SECOND WHERE 1=1"
    
    echo "⏳ Waiting for mutation to complete..."
    sleep 3
    
    # Wait for mutations to finish
    local MUTATIONS_RUNNING=1
    while [ $MUTATIONS_RUNNING -gt 0 ]; do
        MUTATIONS_RUNNING=$($CH_CMD --query "SELECT count() FROM system.mutations WHERE table = '$TABLE' AND database = 'tradelayout' AND is_done = 0")
        
        if [ $MUTATIONS_RUNNING -gt 0 ]; then
            echo "   Processing... (mutations remaining: $MUTATIONS_RUNNING)"
            sleep 5
        fi
    done
    
    # Verify new timestamp range
    echo ""
    echo "New timestamp range:"
    $CH_CMD --query "SELECT min(timestamp) as first_ts, max(timestamp) as last_ts, count() as total_rows FROM $TABLE"
    
    echo "✅ $TABLE - Timezone fixed!"
    echo ""
}

# Fix all tables
fix_table "nse_ticks_indices"
fix_table "nse_ticks_options"
fix_table "nse_ticks_stocks"
fix_table "nse_ohlcv_indices"
fix_table "nse_ohlcv_stocks"

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
$CH_CMD --query "
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
$CH_CMD --query "
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
echo "Expected Oct 29 time range: 09:07:04 to 15:30:00 (IST)"
echo "Data is now ready for backtesting with correct timestamps!"
echo ""
