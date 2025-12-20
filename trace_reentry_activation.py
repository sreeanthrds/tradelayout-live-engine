#!/usr/bin/env python3
"""
Trace what activates the re-entry signal nodes
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.adapters.supabase_adapter import SupabaseStrategyAdapter

print(f"\n{'='*100}")
print(f"TRACE RE-ENTRY SIGNAL NODE ACTIVATION")
print(f"{'='*100}\n")

strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

nodes = strategy_config.get('nodes', [])
edges = strategy_config.get('edges', [])

# Focus on re-entry-signal-3 and re-entry-signal-4
target_node_ids = ['re-entry-signal-3', 're-entry-signal-4']

for target_id in target_node_ids:
    print(f"{'─'*100}")
    print(f"Node: {target_id}")
    print(f"{'─'*100}\n")
    
    # Find incoming edges (what activates this node)
    incoming_edges = [e for e in edges if e.get('target') == target_id]
    
    print(f"Incoming Edges ({len(incoming_edges)}):")
    if not incoming_edges:
        print(f"   ⚠️  NO INCOMING EDGES! Node never gets activated!")
    else:
        for edge in incoming_edges:
            source = edge.get('source')
            print(f"   {source} → {target_id}")
            
            # Find source node type
            source_node = next((n for n in nodes if n.get('id') == source), None)
            if source_node:
                source_type = source_node.get('type')
                source_label = source_node.get('data', {}).get('label', 'N/A')
                print(f"      Source Type: {source_type}")
                print(f"      Source Label: {source_label}")
    
    print()

# Check the full flow: what activates re-entry nodes?
print(f"\n{'='*100}")
print(f"FULL ACTIVATION CHAIN")
print(f"{'='*100}\n")

print("Expected flow for re-entries:")
print("1. entry-3 (EntryNode) places first order → becomes INACTIVE")
print("2. ??? activates re-entry-signal-4 ???")
print("3. re-entry-signal-4 evaluates conditions")
print("4. re-entry-signal-4 activates entry-3 if conditions pass")
print()

print(f"Checking what happens after entry-3 becomes INACTIVE:\n")

# Find outgoing edges from entry-3
outgoing_from_entry3 = [e for e in edges if e.get('source') == 'entry-3']
print(f"Outgoing edges from entry-3 ({len(outgoing_from_entry3)}):")
for edge in outgoing_from_entry3:
    target = edge.get('target')
    target_node = next((n for n in nodes if n.get('id') == target), None)
    target_type = target_node.get('type') if target_node else 'unknown'
    target_label = target_node.get('data', {}).get('label', 'N/A') if target_node else 'N/A'
    print(f"   entry-3 → {target} ({target_type}: {target_label})")

print(f"\n{'='*100}\n")
