#!/usr/bin/env python3
"""
Find entry-2 and entry-3 nodes with maxEntries
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter

print(f"\n{'='*100}")
print(f"FIND ENTRY-2 AND ENTRY-3 NODES")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

nodes = strategy_config.get('nodes', [])

# Find all nodes with 'entry' in their ID or type
print(f"All nodes with 'entry' in ID or type:\n")

for node in nodes:
    node_id = node.get('id', '')
    node_type = node.get('type', '')
    
    if 'entry' in node_id.lower() or 'entry' in node_type.lower():
        node_data = node.get('data', {})
        
        print(f"{'─'*100}")
        print(f"Node ID: {node_id}")
        print(f"Node Type: {node_type}")
        print(f"Data keys: {list(node_data.keys())}")
        
        # Check for maxEntries in various forms
        max_entries_value = (
            node_data.get('maxEntries') or 
            node_data.get('max_entries') or
            node_data.get('maximumEntries') or
            node_data.get('reEntryCount') or
            node_data.get('re_entry_count') or
            'NOT SET'
        )
        
        print(f"maxEntries: {max_entries_value}")
        
        # Show full data for entry-2 and entry-3
        if 'entry-2' in node_id or 'entry-3' in node_id:
            print(f"\n   ⭐ FOUND TARGET NODE!")
            print(f"\n   Full data:")
            print(json.dumps(node_data, indent=6, default=str))
        
        print()

print(f"\n{'='*100}\n")
