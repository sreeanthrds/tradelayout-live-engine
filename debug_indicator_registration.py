#!/usr/bin/env python3
"""
Debug indicator registration to see why RSI is not being calculated
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from datetime import date

STRATEGY_ID = '64c2c932-0e0b-462a-9a36-7cda4371d102'

# Monkey patch to see metadata
from src.backtesting.data_manager import DataManager
orig_register_from_agg = DataManager._register_indicators_from_agg

def logged_register_from_agg(self, strategies_agg):
    """Log what's in strategies_agg"""
    print(f"\n{'='*100}")
    print(f"📋 INDICATOR REGISTRATION DEBUG")
    print(f"{'='*100}")
    
    print(f"\nstrategies_agg keys: {strategies_agg.keys()}")
    
    indicators_dict = strategies_agg.get('indicators', {})
    print(f"\nIndicators dictionary: {json.dumps(indicators_dict, indent=2)}")
    
    if not indicators_dict:
        print(f"\n❌ PROBLEM: indicators dictionary is EMPTY!")
        print(f"\nFull strategies_agg:")
        print(json.dumps(strategies_agg, indent=2, default=str))
    
    print(f"{'='*100}\n")
    
    return orig_register_from_agg(self, strategies_agg)

DataManager._register_indicators_from_agg = logged_register_from_agg

print(f"\n{'='*100}")
print(f"DEBUGGING INDICATOR REGISTRATION")
print(f"{'='*100}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)

try:
    result = engine.run()
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*100}\n")

# Restore
DataManager._register_indicators_from_agg = orig_register_from_agg
