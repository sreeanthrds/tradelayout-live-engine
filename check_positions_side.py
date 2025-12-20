"""
Quick script to check position sides and P&L calculations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from datetime import datetime

# Initialize backtest
config = BacktestConfig(
    strategy_id='5708424d-5962-4629-978c-05b3a174e104',
    backtest_date=datetime(2024, 10, 29),
    mode='backtesting'
)

engine = BacktestEngine(config)

# Run backtest
print("Running backtest...")
results = engine.run()

# Check positions
print("\n" + "="*80)
print("POSITION DETAILS WITH SIDE")
print("="*80)

positions = engine.position_manager.get_all_positions()

for i, pos in enumerate(positions, 1):
    print(f"\nPosition {i}:")
    print(f"  Symbol: {pos.get('symbol')}")
    print(f"  Side: {pos.get('side')}")  # <-- This is what we need!
    print(f"  Entry Price: ₹{pos.get('entry_price', 0):.2f}")
    print(f"  Exit Price: ₹{pos.get('exit_price', 0):.2f}")
    print(f"  P&L: ₹{pos.get('pnl', 0):.2f}")
    print(f"  Entry Time: {pos.get('entry_timestamp')}")
    print(f"  Exit Time: {pos.get('exit_timestamp')}")
    
    # Manual P&L calculation
    side = pos.get('side', 'BUY').upper()
    entry = pos.get('entry_price', 0)
    exit_price = pos.get('exit_price', 0)
    
    if side == 'BUY':
        manual_pnl = exit_price - entry
        print(f"  Manual P&L (BUY): {exit_price} - {entry} = ₹{manual_pnl:.2f}")
    else:  # SELL
        manual_pnl = entry - exit_price
        print(f"  Manual P&L (SELL): {entry} - {exit_price} = ₹{manual_pnl:.2f}")

print("\n" + "="*80)
