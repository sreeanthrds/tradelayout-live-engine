#!/usr/bin/env python3
"""
Debug script to examine condition evaluation at 09:19:00
when the first position should be created.
"""

import os
import sys
from datetime import datetime, date

# Set environment
os.environ['CLICKHOUSE_HOST'] = 'localhost'
os.environ['CLICKHOUSE_HTTP_PORT'] = '8123'
os.environ['CLICKHOUSE_SECURE'] = 'false'
os.environ['CLICKHOUSE_PASSWORD'] = ''  # Empty password for local ClickHouse
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.strategy_manager import StrategyManager
from src.backtesting.data_manager import DataManager
from src.core.shared_data_cache import SharedDataCache

print("="*80)
print("🔍 DEBUGGING ENTRY CONDITION AT 09:19:00")
print("="*80)

# Load strategy
strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
backtest_date = date(2024, 10, 29)

print(f"\n📋 Loading strategy {strategy_id}...")
strategy_manager = StrategyManager()
strategy = strategy_manager.load_strategy(strategy_id)

print(f"✅ Strategy loaded: {strategy.strategy_name}")
print(f"   Instrument configs: {list(strategy.instrument_configs.keys())}")
print(f"   Indicators: {strategy.get_all_indicator_keys()}")

# Initialize SharedDataCache and DataManager
print(f"\n📊 Initializing DataManager...")
cache = SharedDataCache()
data_manager = DataManager(cache=cache)

# Build strategies_agg (single strategy)
strategies_agg = {
    'timeframes': list(strategy.instrument_configs.keys()),
    'indicators': {},
    'options': [],
    'strategies': []
}

# Build indicators dict
for key, inst_config in strategy.instrument_configs.items():
    symbol, timeframe = key.split(':', 1)
    if symbol not in strategies_agg['indicators']:
        strategies_agg['indicators'][symbol] = {}
    if timeframe not in strategies_agg['indicators'][symbol]:
        strategies_agg['indicators'][symbol][timeframe] = []
    
    for indicator in inst_config.indicators:
        strategies_agg['indicators'][symbol][timeframe].append({
            'name': indicator.name,
            'params': indicator.params,
            'key': indicator.key
        })

print(f"   Indicators to register: {strategies_agg['indicators']}")

data_manager.initialize(
    strategy=None,
    backtest_date=backtest_date,
    strategies_agg=strategies_agg
)

print(f"✅ DataManager initialized")
print(f"   Indicator key mappings: {data_manager.indicator_key_mappings}")

# Load ticks for the specific time period around 09:19:00
print(f"\n📡 Loading ticks around 09:19:00...")
ticks = data_manager.load_ticks(
    symbol='NIFTY',
    start_time=datetime(2024, 10, 29, 9, 15, 0),
    end_time=datetime(2024, 10, 29, 9, 25, 0)
)

print(f"✅ Loaded {len(ticks)} ticks")

# Find the tick at 09:19:00
target_time = datetime(2024, 10, 29, 9, 19, 0)
target_ticks = [t for t in ticks if t['timestamp'] >= target_time and t['timestamp'] < datetime(2024, 10, 29, 9, 20, 0)]

print(f"\n🎯 Found {len(target_ticks)} ticks at 09:19:xx")
if target_ticks:
    print(f"   First tick: {target_ticks[0]['timestamp']} - LTP: {target_ticks[0]['ltp']}")
    print(f"   Last tick: {target_ticks[-1]['timestamp']} - LTP: {target_ticks[-1]['ltp']}")

# Process ticks up to 09:19:00 to build candles
print(f"\n🔄 Processing ticks to build candles up to 09:19:00...")
tick_count = 0
for tick in ticks:
    if tick['timestamp'] > target_time:
        break
    data_manager.process_tick(tick)
    tick_count += 1

print(f"✅ Processed {tick_count} ticks")

# Get candles at 09:19:00
candles = data_manager.cache.get_candles('NIFTY', '1m')
print(f"\n📊 Candles at 09:19:00:")
print(f"   Total candles in cache: {len(candles) if candles else 0}")
if candles:
    last_3 = candles[-3:] if len(candles) >= 3 else candles
    for i, candle in enumerate(last_3):
        idx = len(candles) - len(last_3) + i
        print(f"\n   Candle [{idx}] @ {candle['timestamp']}:")
        print(f"      OHLC: {candle['open']:.2f} / {candle['high']:.2f} / {candle['low']:.2f} / {candle['close']:.2f}")
        if 'indicators' in candle:
            print(f"      Indicators: {candle['indicators']}")

# Check entry-3 conditions (CE - bullish)
print(f"\n" + "="*80)
print("🔍 CHECKING ENTRY-3 (CE - BULLISH) CONDITIONS AT 09:19:00")
print("="*80)

# Expected conditions:
# 1. Current Time > 09:17 ✅ (should pass)
# 2. Previous[rsi_1764509210372] < 30 (need to check)
# 3. LTP > Previous[High] (breakout above)

if candles and len(candles) >= 2:
    prev_candle = candles[-2]  # Previous completed candle
    current_ltp = target_ticks[0]['ltp'] if target_ticks else None
    
    print(f"\n📍 Previous candle (offset -1): {prev_candle['timestamp']}")
    print(f"   High: {prev_candle['high']:.2f}")
    print(f"   Low: {prev_candle['low']:.2f}")
    
    if 'indicators' in prev_candle and data_manager.indicator_key_mappings.get('NIFTY:1m'):
        mappings = data_manager.indicator_key_mappings['NIFTY:1m']
        print(f"\n   Available indicator mappings: {mappings}")
        
        # Try to get RSI value
        rsi_db_key = 'rsi_1764509210372'
        rsi_generated_key = mappings.get(rsi_db_key)
        
        if rsi_generated_key:
            rsi_value = prev_candle['indicators'].get(rsi_generated_key)
            print(f"\n   RSI value: {rsi_value}")
            print(f"   Mapped: '{rsi_db_key}' → '{rsi_generated_key}'")
            
            # Check conditions
            print(f"\n📋 Condition Evaluation:")
            print(f"   1. Current Time > 09:17: ✅ TRUE (09:19 > 09:17)")
            print(f"   2. Previous[RSI] < 30: {rsi_value} < 30 = {rsi_value < 30 if rsi_value else 'N/A'}")
            print(f"   3. LTP > Previous[High]: {current_ltp} > {prev_candle['high']:.2f} = {current_ltp > prev_candle['high'] if current_ltp else 'N/A'}")
            
            if rsi_value and rsi_value < 30 and current_ltp and current_ltp > prev_candle['high']:
                print(f"\n✅ ALL CONDITIONS MET - SHOULD CREATE CE POSITION!")
            else:
                print(f"\n❌ CONDITIONS NOT MET")
        else:
            print(f"\n⚠️ No mapping found for '{rsi_db_key}'")
    else:
        print(f"\n⚠️ No indicators in previous candle")

# Check entry-2 conditions (PE - bearish) 
print(f"\n" + "="*80)
print("🔍 CHECKING ENTRY-2 (PE - BEARISH) CONDITIONS AT 09:19:00")
print("="*80)

# Expected conditions:
# 1. Current Time > 09:17 ✅ (should pass)
# 2. Previous[rsi_1764509210372] > 70 (need to check)
# 3. LTP < Previous[Low] (breakdown below)

if candles and len(candles) >= 2:
    prev_candle = candles[-2]
    current_ltp = target_ticks[0]['ltp'] if target_ticks else None
    
    if 'indicators' in prev_candle and data_manager.indicator_key_mappings.get('NIFTY:1m'):
        mappings = data_manager.indicator_key_mappings['NIFTY:1m']
        rsi_db_key = 'rsi_1764509210372'
        rsi_generated_key = mappings.get(rsi_db_key)
        
        if rsi_generated_key:
            rsi_value = prev_candle['indicators'].get(rsi_generated_key)
            
            print(f"\n📋 Condition Evaluation:")
            print(f"   1. Current Time > 09:17: ✅ TRUE (09:19 > 09:17)")
            print(f"   2. Previous[RSI] > 70: {rsi_value} > 70 = {rsi_value > 70 if rsi_value else 'N/A'}")
            print(f"   3. LTP < Previous[Low]: {current_ltp} < {prev_candle['low']:.2f} = {current_ltp < prev_candle['low'] if current_ltp else 'N/A'}")
            
            if rsi_value and rsi_value > 70 and current_ltp and current_ltp < prev_candle['low']:
                print(f"\n✅ ALL CONDITIONS MET - SHOULD CREATE PE POSITION!")
            else:
                print(f"\n❌ CONDITIONS NOT MET")

print(f"\n" + "="*80)
print("✅ DEBUG COMPLETE")
print("="*80)
