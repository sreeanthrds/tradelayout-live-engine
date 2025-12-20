#!/usr/bin/env python3
"""
Test Live Simulation Mode - Unified Execution Engine
Tests the engine in live simulation mode with 500x speed

Run: python test_live_simulation_mode.py
Expected: Same 9 positions as backtest, but with speed control (slower)
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
import asyncio
import time

print("="*80)
print("🎮 LIVE SIMULATION MODE TEST - Unified Execution Engine")
print("="*80)
print()
print("Strategy: 5708424d-5962-4629-978c-05b3a174e104")
print("Date: October 29, 2024")
print("Mode: live_simulation")
print("Speed: 500x (should be noticeably slower than backtest)")
print()
print("="*80)
print()

try:
    # Create config
    config = BacktestConfig(
        strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
        backtest_date=datetime(2024, 10, 29)
    )
    
    # Create engine in LIVE SIMULATION mode with 500x speed
    print("🚀 Creating engine in LIVE SIMULATION mode (speed=500x)...\n")
    engine = CentralizedBacktestEngine(
        config,
        mode="live_simulation",
        speed_multiplier=500
    )
    
    # Run (async) and time it
    start = time.time()
    
    # Run async engine
    results = asyncio.run(engine.run())
    
    end = time.time()
    duration = end - start
    
    print(f"\n{'='*80}")
    print(f"📊 LIVE SIMULATION RESULTS")
    print(f"{'='*80}\n")
    
    if results:
        print(f"✅ Live simulation completed!")
        print(f"\n⚡ Performance:")
        print(f"   Ticks processed: {results.ticks_processed:,}")
        print(f"   Real duration: {duration:.2f}s (with speed control)")
        print(f"   Reported duration: {results.duration_seconds:.2f}s")
        print(f"   Effective speed: {results.ticks_per_second:.0f} ticks/sec")
        
        print(f"\n📊 Position Summary:")
        print(f"   Total Positions: {len(results.positions)}")
        
        # Load from output file to verify
        import json
        data = json.load(open('backtest_dashboard_data.json'))
        actual_positions = len(data.get('positions', []))
        
        print(f"   Verified in file: {actual_positions} positions")
        
        if actual_positions == 9:
            print(f"\n✅ SUCCESS: Live simulation created 9 positions (matches backtest!)")
        else:
            print(f"\n⚠️  WARNING: Expected 9 positions, got {actual_positions}")
        
        print(f"\n📈 Speed Comparison:")
        print(f"   Backtest mode: ~4,900 ticks/sec (no speed control)")
        print(f"   Live sim mode: ~{results.ticks_per_second:.0f} ticks/sec (with speed control)")
        print(f"   Speed control working: {'✅ YES' if results.ticks_per_second < 3000 else '❌ NO'}")
        
    else:
        print("❌ Live simulation failed - no results returned")
        
except Exception as e:
    print(f"\n❌ Error during live simulation: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}\n")
