#!/usr/bin/env python3
"""
Debug why entry at 09:18 on Oct 1st is not being captured
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
from strategy.nodes.entry_signal_node import EntrySignalNode

STRATEGY_ID = '64c2c932-0e0b-462a-9a36-7cda4371d102'

# Track positions with ALL details
positions_tracked = []

orig_add = GlobalPositionStore.add_position
orig_close = GlobalPositionStore.close_position

# Monkey patch EntrySignalNode to see condition evaluations
orig_entry_execute = EntrySignalNode._execute_node_logic

def debug_entry_execute(self, context):
    """Debug entry signal condition evaluation"""
    current_time = context.get('current_time', 'Unknown')
    
    # Only log around 09:18
    if '09:1' in str(current_time):
        cache = context.get('cache', {})
        
        # Get candle data
        candles = cache.get('NIFTY:1m', [])
        if candles:
            last_candle = candles[-1] if len(candles) > 0 else {}
            
            # Get RSI indicator value
            indicators = last_candle.get('indicators', {})
            rsi_value = indicators.get('rsi_1764539168968', None)
            
            # Get underlying LTP
            ltp_store = context.get('ltp_store', {})
            nifty_ltp = 0
            if 'NIFTY' in ltp_store:
                nifty_data = ltp_store['NIFTY']
                if isinstance(nifty_data, dict):
                    nifty_ltp = nifty_data.get('ltp', 0)
                else:
                    nifty_ltp = nifty_data
            
            # Get previous candle low
            prev_low = candles[-2].get('low', 0) if len(candles) >= 2 else 0
            
            print(f"\n⏰ Time: {current_time}")
            print(f"   RSI(14): {rsi_value}")
            print(f"   NIFTY LTP: {nifty_ltp:.2f}")
            print(f"   Previous Candle Low: {prev_low:.2f}")
            print(f"   Condition 1 (RSI > 70): {rsi_value > 70 if rsi_value else False}")
            print(f"   Condition 2 (LTP < Prev Low): {nifty_ltp < prev_low if prev_low > 0 else False}")
            print(f"   Total Candles: {len(candles)}")
    
    # Call original
    return orig_entry_execute(self, context)

EntrySignalNode._execute_node_logic = debug_entry_execute

def track_add(self, pos_id, entry_data, tick_time=None):
    """Track position entry"""
    symbol = entry_data.get('symbol', 'N/A')
    side = entry_data.get('side', 'BUY')
    entry_price = entry_data.get('entry_price', 0)
    quantity = entry_data.get('quantity', 0)
    entry_time = entry_data.get('entry_time', 'N/A')
    
    # Get NIFTY spot
    ltp_store = entry_data.get('ltp_store', {})
    nifty_spot = 0
    if 'NIFTY' in ltp_store:
        nifty_data = ltp_store['NIFTY']
        if isinstance(nifty_data, dict):
            nifty_spot = nifty_data.get('ltp', 0)
        else:
            nifty_spot = nifty_data
    
    # Extract strike and option type
    strike, opt_type, expiry = 'N/A', 'N/A', 'N/A'
    if ':OPT:' in symbol:
        parts = symbol.split(':')
        if len(parts) >= 5:
            expiry = parts[1]
            strike = parts[3]
            opt_type = parts[4]
    
    print(f"\n{'='*100}")
    print(f"🎯 POSITION OPENED AT {entry_time}")
    print(f"{'='*100}")
    print(f"Position ID: {pos_id}")
    print(f"Symbol: {symbol}")
    print(f"Strike: {strike} {opt_type}")
    print(f"Side: {side} {'← SELL ORDER!' if side == 'SELL' else ''}")
    print(f"Entry Price: ₹{entry_price:.2f}")
    print(f"Quantity: {quantity}")
    print(f"NIFTY Spot @ Entry: ₹{nifty_spot:.2f}")
    print(f"{'='*100}\n")
    
    positions_tracked.append({
        'position_id': pos_id,
        'symbol': symbol,
        'strike': strike,
        'option_type': opt_type,
        'side': side,
        'entry_price': entry_price,
        'quantity': quantity,
        'nifty_spot_at_entry': nifty_spot,
        'entry_time': str(entry_time),
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
            
            # Calculate P&L (SELL: profit when price decreases)
            if side.upper() == 'SELL':
                pnl = (entry_price - exit_price) * quantity
            else:
                pnl = (exit_price - entry_price) * quantity
            
            # Get NIFTY spot at exit
            nifty_spot_exit = exit_data.get('nifty_spot', 0)
            
            print(f"\n{'='*100}")
            print(f"🏁 POSITION CLOSED")
            print(f"{'='*100}")
            print(f"Position ID: {pos_id}")
            print(f"Symbol: {pos['symbol']}")
            print(f"Strike: {pos['strike']} {pos['option_type']}")
            print(f"Side: {side}")
            print(f"Entry Price: ₹{entry_price:.2f} (NIFTY: ₹{pos['nifty_spot_at_entry']:.2f})")
            print(f"Exit Price: ₹{exit_price:.2f} (NIFTY: ₹{nifty_spot_exit:.2f})")
            print(f"P&L: ₹{pnl:.2f}")
            print(f"Exit Reason: {exit_data.get('reason', 'N/A')}")
            print(f"Exit Time: {exit_data.get('exit_time', 'N/A')}")
            print(f"{'='*100}\n")
            
            pos['status'] = 'CLOSED'
            pos['exit_price'] = exit_price
            pos['nifty_spot_at_exit'] = nifty_spot_exit
            pos['pnl'] = pnl
            pos['exit_time'] = str(exit_data.get('exit_time', 'N/A'))
            pos['exit_reason'] = exit_data.get('reason', 'N/A')
            break
    
    return orig_close(self, pos_id, exit_data, tick_time)

GlobalPositionStore.add_position = track_add
GlobalPositionStore.close_position = track_close

print(f"\n{'='*100}")
print(f"DEBUGGING ENTRY AT 09:18 ON OCT 1ST 2024")
print(f"{'='*100}")
print(f"Strategy: My New Strategy 6 (ID: {STRATEGY_ID})")
print(f"Expected Entry: 09:18 candle")
print(f"\nEntry Conditions:")
print(f"  1. RSI(14, close, offset=-1) > 70")
print(f"  2. underlying_ltp < Low[offset=-1]")
print(f"\nEntry Order:")
print(f"  Side: SELL")
print(f"  Option: PE ATM W1")
print(f"{'='*100}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

print(f"\n{'='*100}")
print(f"FINAL SUMMARY")
print(f"{'='*100}")
print(f"Total Positions: {len(positions_tracked)}")

if positions_tracked:
    print(f"\n📊 POSITION DETAILS WITH UNDERLYING PRICES:")
    print(f"\n{'#':<3} {'Pos ID':<16} {'Symbol':<40} {'Strike':<7} {'Side':<5} {'Entry':<9} {'NIFTY@E':<10} {'Exit':<9} {'NIFTY@X':<10} {'P&L ₹':<10} {'Reason':<20}")
    print(f"{'-'*100}")
    
    for i, pos in enumerate(positions_tracked, 1):
        entry_time = pos['entry_time'].split('T')[1] if 'T' in pos['entry_time'] else pos['entry_time']
        exit_time = pos.get('exit_time', 'N/A').split('T')[1] if 'T' in pos.get('exit_time', 'N/A') else 'N/A'
        
        print(f"{i:<3} {pos['position_id']:<16} {pos['symbol']:<40} {pos['strike']:<7} {pos['side']:<5} {entry_time:<9} {pos['nifty_spot_at_entry']:>9.2f} {exit_time:<9} {pos.get('nifty_spot_at_exit', 0):>9.2f} {pos.get('pnl', 0):>9.2f} {pos.get('exit_reason', 'N/A'):<20}")
    
    closed = [p for p in positions_tracked if p['status'] == 'CLOSED']
    total_pnl = sum(p.get('pnl', 0) for p in closed)
    
    print(f"\n{'='*100}")
    print(f"Summary:")
    print(f"  Total P&L: ₹{total_pnl:.2f}")
    print(f"  Closed: {len(closed)}/{len(positions_tracked)}")
else:
    print(f"\n❌ NO POSITIONS FOUND")
    print(f"\nThis means either:")
    print(f"  1. Entry conditions were not met")
    print(f"  2. There's a bug in condition evaluation")
    print(f"  3. Indicator calculation is incorrect")

print(f"\n{'='*100}\n")

# Restore
GlobalPositionStore.add_position = orig_add
GlobalPositionStore.close_position = orig_close
EntrySignalNode._execute_node_logic = orig_entry_execute
