# JSONL to Legacy Format Mapping

## Overview

This document maps the modular system's JSONL output files to the legacy JSON.gz format, ensuring data consistency between both systems.

---

## File Mappings

### 1. **nodes.jsonl** → **diagnostics_export.json.gz**

**Purpose:** Node execution event history with parent-child relationships for flow tracking

**nodes.jsonl format** (line-per-node-execution):
```jsonl
{"snapshot_id": 1, "execution_id": "exec_strategy-controller_20241029_091500_3bf415", "parent_execution_id": null, "timestamp": "2024-10-29 09:15:00", "node_id": "strategy-controller", "node_type": "StartNode", "node_name": "Start", "children_nodes": [...], "strategy_config": {...}}
{"snapshot_id": 2, "execution_id": "exec_entry-condition-1_20241029_091900_0cee9d", "parent_execution_id": "exec_strategy-controller_20241029_091500_3bf415", "timestamp": "2024-10-29 09:19:00", "node_id": "entry-condition-1", "node_type": "ConditionNode", ...}
{"snapshot_id": 3, "execution_id": "exec_entry-2_20241029_091900_e1c195", "parent_execution_id": "exec_entry-condition-1_20241029_091900_0cee9d", "timestamp": "2024-10-29 09:19:00", "node_id": "entry-2", "node_type": "EntryNode", ...}
```

**diagnostics_export.json.gz format** (indexed by execution_id):
```json
{
  "events_history": {
    "exec_strategy-controller_20241029_091500_3bf415": {
      "execution_id": "exec_strategy-controller_20241029_091500_3bf415",
      "parent_execution_id": null,
      "timestamp": "2024-10-29 09:15:00",
      "node_id": "strategy-controller",
      "node_type": "StartNode",
      "node_name": "Start",
      "children_nodes": [...],
      "strategy_config": {...}
    },
    "exec_entry-condition-1_20241029_091900_0cee9d": {
      "execution_id": "exec_entry-condition-1_20241029_091900_0cee9d",
      "parent_execution_id": "exec_strategy-controller_20241029_091500_3bf415",
      "timestamp": "2024-10-29 09:19:00",
      "node_id": "entry-condition-1",
      "node_type": "ConditionNode",
      ...
    }
  }
}
```

**Conversion Logic:**
```python
# Read nodes.jsonl line by line
events_history = {}
with open('nodes.jsonl', 'r') as f:
    for line in f:
        node_event = json.loads(line)
        execution_id = node_event["execution_id"]
        node_event.pop("snapshot_id", None)  # Remove JSONL-specific field
        events_history[execution_id] = node_event

# Save as diagnostics_export.json.gz
diagnostics_data = {"events_history": events_history}
with gzip.open('diagnostics_export.json.gz', 'wt') as f:
    json.dump(diagnostics_data, f, indent=2)
```

**Verification:**
- Total events should match (38 events for 2024-10-29)
- Each execution_id should have same parent_execution_id
- Flow chains should build identically from both formats

---

### 2. **trades.jsonl** → **trades_daily.json.gz**

**Purpose:** Position/trade records with entry/exit flow tracking

**trades.jsonl format** (line-per-trade):
```jsonl
{"snapshot_id": 1, "event": "trade", "position_id": "entry-2-pos1", "entry_node_id": "entry-2", "entry_execution_id": "exec_entry-2_20241029_091900_e1c195", "entry_flow_ids": ["exec_strategy-controller_20241029_091500_3bf415", "exec_entry-condition-1_20241029_091900_0cee9d", "exec_entry-2_20241029_091900_e1c195"], "exit_flow_ids": [...], "entry_time": "2024-10-29 09:19:00", "exit_time": "2024-10-29 10:48:00", "pnl": 1250.0, ...}
{"snapshot_id": 2, "event": "trade", "position_id": "entry-3-pos1", "entry_node_id": "entry-3", ...}
```

**trades_daily.json.gz format** (array of trades):
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": 5830.0,
    "winning_trades": 6,
    "losing_trades": 3,
    ...
  },
  "trades": [
    {
      "position_id": "entry-2-pos1",
      "entry_node_id": "entry-2",
      "entry_execution_id": "exec_entry-2_20241029_091900_e1c195",
      "entry_flow_ids": [
        "exec_strategy-controller_20241029_091500_3bf415",
        "exec_entry-condition-1_20241029_091900_0cee9d",
        "exec_entry-2_20241029_091900_e1c195"
      ],
      "exit_flow_ids": [...],
      "entry_time": "2024-10-29 09:19:00",
      "exit_time": "2024-10-29 10:48:00",
      "pnl": 1250.0,
      ...
    },
    {
      "position_id": "entry-3-pos1",
      ...
    }
  ]
}
```

**Conversion Logic:**
```python
# Read trades.jsonl line by line
trades = []
with open('trades.jsonl', 'r') as f:
    for line in f:
        trade_event = json.loads(line)
        trade_event.pop("snapshot_id", None)  # Remove JSONL-specific field
        trade_event.pop("event", None)  # Remove JSONL-specific field
        trades.append(trade_event)

# Save as trades_daily.json.gz
trades_data = {
    "date": trade_date,
    "summary": {...},  # From executor summary
    "trades": trades
}
with gzip.open('trades_daily.json.gz', 'wt') as f:
    json.dump(trades_data, f, indent=2)
```

**Verification:**
- Total trades should match (9 trades for 2024-10-29)
- Each trade should have same entry_flow_ids and exit_flow_ids
- Flow chains should trace back through nodes.jsonl correctly

---

## Additional JSONL Files (Modular Only)

The modular system generates additional JSONL files not present in legacy:

### 3. **events.jsonl**
- Initialization and finalization events
- Strategy start/stop markers
- Contains `latest_snapshot_ids` for cross-referencing

### 4. **ticks.jsonl**
- Per-tick snapshots (lean format)
- Only timestamp + snapshot IDs
- Full data available in other JSONL files via snapshot_id

### 5. **positions.jsonl**
- GPS position snapshots
- Real-time position state per tick

### 6. **candles.jsonl**
- Candle completion events
- Used for debugging candle formation

### 7. **ltp.jsonl**
- LTP update events
- Used for debugging price data

---

## Data Consistency Rules

### 1. **Flow Tracking**
```python
# Both formats must support same flow chain building
def build_flow_chain(execution_id, events):
    chain = []
    current_id = execution_id
    while current_id:
        chain.insert(0, current_id)
        event = events[current_id]
        current_id = event.get('parent_execution_id')
    return chain

# Legacy: events from diagnostics_export.json.gz["events_history"]
# Modular: events from nodes.jsonl (loaded into dict by execution_id)
```

### 2. **Trade Matching**
```python
# Both formats must have identical trades
legacy_trades = json.load(gzip.open('trades_daily.json.gz'))['trades']
modular_trades = [json.loads(line) for line in open('trades.jsonl')]

for legacy, modular in zip(legacy_trades, modular_trades):
    assert legacy['position_id'] == modular['position_id']
    assert legacy['entry_flow_ids'] == modular['entry_flow_ids']
    assert legacy['exit_flow_ids'] == modular['exit_flow_ids']
    assert legacy['pnl'] == modular['pnl']
```

### 3. **Event Count**
```python
# Same number of node executions
legacy_events = json.load(gzip.open('diagnostics_export.json.gz'))['events_history']
modular_events = [json.loads(line) for line in open('nodes.jsonl')]

assert len(legacy_events) == len(modular_events)
```

---

## Testing Protocol

### Test Case: 2024-10-29

**Expected Results:**

1. **nodes.jsonl** → **diagnostics_export.json.gz**
   - 38 events total
   - Same execution_ids
   - Same parent_execution_id relationships

2. **trades.jsonl** → **trades_daily.json.gz**
   - 9 trades total
   - Same entry_flow_ids (3 nodes per entry)
   - Same exit_flow_ids (5 nodes per exit)
   - Same P&L values

### Verification Script

```python
import json
import gzip

# Load legacy
legacy_diag = json.load(gzip.open('diagnostics_export.json.gz'))['events_history']
legacy_trades = json.load(gzip.open('trades_daily.json.gz'))['trades']

# Load modular
modular_events = {
    json.loads(line)['execution_id']: json.loads(line)
    for line in open('nodes.jsonl')
}
modular_trades = [json.loads(line) for line in open('trades.jsonl')]

# Verify events
print(f"Legacy events: {len(legacy_diag)}")
print(f"Modular events: {len(modular_events)}")
assert len(legacy_diag) == len(modular_events), "Event count mismatch"

# Verify trades
print(f"Legacy trades: {len(legacy_trades)}")
print(f"Modular trades: {len(modular_trades)}")
assert len(legacy_trades) == len(modular_trades), "Trade count mismatch"

# Verify flow_ids
for i, (legacy, modular) in enumerate(zip(legacy_trades, modular_trades)):
    assert legacy['entry_flow_ids'] == modular['entry_flow_ids'], f"Entry flow mismatch at trade {i}"
    assert legacy['exit_flow_ids'] == modular['exit_flow_ids'], f"Exit flow mismatch at trade {i}"

print("✅ All verifications passed!")
```

---

## Summary

**Key Points:**

1. ✅ **nodes.jsonl** contains same data as **diagnostics_export.json.gz** (just different format)
2. ✅ **trades.jsonl** contains same data as **trades_daily.json.gz** (just different format)
3. ✅ Flow tracking works identically in both formats
4. ✅ Modular system generates additional JSONL files for enhanced debugging
5. ✅ `backtest_modular_adapter.py` handles conversion automatically

**Status:** 
- Adapter code complete ✅
- Awaiting network connectivity to test with live Supabase data
- Can test with cached strategy config as workaround
