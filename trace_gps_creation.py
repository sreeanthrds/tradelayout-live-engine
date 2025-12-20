#!/usr/bin/env python3
"""
Trace WHERE each GPS instance is created
"""
import os
import sys
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.core.gps import GlobalPositionStore

print("\n" + "="*100)
print("TRACE GPS CREATION: Find where each GPS instance is created")
print("="*100 + "\n")

# Patch GPS init to capture creation stack trace
original_init = GlobalPositionStore.__init__
def patched_init(self):
    original_init(self)
    stack = ''.join(traceback.format_stack()[:-1])  # Exclude this frame
    print(f"\n🔍 GPS Instance Created: ID={id(self)}")
    print(f"   Creation stack trace:")
    # Print only last 10 lines of stack trace for readability
    stack_lines = stack.split('\n')
    for line in stack_lines[-15:]:
        if line.strip():
            print(f"   {line}")

GlobalPositionStore.__init__ = patched_init

# Run backtest
print("Starting backtest...\n")
config = BacktestConfig(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date=datetime(2024, 10, 29)
)

engine = CentralizedBacktestEngine(config)
results = engine.run()

print("\n" + "="*100)
print(f"Backtest complete: {len(results.positions)} positions in results")
print("="*100 + "\n")
