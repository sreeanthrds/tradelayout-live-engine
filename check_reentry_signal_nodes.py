#!/usr/bin/env python3
"""
Check re-entry signal nodes and their connection to entry-3
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter

print(f"\n{'='*100}")
print(f"RE-ENTRY SIGNAL NODES FOR ENTRY-3")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

nodes = strategy_config.get('nodes', [])
edges = strategy_config.get('edges', [])

# Find all re-entry signal nodes
re_entry_nodes = [n for n in nodes if n.get('type') == 'reEntrySignalNode']

print(f"Found {len(re_entry_nodes)} re-entry signal nodes:\n")

for node in re_entry_nodes:
    node_id = node.get('id')
    node_data = node.get('data', {})
    target_entry_node_id = node_data.get('targetEntryNodeId')
    
    print(f"{'─'*100}")
    print(f"Node ID: {node_id}")
    print(f"Label: {node_data.get('label', 'N/A')}")
    print(f"Target Entry Node ID: {target_entry_node_id}")
    
    # Find edges connecting this re-entry node
    outgoing_edges = [e for e in edges if e.get('source') == node_id]
    
    print(f"\nOutgoing Edges ({len(outgoing_edges)}):")
    for edge in outgoing_edges:
        target = edge.get('target')
        print(f"   → {target}")
        
        # Check if this connects to entry-3
        if target == 'entry-3':
            print(f"   ⭐ CONNECTS TO ENTRY-3!")
    
    # Show conditions
    conditions = node_data.get('conditions', [])
    if conditions:
        print(f"\nConditions:")
        print(json.dumps(conditions, indent=6, default=str))
    
    print()

print(f"\n{'='*100}\n")
