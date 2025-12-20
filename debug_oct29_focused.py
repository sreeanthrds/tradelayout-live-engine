#!/usr/bin/env python3
"""
Debug Strategy 5708424d-5962-4629-978c-05b3a174e104 on Oct 29, 2024
Focus on timestamps: 09:17:00 (entry) and 10:48:00 (exit)

Expected Entry Conditions:
- RSI < 30 (potential_entry = True at 09:17:00, RSI=27.39)
- Time after 09:17:00
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

import pandas as pd
from src.backtesting.backtest_runner import run_backtest
from src.adapters.supabase_adapter import SupabaseStrategyAdapter
import json

print(f"\n{'='*100}")
print(f"DEBUG STRATEGY: 5708424d-5962-4629-978c-05b3a174e104")
print(f"Date: 2024-10-29")
print(f"Focus: 09:17:00 (entry RSI=27.39), 10:48:00 (exit)")
print(f"{'='*100}\n")

# Load strategy to inspect
strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

if not strategy_config:
    print(f"❌ Strategy {strategy_id} not found!")
    sys.exit(1)

print(f"✅ Strategy loaded: {strategy_config.get('name', 'Unknown')}")

# Show entry conditions
entry_config = strategy_config.get('tradeConfig', {}).get('entry', {})
entry_conditions = entry_config.get('conditions', [])

print(f"\n📝 Entry Conditions:")
print(json.dumps(entry_conditions, indent=2))

# Load candle data to show RSI values
csv_file = '/Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine/candles_rsi_NIFTY_2024-10-29.csv'
print(f"\n📊 Loading candle data from: {os.path.basename(csv_file)}")

df = pd.read_csv(csv_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

print(f"   Candles loaded: {len(df)}")

# Check RSI values at key timestamps
print(f"\n🔍 RSI Values at Key Timestamps (from your manual data):")
key_times = [
    ('2024-10-29 09:17:00', 27.39, True),
    ('2024-10-29 09:18:00', 26.07, True),
    ('2024-10-29 10:45:00', 29.56, True),
    ('2024-10-29 10:47:00', 28.57, True),
]
for ts, expected_rsi, should_entry in key_times:
    if ts in df.index.astype(str).values:
        row = df.loc[ts]
        actual_rsi = row['rsi_14']
        match = '✓' if abs(actual_rsi - expected_rsi) < 0.1 else '✗'
        print(f"   {ts}: RSI={actual_rsi:.2f} (expected={expected_rsi:.2f}) {match}, Entry={should_entry}")

# Run backtest with breakpoint at first entry time
print(f"\n{'='*100}")
print(f"RUNNING BACKTEST (Full Day)")
print(f"{'='*100}\n")

try:
    results = run_backtest(
        strategy_ids=strategy_id,
        backtest_date='2024-10-29'
    )
    
    print(f"\n{'='*100}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*100}\n")
    
    print(f"⚡ Performance:")
    print(f"   Ticks processed: {results.ticks_processed:,}")
    print(f"   Duration: {results.duration_seconds:.2f}s")
    print(f"   Speed: {results.ticks_per_second:.0f} ticks/sec")
    
    print(f"\n📊 Position Summary:")
    print(f"   Total Positions: {len(results.positions)}")
    
    if results.positions:
        print(f"\n📝 Position Details:\n")
        for idx, pos in enumerate(results.positions, 1):
            print(f"{idx}. Position ID: {pos.get('position_id')}")
            print(f"   Entry Time: {pos.get('entry_time')}")
            print(f"   Entry Price: {pos.get('entry_price')}")
            print(f"   Exit Time: {pos.get('exit_time', 'Still Open')}")
            print(f"   Exit Price: {pos.get('exit_price', 'N/A')}")
            print(f"   Status: {pos.get('status')}")
            print(f"   PNL: {pos.get('pnl', 0):.2f}")
            print(f"   reEntryNum: {pos.get('reEntryNum', 0)}")
            print(f"   position_num: {pos.get('position_num', 1)}")
            
            # Show condition text if available
            diagnostic_data = pos.get('diagnostic_data', {})
            conditions_evaluated = diagnostic_data.get('conditions_evaluated', [])
            if conditions_evaluated:
                print(f"\n   📋 Entry Condition Evaluations:")
                for cond in conditions_evaluated:
                    cond_text = cond.get('condition_text', 'No text')
                    print(f"      {cond_text}")
            print()
    else:
        print(f"\n❌ NO POSITIONS CREATED!")
        print(f"\n🔍 INVESTIGATING WHY...")
        
        print(f"\n1️⃣  Check Strategy Config:")
        print(f"   Entry Node Count: {len(strategy_config.get('tradeConfig', {}).get('entry', {}).get('conditions', []))}")
        print(f"   Exit Node Count: {len(strategy_config.get('tradeConfig', {}).get('exit', {}).get('conditions', []))}")
        
        print(f"\n2️⃣  Check if RSI is in conditions:")
        entry_json = json.dumps(entry_conditions)
        has_rsi = 'rsi' in entry_json.lower() or 'RSI' in entry_json
        print(f"   RSI mentioned in entry conditions: {has_rsi}")
        
        print(f"\n3️⃣  Check time condition:")
        has_time = 'time' in entry_json.lower()
        print(f"   Time mentioned in entry conditions: {has_time}")
        
        print(f"\n4️⃣  Possible Issues:")
        print(f"   - Entry conditions might not match RSI < 30 pattern")
        print(f"   - Time condition might be restricting entries")
        print(f"   - Node graph might not be traversing correctly")
        print(f"   - Indicator calculation might be different")

except Exception as e:
    print(f"\n❌ Error during backtest: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*100}\n")
