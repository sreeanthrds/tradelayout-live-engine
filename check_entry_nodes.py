#!/usr/bin/env python3
import json

with open('strategy_5708424d_full.json', 'r') as f:
    data = json.load(f)

nodes = data.get('nodes', [])
print(f"Total nodes: {len(nodes)}\n")

# Find all entry signal nodes
entry_signal_nodes = [n for n in nodes if n.get('type') == 'entrySignalNode']
print(f"Entry Signal Nodes: {len(entry_signal_nodes)}\n")

for node in entry_signal_nodes:
    print(f"{'='*80}")
    print(f"Node ID: {node.get('id')}")
    print(f"Type: {node.get('type')}")
    node_data = node.get('data', {})
    conditions = node_data.get('conditions', [])
    print(f"Conditions count: {len(conditions)}")
    if conditions:
        print(f"\nConditions:")
        print(json.dumps(conditions, indent=2))
    print()

# Also check for entry nodes
entry_nodes = [n for n in nodes if n.get('type') == 'entryNode']
print(f"\n{'='*80}")
print(f"Entry Nodes: {len(entry_nodes)}")
for node in entry_nodes:
    print(f"  - {node.get('id')}: {node.get('data', {}).get('name', 'Unnamed')}")
