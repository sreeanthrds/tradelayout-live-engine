#!/usr/bin/env python3
"""
Run backtest for strategy 5708424d-5962-4629-978c-05b3a174e104 on Oct 1, 2024
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_runner import run_backtest

# Run backtest
result = run_backtest(
    strategy_ids='5708424d-5962-4629-978c-05b3a174e104',
    backtest_date='2024-10-01'
)

print(f"\n✅ Backtest completed")
print(f"Now check show_dashboard_data.py for the new strategy")
