# Backend-UI Data Flow Architecture Plan

## Current State Analysis

### Backend Event Emissions (Live Backtest Runner)

#### 1. **Tick Update** (Every Tick)
- **Frequency**: Every tick (~23,400 ticks/day for 1-min data)
- **Current Content**:
  ```json
  {
    "timestamp": "2024-10-29T09:15:00+05:30",
    "progress": { "ticks_processed": 100, "total_ticks": 23400 },
    "active_nodes": ["entry-1", "exit-condition-2"],
    "pending_nodes": [],
    "positions": [...],  // Unified list (open + closed)
    "open_positions": [...],  // Filtered
    "closed_positions": [...],  // Filtered
    "pnl_summary": { "realized_pnl": "100.00", "unrealized_pnl": "-50.00" },
    "ltp_store": { "NIFTY:2024-11-07:OPT:24250:PE": { "ltp": 181.60 } },
    "candle_data": { "NIFTY": { "1min": {...} } }
  }
  ```
- **Size**: ~5-50KB per tick (varies with positions)
- **Issue**: Too heavy for every tick

#### 2. **Node Event** (When Node Completes)
- **Frequency**: ~10-50 times/day (when nodes execute)
- **Current Content**:
  ```json
  {
    "execution_id": "exec_entry-2_20241029_091900_51380c",
    "parent_execution_id": "exec_entry-condition-1_20241029_091900_112a10",
    "timestamp": "2024-10-29T09:19:00+05:30",
    "node_type": "EntryNode",
    "node_id": "entry-2",
    "node_name": "Entry 2 - Bullish",
    "action": { "type": "place_order", "symbol": "...", "price": 181.60 },
    "position": { "position_id": "entry-2-pos1", "entry_price": 181.60 },
    "entry_config": { "position_num": 1, "re_entry_num": 0 }
  }
  ```
- **Issue**: Missing position state snapshot at action completion

#### 3. **Trade Update** (Position Closed)
- **Frequency**: ~5-15 times/day (when positions close)
- **Current Content**:
  ```json
  {
    "trade_id": "entry-3-pos1",
    "position_id": "entry-3-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:...",
    "entry_price": "262.05",
    "exit_price": "287.80",
    "pnl": "-25.75",
    "entry_flow_ids": [...],
    "exit_flow_ids": [...]
  }
  ```
- **Issue**: Only emitted on close, not on entry

---

## Problems Identified

### 1. **Trade Event Timing**
- **Current**: Only emits when position closes (Exit/SquareOff)
- **Required**: Emit on ALL action nodes (Entry, Exit, SquareOff)
  - Entry: Emit with entry data + flow + unrealized P&L = 0
  - Exit/SquareOff: Emit with exit data + flow + realized P&L

### 2. **Position State Ambiguity**
- Position = (position_id + re_entry_num)
- Current `positions` list doesn't clearly show:
  - Partial closes (50% qty closed)
  - Re-entry sequence
  - P&L breakdown (realized vs unrealized)

### 3. **P&L Calculation Complexity**
- **Fully Open**: Only unrealized P&L
- **Fully Closed**: Only realized P&L
- **Partially Closed**: Need both realized (closed qty) + unrealized (open qty)
- GPS tracks this, but not clearly exposed

### 4. **Tick Update Weight**
- Sending full position list every tick is heavy
- UI needs delta updates, not full snapshots

---

## Proposed Architecture

### Core Principles
1. **Event-Driven**: Emit events when state changes (not on every tick)
2. **Incremental**: Send only what changed
3. **Single Source of Truth**: Backend GPS is authoritative
4. **UI Reconstruction**: UI builds state from events

---

## Data Flow Design

### Backend Responsibilities

#### 1. **Tick Update** (Every Tick) - LIGHTWEIGHT
```json
{
  "event_type": "tick_update",
  "timestamp": "2024-10-29T09:15:00+05:30",
  "progress": {
    "ticks_processed": 100,
    "total_ticks": 23400,
    "progress_percentage": 0.43
  },
  "active_nodes": ["entry-1", "exit-condition-2"],
  "ltp_updates": {  // Only changed symbols
    "NIFTY:2024-11-07:OPT:24250:PE": 181.60
  },
  "pnl_snapshot": {  // Recalculated with new LTP
    "realized_pnl": "100.00",
    "unrealized_pnl": "-50.00",
    "total_pnl": "50.00"
  }
}
```
- **Size**: ~1-2KB (minimal)
- **Purpose**: Progress, active nodes, LTP changes, P&L recalc
- **No positions** - UI calculates unrealized P&L from LTP updates

#### 2. **Node Event** (Node Execution) - UNCHANGED
```json
{
  "event_type": "node_event",
  "execution_id": "exec_entry-2_20241029_091900_51380c",
  "parent_execution_id": "...",
  "timestamp": "2024-10-29T09:19:00+05:30",
  "node_type": "EntryNode",
  "node_id": "entry-2",
  "node_name": "Entry 2 - Bullish",
  "action": {...},
  "position": {...},
  "entry_config": {...}
}
```
- **Purpose**: Execution flow tracking (UI event history)

#### 3. **Position Event** (Action Node Completion) - NEW
Emitted when EntryNode, ExitNode, or SquareOffNode completes.

**On Entry (EntryNode completion):**
```json
{
  "event_type": "position_event",
  "action": "entry",
  "timestamp": "2024-10-29T09:19:00+05:30",
  "execution_id": "exec_entry-2_20241029_091900_51380c",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity": 1,
    "entry_price": "181.60",
    "entry_time": "2024-10-29T09:19:00+05:30",
    "status": "OPEN",
    "entry_flow_ids": ["exec_strategy-controller_...", "exec_entry-2_..."],
    "entry_trigger": "Entry 2 - Bullish"
  },
  "pnl": {
    "realized_pnl": "0.00",
    "unrealized_pnl": "0.00"  // Calculated with current LTP
  }
}
```

**On Exit (ExitNode/SquareOffNode completion):**
```json
{
  "event_type": "position_event",
  "action": "exit",
  "timestamp": "2024-10-29T10:48:00+05:30",
  "execution_id": "exec_exit-3_20241029_104800_ab99d0",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity": 1,  // Qty closed
    "entry_price": "181.60",
    "entry_time": "2024-10-29T09:19:00+05:30",
    "exit_price": "260.05",
    "exit_time": "2024-10-29T10:48:00+05:30",
    "status": "CLOSED",  // or "PARTIAL" if qty_closed < qty_total
    "exit_flow_ids": ["exec_strategy-controller_...", "exec_exit-3_..."],
    "exit_reason": "Exit - SL Hit"
  },
  "pnl": {
    "realized_pnl": "-78.45",  // For closed qty
    "unrealized_pnl": "0.00"   // Remaining qty (if partial)
  }
}
```

**On Partial Exit:**
```json
{
  "event_type": "position_event",
  "action": "partial_exit",
  "timestamp": "2024-10-29T10:30:00+05:30",
  "execution_id": "exec_exit-3_20241029_103000_xyz123",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:...",
    "quantity_total": 2,      // Original qty
    "quantity_closed": 1,     // Qty closed in this exit
    "quantity_remaining": 1,  // Qty still open
    "entry_price": "181.60",
    "exit_price": "200.00",   // Price for this partial exit
    "status": "PARTIAL"
  },
  "pnl": {
    "realized_pnl": "-18.40",     // P&L for closed qty (1 lot)
    "unrealized_pnl": "-18.40",   // P&L for remaining qty (1 lot) at current LTP
    "total_pnl": "-36.80"
  }
}
```

---

### UI Responsibilities

#### 1. **Event History Store** (In-Memory)
```typescript
interface NodeEvent {
  execution_id: string;
  parent_execution_id: string;
  timestamp: string;
  node_type: string;
  node_id: string;
  // ... full event payload
}

const eventHistory: Map<string, NodeEvent> = new Map();
```
- **Purpose**: Diagnostics, flow visualization
- **Storage**: Keep all events (append-only)

#### 2. **Position Store** (In-Memory) - GPS-like
```typescript
interface Position {
  position_id: string;
  re_entry_num: number;
  symbol: string;
  side: string;
  quantity_total: number;
  quantity_closed: number;
  quantity_remaining: number;
  entry_price: number;
  entry_time: string;
  exit_price?: number;
  exit_time?: string;
  status: 'OPEN' | 'PARTIAL' | 'CLOSED';
  realized_pnl: number;
  unrealized_pnl: number;
  entry_flow_ids: string[];
  exit_flow_ids: string[];
}

const positions: Map<string, Position> = new Map(); // Key: `${position_id}-${re_entry_num}`
```
- **Purpose**: Current position state
- **Updates**:
  - On `position_event` (entry/exit): Update position
  - On `tick_update` (LTP change): Recalculate unrealized P&L for open positions

#### 3. **Trade History** (In-Memory)
```typescript
interface Trade {
  trade_id: string;
  position_id: string;
  re_entry_num: number;
  symbol: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  status: 'CLOSED';
  // ... full trade data
}

const tradeHistory: Trade[] = [];
```
- **Purpose**: Completed trades (for P&L analysis)
- **Source**: Derived from `position_event` with `action: "exit"` and `status: "CLOSED"`

#### 4. **P&L Calculator** (Real-time)
```typescript
function calculatePnL(positions: Map<string, Position>, ltpStore: Map<string, number>) {
  let realized = 0;
  let unrealized = 0;
  
  for (const [key, pos] of positions.entries()) {
    // Add realized P&L (from closed qty)
    realized += pos.realized_pnl;
    
    // Calculate unrealized P&L (from open qty with current LTP)
    if (pos.quantity_remaining > 0) {
      const currentLTP = ltpStore.get(pos.symbol) || pos.entry_price;
      const pnl = pos.side === 'BUY' 
        ? (currentLTP - pos.entry_price) * pos.quantity_remaining
        : (pos.entry_price - currentLTP) * pos.quantity_remaining;
      unrealized += pnl;
    }
  }
  
  return { realized, unrealized, total: realized + unrealized };
}
```

---

## Event Emission Logic (Backend)

### When to Emit Position Event

```python
# In live_backtest_runner.py

def _emit_position_events(self, node_events_history):
    """
    Emit position_event when action nodes complete.
    """
    for exec_id, event in new_events:
        node_type = event.get('node_type')
        
        if node_type == 'EntryNode':
            # Entry completed - emit position with OPEN status
            position_data = self._build_position_from_entry(event)
            self.session.emit_position_event({
                'action': 'entry',
                'position': position_data,
                'pnl': {'realized_pnl': 0, 'unrealized_pnl': 0}
            })
        
        elif node_type in ['ExitNode', 'SquareOffNode']:
            # Exit completed - emit position with CLOSED/PARTIAL status
            position_data = self._build_position_from_exit(event)
            self.session.emit_position_event({
                'action': 'exit' if position_data['status'] == 'CLOSED' else 'partial_exit',
                'position': position_data,
                'pnl': self._calculate_pnl(position_data)
            })
```

---

## Summary: Backend vs UI Responsibilities

| Aspect | Backend | UI |
|--------|---------|-----|
| **Node Events** | Emit when node completes | Store in event history |
| **Position Tracking** | Emit on action node completion | Maintain position store (GPS-like) |
| **P&L Calculation** | Realized P&L (on close), send unrealized snapshot | Recalculate unrealized P&L on LTP updates |
| **Trade History** | Emit closed positions | Build from position events |
| **Tick Updates** | Send progress + LTP changes | Update unrealized P&L |

---

## Benefits

### 1. **Reduced Bandwidth**
- Tick updates: ~1-2KB (no positions)
- Position events: Only when action happens (~10-20/day)
- Total: ~90% reduction vs current

### 2. **Clear State Separation**
- Events = Immutable history
- Positions = Mutable state (like GPS)
- Trades = Derived from closed positions

### 3. **Flexible UI**
- Can reconstruct full state from events
- Can show real-time P&L with LTP updates
- Can handle partial closes elegantly

### 4. **Scalability**
- Event-driven = handles multi-leg, partial closes
- Position store = O(1) lookups by (position_id, re_entry_num)
- No need to send full snapshot every tick

---

## Implementation Phases

### Phase 1: Backend Changes (Priority)
1. Add `emit_position_event()` to SSE session
2. Detect action node completions (Entry/Exit/SquareOff)
3. Build position payload with P&L from GPS
4. Emit position event on action completion

### Phase 2: Optimize Tick Updates
1. Remove `positions` from tick_state
2. Keep only `ltp_updates` (delta, not full store)
3. Send P&L snapshot (backend calculates)

### Phase 3: UI Integration
1. Add position store (Map)
2. Handle position events (entry/exit/partial)
3. Recalculate unrealized P&L on LTP updates
4. Build trade history from closed positions

---

## Open Questions for Discussion

1. **Partial Closes**: Should we support partial qty exits? (Strategy dependent)
2. **Historical Playback**: Should UI be able to rebuild state from events alone?
3. **Position Aggregation**: Should UI aggregate multi-leg positions? (e.g., Iron Condor)
4. **P&L Granularity**: Per position or aggregated only?
