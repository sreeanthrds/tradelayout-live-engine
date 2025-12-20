#!/usr/bin/env python3
"""
Check why re-entry didn't happen at 12:05 for entry-3-pos1
"""
import os
import sys
import json
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter

print(f"\n{'='*100}")
print(f"RE-ENTRY ANALYSIS: Strategy 5708424d on Oct 29, 2024")
print(f"{'='*100}\n")

# 1. Check strategy configuration for max_entries
strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

print(f"{'─'*100}")
print(f"STRATEGY CONFIGURATION")
print(f"{'─'*100}\n")

# Check for maxEntries in the config
nodes = strategy_config.get('nodes', [])
entry_nodes = [n for n in nodes if n.get('type') == 'entrySignalNode']

print(f"Entry Nodes Found: {len(entry_nodes)}\n")

for idx, node in enumerate(entry_nodes, 1):
    node_id = node.get('id')
    node_data = node.get('data', {})
    max_entries = node_data.get('maxEntries', 'NOT SET')
    
    print(f"{idx}. Node ID: {node_id}")
    print(f"   Label: {node_data.get('label', 'N/A')}")
    print(f"   maxEntries: {max_entries}")
    
    # Check if this is entry-3
    if 'entry-3' in node_id:
        print(f"   ⭐ This is entry-3 (CALL entry)")
        print(f"\n   Node Data Keys: {list(node_data.keys())}")
        
        # Check conditions
        conditions = node_data.get('conditions', {})
        print(f"\n   Conditions:")
        print(json.dumps(conditions, indent=6, default=str))
    
    print()

# 2. Check candle data around 12:05
print(f"\n{'─'*100}")
print(f"CANDLE DATA AROUND 12:05 (for re-entry analysis)")
print(f"{'─'*100}\n")

csv_path = '/Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine/candles_rsi_NIFTY_2024-10-29.csv'
df = pd.read_csv(csv_path)

# Strip whitespace from column names
df.columns = df.columns.str.strip()

# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Show candles from 12:00 to 12:20
mask = (df['timestamp'] >= '2024-10-29 12:00:00') & (df['timestamp'] <= '2024-10-29 12:20:00')
candles_12_00_to_12_20 = df[mask].copy()

print(f"Candles from 12:00 to 12:20:\n")
print(candles_12_00_to_12_20[['timestamp', 'close', 'rsi_14', 'high', 'low']].to_string(index=False))

# 3. Check what conditions would need to be met for entry-3 re-entry
print(f"\n{'─'*100}")
print(f"RE-ENTRY CONDITION ANALYSIS")
print(f"{'─'*100}\n")

# Based on the transaction data, entry-3 requires:
# - TIME.hour >= 9
# - RSI > 70 (with offset=-1, so previous candle)
# - NIFTY.ltp < NIFTY.Low[-1]

print("Entry-3 conditions (from previous output):")
print("  1. TIME.hour >= 9")
print("  2. RSI > 70 (previous candle)")
print("  3. NIFTY.ltp < NIFTY.Low[-1]")
print()

# Check each candle from 12:00 to 12:20
for idx, row in candles_12_00_to_12_20.iterrows():
    ts = row['timestamp']
    
    # Get previous candle RSI
    prev_idx = idx - 1
    if prev_idx >= 0:
        prev_rsi = df.loc[prev_idx, 'rsi_14']
        prev_low = df.loc[prev_idx, 'low']
        current_close = row['close']
        
        time_check = ts.hour >= 9
        rsi_check = prev_rsi > 70
        ltp_low_check = current_close < prev_low
        
        all_conditions = time_check and rsi_check and ltp_low_check
        
        if all_conditions or ts.strftime('%H:%M') in ['12:04', '12:05', '12:06', '12:15']:
            print(f"\n{ts.strftime('%H:%M:%S')}:")
            print(f"   Time >= 9: {time_check} ✓" if time_check else f"   Time >= 9: {time_check} ✗")
            print(f"   Prev RSI > 70: {rsi_check} (prev_rsi={prev_rsi:.2f}) {'✓' if rsi_check else '✗'}")
            print(f"   Close < Prev Low: {ltp_low_check} (close={current_close:.2f}, prev_low={prev_low:.2f}) {'✓' if ltp_low_check else '✗'}")
            print(f"   → ALL CONDITIONS MET: {'YES ✓✓✓' if all_conditions else 'NO'}")

print(f"\n{'='*100}\n")
