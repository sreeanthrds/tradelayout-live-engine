#!/bin/bash
# ClickHouse Database Setup Script

echo "======================================================================================================"
echo "🗄️  SETTING UP CLICKHOUSE DATABASE"
echo "======================================================================================================"

# Create database
echo "Creating database 'tradelayout'..."
clickhouse client --host localhost --port 9000 --user default --query "CREATE DATABASE IF NOT EXISTS tradelayout"

if [ $? -eq 0 ]; then
    echo "✅ Database created"
else
    echo "❌ Failed to create database"
    exit 1
fi

# Create tables
echo ""
echo "Creating tables..."

# Table 1: nse_ticks_indices
echo "  - nse_ticks_indices..."
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

# Table 2: nse_ticks_options
echo "  - nse_ticks_options..."
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

# Table 3: nse_ticks_stocks
echo "  - nse_ticks_stocks..."
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
echo "✅ DATABASE SETUP COMPLETE"
echo "======================================================================================================"
echo ""
echo "Connection Details:"
echo "  Host: localhost"
echo "  Port: 9000"
echo "  Database: tradelayout"
echo "  User: default"
echo ""
echo "To connect: clickhouse client --host localhost --port 9000 --user default --database tradelayout"
echo "======================================================================================================"
