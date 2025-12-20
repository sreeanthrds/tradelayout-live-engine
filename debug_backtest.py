#!/usr/bin/env python3
"""
Debug script to understand why entry conditions aren't triggering
"""

import os
import sys
from datetime import datetime, date

# Set environment variables
os.environ['CLICKHOUSE_HOST'] = 'localhost'
os.environ['CLICKHOUSE_PORT'] = '8123'
os.environ['CLICKHOUSE_USER'] = 'default'
os.environ['CLICKHOUSE_PASSWORD'] = ''
os.environ['CLICKHOUSE_DATABASE'] = 'tradelayout'
os.environ['CLICKHOUSE_SECURE'] = 'false'

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.data_manager import DataManager
from src.data.clickhouse_client import ClickHouseClient
from src.backtesting.show_dashboard_data import get_strategy_from_supabase

print("=" * 100)
print("🔍 DEBUG BACKTEST - WHY NO ENTRIES?")
print("=" * 100)

# Load strategy
strategy_id = "5708424d-5962-4629-978c-05b3a174e104"
backtest_date = date(2024, 10, 29)

print(f"\n📋 Loading strategy: {strategy_id}")
print(f"📅 Date: {backtest_date}")

strategy = get_strategy_from_supabase(strategy_id)
print(f"✅ Strategy loaded: {strategy['name']}")

# Initialize data manager
print("\n📊 Initializing DataManager...")
data_manager = DataManager(
    strategy=strategy,
    start_date=backtest_date,
    end_date=backtest_date
)

# Check RSI indicator
print("\n" + "=" * 100)
print("📈 CHECKING RSI INDICATOR")
print("=" * 100)

indicator_configs = data_manager._extract_indicator_configs(strategy)
print(f"\nFound {len(indicator_configs)} indicator configs:")
for config in indicator_configs:
    print(f"  - {config}")

# Load candles and compute indicators
print("\n⏳ Loading candles...")
data_manager.initialize_from_historical_data()

print("\n📊 Cache contents:")
for key in data_manager.candle_buffers.keys():
    buffer = data_manager.candle_buffers[key]
    print(f"\n  {key}: {len(buffer)} candles")
    if len(buffer) > 0:
        last_candle = buffer[-1]
        print(f"    Last candle: {last_candle.get('timestamp')}")
        if 'rsi' in str(last_candle):
            for k, v in last_candle.items():
                if 'rsi' in k.lower():
                    print(f"    {k}: {v}")

# Check specific times when entries should have occurred
print("\n" + "=" * 100)
print("🔍 CHECKING ENTRY TIMES")
print("=" * 100)

entry_times = [
    "2024-10-29 09:19:00",
    "2024-10-29 11:42:00",
    "2024-10-29 12:05:00",
    "2024-10-29 12:17:00"
]

for time_str in entry_times:
    print(f"\n⏰ {time_str}:")
    
    # Get candle at this time
    key = "NIFTY:1m"
    if key in data_manager.candle_buffers:
        buffer = data_manager.candle_buffers[key]
        candle = None
        for c in buffer:
            if str(c.get('timestamp')) == time_str:
                candle = c
                break
        
        if candle:
            print(f"  ✅ Found candle:")
            print(f"     Close: {candle.get('close')}")
            print(f"     Low: {candle.get('low')}")
            
            # Find previous candle
            idx = buffer.index(candle)
            if idx > 0:
                prev_candle = buffer[idx - 1]
                print(f"  📊 Previous candle:")
                print(f"     Close: {prev_candle.get('close')}")
                print(f"     Low: {prev_candle.get('low')}")
                
                # Check for RSI
                for k, v in prev_candle.items():
                    if 'rsi' in k.lower():
                        print(f"     {k}: {v}")
                        if isinstance(v, (int, float)) and v > 70:
                            print(f"     ✅ RSI > 70!")
                
                # Check breakdown condition
                if candle.get('close') < prev_candle.get('low'):
                    print(f"  ✅ BREAKDOWN: Close ({candle.get('close')}) < Prev Low ({prev_candle.get('low')})")
                else:
                    print(f"  ❌ NO BREAKDOWN: Close ({candle.get('close')}) >= Prev Low ({prev_candle.get('low')})")
        else:
            print(f"  ❌ Candle not found in buffer")

print("\n" + "=" * 100)
print("🔍 DIAGNOSIS")
print("=" * 100)
print("\nPossible issues:")
print("1. RSI indicator not being calculated")
print("2. RSI values not stored in candle buffer")
print("3. Entry condition not checking Previous[RSI] correctly")
print("4. Entry node not being activated")
print("=" * 100)
