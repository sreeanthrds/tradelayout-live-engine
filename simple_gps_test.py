#!/usr/bin/env python3
"""
Simple test: Check GPS DURING execution by patching add_position
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.core.gps import GlobalPositionStore

print("\n" + "="*100)
print("SIMPLE GPS TEST: Patch GPS to track all add_position calls")
print("="*100 + "\n")

# Track GPS instances
gps_instances = []
positions_added = []

# Patch GlobalPositionStore.__init__ to track all instances
original_init = GlobalPositionStore.__init__
def patched_init(self):
    original_init(self)
    gps_instances.append(self)
    print(f"🔍 GPS Instance Created: ID={id(self)}")

GlobalPositionStore.__init__ = patched_init

# Patch add_position to track calls
original_add = GlobalPositionStore.add_position
def patched_add(self, position_id, entry_data, tick_time=None):
    print(f"📥 add_position called: GPS_ID={id(self)}, position_id={position_id}")
    positions_added.append({
        'gps_id': id(self),
        'position_id': position_id,
        'entry_data': entry_data
    })
    return original_add(self, position_id, entry_data, tick_time)

GlobalPositionStore.add_position = patched_add

# Run backtest
config = BacktestConfig(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date=datetime(2024, 10, 29)
)

engine = CentralizedBacktestEngine(config)
results = engine.run()

print("\n" + "="*100)
print("GPS TRACKING RESULTS")
print("="*100 + "\n")

print(f"📦 GPS Instances Created: {len(gps_instances)}")
for idx, gps in enumerate(gps_instances, 1):
    print(f"   {idx}. ID={id(gps)}, positions={len(gps.get_all_positions())}")

print(f"\n📥 add_position Calls: {len(positions_added)}")
for idx, call in enumerate(positions_added, 1):
    print(f"   {idx}. GPS_ID={call['gps_id']}, position_id={call['position_id']}")

print(f"\n🔍 Engine's context_adapter GPS ID: {id(engine.context_adapter.gps) if hasattr(engine, 'context_adapter') and hasattr(engine.context_adapter, 'gps') else 'N/A'}")

print(f"\n📊 Results: {len(results.positions)} positions")

# Check if positions were added to a different GPS than the one checked
if positions_added and hasattr(engine, 'context_adapter') and hasattr(engine.context_adapter, 'gps'):
    gps_used_for_add = positions_added[0]['gps_id']
    gps_checked_for_results = id(engine.context_adapter.gps)
    
    if gps_used_for_add != gps_checked_for_results:
        print(f"\n❌ PROBLEM IDENTIFIED:")
        print(f"   Positions added to GPS: {gps_used_for_add}")
        print(f"   Results checked GPS: {gps_checked_for_results}")
        print(f"   → DIFFERENT GPS INSTANCES!")
    else:
        print(f"\n✅ Same GPS used for add and results check")
        # If same GPS, why is it empty?
        checked_gps = engine.context_adapter.gps
        print(f"   But GPS has {len(checked_gps.get_all_positions())} positions at results time")
        print(f"   position_counters: {checked_gps.position_counters}")

print("\n" + "="*100 + "\n")
