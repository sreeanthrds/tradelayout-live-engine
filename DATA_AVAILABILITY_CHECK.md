# Data Availability Check

## Overview

The data availability checker ensures that sufficient OHLC data exists in ClickHouse before running backtests. This prevents failed backtests due to missing data and provides clear feedback about data coverage.

## Features

✅ **Pre-backtest validation** - Checks data before starting the backtest  
✅ **Date range checking** - Verifies requested date is within available range  
✅ **Symbol-specific validation** - Checks each symbol individually  
✅ **Automatic skip** - Raises error if data is missing, preventing wasted execution  
✅ **Clear error messages** - Tells you exactly what's missing and what's available

## How It Works

### 1. Automatic Check in Backtests

When you run a backtest using `run_backtest()`, the system automatically checks data availability:

```python
from src.backtesting.backtest_runner import run_backtest

# This will automatically check if data exists for 2024-10-01
results = run_backtest(
    strategy_ids='your-strategy-id',
    backtest_date='2024-10-01'
)
```

**If data is missing:**
```
❌ Data not available: Backtest date 2024-10-01 is beyond last available date 2024-09-30
📅 Data available from 2024-01-15 to 2024-09-30
ValueError: Data not available: Backtest date 2024-10-01 is beyond last available date 2024-09-30
```

**If data is available:**
```
✅ Data availability confirmed for 2024-10-01
🚀 BACKTEST WITH CENTRALIZED TICK PROCESSOR
...
```

### 2. Manual Check

You can also check data availability manually:

```python
import clickhouse_connect
from src.utils.data_availability_checker import DataAvailabilityChecker
from src.config.clickhouse_config import ClickHouseConfig
from datetime import datetime

# Connect to ClickHouse
client = clickhouse_connect.get_client(**ClickHouseConfig.get_clickhouse_connect_config())

# Create checker
checker = DataAvailabilityChecker(client)

# Check specific date
result = checker.check_date_availability(
    backtest_date=datetime(2024, 10, 1),
    symbols=['NIFTY', 'BANKNIFTY'],
    timeframe='1d'
)

if result['available']:
    print("✅ Data available!")
else:
    print(f"❌ {result['reason']}")
    print(f"Available range: {result['first_available']} to {result['last_available']}")
```

### 3. Get Available Date Range

Check the complete date range for your symbols:

```python
date_ranges = checker.get_available_date_range(
    symbols=['NIFTY', 'BANKNIFTY'],
    timeframe='1d'
)

for symbol, info in date_ranges.items():
    print(f"{symbol}:")
    print(f"  First date: {info['first_date']}")
    print(f"  Last date: {info['last_date']}")
    print(f"  Total candles: {info['total_candles']:,}")
```

## Response Structure

### check_date_availability()

Returns a dictionary with:

```python
{
    'available': bool,              # True if data exists
    'reason': str,                  # Explanation (if not available)
    'first_available': datetime,    # First date with data
    'last_available': datetime,     # Last date with data
    'missing_symbols': List[str]    # Symbols without data
}
```

### get_available_date_range()

Returns a dictionary mapping symbols to their date ranges:

```python
{
    'NIFTY': {
        'first_date': datetime(2024, 1, 15),
        'last_date': datetime(2024, 11, 30),
        'total_candles': 220
    },
    'BANKNIFTY': {
        'first_date': datetime(2024, 1, 15),
        'last_date': datetime(2024, 11, 30),
        'total_candles': 220
    }
}
```

## Common Scenarios

### Scenario 1: Date Too Early

```
❌ Backtest date 2020-01-01 is before first available date 2024-01-15
```

**Solution:** Choose a date within the available range

### Scenario 2: Date Too Recent/Future

```
❌ Backtest date 2024-12-01 is beyond last available date 2024-11-30
```

**Solution:** Wait for data to be populated or choose an earlier date

### Scenario 3: Missing Symbol Data

```
❌ Missing data for symbols: BANKNIFTY on 2024-10-15
```

**Solution:** Check if that symbol had trading on that date (might be holiday)

### Scenario 4: No Data in Database

```
❌ No OHLC data found in nse_ohlcv_indices table for timeframe 1d
```

**Solution:** Ensure data has been loaded into ClickHouse

## Testing

Run the test script to see data availability for your database:

```bash
python test_data_availability.py
```

**Output:**
```
AVAILABLE DATE RANGES
================================================================================

NIFTY:
  First date: 2024-01-15
  Last date:  2024-11-30
  Total candles: 220

BANKNIFTY:
  First date: 2024-01-15
  Last date:  2024-11-30
  Total candles: 220

TESTING DIFFERENT BACKTEST DATES
================================================================================

Testing date: 2024-09-01
================================================================================
✅ AVAILABLE - Data exists for 2024-09-01

Testing date: 2024-12-01
================================================================================
❌ NOT AVAILABLE
   Reason: Backtest date 2024-12-01 is beyond last available date 2024-11-30
   Valid range: 2024-01-15 to 2024-11-30
```

## Database Tables Checked

The checker queries the following table:

- **nse_ohlcv_indices** - Daily OHLC data for indices (NIFTY, BANKNIFTY, etc.)

**Table Structure:**
```sql
CREATE TABLE nse_ohlcv_indices (
    ticker LowCardinality(String),
    timestamp DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (ticker, timestamp)
```

## Configuration

The checker uses the centralized ClickHouse configuration:

**File:** `src/config/clickhouse_config.py`

```python
class ClickHouseConfig:
    HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    PORT = int(os.getenv('CLICKHOUSE_PORT', '8123'))
    DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'tradelayout')
```

## Benefits

1. **Prevents Wasted Time** - No more running backtests that will fail due to missing data
2. **Clear Feedback** - Know exactly what data is available before starting
3. **Automatic Skip** - System won't proceed if data is missing
4. **Date Range Visibility** - See your complete data coverage at a glance
5. **Symbol-Level Check** - Ensures all required symbols have data

## Files

**Core Implementation:**
- `src/utils/data_availability_checker.py` - Checker implementation
- `src/backtesting/backtest_runner.py` - Integration into backtest flow

**Testing:**
- `test_data_availability.py` - Test script

**Documentation:**
- `DATA_AVAILABILITY_CHECK.md` - This file

## Error Handling

The checker handles various error scenarios:

- **No data in database** - Returns clear error message
- **Connection failures** - Catches and reports connection errors
- **Invalid dates** - Validates date format and range
- **Missing symbols** - Reports which symbols are missing data

## Future Enhancements

Potential improvements:

- [ ] Check intraday data availability (1m, 5m, 15m, etc.)
- [ ] Weekend/holiday detection
- [ ] Batch date range checking
- [ ] Data quality metrics (gaps, outliers)
- [ ] Auto-download missing data from external sources

---

**Status:** ✅ Implemented and tested  
**Version:** 1.0  
**Date:** December 6, 2025
