#!/usr/bin/env python3
"""Check what indicator field name is used in the strategy condition."""

import os
import sys

# Set Supabase environment
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from supabase import create_client
import json

# Initialize Supabase client
supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_ROLE_KEY']
)

# Fetch strategy
strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
response = supabase.table('strategies').select('*').eq('id', strategy_id).execute()

if not response.data:
    print(f"Strategy not found: {strategy_id}")
    sys.exit(1)

strategy = response.data[0]

# Get config from either 'strategy' or 'config' field
config = strategy.get('strategy') or strategy.get('config')
if isinstance(config, str):
    config = json.loads(config)

nodes = config['nodes']

# Find entry-condition-2 node (not entry-2!)
cond_node = None
for node in nodes:
    if node.get('id') == 'entry-condition-2':
        cond_node = node
        break

if not cond_node:
    print("entry-condition-2 node not found")
    sys.exit(1)

print("entry-condition-2 Node:")
print(json.dumps(cond_node, indent=2)[:3000])

# Check conditions
conditions = cond_node['data'].get('conditions', {})
print("\n" + "="*80)
print("RSI CONDITION FIELD NAMES:")
print("="*80)

for cond in conditions.get('conditions', []):
    if 'lhs' in cond and isinstance(cond['lhs'], dict):
        lhs = cond['lhs']
        if 'dataField' in lhs:
            print(f"\n✅ Found indicator field: '{lhs['dataField']}'")
            print(f"   Type: {lhs.get('type')}")
            print(f"   Offset: {lhs.get('offset')}")
            print(f"   Full LHS: {json.dumps(lhs, indent=4)}")
