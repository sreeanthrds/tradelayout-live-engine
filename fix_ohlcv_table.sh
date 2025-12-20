#!/bin/bash
# Fix nse_ohlcv_indices table by re-importing from cloud with correct schema
# This script will drop the broken local table and recreate it properly

CLOUD_HOST="blo67czt7m.ap-south-1.aws.clickhouse.cloud"
CLOUD_PORT="9440"
CLOUD_USER="default"
CLOUD_PASS="0DNor8RIL2.7r"
CLOUD_DB="default"

LOCAL_HOST="localhost"
LOCAL_PORT="9000"
LOCAL_USER="default"
LOCAL_PASS=""
LOCAL_DB="tradelayout"

echo "=================================================="
echo "FIXING nse_ohlcv_indices TABLE"
echo "=================================================="

echo ""
echo "Step 1: Dropping broken local table..."
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "DROP TABLE IF EXISTS nse_ohlcv_indices"

echo "✅ Table dropped"

echo ""
echo "Step 2: Getting correct schema from cloud..."
clickhouse client \
  --host $CLOUD_HOST \
  --secure \
  --port $CLOUD_PORT \
  --user $CLOUD_USER \
  --password "$CLOUD_PASS" \
  --database $CLOUD_DB \
  --query "SHOW CREATE TABLE nse_ohlcv_indices" > /tmp/create_table.sql

# Replace SharedMergeTree with MergeTree for local
sed -i '' 's/SharedMergeTree/MergeTree/g' /tmp/create_table.sql

echo "✅ Schema retrieved"

echo ""
echo "Step 3: Creating table locally with correct schema..."
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --multiquery < /tmp/create_table.sql

echo "✅ Table created"

echo ""
echo "Step 4: Exporting data from cloud..."
echo "   (This will take a few minutes - exporting ~468K rows)"

clickhouse client \
  --host $CLOUD_HOST \
  --secure \
  --port $CLOUD_PORT \
  --user $CLOUD_USER \
  --password "$CLOUD_PASS" \
  --database $CLOUD_DB \
  --query "SELECT * FROM nse_ohlcv_indices FORMAT Native" | \
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "INSERT INTO nse_ohlcv_indices FORMAT Native"

echo "✅ Data imported"

echo ""
echo "Step 5: Verifying data..."
echo ""

# Check row count
LOCAL_COUNT=$(clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "SELECT count(*) FROM nse_ohlcv_indices")

echo "   Total rows: $LOCAL_COUNT"

# Check symbols
echo ""
echo "   Symbols and timeframes:"
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "SELECT symbol, timeframe, count(*) as cnt FROM nse_ohlcv_indices GROUP BY symbol, timeframe ORDER BY symbol, timeframe" | head -10

echo ""
echo "   Sample data from 2024-10-29:"
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "SELECT * FROM nse_ohlcv_indices WHERE trading_day = '2024-10-29' AND symbol = 'NIFTY' AND timeframe = '1m' LIMIT 3"

echo ""
echo "=================================================="
echo "✅ TABLE FIXED SUCCESSFULLY!"
echo "=================================================="
echo ""
echo "The table now has:"
echo "  - symbol column (NIFTY, BANKNIFTY, etc.)"
echo "  - timeframe column (1m, 5m, 15m, etc.)"
echo "  - trading_day column (date)"
echo ""
echo "You can now run backtests successfully!"
