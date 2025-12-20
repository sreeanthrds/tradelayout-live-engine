#!/usr/bin/env python3
"""
Deep inspection of strategy 5708424d-5962-4629-978c-05b3a174e104
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter
import json

print(f"\n{'='*100}")
print(f"STRATEGY INSPECTION: 5708424d-5962-4629-978c-05b3a174e104")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

if not strategy_config:
    print(f"❌ Strategy not found!")
    sys.exit(1)

print(f"✅ Strategy loaded: {strategy_config.get('name')}")
print(f"   User ID: {strategy_config.get('user_id')}")
print(f"   Strategy ID: {strategy_config.get('id')}")
print(f"   Created: {strategy_config.get('created_at')}")

# Save full config to file
with open('strategy_5708424d_full.json', 'w') as f:
    json.dump(strategy_config, f, indent=2)
    print(f"\n💾 Full config saved to: strategy_5708424d_full.json")

# Check trade config
trade_config = strategy_config.get('tradeConfig', {})
print(f"\n📋 Trade Config Keys: {list(trade_config.keys())}")

# Entry config
entry_config = trade_config.get('entry', {})
print(f"\n📝 Entry Config:")
print(f"   Keys: {list(entry_config.keys())}")
print(f"   Conditions: {entry_config.get('conditions', [])}")
print(f"   Conditions Type: {type(entry_config.get('conditions', []))}")
print(f"   Conditions Length: {len(entry_config.get('conditions', []))}")

# Exit config
exit_config = trade_config.get('exit', {})
print(f"\n🚪 Exit Config:")
print(f"   Keys: {list(exit_config.keys())}")
print(f"   Conditions: {exit_config.get('conditions', [])}")
print(f"   Conditions Length: {len(exit_config.get('conditions', []))}")

# Check strategy_config structure
print(f"\n🏗️  Strategy Config Top-level Keys:")
for key in strategy_config.keys():
    value = strategy_config[key]
    if isinstance(value, dict):
        print(f"   {key}: dict with {len(value)} keys")
    elif isinstance(value, list):
        print(f"   {key}: list with {len(value)} items")
    else:
        print(f"   {key}: {type(value).__name__}")

# Check if there's a strategy_json field
if 'strategy_json' in strategy_config:
    print(f"\n📦 Found strategy_json field!")
    strategy_json = strategy_config['strategy_json']
    if isinstance(strategy_json, str):
        print(f"   Type: string (needs parsing)")
        strategy_json = json.loads(strategy_json)
    elif isinstance(strategy_json, dict):
        print(f"   Type: dict (already parsed)")
    
    print(f"   Keys: {list(strategy_json.keys())}")
    
    if 'tradeConfig' in strategy_json:
        tc = strategy_json['tradeConfig']
        entry = tc.get('entry', {})
        print(f"\n   Entry conditions in strategy_json: {len(entry.get('conditions', []))}")
        if entry.get('conditions'):
            print(f"   First condition: {json.dumps(entry['conditions'][0], indent=6)}")

print(f"\n{'='*100}\n")
