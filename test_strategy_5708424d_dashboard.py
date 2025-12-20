#!/usr/bin/env python3
"""
Test Strategy 5708424d-5962-4629-978c-05b3a174e104
Shows dashboard data with full position details
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import date
from src.backtesting.backtest_runner import run_backtest
from src.core.global_position_store import GlobalPositionStore
import json

print(f"\n{'='*100}")
print(f"TESTING STRATEGY: 5708424d-5962-4629-978c-05b3a174e104")
print(f"Date: October 1, 2024")
print(f"{'='*100}\n")

try:
    # Run backtest
    print("🚀 Running backtest...\n")
    results = run_backtest(
        strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
        backtest_date='2024-10-01'
    )
    
    print(f"\n{'='*100}")
    print(f"📊 DASHBOARD DATA")
    print(f"{'='*100}\n")
    
    # Get all positions from GPS
    all_positions = GlobalPositionStore.get_all_positions()
    
    print(f"{'='*100}")
    print(f"📝 ALL POSITIONS")
    print(f"{'='*100}\n")
    
    if all_positions:
        for idx, pos in enumerate(all_positions, 1):
            print(f"{idx}. ✅ Position {pos.position_id}")
            print(f"   Contract: {pos.instrument}:{pos.expiry}:OPT:{pos.strike}:{pos.option_type}")
            print(f"   Strike: {pos.strike} {pos.option_type}")
            print(f"   Entry Node: {pos.entry_node_id} @ {pos.entry_time}")
            print(f"   Entry Price: ₹{pos.entry_price:.2f}")
            print(f"   Quantity: {pos.quantity}")
            
            if pos.exit_time:
                print(f"   Exit Node: {pos.exit_node_id} @ {pos.exit_time}")
                print(f"   Exit Price: ₹{pos.exit_price:.2f}")
                
                pnl = (pos.exit_price - pos.entry_price) * pos.quantity
                pnl_pct = ((pos.exit_price - pos.entry_price) / pos.entry_price) * 100
                pnl_emoji = '🟢' if pnl >= 0 else '🔴'
                
                duration_minutes = (pos.exit_time - pos.entry_time).total_seconds() / 60
                print(f"   Duration: {duration_minutes:.1f} minutes")
                print(f"   P&L: {pnl_emoji} ₹{pnl:.2f} ({pnl_pct:.2f}%)")
                print(f"   Exit Reason: {pos.exit_reason}")
            else:
                print(f"   Status: OPEN")
            
            print()
        
        # Summary statistics
        print(f"\n{'='*100}")
        print(f"📊 SUMMARY STATISTICS")
        print(f"{'='*100}\n")
        
        total_positions = len(all_positions)
        closed_positions = sum(1 for p in all_positions if p.exit_time)
        open_positions = total_positions - closed_positions
        
        print(f"Total Positions: {total_positions}")
        print(f"  Closed: {closed_positions}")
        print(f"  Open: {open_positions}")
        
        if closed_positions > 0:
            total_pnl = sum((p.exit_price - p.entry_price) * p.quantity for p in all_positions if p.exit_time)
            winning_trades = sum(1 for p in all_positions if p.exit_time and p.exit_price > p.entry_price)
            losing_trades = sum(1 for p in all_positions if p.exit_time and p.exit_price < p.entry_price)
            breakeven_trades = closed_positions - winning_trades - losing_trades
            
            pnl_emoji = '🟢' if total_pnl >= 0 else '🔴'
            
            print(f"\nP&L Summary:")
            print(f"  Total P&L: {pnl_emoji} ₹{total_pnl:.2f}")
            print(f"\nTrade Statistics:")
            print(f"  Winning Trades: {winning_trades}")
            print(f"  Losing Trades: {losing_trades}")
            print(f"  Breakeven Trades: {breakeven_trades}")
            
            if closed_positions > 0:
                win_rate = (winning_trades / closed_positions) * 100
                print(f"  Win Rate: {win_rate:.2f}%")
    
    else:
        print("No positions found")
    
    print(f"\n{'='*100}\n")
    
except Exception as e:
    print(f"\n❌ Error during backtest: {e}")
    import traceback
    traceback.print_exc()
