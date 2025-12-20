#!/bin/bash
# ClickHouse Localhost Startup Script

echo "======================================================================================================"
echo "🚀 STARTING CLICKHOUSE SERVER (LOCALHOST)"
echo "======================================================================================================"

# Check if ClickHouse is installed
if ! command -v clickhouse &> /dev/null; then
    echo "❌ ClickHouse is not installed!"
    echo "Install with: brew install clickhouse"
    exit 1
fi

# Check if already running
if pgrep -x "clickhouse-serv" > /dev/null; then
    echo "✅ ClickHouse server is already running"
else
    echo "🔄 Starting ClickHouse server..."
    clickhouse server --daemon
    sleep 3
    
    if pgrep -x "clickhouse-serv" > /dev/null; then
        echo "✅ ClickHouse server started successfully"
    else
        echo "❌ Failed to start ClickHouse server"
        exit 1
    fi
fi

echo ""
echo "======================================================================================================"
echo "🗄️  SETTING UP DATABASE"
echo "======================================================================================================"

# Create database
echo "Creating database 'tradelayout'..."
clickhouse client --host localhost --port 9000 --user default --query "CREATE DATABASE IF NOT EXISTS tradelayout"

# Create tables
echo "Creating tables..."

# Table 1: nse_ticks_indices (for NIFTY/BANKNIFTY underlying)
clickhouse client --host localhost --port 9000 --user default --database tradelayout --query "
CREATE TABLE IF NOT EXISTS nse_ticks_indices (
    trading_day Date,
    timestamp DateTime,
    symbol String,
    ltp Float64,
    volume UInt64,
    ltq UInt64,
    oi UInt64,
    bid_price Float64,
    ask_price Float64,
    bid_qty UInt64,
    ask_qty UInt64,
    buy_qty UInt64,
    sell_qty UInt64
) ENGINE = MergeTree()
PARTITION BY trading_day
ORDER BY (trading_day, symbol, timestamp)
SETTINGS index_granularity = 8192
"

# Table 2: nse_ticks_options (for option contracts)
clickhouse client --host localhost --port 9000 --user default --database tradelayout --query "
CREATE TABLE IF NOT EXISTS nse_ticks_options (
    trading_day Date,
    timestamp DateTime,
    ticker String,
    underlying String,
    strike_price Float64,
    option_type String,
    expiry Date,
    ltp Float64,
    volume UInt64,
    ltq UInt64,
    oi UInt64,
    bid_price Float64,
    ask_price Float64,
    bid_qty UInt64,
    ask_qty UInt64
) ENGINE = MergeTree()
PARTITION BY trading_day
ORDER BY (trading_day, ticker, timestamp)
SETTINGS index_granularity = 8192
"

# Table 3: nse_ticks_stocks (for individual stocks)
clickhouse client --host localhost --port 9000 --user default --database tradelayout --query "
CREATE TABLE IF NOT EXISTS nse_ticks_stocks (
    trading_day Date,
    timestamp DateTime,
    symbol String,
    ltp Float64,
    volume UInt64,
    ltq UInt64,
    oi UInt64,
    bid_price Float64,
    ask_price Float64,
    bid_qty UInt64,
    ask_qty UInt64,
    buy_qty UInt64,
    sell_qty UInt64
) ENGINE = MergeTree()
PARTITION BY trading_day
ORDER BY (trading_day, symbol, timestamp)
SETTINGS index_granularity = 8192
"

echo ""
echo "======================================================================================================"
echo "✅ CLICKHOUSE SETUP COMPLETE"
echo "======================================================================================================"
echo ""
echo "Connection Details:"
echo "  Host: localhost"
echo "  Port: 9000"
echo "  Database: tradelayout"
echo "  User: default"
echo ""
echo "Available Tables:"
echo "  - nse_ticks_indices (NIFTY/BANKNIFTY)"
echo "  - nse_ticks_options (Option contracts)"
echo "  - nse_ticks_stocks (Individual stocks)"
echo ""
echo "To connect: clickhouse client --host localhost --port 9000 --user default --database tradelayout"
echo "To stop: killall clickhouse-server"
echo ""
echo "======================================================================================================"
