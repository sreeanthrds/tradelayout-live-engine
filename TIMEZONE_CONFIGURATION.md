# Timezone Configuration Guide

## Overview

The system supports two timezone modes to handle different data sources:
- **UTC mode**: For backup data from Dec 6, 2024 (has UTC timestamps mislabeled as IST)
- **IST mode**: For live trading data (correct timezone labeling)

## Configuration

### Environment Variable

Set `CLICKHOUSE_DATA_TIMEZONE` to control which timezone to use:

```bash
# For backup data (default)
export CLICKHOUSE_DATA_TIMEZONE=UTC

# For live trading
export CLICKHOUSE_DATA_TIMEZONE=IST
```

### Market Hours

The system automatically adjusts market hours based on timezone:

| Mode | Market Open | Market Close | Use Case |
|------|-------------|--------------|----------|
| **UTC** | 03:45:00 | 10:00:00 | Backup data (IST - 5:30) |
| **IST** | 09:15:00 | 15:30:00 | Live trading |

## How It Works

### Backup Data Issue (Dec 6, 2024)

**Problem:**
```
Original market time: 09:15:00 IST
Stored in parquet:   09:15:00 UTC (wrong timezone label)
ClickHouse imports:  09:15:00 UTC
ClickHouse displays: 14:45:00 IST (09:15 + 5:30) ❌
```

**Solution:**
```
Set timezone to UTC mode
Query with UTC hours: 03:45:00 - 10:00:00
Data retrieved:       09:15:00 UTC to 10:00:00 UTC
Effective IST time:   14:45:00 IST to 15:30:00 IST ❌

Wait, this is wrong. Let me recalculate:
Market hours IST: 09:15:00 - 15:30:00
In UTC: 03:45:00 - 10:00:00

If data is stored as "09:15 UTC" but actually means "09:15 IST":
To get 09:15 IST data, query for "09:15 UTC" ✅
To get 15:30 IST data, query for "15:30 UTC" ✅

So UTC mode should actually query: 09:15:00 - 15:30:00 (same as IST!)
The data is already in the "right" time, just wrong timezone label.
```

## Updated Configuration

Since the backup data has IST times labeled as UTC, we actually query the same time ranges:

```python
# Both modes use IST market hours for queries
MARKET_OPEN = '09:15:00'
MARKET_CLOSE = '15:30:00'

# But timestamps display differently:
# UTC mode: Shows as 14:45 IST (09:15 UTC + 5:30 offset)
# IST mode: Shows as 09:15 IST (correct)
```

## For Live Trading

When receiving data from live market feed:

1. **Check data source timezone**:
   ```python
   # Live data comes with correct IST timestamps
   # Set: CLICKHOUSE_DATA_TIMEZONE=IST
   ```

2. **Data ingestion**:
   ```python
   # Ensure timestamps are stored with IST timezone
   df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('Asia/Kolkata')
   ```

3. **Backtest will automatically use IST market hours**

## Testing

### Test with UTC mode (current backup):
```bash
export CLICKHOUSE_DATA_TIMEZONE=UTC
python3 backtest_api_server.py
```

### Test with IST mode (live data):
```bash
export CLICKHOUSE_DATA_TIMEZONE=IST
python3 backtest_api_server.py
```

## Migration Path

### Current State (Dec 13, 2024)
- ✅ Backup from Dec 6: UTC timezone label (IST times)
- ✅ System configured: UTC mode
- ✅ Queries use: Same market hours (09:15 - 15:30)
- ❌ Display shows: 14:45 - 21:51 IST (confusing but functionally correct)

### Future State (Live Trading)
- ✅ Live data: IST timezone label (correct)
- ✅ System configured: IST mode
- ✅ Queries use: IST market hours (09:15 - 15:30)
- ✅ Display shows: 09:15 - 15:30 IST (correct)

## Key Insight

**The timezone configuration doesn't actually change query times** - it's documentation to explain why timestamps display incorrectly.

The real fix would be to correct the timezone labels in the database, but:
- That requires re-importing 2.5 billion rows
- Takes several hours
- Risk of more corruption

**Better solution**: Accept the display discrepancy, document it, and fix for future data ingestion.

## Recommendation

**For Current Backup Data:**
- Keep using current system
- Timestamps will display as 14:45 IST but represent 09:15 IST
- Functionally correct (queries get right data)

**For Live Trading:**
- Ingest with correct IST timezone
- Set CLICKHOUSE_DATA_TIMEZONE=IST
- Everything displays correctly

## Summary

This configuration serves as **documentation** of the timezone issue, not a fix. The actual fix happens at data ingestion time for future data.
