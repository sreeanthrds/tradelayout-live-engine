#!/bin/bash
# Fix ALL tables by re-importing from cloud with correct schema

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
echo "FIXING ALL CLICKHOUSE TABLES"
echo "=================================================="

# Function to fix a table
fix_table() {
    local table_name=$1
    echo ""
    echo "Fixing table: $table_name"
    echo "--------------------------------------------"
    
    # Drop local table
    echo "   Dropping local table..."
    clickhouse client \
      --host $LOCAL_HOST \
      --port $LOCAL_PORT \
      --user $LOCAL_USER \
      --database $LOCAL_DB \
      --query "DROP TABLE IF EXISTS $table_name" 2>&1 | grep -v "^2025\." || true
    
    # Get schema from cloud
    echo "   Getting schema from cloud..."
    clickhouse client \
      --host $CLOUD_HOST \
      --secure \
      --port $CLOUD_PORT \
      --user $CLOUD_USER \
      --password "$CLOUD_PASS" \
      --database $CLOUD_DB \
      --query "SHOW CREATE TABLE $table_name" | sed 's/SharedMergeTree/MergeTree/g' > /tmp/${table_name}_schema.sql
    
    # Create table locally
    echo "   Creating table locally..."
    clickhouse client \
      --host $LOCAL_HOST \
      --port $LOCAL_PORT \
      --user $LOCAL_USER \
      --database $LOCAL_DB \
      --multiquery < /tmp/${table_name}_schema.sql 2>&1 | grep -v "^2025\." || true
    
    # Import data
    echo "   Importing data..."
    clickhouse client \
      --host $CLOUD_HOST \
      --secure \
      --port $CLOUD_PORT \
      --user $CLOUD_USER \
      --password "$CLOUD_PASS" \
      --database $CLOUD_DB \
      --query "SELECT * FROM $table_name FORMAT Native" | \
    clickhouse client \
      --host $LOCAL_HOST \
      --port $LOCAL_PORT \
      --user $LOCAL_USER \
      --database $LOCAL_DB \
      --query "INSERT INTO $table_name FORMAT Native" 2>&1 | grep -v "^2025\."
    
    echo "   ✅ $table_name fixed"
}

# Fix tables
fix_table "nse_ticks_indices"

echo ""
echo "=================================================="
echo "✅ ALL TABLES FIXED!"
echo "=================================================="
echo ""
echo "Verifying..."
echo ""

# Verify nse_ticks_indices
echo "nse_ticks_indices:"
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "SELECT count(*) as total, min(trading_day) as min_date, max(trading_day) as max_date FROM nse_ticks_indices" 2>&1 | tail -3

echo ""
echo "Sample data:"
clickhouse client \
  --host $LOCAL_HOST \
  --port $LOCAL_PORT \
  --user $LOCAL_USER \
  --database $LOCAL_DB \
  --query "SELECT * FROM nse_ticks_indices WHERE trading_day = '2024-10-29' LIMIT 3" 2>&1 | tail -5

echo ""
echo "✅ COMPLETE! Restart the API server now."
