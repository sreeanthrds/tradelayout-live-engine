#!/usr/bin/env python3
"""
Test if indicator fix works
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from src.core.gps import GlobalPositionStore
from datetime import date

# Track entries
entry_count = [0]
orig_add = GlobalPositionStore.add_position

def track_add(self, pos_id, entry_data, tick_time=None):
    entry_count[0] += 1
    entry_time = entry_data.get('entry_time', 'N/A')
    print(f"\n🎯 ENTRY #{entry_count[0]} at {entry_time}")
    print(f"   Symbol: {entry_data.get('symbol')}")
    print(f"   Side: {entry_data.get('side')}")
    print(f"   Price: ₹{entry_data.get('entry_price')}")
    return orig_add(self, pos_id, entry_data, tick_time)

GlobalPositionStore.add_position = track_add

# Patch expression evaluator to log indicator lookups
from src.core.expression_evaluator import ExpressionEvaluator
orig_get_ind = ExpressionEvaluator._get_indicator_value
lookup_count = [0]

def logged_get_ind(self, config):
    lookup_count[0] += 1
    
    # Only log first few and around 09:18
    current_time = str((self.context or {}).get('current_time', ''))
    
    if lookup_count[0] <= 5 or '09:18' in current_time:
        result = orig_get_ind(self, config)
        
        if '09:18' in current_time or lookup_count[0] <= 5:
            print(f"\n[Indicator Lookup #{lookup_count[0]}]")
            print(f"  Time: {current_time}")
            print(f"  Looking for: {config.get('name')}")
            print(f"  Timeframe ID: {config.get('timeframeId')}")
            print(f"  Offset: {config.get('offset')}")
            print(f"  Result: {result}")
        
        return result
    else:
        return orig_get_ind(self, config)

ExpressionEvaluator._get_indicator_value = logged_get_ind

print(f"\n{'='*80}")
print(f"TESTING INDICATOR FIX")
print(f"{'='*80}\n")

config = BacktestConfig(
    strategy_ids=['64c2c932-0e0b-462a-9a36-7cda4371d102'],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

print(f"\n{'='*80}")
print(f"RESULTS")
print(f"{'='*80}")
print(f"Indicator lookups: {lookup_count[0]}")
print(f"Entries taken: {entry_count[0]}")
print(f"{'='*80}\n")

GlobalPositionStore.add_position = orig_add
ExpressionEvaluator._get_indicator_value = orig_get_ind
