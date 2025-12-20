#!/usr/bin/env python3
"""
Find where maxEntries should be configured
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter

print(f"\n{'='*100}")
print(f"FIND maxEntries CONFIGURATION LOCATION")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

# Check different locations where maxEntries might be
print("Checking possible locations for maxEntries:\n")

# 1. Top-level config
print("1. Top-level config keys:")
print(f"   {list(strategy_config.keys())}")
if 'maxEntries' in strategy_config:
    print(f"   maxEntries: {strategy_config['maxEntries']}")
else:
    print(f"   maxEntries: NOT FOUND at top level")

# 2. tradeConfig
print("\n2. tradeConfig:")
trade_config = strategy_config.get('tradeConfig', {})
if trade_config:
    print(f"   Keys: {list(trade_config.keys())}")
    if 'maxEntries' in trade_config:
        print(f"   maxEntries: {trade_config['maxEntries']}")
    else:
        print(f"   maxEntries: NOT FOUND in tradeConfig")
else:
    print(f"   tradeConfig is empty or missing")

# 3. Entry nodes
print("\n3. Entry Nodes:")
nodes = strategy_config.get('nodes', [])
entry_signal_nodes = [n for n in nodes if n.get('type') == 'entrySignalNode']

for idx, node in enumerate(entry_signal_nodes, 1):
    node_id = node.get('id')
    node_data = node.get('data', {})
    
    print(f"\n   Entry Node {idx}: {node_id}")
    print(f"   All data keys: {list(node_data.keys())}")
    
    # Check all possible maxEntries variations
    if 'maxEntries' in node_data:
        print(f"   ✓ maxEntries: {node_data['maxEntries']}")
    elif 'max_entries' in node_data:
        print(f"   ✓ max_entries: {node_data['max_entries']}")
    else:
        print(f"   ✗ maxEntries/max_entries: NOT FOUND")
    
    # Show the actual entry nodes that this entry signal connects to
    print(f"\n   Full node data:")
    print(json.dumps(node_data, indent=6, default=str))

# 4. Check actual entry nodes (not entry signal nodes)
print("\n4. Entry Nodes (type='entry'):")
entry_nodes = [n for n in nodes if n.get('type') == 'entry']

for idx, node in enumerate(entry_nodes, 1):
    node_id = node.get('id')
    node_data = node.get('data', {})
    
    print(f"\n   Entry Node {idx}: {node_id}")
    print(f"   All data keys: {list(node_data.keys())}")
    
    if 'maxEntries' in node_data:
        print(f"   ✓ maxEntries: {node_data['maxEntries']}")
    elif 'max_entries' in node_data:
        print(f"   ✓ max_entries: {node_data['max_entries']}")
    else:
        print(f"   ✗ maxEntries/max_entries: NOT FOUND")
    
    print(f"\n   Full node data:")
    print(json.dumps(node_data, indent=6, default=str))

print(f"\n{'='*100}\n")
