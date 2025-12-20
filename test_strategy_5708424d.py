#!/usr/bin/env python3
"""
Test Strategy 5708424d-5962-4629-978c-05b3a174e104
Validates all indicators are loading and evaluating correctly
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_runner import run_backtest

print(f"\n{'='*100}")
print(f"TESTING STRATEGY: 5708424d-5962-4629-978c-05b3a174e104")
print(f"Date: October 29, 2024")
print(f"{'='*100}\n")

try:
    # Run backtest
    print("🚀 Running backtest...\n")
    results = run_backtest(
        strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
        backtest_date='2024-10-29'
    )
    
    print(f"\n{'='*100}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*100}\n")
    
    if results:
        print(f"✅ Backtest completed successfully!")
        print(f"\n⚡ Performance:")
        print(f"   Ticks processed: {results.ticks_processed:,}")
        print(f"   Duration: {results.duration_seconds:.2f}s")
        print(f"   Speed: {results.ticks_per_second:.0f} ticks/sec")
        
        print(f"\n📊 Position Summary:")
        print(f"   Total Positions: {len(results.positions)}")
        print(f"   Signals: {results.signals}")
        
        # Show positions
        if results.positions:
            print(f"\n📝 Position Details:\n")
            for idx, pos in enumerate(results.positions, 1):
                print(f"{idx}. {pos}")
                print()
        else:
            print("\n   No positions created")
        
    else:
        print("❌ Backtest failed - no results returned")
        
except Exception as e:
    print(f"\n❌ Error during backtest: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*100}\n")
