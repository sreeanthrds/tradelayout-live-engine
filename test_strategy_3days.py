#!/usr/bin/env python3
"""
Test Strategy for 3 days to measure timing
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import date
from show_dashboard_data import run_dashboard_backtest
import time

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'

test_dates = [
    date(2024, 10, 1),
    date(2024, 10, 2),
    date(2024, 10, 3)
]

print(f"\n{'='*100}")
print(f"TESTING 3 DAYS TO MEASURE TIMING")
print(f"{'='*100}\n")

total_start = time.time()
results = []

for idx, test_date in enumerate(test_dates, 1):
    print(f"\n--- Day {idx}: {test_date} ---")
    day_start = time.time()
    
    try:
        result = run_dashboard_backtest(strategy_id, test_date)
        day_end = time.time()
        day_duration = day_end - day_start
        
        if result and 'summary' in result:
            summary = result['summary']
            pnl = summary.get('total_pnl', 0)
            positions = summary.get('total_positions', 0)
            
            results.append({
                'date': str(test_date),
                'duration': day_duration,
                'positions': positions,
                'pnl': pnl
            })
            
            print(f"✅ Complete: {day_duration:.2f}s | Positions: {positions} | P&L: ₹{pnl:.2f}")
        else:
            print(f"❌ Failed: {day_duration:.2f}s")
    except Exception as e:
        day_end = time.time()
        day_duration = day_end - day_start
        print(f"❌ Error: {str(e)[:100]} | Time: {day_duration:.2f}s")

total_end = time.time()
total_duration = total_end - total_start

print(f"\n{'='*100}")
print(f"TIMING ANALYSIS")
print(f"{'='*100}\n")

print(f"Total Time: {total_duration:.2f}s ({total_duration/60:.2f} minutes)")
print(f"Avg per Day: {total_duration/len(test_dates):.2f}s")

if results:
    total_positions = sum(r['positions'] for r in results)
    total_pnl = sum(r['pnl'] for r in results)
    
    print(f"\nPositions: {total_positions}")
    print(f"P&L: ₹{total_pnl:.2f}")

# Extrapolate for full month (23 trading days in Oct 2024)
trading_days_oct = 23
estimated_full_month = (total_duration / len(test_dates)) * trading_days_oct

print(f"\n{'='*100}")
print(f"FULL MONTH ESTIMATE (23 trading days)")
print(f"{'='*100}\n")
print(f"Estimated Time: {estimated_full_month:.2f}s ({estimated_full_month/60:.2f} minutes)")

print(f"\n{'='*100}\n")
