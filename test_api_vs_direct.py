"""
Direct comparison: API path vs Direct script path
"""
from datetime import date
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine

print("=" * 80)
print("TESTING: Direct Script Execution (Same as API)")
print("=" * 80)

# Use EXACT same parameters as API
strategy_id = "5708424d-5962-4629-978c-05b3a174e104"
backtest_date = date(2024, 10, 29)
strategy_scale = 2.0

print(f"\nStrategy ID: {strategy_id}")
print(f"Date: {backtest_date}")
print(f"Strategy Scale: {strategy_scale}")
print("\n" + "=" * 80)

# Create config exactly like API does
config = BacktestConfig(
    strategy_ids=[strategy_id],
    backtest_date=backtest_date,
    debug_mode=None,
    strategy_scale=strategy_scale
)

print("\n🚀 Running backtest...")
print("=" * 80)

# Run backtest
engine = CentralizedBacktestEngine(config)
engine.run()

print("\n" + "=" * 80)
print("✅ Backtest Complete")
print("=" * 80)

# Check results
print("\n📊 Checking GPS for positions...")
if hasattr(engine, 'gps'):
    all_positions = engine.gps.get_all_positions()
    print(f"   Total positions in GPS: {len(all_positions)}")
    
    if len(all_positions) > 0:
        print(f"\n   First position:")
        first_pos = list(all_positions.values())[0]
        print(f"      Position ID: {first_pos.get('position_id')}")
        print(f"      Quantity: {first_pos.get('quantity')} lots")
        print(f"      Actual Quantity: {first_pos.get('actual_quantity')} shares")
        print(f"      Multiplier: {first_pos.get('multiplier')}")
        print(f"      Status: {first_pos.get('status')}")
    else:
        print("   ⚠️ NO POSITIONS FOUND!")
else:
    print("   ⚠️ GPS not found in engine!")

print("\n" + "=" * 80)
