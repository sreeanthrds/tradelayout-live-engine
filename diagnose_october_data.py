#!/usr/bin/env python3
"""
Diagnose October 2024 Data Issues
1. Check if Oct 2 (holiday) has data
2. Check why 18 days failed
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import date, timedelta
import clickhouse_connect
from src.config.clickhouse_config import ClickHouseConfig

print(f"\n{'='*100}")
print("DIAGNOSING OCTOBER 2024 DATA ISSUES")
print(f"{'='*100}\n")

# Get ClickHouse client
try:
    print("🔌 Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host=ClickHouseConfig.HOST,
        user=ClickHouseConfig.USER,
        password=ClickHouseConfig.PASSWORD,
        secure=ClickHouseConfig.SECURE,
        database=ClickHouseConfig.DATABASE
    )
    print("✅ Connected\n")
except Exception as e:
    print(f"❌ Failed to connect: {e}\n")
    sys.exit(1)

# Check data availability for each day in October
print(f"{'='*100}")
print("CHECKING DATA AVAILABILITY FOR OCTOBER 2024")
print(f"{'='*100}\n")

october_days = []
start_date = date(2024, 10, 1)
end_date = date(2024, 11, 1)

current_date = start_date
while current_date < end_date:
    october_days.append(current_date)
    current_date += timedelta(days=1)

results = []

for test_date in october_days:
    trading_day = test_date.strftime('%Y-%m-%d')
    day_name = test_date.strftime('%A')
    
    try:
        # Check if data exists for NIFTY
        query = f"""
            SELECT 
                COUNT(*) as tick_count,
                MIN(timestamp) as first_tick,
                MAX(timestamp) as last_tick
            FROM nse_ticks_indices
            WHERE trading_day = '{trading_day}'
              AND symbol = 'NIFTY'
        """
        
        result = client.query(query)
        row = result.result_rows[0] if result.result_rows else None
        
        if row:
            tick_count = row[0]
            first_tick = row[1]
            last_tick = row[2]
            
            status = '✅' if tick_count > 0 else '❌'
            
            results.append({
                'date': trading_day,
                'day': day_name,
                'ticks': tick_count,
                'first': first_tick,
                'last': last_tick
            })
            
            print(f"{status} {trading_day} ({day_name:9s}): {tick_count:6,} ticks", end='')
            if tick_count > 0:
                print(f" | {first_tick} to {last_tick}")
            else:
                print()
        else:
            print(f"❌ {trading_day} ({day_name:9s}): Query returned no rows")
            results.append({
                'date': trading_day,
                'day': day_name,
                'ticks': 0,
                'first': None,
                'last': None
            })
    except Exception as e:
        print(f"❌ {trading_day} ({day_name:9s}): Error - {str(e)[:60]}")
        results.append({
            'date': trading_day,
            'day': day_name,
            'ticks': -1,
            'error': str(e)
        })

# Summary
print(f"\n{'='*100}")
print("SUMMARY")
print(f"{'='*100}\n")

days_with_data = sum(1 for r in results if r['ticks'] > 0)
days_without_data = sum(1 for r in results if r['ticks'] == 0)
days_with_errors = sum(1 for r in results if r['ticks'] < 0)

print(f"Total Days: {len(results)}")
print(f"Days WITH Data: {days_with_data}")
print(f"Days WITHOUT Data: {days_without_data}")
print(f"Days with Errors: {days_with_errors}")

# Show holidays/weekends
print(f"\n{'='*100}")
print("DAYS WITHOUT DATA (Likely Holidays/Weekends)")
print(f"{'='*100}\n")

for r in results:
    if r['ticks'] == 0:
        print(f"  {r['date']} ({r['day']})")

# Check known holidays
print(f"\n{'='*100}")
print("KNOWN OCTOBER 2024 HOLIDAYS")
print(f"{'='*100}\n")

holidays = [
    ('2024-10-02', 'Gandhi Jayanti'),
    ('2024-10-12', 'Dussehra'),
    ('2024-10-31', 'Diwali'),
]

for holiday_date, holiday_name in holidays:
    # Find in results
    for r in results:
        if r['date'] == holiday_date:
            if r['ticks'] > 0:
                print(f"⚠️  {holiday_date} ({holiday_name}): HAS DATA ({r['ticks']} ticks) - SHOULD NOT!")
            else:
                print(f"✅ {holiday_date} ({holiday_name}): No data (correct)")
            break

print(f"\n{'='*100}\n")

client.close()
