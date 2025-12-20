#!/usr/bin/env python3
"""
Run Strategy 5708424d-5962-4629-978c-05b3a174e104 (My New Strategy5) for October 2024
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_runner import run_backtest
import json
from pathlib import Path

STRATEGY_ID = '5708424d-5962-4629-978c-05b3a174e104'

# Test a few days to find trades
test_dates = ['2024-10-01', '2024-10-03', '2024-10-04', '2024-10-07', '2024-10-08', '2024-10-09', '2024-10-10']

print(f"{'='*80}")
print(f"Testing Strategy: My New Strategy5")
print(f"ID: {STRATEGY_ID}")
print(f"{'='*80}\n")

for date in test_dates:
    print(f"Testing {date}...", end=' ')
    result = run_backtest(
        strategy_ids=STRATEGY_ID,
        backtest_date=date
    )
    
    # Check if any trades were taken
    json_file = Path(f'backtest_dashboard_data.json')
    if json_file.exists():
        with open(json_file, 'r') as f:
            data = json.load(f)
            if data['positions']:
                print(f"✅ {len(data['positions'])} positions, P&L: ₹{data['summary']['total_pnl']}")
            else:
                print(f"⚪ No trades")
    print()

print(f"\n{'='*80}")
print("Test complete! Check dates with trades above.")
print(f"{'='*80}\n")
