"""
Test Data Availability Checker
================================

Test the data availability checking functionality before running backtests.
"""

import clickhouse_connect
from datetime import datetime
from src.utils.data_availability_checker import DataAvailabilityChecker
from src.config.clickhouse_config import ClickHouseConfig

# Connect to ClickHouse
print("Connecting to ClickHouse...")
client = clickhouse_connect.get_client(**ClickHouseConfig.get_clickhouse_connect_config())

# Initialize checker
checker = DataAvailabilityChecker(client)

# Test symbols
test_symbols = ['NIFTY', 'BANKNIFTY']

# Get available date range
print("\n" + "="*80)
print("AVAILABLE DATE RANGES")
print("="*80)

date_ranges = checker.get_available_date_range(test_symbols, timeframe='1d')
for symbol, info in date_ranges.items():
    print(f"\n{symbol}:")
    print(f"  First date: {info['first_date']}")
    print(f"  Last date:  {info['last_date']}")
    print(f"  Total candles: {info['total_candles']:,}")

# Test different dates
print("\n" + "="*80)
print("TESTING DIFFERENT BACKTEST DATES")
print("="*80)

test_dates = [
    '2024-09-01',  # Should work
    '2024-10-01',  # Should work
    '2024-11-01',  # Should work
    '2024-12-01',  # Might not work (future)
    '2020-01-01',  # Likely too old
]

for test_date_str in test_dates:
    print(f"\n{'='*80}")
    print(f"Testing date: {test_date_str}")
    print('='*80)
    
    test_date = datetime.strptime(test_date_str, '%Y-%m-%d')
    
    result = checker.check_date_availability(
        backtest_date=test_date,
        symbols=test_symbols,
        timeframe='1d'
    )
    
    if result['available']:
        print(f"✅ AVAILABLE - Data exists for {test_date_str}")
    else:
        print(f"❌ NOT AVAILABLE")
        print(f"   Reason: {result['reason']}")
        if result['first_available'] and result['last_available']:
            print(f"   Valid range: {result['first_available']} to {result['last_available']}")
        if result['missing_symbols']:
            print(f"   Missing symbols: {result['missing_symbols']}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

client.close()
