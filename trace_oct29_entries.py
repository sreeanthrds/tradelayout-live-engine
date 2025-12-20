#!/usr/bin/env python3
"""
Trace exact timing of entries on Oct 29, 2024
"""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

# Enable detailed logging
os.environ['LOG_LEVEL'] = 'DEBUG'

from src.backtesting.backtest_runner import run_backtest
from src.utils.logger import log_info

print(f"\n{'='*100}")
print(f"TRACING STRATEGY: 5708424d-5962-4629-978c-05b3a174e104 on Oct 29, 2024")
print(f"{'='*100}\n")

# Run with full logging
results = run_backtest(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date='2024-10-29'
)

print(f"\n{'='*100}")
print(f"DETAILED RESULTS")
print(f"{'='*100}\n")

print(f"📊 Results Object:")
print(f"   Type: {type(results)}")
print(f"   Ticks Processed: {results.ticks_processed}")
print(f"   Duration: {results.duration_seconds:.2f}s")
print(f"   Positions Count: {len(results.positions)}")

# Check if results has a GPS or context manager
if hasattr(results, 'gps'):
    print(f"\n📦 GPS Found in Results:")
    gps = results.gps
    all_positions = gps.get_all_positions()
    print(f"   Total GPS Positions: {len(all_positions)}")
    
    for idx, pos in enumerate(all_positions, 1):
        print(f"\n   Position {idx}:")
        print(f"      Position ID: {pos.get('position_id')}")
        print(f"      Entry Time: {pos.get('entry_time')}")
        print(f"      Exit Time: {pos.get('exit_time', 'Still Open')}")
        print(f"      Status: {pos.get('status')}")
        print(f"      PNL: {pos.get('pnl', 0)}")
        print(f"      reEntryNum: {pos.get('reEntryNum', 0)}")
        print(f"      position_num: {pos.get('position_num', 1)}")

if hasattr(results, 'context_manager'):
    print(f"\n🔧 Context Manager Found in Results:")
    cm = results.context_manager
    if hasattr(cm, 'gps'):
        gps = cm.gps
        all_positions = gps.get_all_positions()
        print(f"   Total GPS Positions: {len(all_positions)}")
        
        for idx, pos in enumerate(all_positions, 1):
            print(f"\n   Position {idx}:")
            print(f"      Position ID: {pos.get('position_id')}")
            print(f"      Entry Time: {pos.get('entry_time')}")
            print(f"      Exit Time: {pos.get('exit_time', 'Still Open')}")
            print(f"      Status: {pos.get('status')}")

# Check results attributes
print(f"\n🔍 Results Object Attributes:")
for attr in dir(results):
    if not attr.startswith('_'):
        try:
            value = getattr(results, attr)
            if not callable(value):
                print(f"   {attr}: {type(value).__name__}")
        except:
            pass

print(f"\n{'='*100}\n")
