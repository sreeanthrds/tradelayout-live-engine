#!/usr/bin/env python3
"""
Verify RSI calculation methodology and show values at 09:18:41
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

# Capture data during backtest
candle_data = []
ltp_at_signal = None
signal_found = False

orig_add = GlobalPositionStore.add_position

def track_add(self, pos_id, entry_data, tick_time=None):
    """Track position entry and capture signal time"""
    global signal_found
    signal_found = True
    entry_time = str(entry_data.get('entry_time', 'N/A'))
    print(f"\n🎯 SIGNAL TRIGGERED AT: {entry_time}")
    return orig_add(self, pos_id, entry_data, tick_time)

GlobalPositionStore.add_position = track_add

# Monkey patch onTick to capture candle and LTP data
from src.backtesting import tick_processor
orig_onTick = tick_processor.onTick

def logged_onTick(context, tick_data):
    """Capture candle and LTP data"""
    global ltp_at_signal
    
    current_time = context.get('current_time', None)
    time_str = str(current_time)
    
    # Capture data for first 5 minutes and at signal time
    if ('09:15' in time_str or '09:16' in time_str or '09:17' in time_str or 
        '09:18' in time_str or '09:19' in time_str):
        
        cache = context.get('cache', {})
        candles = cache.get('NIFTY:1m', [])
        
        if candles:
            last_candle = candles[-1]
            indicators = last_candle.get('indicators', {})
            rsi = indicators.get('rsi_1764539168968', None)
            
            # Get LTP
            ltp_store = context.get('ltp_store', {})
            nifty_ltp = 0
            if 'NIFTY' in ltp_store:
                nifty_data = ltp_store['NIFTY']
                if isinstance(nifty_data, dict):
                    nifty_ltp = nifty_data.get('ltp', 0)
                else:
                    nifty_ltp = nifty_data
            
            # Check if this is close to signal time
            if '09:18:41' in time_str:
                ltp_at_signal = nifty_ltp
            
            candle_data.append({
                'time': time_str,
                'candle_timestamp': last_candle.get('timestamp', 'N/A'),
                'open': last_candle.get('open', 0),
                'high': last_candle.get('high', 0),
                'low': last_candle.get('low', 0),
                'close': last_candle.get('close', 0),
                'rsi': rsi,
                'ltp': nifty_ltp,
                'num_candles': len(candles)
            })
    
    return orig_onTick(context, tick_data)

tick_processor.onTick = logged_onTick

# Monkey patch DataManager to log initialization
from src.backtesting.data_manager import DataManager
orig_init_historical = DataManager.initialize_from_historical_data

def logged_init_historical(self, symbol, timeframe, candles):
    """Log historical data initialization"""
    print(f"\n{'='*100}")
    print(f"📊 HISTORICAL DATA INITIALIZATION")
    print(f"{'='*100}")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Historical candles received: {len(candles)}")
    
    if len(candles) > 0:
        print(f"First candle: {candles.iloc[0]['timestamp']}")
        print(f"Last candle: {candles.iloc[-1]['timestamp']}")
    
    result = orig_init_historical(self, symbol, timeframe, candles)
    
    # Check how many candles were stored in cache
    cached_candles = self.cache.get_candles(symbol, timeframe, count=20)
    
    if cached_candles:
        print(f"\n✅ Stored in cache ({symbol}:{timeframe}):")
        print(f"   Cached candles: {len(cached_candles)}")
        
        last_candle = cached_candles[-1]
        
        # Check if indicators were calculated
        indicators = last_candle.get('indicators', {})
        if indicators:
            print(f"   ✅ Indicators calculated on historical data")
            for ind_key, ind_value in indicators.items():
                print(f"      {ind_key}: {ind_value}")
        else:
            print(f"   ❌ No indicators found in cached candles!")
    else:
        print(f"\n❌ No candles found in cache for {symbol}:{timeframe}")
    
    print(f"{'='*100}\n")
    return result

DataManager.initialize_from_historical_data = logged_init_historical

print(f"\n{'='*100}")
print(f"VERIFYING RSI CALCULATION FOR OCT 1ST 2024")
print(f"{'='*100}")
print(f"Strategy: My New Strategy 6")
print(f"Expected Signal: 09:18:41")
print(f"\nVerification Points:")
print(f"  1. Load 500 historical 1m candles before 09:15")
print(f"  2. Calculate RSI(14) on historical data")
print(f"  3. Incrementally update RSI as new candles form")
print(f"  4. Show first 5 minutes candles + RSI values")
print(f"  5. Show LTP at signal time (09:18:41)")
print(f"{'='*100}\n")

config = BacktestConfig(
    strategy_ids=[STRATEGY_ID],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

engine = CentralizedBacktestEngine(config)
result = engine.run()

print(f"\n{'='*100}")
print(f"CANDLE DATA - FIRST 5 MINUTES")
print(f"{'='*100}\n")

if candle_data:
    # Group by candle (each candle has multiple ticks)
    candles_by_time = {}
    for data in candle_data:
        candle_time = str(data['candle_timestamp'])
        if candle_time not in candles_by_time:
            candles_by_time[candle_time] = data
    
    print(f"{'Candle Time':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'RSI(14)':<10} {'#Candles':<10}")
    print(f"{'-'*100}")
    
    for candle_time in sorted(candles_by_time.keys()):
        data = candles_by_time[candle_time]
        rsi_val = f"{data['rsi']:.2f}" if data['rsi'] is not None else "N/A"
        
        print(f"{candle_time:<20} {data['open']:<10.2f} {data['high']:<10.2f} {data['low']:<10.2f} {data['close']:<10.2f} {rsi_val:<10} {data['num_candles']:<10}")
    
    print(f"\n{'='*100}")
    print(f"SIGNAL TIME DETAILS (09:18:41)")
    print(f"{'='*100}\n")
    
    # Find data closest to signal time
    signal_data = [d for d in candle_data if '09:18:41' in d['time']]
    
    if signal_data:
        data = signal_data[0]
        print(f"Exact Time: {data['time']}")
        print(f"Current Candle: {data['candle_timestamp']}")
        print(f"NIFTY LTP: ₹{data['ltp']:.2f}")
        print(f"Candle OHLC:")
        print(f"  Open:  ₹{data['open']:.2f}")
        print(f"  High:  ₹{data['high']:.2f}")
        print(f"  Low:   ₹{data['low']:.2f}")
        print(f"  Close: ₹{data['close']:.2f}")
        print(f"RSI(14): {data['rsi']:.2f if data['rsi'] else 'N/A'}")
        print(f"Total candles in buffer: {data['num_candles']}")
        
        # Check previous candle for condition
        prev_candles = [d for d in candle_data if '09:17' in str(d['candle_timestamp'])]
        if prev_candles:
            prev = prev_candles[-1]
            print(f"\nPrevious Candle (09:17):")
            print(f"  Low: ₹{prev['low']:.2f}")
            print(f"  RSI(14): {prev['rsi']:.2f if prev['rsi'] else 'N/A'}")
            
            print(f"\nCondition Check:")
            if prev['rsi'] is not None:
                print(f"  RSI(offset=-1) > 70: {prev['rsi']:.2f} > 70 = {prev['rsi'] > 70} {'✅' if prev['rsi'] > 70 else '❌'}")
            print(f"  LTP < Low(offset=-1): {data['ltp']:.2f} < {prev['low']:.2f} = {data['ltp'] < prev['low']} {'✅' if data['ltp'] < prev['low'] else '❌'}")
    else:
        print(f"⚠️  No data captured at exact signal time 09:18:41")
        if ltp_at_signal:
            print(f"LTP at signal: ₹{ltp_at_signal:.2f}")
else:
    print(f"❌ No candle data captured")

print(f"\n{'='*100}")
print(f"SIGNAL STATUS")
print(f"{'='*100}")

if signal_found:
    print(f"✅ SIGNAL TRIGGERED - Position opened")
else:
    print(f"❌ NO SIGNAL - Conditions not met")

print(f"\n{'='*100}\n")

# Restore
GlobalPositionStore.add_position = orig_add
tick_processor.onTick = orig_onTick
DataManager.initialize_from_historical_data = orig_init_historical
