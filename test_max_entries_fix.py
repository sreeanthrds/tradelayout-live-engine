#!/usr/bin/env python3
"""
Test if maxEntries is now being read correctly
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NzenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter
from strategy.strategy_builder import build_strategy

print(f"\n{'='*100}")
print(f"TEST maxEntries FIX")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

# Load strategy
adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

# Build strategy (creates nodes)
strategy = build_strategy(strategy_config)

# Check entry nodes
print("Entry Nodes maxEntries:\n")

for node in strategy.start_node.children:
    if hasattr(node, 'maxEntries'):
        print(f"{node.id}:")
        print(f"   Node type: {node.node_type}")
        print(f"   maxEntries: {node.maxEntries}")
        if hasattr(node, 'positions') and node.positions:
            print(f"   Position config: {node.positions[0].get('maxEntries', 'NOT SET')}")
        print()

print(f"{'='*100}\n")
