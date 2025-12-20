#!/usr/bin/env python3
"""
Capture RSI values and trade entries for Oct 1st 2024
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

STRATEGY_ID = '64c2c932-0e0b-462a-9a36-7cda4371d102'

# Track RSI values
rsi_log = []

# Track positions
positions_tracked = []

orig_add = GlobalPositionStore.add_position
orig_close = GlobalPositionStore.close_position

# Monkey patch tick processor to log RSI
from src.backtesting.tick_processor import TickProcessor
orig_tick_process = TickProcessor.process_tick

def logged_process_tick(self, tick, context):
    """Log RSI values during tick processing"""
    result = orig_tick_process(self, tick, context)
    
    # Get time
    current_time = str(context.get('current_time', 'Unknown'))
    
    # Only log 09:15 to 09:25
    if '09:1' in current_time or '09:2' in current_time:
        cache = context.get('cache', {})
        candles = cache.get('NIFTY:1m', [])
        
        if candles and len(candles) >= 2:
            last_candle = candles[-1]
            prev_candle = candles[-2]
            
            indicators = last_candle.get('indicators', {})
            rsi_current = indicators.get('rsi_1764539168968', None)
            
            prev_indicators = prev_candle.get('indicators', {})
            rsi_prev = prev_indicators.get('rsi_1764539168968', None)
            
            ltp_store = context.get('ltp_store', {})
            nifty_ltp = 0
            if 'NIFTY' in ltp_store:
                nifty_data = ltp_store['NIFTY']
                if isinstance(nifty_data, dict):
                    nifty_ltp = nifty_data.get('ltp', 0)
                else:
                    nifty_ltp = nifty_data
            
            prev_low = prev_candle.get('low', 0)
            
            rsi_log.append({
                'time': current_time,
                'rsi_current': rsi_current,
                'rsi_prev': rsi_prev,
                'nifty_ltp': nifty_ltp,
                'prev_low': prev_low,
                'condition1': rsi_prev > 70 if rsi_prev else False,
                'condition2': nifty_ltp < prev_low if prev_low > 0 else False
            })
    
    return result

TickProcessor.process_tick = logged_process_tick

def track_add(self, pos_id, entry_data, tick_time=None):
    """Track position entry"""
    symbol = entry_data.get('symbol', 'N/A')
    side = entry_data.get('side', 'BUY')
    entry_price = entry_data.get('entry_price', 0)
    quantity = entry_data.get('quantity', 0)
    entry_time = entry_data.get('entry_time', 'N/A')
    
    ltp_store = entry_data.get('ltp_store', {})
    nifty_spot = 0
    if 'NIFTY' in ltp_store:
        nifty_data = ltp_store['NIFTY']
        if isinstance(nifty_data, dict):
            nifty_spot = nifty_data.get('ltp', 0)
        else:
            nifty_spot = nifty_data
    
    strike, opt_type, expiry = 'N/A', 'N/A', 'N/A'
    if ':OPT:' in symbol:
        parts = symbol.split(':')
        if len(parts) >= 5:
            expiry = parts[1]
            strike = parts[3]
            opt_type = parts[4]
    
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
            
            if side.upper() == 'SELL':
                pnl = (entry_price - exit_price) * quantity
            else:
                pnl = (exit_price - entry_price) * quantity
            
            nifty_spot_exit = exit_data.get('nifty_spot', 0)
            
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
print(f"TESTING INDICATOR STRATEGY - OCT 1ST 2024")
print(f"{'='*100}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

# Show RSI log
print(f"\n{'='*100}")
print(f"RSI VALUES AND CONDITIONS (09:15 - 09:25)")
print(f"{'='*100}\n")

if rsi_log:
    print(f"{'Time':<12} {'RSI(prev)':<12} {'RSI(curr)':<12} {'NIFTY LTP':<12} {'Prev Low':<12} {'C1:RSI>70':<12} {'C2:LTP<Low':<12}")
    print(f"{'-'*100}")
    
    for log in rsi_log:
        c1 = '✅' if log['condition1'] else '❌'
        c2 = '✅' if log['condition2'] else '❌'
        print(f"{log['time']:<12} {log['rsi_prev']:<12.2f} {log['rsi_current']:<12.2f} {log['nifty_ltp']:<12.2f} {log['prev_low']:<12.2f} {c1:<12} {c2:<12}")

# Show positions
print(f"\n{'='*100}")
print(f"POSITIONS")
print(f"{'='*100}\n")

if positions_tracked:
    print(f"Total Positions: {len(positions_tracked)}\n")
    
    for i, pos in enumerate(positions_tracked, 1):
        entry_time = pos['entry_time'].split('T')[1] if 'T' in pos['entry_time'] else pos['entry_time']
        print(f"{i}. {pos['position_id']}")
        print(f"   Symbol: {pos['symbol']}")
        print(f"   Strike: {pos['strike']} {pos['option_type']}")
        print(f"   Side: {pos['side']}")
        print(f"   Entry: ₹{pos['entry_price']:.2f} @ {entry_time} (NIFTY: ₹{pos['nifty_spot_at_entry']:.2f})")
        if pos['status'] == 'CLOSED':
            exit_time = pos['exit_time'].split('T')[1] if 'T' in pos['exit_time'] else pos['exit_time']
            print(f"   Exit: ₹{pos['exit_price']:.2f} @ {exit_time} (NIFTY: ₹{pos.get('nifty_spot_at_exit', 0):.2f})")
            print(f"   P&L: ₹{pos['pnl']:.2f}")
        print()
else:
    print(f"❌ NO POSITIONS TAKEN\n")

print(f"{'='*100}\n")

# Restore
GlobalPositionStore.add_position = orig_add
GlobalPositionStore.close_position = orig_close
TickProcessor.process_tick = orig_tick_process
