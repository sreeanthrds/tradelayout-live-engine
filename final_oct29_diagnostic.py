#!/usr/bin/env python3
"""
FINAL DIAGNOSTIC: Oct 29, 2024 - Strategy 5708424d
Check GPS state and verify positions are being properly stored/retrieved
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

import json
from datetime import datetime
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine

print(f"\n{'='*100}")
print(f"FINAL DIAGNOSTIC: Strategy 5708424d-5962-4629-978c-05b3a174e104")
print(f"Date: October 29, 2024")
print(f"Focus: GPS state and position retrieval")
print(f"{'='*100}\n")

# Create config
config = BacktestConfig(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date=datetime(2024, 10, 29)
)

# Create engine
engine = CentralizedBacktestEngine(config)

# Run backtest
print("🚀 Running backtest...\n")
results = engine.run()

print(f"\n{'='*100}")
print(f"POST-BACKTEST DIAGNOSTICS")
print(f"{'='*100}\n")

# Check GPS instances
print(f"🔍 Checking GPS Instances:")
print(f"   Engine has context_adapter: {hasattr(engine, 'context_adapter')}")

if hasattr(engine, 'context_adapter'):
    context_adapter = engine.context_adapter
    print(f"   Context adapter has GPS: {hasattr(context_adapter, 'gps')}")
    
    if hasattr(context_adapter, 'gps'):
        gps = context_adapter.gps
        all_positions = gps.get_all_positions()
        
        print(f"\n📦 GPS from context_adapter:")
        print(f"   GPS ID: {id(gps)}")
        print(f"   Total positions: {len(all_positions)}")
        print(f"   Position counters: {gps.position_counters}")
        print(f"   Open positions: {len([p for p in all_positions if p.get('status') == 'open'])}")
        
        if all_positions:
            print(f"\n   Positions found:")
            for idx, pos in enumerate(all_positions, 1):
                print(f"      {idx}. ID={pos.get('position_id')}, "
                      f"Entry={pos.get('entry_time')}, "
                      f"Exit={pos.get('exit_time', 'N/A')}, "
                      f"Status={pos.get('status')}")
                
                # Show condition text if available
                diagnostic_data = pos.get('diagnostic_data', {})
                conditions = diagnostic_data.get('conditions_evaluated', [])
                if conditions:
                    print(f"         Entry Conditions:")
                    for cond in conditions[:2]:  # First 2 conditions
                        text = cond.get('condition_text', 'No text')
                        print(f"         - {text}")

# Check results manager GPS
print(f"\n🔍 Checking Results Manager:")
if hasattr(engine, 'results_manager'):
    rm = engine.results_manager
    print(f"   Results Manager GPS ID: {id(rm.gps)}")
    print(f"   Same GPS as context_adapter: {id(rm.gps) == id(context_adapter.gps) if hasattr(engine, 'context_adapter') and hasattr(context_adapter, 'gps') else 'N/A'}")
    
    rm_positions = rm.gps.get_all_positions()
    print(f"   Positions from results_manager.gps: {len(rm_positions)}")

# Check results object
print(f"\n📊 Results Object:")
print(f"   Positions in results: {len(results.positions)}")
print(f"   Signals: {results.signals}")
print(f"   Ticks processed: {results.ticks_processed}")

if len(results.positions) == 0 and hasattr(engine, 'context_adapter') and hasattr(engine.context_adapter, 'gps'):
    print(f"\n❌ ISSUE IDENTIFIED:")
    print(f"   GPS has {len(all_positions)} positions")
    print(f"   Results has {len(results.positions)} positions")
    print(f"   → Positions are NOT being transferred to results!")
    
    # Try calling generate_results manually to see what happens
    print(f"\n🔧 Manual results generation test:")
    if hasattr(engine, 'results_manager'):
        manual_results = engine.results_manager.generate_results(
            ticks_processed=results.ticks_processed,
            duration_seconds=results.duration_seconds
        )
        print(f"   Manual generation → {len(manual_results.positions)} positions")
        
        if len(manual_results.positions) > 0:
            print(f"   ✅ Manual generation works - issue is in timing/flow")
        else:
            print(f"   ❌ Manual generation also returns 0 - GPS is empty at results time")

print(f"\n{'='*100}\n")
