#!/bin/bash
# Fix ClickHouse to use permanent storage location

echo "======================================================================================================"
echo "🔧 FIXING CLICKHOUSE TO USE PERMANENT STORAGE"
echo "======================================================================================================"

# Stop current ClickHouse server
echo "Stopping ClickHouse server..."
killall clickhouse-server 2>/dev/null
sleep 2

# Create permanent data directory
PERMANENT_DIR="$HOME/clickhouse_data"
echo "Creating permanent directory: $PERMANENT_DIR"
mkdir -p "$PERMANENT_DIR"

# Create config directory
CONFIG_DIR="$HOME/clickhouse_config"
mkdir -p "$CONFIG_DIR"

# Create config.xml with permanent path
cat > "$CONFIG_DIR/config.xml" << EOF
<clickhouse>
    <path>$PERMANENT_DIR/</path>
    <tmp_path>$PERMANENT_DIR/tmp/</tmp_path>
    <user_files_path>$PERMANENT_DIR/user_files/</user_files_path>
    <format_schema_path>$PERMANENT_DIR/format_schemas/</format_schema_path>
    
    <logger>
        <level>information</level>
        <log>$PERMANENT_DIR/logs/clickhouse-server.log</log>
        <errorlog>$PERMANENT_DIR/logs/clickhouse-server.err.log</errorlog>
        <size>1000M</size>
        <count>3</count>
    </logger>
    
    <http_port>8123</http_port>
    <tcp_port>9000</tcp_port>
    
    <listen_host>::</listen_host>
    <listen_host>0.0.0.0</listen_host>
</clickhouse>
EOF

echo "✅ Config created at: $CONFIG_DIR/config.xml"

# Start ClickHouse with custom config
echo ""
echo "Starting ClickHouse with permanent storage..."
clickhouse server --config-file="$CONFIG_DIR/config.xml" --daemon

sleep 3

# Check if running
if pgrep -x "clickhouse-serv" > /dev/null; then
    echo "✅ ClickHouse server started successfully"
else
    echo "❌ Failed to start ClickHouse server"
    echo "Check logs at: $PERMANENT_DIR/logs/"
    exit 1
fi

# Recreate database and tables
echo ""
echo "Recreating database and tables..."
clickhouse client --host localhost --port 9000 --user default --query "CREATE DATABASE IF NOT EXISTS tradelayout"

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
echo "✅ CLICKHOUSE FIXED!"
echo "======================================================================================================"
echo ""
echo "Data Location: $PERMANENT_DIR"
echo "Config Location: $CONFIG_DIR/config.xml"
echo "Logs Location: $PERMANENT_DIR/logs/"
echo ""
echo "⚠️  IMPORTANT: Data will now persist across reboots!"
echo ""
echo "To stop: killall clickhouse-server"
echo "To start: clickhouse server --config-file=$CONFIG_DIR/config.xml --daemon"
echo ""
echo "======================================================================================================"
