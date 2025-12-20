# SSE Events and Trades - Final Architecture

## Overview
Node execution events and trade updates are sent separately via SSE. UI caches node events and resolves flow IDs when trades arrive. This avoids redundancy and memory bloat.

---

## Architecture

### Data Flow

```
Backend                           SSE                          UI
--------                          ---                          --
Node executes                     
  ↓
Add to diagnostics                
  ↓
Emit node_events          →→→  node_events event      →→→  Cache in eventsHistory
                                                              {exec_id: event_data}

Position closes
  ↓
Build trade with flow IDs
  ↓
Emit trade_update         →→→  trade_update event     →→→  Look up flow IDs
                                {                              from cached events
                                  entry_flow_ids: [...],       ↓
                                  exit_flow_ids: [...]      Render flow diagram
                                }
```

### Why This Design?

**Problem with bundling:**
```
Trade 1: [A, B, C] → [A, B, C, D, E]     (5 events)
Trade 2: [A, B, C, D, E, F, G] → [...]   (9 events)

Bundled: Send 14 events (A-E sent twice) ❌
Separate: Send 9 events once ✅
```

**Benefits:**
- ✅ No redundant data - each event sent once
- ✅ Memory efficient - UI caches unique events
- ✅ Works for re-entry trades - shared parent chains
- ✅ Real-time - events arrive as they execute
- ✅ Complete history - UI has full event log

---

## SSE Events

### Event 1: `node_events` (Incremental)

**Sent when:** Nodes execute (entry conditions, order placements, exits)

**Frequency:** Multiple per tick (as nodes execute)

**Compression:** gzip + base64

**Structure:**
```json
{
  "event": "node_events",
  "data": {
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
            "current_value": 24500,
            "threshold": 24450
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
        "price": 181.60
      }
    }
  }
}
```

**Key Points:**
- Contains multiple events per emission
- Each event has unique `execution_id`
- Events linked via `parent_execution_id`
- Complete node execution details included

---

### Event 2: `trade_update` (Per Trade)

**Sent when:** A position closes (trade completes)

**Frequency:** Once per closed trade

**Compression:** gzip + base64

**Structure:**
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
    }
  }
}
```

**Key Points:**
- Contains trade details + P&L summary
- Has `entry_flow_ids` and `exit_flow_ids` arrays
- **NO events_history included** - UI resolves from cache
- Small payload (just IDs, not full events)

---

### Event 3: `tick_update` (Every Tick)

**Sent when:** Every market tick

**Frequency:** Every 1-5 seconds (depends on timeframe)

**Compression:** None (needs to be fast)

**Structure:**
```json
{
  "event": "tick_update",
  "data": {
    "timestamp": "2024-10-29T09:19:05+05:30",
    "current_time": "2024-10-29T09:19:05+05:30",
    "open_positions": [
      {
        "position_id": "entry-2-pos1",
        "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
        "side": "sell",
        "quantity": 1,
        "entry_price": 181.60,
        "current_price": 185.30,
        "unrealized_pnl": -3.70
      }
    ],
    "pnl_summary": {
      "realized_pnl": 0.00,
      "unrealized_pnl": -3.70,
      "total_pnl": -3.70,
      "closed_trades": 0,
      "open_trades": 1
    },
    "active_nodes": ["entry-condition-1", "exit-condition-2"],
    "ltp_store": {
      "NIFTY:2024-11-07:OPT:24250:PE": 185.30
    }
  }
}
```

---

## UI Implementation

### State Management

```typescript
// Store events in memory as they arrive
const [eventsHistory, setEventsHistory] = useState<Record<string, any>>({});
const [trades, setTrades] = useState<Trade[]>([]);

// SSE Event Handlers
eventSource.addEventListener('node_events', (event) => {
  const data = decompressAndParse(event.data);
  
  // Merge new events into cache
  setEventsHistory(prev => ({
    ...prev,
    ...data  // data is {exec_id: event_data, ...}
  }));
});

eventSource.addEventListener('trade_update', (event) => {
  const { trade, summary } = decompressAndParse(event.data);
  
  // Resolve flow IDs from cached events
  const entryFlow = trade.entry_flow_ids.map(id => eventsHistory[id]);
  const exitFlow = trade.exit_flow_ids.map(id => eventsHistory[id]);
  
  // Update UI
  setTrades(prev => [...prev, trade]);
  updatePnLSummary(summary);
  renderFlowDiagram(entryFlow, exitFlow);
});
```

### Flow Diagram Resolution

```typescript
function getFlowNodes(flowIds: string[], eventsHistory: Record<string, any>) {
  return flowIds
    .map(id => eventsHistory[id])
    .filter(event => event !== undefined)  // Handle missing events gracefully
    .map(event => ({
      id: event.execution_id,
      name: event.node_name,
      type: event.node_type,
      timestamp: event.timestamp,
      details: event.evaluated_conditions || event.order_details
    }));
}

// Usage
const entryNodes = getFlowNodes(trade.entry_flow_ids, eventsHistory);
const exitNodes = getFlowNodes(trade.exit_flow_ids, eventsHistory);
```

### Handling Missing Events

```typescript
// Check if all flow IDs are resolved
const missingIds = trade.entry_flow_ids.filter(id => !eventsHistory[id]);

if (missingIds.length > 0) {
  console.warn(`⚠️ Missing events: ${missingIds.join(', ')}`);
  // Option 1: Wait for events to arrive
  // Option 2: Fetch from diagnostics endpoint
  // Option 3: Show partial flow with warning
}
```

---

## Memory Management

### Backend (Python)

```python
class LiveSimulationState:
    def __init__(self):
        self.diagnostics = {
            "events_history": {},  # Grows with each node execution
            "current_state": {}    # Fixed size (one per node)
        }
    
    def add_node_event(self, execution_id, event_payload):
        # Add to events_history (append-only)
        self.diagnostics["events_history"][execution_id] = event_payload
        
        # Update current_state (overwrite per node)
        node_id = event_payload.get("node_id")
        self.diagnostics["current_state"][node_id] = event_payload
        
        # Emit via SSE
        self._emit_node_events({execution_id: event_payload})
```

**Memory growth:**
- `events_history`: O(n) where n = total node executions
- `current_state`: O(m) where m = number of nodes
- For 10k ticks, ~50k events, ~100 nodes → ~10MB memory

### UI (JavaScript)

```typescript
// Store in React state or Context
const [eventsHistory, setEventsHistory] = useState<Record<string, any>>({});

// Memory growth: Same as backend
// For 10k ticks: ~50k events → ~10MB in browser memory
// Modern browsers handle this easily
```

---

## Session Lifecycle

### 1. Session Start
```
UI connects to SSE → Receives initial_state (if any)
```

### 2. Active Trading
```
node_events arrive → UI caches them
tick_update arrives → UI updates positions/PnL
trade_update arrives → UI resolves flows + renders
```

### 3. Session Complete
```
Backend: status = "completed"
Backend: Emit session_complete event
Backend: Remove from memory
UI: Stop polling, keep cached events for review
```

### 4. Post-Completion Review
```
UI: Can still view trades + flow diagrams
UI: Events cached in browser, no backend needed
Optional: Fetch diagnostics file for long-term storage
```

---

## Polling API (Lightweight)

### `/api/live-trading/dashboard/{user_id}`

**Purpose:** Get active sessions snapshot (NOT events)

**Response:**
```json
{
  "total_sessions": 1,
  "active_sessions": 1,
  "sessions": {
    "sim-xxx": {
      "status": "running",
      "data": {
        "gps_data": {
          "positions": [...],
          "trades": [...],  // Trade list with flow IDs
          "pnl": {...}
        },
        "market_data": {
          "ltp_store": {...}
        }
      }
    }
  }
}
```

**Key Points:**
- ❌ NO events_history in response
- ✅ Includes trades with flow IDs
- ✅ UI resolves flows from SSE-cached events
- ✅ Lightweight response (~10KB vs ~10MB)

---

## Comparison: Bundled vs Separated

### Bundled Approach (❌ Inefficient)

```
Trade 1: Send 5 events (A, B, C, D, E)
Trade 2: Send 9 events (A, B, C, D, E, F, G, H, I)
Trade 3: Send 12 events (A, B, C, D, E, F, G, H, I, J, K, L)

Total: 26 events sent (A-E sent 3 times, F-I sent 2 times)
Redundancy: ~60%
```

### Separated Approach (✅ Efficient)

```
As nodes execute: Send A, B, C, D, E, F, G, H, I, J, K, L once
Trade 1: Send flow IDs [A, B, C, D, E]
Trade 2: Send flow IDs [A, B, C, D, E, F, G, H, I]
Trade 3: Send flow IDs [A, B, C, D, E, F, G, H, I, J, K, L]

Total: 12 events sent once + 3 flow ID arrays
Redundancy: 0%
```

---

## Error Handling

### Missing Events in Cache

**Scenario:** Trade arrives before some node events

**Solution:**
```typescript
// Check for missing events
const allFlowIds = [...trade.entry_flow_ids, ...trade.exit_flow_ids];
const missingIds = allFlowIds.filter(id => !eventsHistory[id]);

if (missingIds.length > 0) {
  // Wait briefly for events to arrive
  setTimeout(() => {
    // Retry flow resolution
    const resolved = getFlowNodes(allFlowIds, eventsHistory);
    if (resolved.length === allFlowIds.length) {
      renderFlowDiagram(resolved);
    } else {
      console.warn('Some events still missing');
    }
  }, 1000);
}
```

### SSE Reconnection

**Scenario:** Connection drops, events missed

**Solution:**
```typescript
eventSource.addEventListener('error', () => {
  // Reconnect to SSE
  reconnectSSE();
  
  // Fetch diagnostics file to rebuild cache
  const diagnostics = await fetch(`/api/session/${sessionId}/diagnostics`);
  setEventsHistory(diagnostics.events_history);
});
```

---

## Summary

### Data Flow
1. **node_events** → UI caches → eventsHistory
2. **trade_update** → UI resolves flow IDs → render
3. **tick_update** → UI updates live data

### Memory
- Backend: Events stored once, trades reference IDs
- UI: Events cached once, trades lookup from cache
- Zero redundancy, efficient memory usage

### Performance
- Reduced SSE payload size (no duplicate events)
- Fast flow resolution (O(1) lookup from cache)
- Scalable (handles 100k+ events efficiently)

### UI Requirements
- Cache node_events in state/context
- Resolve flow IDs when trade_update arrives
- Handle missing events gracefully
- Clear cache on session end (optional)
