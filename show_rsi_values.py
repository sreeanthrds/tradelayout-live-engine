#!/usr/bin/env python3
"""
Show RSI values for first 10 minutes of Oct 1st
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from datetime import date

STRATEGY_ID = '64c2c932-0e0b-462a-9a36-7cda4371d102'

# Capture candle data
rsi_data = []

# Monkey patch data manager to capture RSI values
from src.backtesting.data_manager import DataManager
orig_add_to_buffer = DataManager._add_to_candle_buffer

def logged_add_to_buffer(self, symbol, timeframe, candle):
    """Capture RSI values as candles complete"""
    result = orig_add_to_buffer(self, symbol, timeframe, candle)
    
    # Get the candle that was just added
    buffer = self.cache.get_candles(symbol, timeframe, count=20)
    if buffer and len(buffer) > 0:
        # Get the last completed candle (not the forming one)
        for candle_data in reversed(buffer):
            if 'indicators' in candle_data:
                timestamp = str(candle_data.get('timestamp', ''))
                if '09:' in timestamp or '10:' in timestamp:  # First hour
                    rsi_data.append({
                        'timestamp': timestamp,
                        'open': candle_data.get('open', 0),
                        'high': candle_data.get('high', 0),
                        'low': candle_data.get('low', 0),
                        'close': candle_data.get('close', 0),
                        'rsi': candle_data['indicators'].get('rsi(14,close)', None)
                    })
                break
    
    return result

DataManager._add_to_candle_buffer = logged_add_to_buffer

print(f"\n{'='*100}")
print(f"RSI VALUES - FIRST HOUR OF OCT 1ST 2024")
print(f"{'='*100}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

print(f"\n{'='*100}")
print(f"RSI VALUES (First Hour)")
print(f"{'='*100}\n")

if rsi_data:
    print(f"{'Candle Time':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'RSI(14)':<10} {'>70?':<8}")
    print(f"{'-'*100}")
    
    for data in rsi_data:
        rsi_val = data['rsi']
        rsi_check = '✅ YES' if rsi_val and rsi_val > 70 else '❌ No'
        rsi_str = f"{rsi_val:.2f}" if rsi_val is not None else "N/A"
        
        print(f"{data['timestamp']:<20} {data['open']:<10.2f} {data['high']:<10.2f} {data['low']:<10.2f} {data['close']:<10.2f} {rsi_str:<10} {rsi_check:<8}")
    
    # Highlight 09:18 specifically
    candle_0918 = [d for d in rsi_data if '09:18' in str(d['timestamp'])]
    if candle_0918:
        print(f"\n{'='*100}")
        print(f"AT 09:18 CANDLE (Expected Signal Time)")
        print(f"{'='*100}")
        data = candle_0918[0]
        print(f"Timestamp: {data['timestamp']}")
        print(f"OHLC: O={data['open']:.2f}, H={data['high']:.2f}, L={data['low']:.2f}, C={data['close']:.2f}")
        print(f"RSI(14): {data['rsi']:.2f if data['rsi'] else 'N/A'}")
        print(f"Condition (RSI > 70): {data['rsi'] > 70 if data['rsi'] else False}")
        
        # Previous candle
        idx = rsi_data.index(data)
        if idx > 0:
            prev = rsi_data[idx - 1]
            print(f"\nPrevious Candle (09:17):")
            print(f"  Low: {prev['low']:.2f}")
            print(f"  RSI(14): {prev['rsi']:.2f if prev['rsi'] else 'N/A'}")
            print(f"  Condition (RSI > 70): {prev['rsi'] > 70 if prev['rsi'] else False}")
else:
    print("❌ No RSI data captured")

print(f"\n{'='*100}\n")

# Restore
DataManager._add_to_candle_buffer = orig_add_to_buffer
