#!/bin/bash
# ClickHouse Localhost Startup Script

# Ensure common install locations are on PATH (macOS/Homebrew)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "======================================================================================================"
echo "🚀 STARTING CLICKHOUSE SERVER (LOCALHOST)"
echo "======================================================================================================"

# Check if ClickHouse is installed
CLICKHOUSE_BIN="$(command -v clickhouse || true)"
if [ -z "$CLICKHOUSE_BIN" ] && [ -x "/opt/homebrew/bin/clickhouse" ]; then
    CLICKHOUSE_BIN="/opt/homebrew/bin/clickhouse"
fi
if [ -z "$CLICKHOUSE_BIN" ] && [ -x "/usr/local/bin/clickhouse" ]; then
    CLICKHOUSE_BIN="/usr/local/bin/clickhouse"
fi

if [ -z "$CLICKHOUSE_BIN" ]; then
    echo "❌ ClickHouse is not installed!"
    echo "Install with: brew install clickhouse"
    exit 1
fi

CONFIG_DIR="$HOME/clickhouse_config"
CONFIG_FILE="$CONFIG_DIR/config.xml"
USERS_FILE="$CONFIG_DIR/users.xml"
DATA_DIR="$HOME/clickhouse_data"
ERR_LOG="$DATA_DIR/logs/clickhouse-server.err.log"

CLIENT_CONNECT_TIMEOUT_SECS="2"

# Check if already running
if lsof -nP -iTCP:9000 -sTCP:LISTEN >/dev/null 2>&1 || lsof -nP -iTCP:8123 -sTCP:LISTEN >/dev/null 2>&1 || pgrep -x "clickhouse-server" > /dev/null || pgrep -x "clickhouse-serv" > /dev/null; then
    echo "✅ ClickHouse server is already running"
else
    echo "🔄 Starting ClickHouse server..."
    if [ -f "$CONFIG_FILE" ] && { [ ! -f "$USERS_FILE" ] || ! grep -q "<log_queries>" "$USERS_FILE" 2>/dev/null; }; then
        echo "ℹ️  Creating users config: $USERS_FILE"
        cat > "$USERS_FILE" << 'EOF'
<clickhouse>
    <profiles>
        <default>
            <log_queries>0</log_queries>
        </default>
    </profiles>

    <users>
        <default>
            <password></password>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
            <access_management>1</access_management>
        </default>
    </users>

    <quotas>
        <default>
            <interval>
                <duration>3600</duration>
                <queries>0</queries>
                <errors>0</errors>
                <result_rows>0</result_rows>
                <read_rows>0</read_rows>
                <execution_time>0</execution_time>
            </interval>
        </default>
    </quotas>
</clickhouse>
EOF
    fi

    if [ -f "$CONFIG_FILE" ]; then
        echo "ℹ️  Using config: $CONFIG_FILE"
        "$CLICKHOUSE_BIN" server --config-file="$CONFIG_FILE" --daemon
    else
        "$CLICKHOUSE_BIN" server --daemon
    fi
    sleep 3
    
    if pgrep -x "clickhouse-server" > /dev/null || pgrep -x "clickhouse-serv" > /dev/null; then
        echo "✅ ClickHouse server started successfully"
    else
        echo "❌ Failed to start ClickHouse server"
        if [ -f "$ERR_LOG" ]; then
            echo "---- Last 60 lines: $ERR_LOG ----"
            tail -n 60 "$ERR_LOG"
        fi
        exit 1
    fi

    "$CLICKHOUSE_BIN" client --host 127.0.0.1 --port 9000 --user default --connect_timeout "$CLIENT_CONNECT_TIMEOUT_SECS" --query "SELECT 1" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "❌ ClickHouse server did not respond on 127.0.0.1:9000"
        if [ -f "$ERR_LOG" ]; then
            echo "---- Last 60 lines: $ERR_LOG ----"
            tail -n 60 "$ERR_LOG"
        fi
        exit 1
    fi
fi

echo ""
echo "======================================================================================================"
echo "🗄️  SETTING UP DATABASE"
echo "======================================================================================================"

# Create database
echo "Creating database 'tradelayout'..."
"$CLICKHOUSE_BIN" client --host 127.0.0.1 --port 9000 --user default --connect_timeout "$CLIENT_CONNECT_TIMEOUT_SECS" --query "CREATE DATABASE IF NOT EXISTS tradelayout"

# Create tables
echo "Creating tables..."

# Table 1: nse_ticks_indices (for NIFTY/BANKNIFTY underlying)
"$CLICKHOUSE_BIN" client --host 127.0.0.1 --port 9000 --user default --connect_timeout "$CLIENT_CONNECT_TIMEOUT_SECS" --database tradelayout --query "
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
"$CLICKHOUSE_BIN" client --host 127.0.0.1 --port 9000 --user default --connect_timeout "$CLIENT_CONNECT_TIMEOUT_SECS" --database tradelayout --query "
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
"$CLICKHOUSE_BIN" client --host 127.0.0.1 --port 9000 --user default --connect_timeout "$CLIENT_CONNECT_TIMEOUT_SECS" --database tradelayout --query "
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
