#!/usr/bin/env python3
"""
Debug indicator strategy - check RSI values and condition evaluations
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from datetime import date
from src.core.gps import GlobalPositionStore
import json

STRATEGY_ID = '64c2c932-0e0b-462a-9a36-7cda4371d102'

# Track positions
positions_tracked = []

orig_add = GlobalPositionStore.add_position
orig_close = GlobalPositionStore.close_position

def track_add(self, pos_id, entry_data, tick_time=None):
    """Track position entry"""
    symbol = entry_data.get('symbol', 'N/A')
    side = entry_data.get('side', 'BUY')
    
    print(f"\n{'='*80}")
    print(f"🎯 POSITION OPENED!")
    print(f"{'='*80}")
    print(f"Position ID: {pos_id}")
    print(f"Symbol: {symbol}")
    print(f"Side: {side}")
    print(f"Entry Price: ₹{entry_data.get('entry_price', 0):.2f}")
    print(f"Quantity: {entry_data.get('quantity', 0)}")
    print(f"Time: {entry_data.get('entry_time', 'N/A')}")
    
    # Get NIFTY spot
    ltp_store = entry_data.get('ltp_store', {})
    nifty_spot = 0
    if 'NIFTY' in ltp_store:
        nifty_data = ltp_store['NIFTY']
        if isinstance(nifty_data, dict):
            nifty_spot = nifty_data.get('ltp', 0)
        else:
            nifty_spot = nifty_data
    print(f"NIFTY Spot @ Entry: ₹{nifty_spot:.2f}")
    print(f"{'='*80}\n")
    
    positions_tracked.append({
        'position_id': pos_id,
        'symbol': symbol,
        'side': side,
        'entry_price': entry_data.get('entry_price', 0),
        'quantity': entry_data.get('quantity', 0),
        'nifty_spot_at_entry': nifty_spot,
        'entry_time': str(entry_data.get('entry_time', 'N/A')),
        'status': 'OPEN'
    })
    
    return orig_add(self, pos_id, entry_data, tick_time)

def track_close(self, pos_id, exit_data, tick_time=None):
    """Track position exit"""
    for pos in positions_tracked:
        if pos['position_id'] == pos_id and pos['status'] == 'OPEN':
            exit_price = exit_data.get('price', 0)
            entry_price = pos['entry_price']
            quantity = pos['quantity']
            side = pos['side']
            
            # Calculate P&L (SELL PE: profit when price decreases)
            if side.upper() == 'SELL':
                pnl = (entry_price - exit_price) * quantity
            else:
                pnl = (exit_price - entry_price) * quantity
            
            print(f"\n{'='*80}")
            print(f"🏁 POSITION CLOSED!")
            print(f"{'='*80}")
            print(f"Position ID: {pos_id}")
            print(f"Symbol: {pos['symbol']}")
            print(f"Side: {side}")
            print(f"Entry Price: ₹{entry_price:.2f}")
            print(f"Exit Price: ₹{exit_price:.2f}")
            print(f"P&L: ₹{pnl:.2f}")
            print(f"Exit Reason: {exit_data.get('reason', 'N/A')}")
            print(f"Exit Time: {exit_data.get('exit_time', 'N/A')}")
            print(f"{'='*80}\n")
            
            pos['status'] = 'CLOSED'
            pos['exit_price'] = exit_price
            pos['pnl'] = pnl
            pos['exit_time'] = str(exit_data.get('exit_time', 'N/A'))
            break
    
    return orig_close(self, pos_id, exit_data, tick_time)

GlobalPositionStore.add_position = track_add
GlobalPositionStore.close_position = track_close

print(f"\n{'='*80}")
print(f"TESTING INDICATOR STRATEGY WITH SELL PE")
print(f"{'='*80}")
print(f"Strategy: My New Strategy 6")
print(f"ID: {STRATEGY_ID}")
print(f"Date: 2024-10-01")
print(f"\nEntry Conditions:")
print(f"  1. RSI(14) > 70")
print(f"  2. Underlying LTP < Low of previous candle")
print(f"\nEntry Order:")
print(f"  Side: SELL PE (ATM, W1)")
print(f"{'='*80}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

print(f"\n{'='*80}")
print(f"BACKTEST SUMMARY")
print(f"{'='*80}")
print(f"Total Positions Opened: {len(positions_tracked)}")

if positions_tracked:
    closed = [p for p in positions_tracked if p['status'] == 'CLOSED']
    open_pos = [p for p in positions_tracked if p['status'] == 'OPEN']
    total_pnl = sum(p.get('pnl', 0) for p in closed)
    
    print(f"Closed Positions: {len(closed)}")
    print(f"Open Positions: {len(open_pos)}")
    print(f"Total P&L: ₹{total_pnl:.2f}")
    
    print(f"\n{'='*80}")
    print(f"POSITION DETAILS")
    print(f"{'='*80}")
    
    for i, pos in enumerate(positions_tracked, 1):
        print(f"\n{i}. Position: {pos['position_id']}")
        print(f"   Symbol: {pos['symbol']}")
        print(f"   Side: {pos['side']}")
        print(f"   Entry: ₹{pos['entry_price']:.2f} @ {pos['entry_time']}")
        print(f"   NIFTY Spot @ Entry: ₹{pos['nifty_spot_at_entry']:.2f}")
        if pos['status'] == 'CLOSED':
            print(f"   Exit: ₹{pos['exit_price']:.2f} @ {pos.get('exit_time', 'N/A')}")
            print(f"   P&L: ₹{pos['pnl']:.2f}")
        else:
            print(f"   Status: OPEN")
else:
    print(f"\n❌ NO TRADES TAKEN")
    print(f"\nPossible reasons:")
    print(f"  1. RSI(14) never went above 70 on Oct 1st")
    print(f"  2. When RSI > 70, the LTP wasn't below previous candle low")
    print(f"  3. Condition timing issue")

print(f"\n{'='*80}\n")

# Restore
GlobalPositionStore.add_position = orig_add
GlobalPositionStore.close_position = orig_close
