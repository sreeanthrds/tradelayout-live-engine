# Trade Update with Events History - SSE Specification

## Overview
Trade updates now include execution flow events bundled together. When a position closes, the `trade_update` SSE event contains both the trade data AND all relevant events from `events_history` needed to build flow diagrams.

## Why Bundle Together?

### Problems with Separate Polling
- ❌ Timing mismatch - Trade arrives via SSE, events_history via polling
- ❌ Race condition - UI might get trade before polling updates
- ❌ Extra requests - UI needs to poll separately for events
- ❌ Complexity - Two data sources for one feature

### Benefits of Bundling
- ✅ Atomic delivery - Trade + flow events arrive together
- ✅ No race conditions - Everything in one message
- ✅ Reduced requests - No separate polling needed
- ✅ Efficient - Only sends relevant events (not entire history)
- ✅ Real-time - Immediate flow diagram data

---

## SSE Event Structure

### Event: `trade_update`

**Sent when:** A position closes (trade completes)

**Data structure:**
```json
{
  "event": "trade_update",
  "data": {
    "trade": {
      "trade_id": "entry-2-pos1",
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": "181.60",
      "entry_time": "2024-10-29T09:19:00+05:30",
      "exit_price": "260.05",
      "exit_time": "2024-10-29T10:48:00+05:30",
      "pnl": "-78.45",
      "pnl_percent": "-43.20",
      "duration_minutes": 89.0,
      "status": "CLOSED",
      "entry_flow_ids": [
        "exec_strategy-controller_20241029_091500_e8b619",
        "exec_entry-condition-1_20241029_091900_112a10",
        "exec_entry-2_20241029_091900_51380c"
      ],
      "exit_flow_ids": [
        "exec_strategy-controller_20241029_091500_e8b619",
        "exec_entry-condition-1_20241029_091900_112a10",
        "exec_entry-2_20241029_091900_51380c",
        "exec_exit-condition-2_20241029_104800_42e8f7",
        "exec_exit-3_20241029_104800_ab99d0"
      ],
      "entry_trigger": "entry-2",
      "exit_reason": "exit_condition_met"
    },
    "summary": {
      "total_trades": 1,
      "total_pnl": "-78.45",
      "winning_trades": 0,
      "losing_trades": 1,
      "win_rate": "0.00"
    },
    "events_history": {
      "exec_strategy-controller_20241029_091500_e8b619": {
        "execution_id": "exec_strategy-controller_20241029_091500_e8b619",
        "parent_execution_id": null,
        "timestamp": "2024-10-29T09:15:00+05:30",
        "event_type": "logic_completed",
        "node_id": "strategy-controller",
        "node_name": "Start",
        "node_type": "StartNode",
        "children_nodes": [
          {"id": "entry-condition-1"}
        ]
      },
      "exec_entry-condition-1_20241029_091900_112a10": {
        "execution_id": "exec_entry-condition-1_20241029_091900_112a10",
        "parent_execution_id": "exec_strategy-controller_20241029_091500_e8b619",
        "timestamp": "2024-10-29T09:19:00+05:30",
        "event_type": "signal_emitted",
        "node_id": "entry-condition-1",
        "node_name": "Entry Condition 1",
        "node_type": "EntrySignalNode",
        "signal_emitted": true,
        "evaluated_conditions": {
          "condition_results": [
            {
              "condition_type": "price_above",
              "result": true,
              "details": {...}
            }
          ]
        }
      },
      "exec_entry-2_20241029_091900_51380c": {
        "execution_id": "exec_entry-2_20241029_091900_51380c",
        "parent_execution_id": "exec_entry-condition-1_20241029_091900_112a10",
        "timestamp": "2024-10-29T09:19:00+05:30",
        "event_type": "order_placed",
        "node_id": "entry-2",
        "node_name": "Entry Order 2",
        "node_type": "EntryNode",
        "order_details": {
          "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
          "side": "sell",
          "quantity": 1,
          "price": "181.60"
        }
      },
      "exec_exit-condition-2_20241029_104800_42e8f7": {
        "execution_id": "exec_exit-condition-2_20241029_104800_42e8f7",
        "parent_execution_id": "exec_entry-2_20241029_091900_51380c",
        "timestamp": "2024-10-29T10:48:00+05:30",
        "event_type": "exit_signal",
        "node_id": "exit-condition-2",
        "node_name": "Exit Condition 2",
        "node_type": "ExitSignalNode",
        "exit_reason": "stop_loss_hit"
      },
      "exec_exit-3_20241029_104800_ab99d0": {
        "execution_id": "exec_exit-3_20241029_104800_ab99d0",
        "parent_execution_id": "exec_exit-condition-2_20241029_104800_42e8f7",
        "timestamp": "2024-10-29T10:48:00+05:30",
        "event_type": "order_placed",
        "node_id": "exit-3",
        "node_name": "Exit Order 3",
        "node_type": "ExitNode",
        "order_details": {
          "action": "exit",
          "price": "260.05"
        }
      }
    }
  }
}
```

---

## Key Points

### Efficient Event Filtering
- **NOT full events_history** - Only events referenced in `entry_flow_ids` + `exit_flow_ids`
- **Example:** Trade has 5 flow IDs → Only those 5 events included
- **Benefit:** Small payload even with thousands of total events

### Data Types
- All numeric fields as **numbers** (not strings)
- Timestamps as **ISO 8601 strings**
- Flow IDs as **array of strings**

### Compression
- `trade_update` events are **gzip compressed** (like node_events)
- UI must decompress before parsing

---

## UI Integration

### TypeScript Interface
```typescript
interface TradeUpdateEvent {
  trade: {
    trade_id: string;
    entry_flow_ids: string[];
    exit_flow_ids: string[];
    // ... other trade fields
  };
  summary: {
    total_trades: number;
    total_pnl: string;
    winning_trades: number;
    losing_trades: number;
    win_rate: string;
  };
  events_history: {
    [execution_id: string]: {
      execution_id: string;
      parent_execution_id: string | null;
      timestamp: string;
      event_type: string;
      node_id: string;
      node_name: string;
      node_type: string;
      // ... event-specific fields
    };
  };
}
```

### Event Handler
```typescript
eventSource.addEventListener('trade_update', (event) => {
  // Decompress if needed
  const data: TradeUpdateEvent = decompressAndParse(event.data);
  
  // Trade data
  const trade = data.trade;
  
  // Build flow diagram using bundled events
  const entryFlow = trade.entry_flow_ids.map(id => 
    data.events_history[id]
  );
  
  const exitFlow = trade.exit_flow_ids.map(id => 
    data.events_history[id]
  );
  
  // Update UI
  addTradeToTable(trade);
  updatePnLSummary(data.summary);
  renderFlowDiagram(entryFlow, exitFlow);
});
```

### Benefits for UI
- ✅ **No polling needed** - All data arrives via SSE
- ✅ **Immediate rendering** - Flow diagrams available instantly
- ✅ **No caching logic** - Events arrive with trade
- ✅ **Simplified code** - Single data source

---

## Polling API Changes

### `/api/live-trading/dashboard/{user_id}`

**Removed:** `events_history` from response

**Before:**
```json
{
  "sessions": {
    "sim-xxx": {
      "data": {
        "gps_data": {...},
        "events_history": {...}  // ❌ REMOVED
      }
    }
  }
}
```

**After:**
```json
{
  "sessions": {
    "sim-xxx": {
      "data": {
        "gps_data": {...},
        "market_data": {...}
        // ✅ No events_history
      }
    }
  }
}
```

**Reason:** Events come with trades via SSE, no need in polling response.

---

## Migration Guide

### Old Approach (Polling for events_history)
```typescript
// ❌ OLD - Don't do this anymore
const pollingData = await fetch('/api/live-trading/dashboard/user123');
const eventsHistory = pollingData.sessions['sim-xxx'].data.events_history;
const flowNodes = getFlowNodes(trade.entry_flow_ids, eventsHistory);
```

### New Approach (Receive with trade)
```typescript
// ✅ NEW - Events arrive with trade
eventSource.addEventListener('trade_update', (event) => {
  const { trade, events_history } = decompressAndParse(event.data);
  const flowNodes = getFlowNodes(trade.entry_flow_ids, events_history);
  renderFlowDiagram(flowNodes);
});
```

---

## Testing

### Test Case 1: Single Trade
```bash
# Start backtest
python live_backtest_runner.py

# Connect SSE
curl -N http://localhost:8000/api/live-trading/stream/sim-xxx

# Wait for trade_update event
# Verify: events_history contains all IDs from entry_flow_ids + exit_flow_ids
```

### Test Case 2: Re-entry Trade
```bash
# Trade with re-entries will have longer flow chains
# Verify: events_history includes parent chain + re-entry nodes
```

### Expected Results
- Trade `entry_flow_ids` count: 3-5 events
- Trade `exit_flow_ids` count: 5-10 events (includes entry chain)
- `events_history` size: Same as total unique flow IDs
- All flow IDs resolvable in `events_history`

---

## Backend Implementation

### File: `live_simulation_sse.py`

**Function:** `emit_trade_update(trade_payload)`
- Extracts relevant events using `_extract_trade_events()`
- Bundles trade + summary + events_history
- Emits via SSE as `trade_update` event

**Function:** `_extract_trade_events(trade)`
- Reads `entry_flow_ids` and `exit_flow_ids` from trade
- Looks up matching events in `self.diagnostics["events_history"]`
- Returns filtered subset of events_history

---

## Summary

**What changed:**
- ✅ `trade_update` event now includes `events_history`
- ✅ Polling API no longer returns `events_history`
- ✅ UI gets everything in one SSE message

**Why better:**
- ✅ No race conditions
- ✅ Atomic delivery
- ✅ Reduced requests
- ✅ Simpler UI code

**UI action required:**
- Update SSE handler to read `events_history` from `trade_update` event
- Remove polling logic for events_history
- Use bundled events for flow diagrams
