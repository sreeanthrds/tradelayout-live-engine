#!/usr/bin/env python3
"""
Test script for OLD backtesting engine (v1 backup)
Use this to establish baseline results for comparison with new unified engine

Run: python test_old_backtest_baseline.py
Expected: 9 positions created
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_runner import run_backtest

print("="*80)
print("🧪 BASELINE TEST - Old Backtesting Engine (v1)")
print("="*80)
print()
print("Strategy: 5708424d-5962-4629-978c-05b3a174e104")
print("Date: October 29, 2024")
print("Engine: centralized_backtest_engine_v1_backup.py")
print()
print("="*80)
print()

try:
    # Run backtest with OLD engine
    print("🚀 Running OLD backtesting engine...\n")
    
    # Temporarily swap the engines to use v1 backup
    import src.backtesting.centralized_backtest_engine as current_engine
    import src.backtesting.centralized_backtest_engine_v1_backup as backup_engine
    
    # Swap CentralizedBacktestEngine to use backup version
    original_class = current_engine.CentralizedBacktestEngine
    current_engine.CentralizedBacktestEngine = backup_engine.CentralizedBacktestEngine
    
    results = run_backtest(
        strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
        backtest_date='2024-10-29'
    )
    
    # Restore original
    current_engine.CentralizedBacktestEngine = original_class
    
    print(f"\n{'='*80}")
    print(f"📊 BASELINE RESULTS (OLD ENGINE)")
    print(f"{'='*80}\n")
    
    if results:
        print(f"✅ Backtest completed successfully!")
        print(f"\n⚡ Performance:")
        print(f"   Ticks processed: {results.ticks_processed:,}")
        print(f"   Duration: {results.duration_seconds:.2f}s")
        print(f"   Speed: {results.ticks_per_second:.0f} ticks/sec")
        
        print(f"\n📊 Position Summary:")
        print(f"   Total Positions: {len(results.positions)}")
        print(f"   Signals: {results.signals}")
        
        if len(results.positions) == 9:
            print(f"\n✅ BASELINE VERIFIED: 9 positions created (as expected)")
        else:
            print(f"\n⚠️  WARNING: Expected 9 positions, got {len(results.positions)}")
        
        # Show positions
        if results.positions:
            print(f"\n📝 Position Details:\n")
            for idx, pos in enumerate(results.positions, 1):
                print(f"{idx}. {pos}")
                print()
        else:
            print("\n   No positions created")
        
        print(f"\n📁 Results saved to: backtest_dashboard_data.json")
        print(f"\n✅ Use this as baseline to compare with new unified engine")
        
    else:
        print("❌ Backtest failed - no results returned")
        
except Exception as e:
    print(f"\n❌ Error during backtest: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}\n")
