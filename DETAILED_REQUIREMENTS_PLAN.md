# Detailed Requirements & Implementation Plan

## User Requirements Summary

### Position Display Requirements
1. ✅ Show positions when opened (keep existing positions intact)
2. ✅ Display qty (for options: qty × lot_size)
3. ❌ Remove Duration and Trigger columns
4. ✅ Update unrealized P&L on every tick for open positions
5. ✅ Partial close handling: keep position open, show both realized (closed qty) + unrealized (remaining qty)
6. ✅ Quantity column shows: "50/100 closed" or "Closed qty: Full"

### Dashboard P&L Requirements
1. ✅ Show Unrealized P&L (sum of all open positions)
2. ✅ Show Realized P&L (sum of all closed trades)
3. ✅ Show Total P&L (Unrealized + Realized)
4. ❌ Remove Winners/Losers counts (not needed)

### Flow & Events Requirements
1. ✅ Node events incrementally updated to UI cache
2. ✅ Entry flow display (reuse existing node details on click)
3. ✅ Exit flow display (reuse existing node details on click)
4. ✅ Partial exits: separate flow tabs for each partial exit

### Position Lifecycle
1. ✅ Open: Entry node completes
2. ✅ Update: Every tick (unrealized P&L recalculation)
3. ✅ Partial Close: Some qty closed, position stays open
4. ✅ Full Close: All qty closed, position closed

---

## Current Data Being Sent to UI

### 1. **Tick Update** (Every Tick)
**File:** `live_backtest_runner.py` line ~626

```json
{
  "timestamp": "2024-10-29T09:15:00+05:30",
  "current_time": "2024-10-29 09:15:00",
  "progress": {
    "ticks_processed": 100,
    "total_ticks": 23400,
    "progress_percentage": 0.43
  },
  "active_nodes": ["entry-1", "exit-condition-2"],
  "pending_nodes": [],
  "positions": [
    {
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "SELL",
      "quantity": 1,
      "entry_price": "181.60",
      "current_price": 185.50,
      "unrealized_pnl": -3.90,
      "entry_time": "2024-10-29 09:19:00",
      "exit_price": null,
      "exit_time": null,
      "pnl": null,
      "status": "OPEN"
    }
  ],
  "open_positions": [...],  // Filtered
  "closed_positions": [...],  // Filtered
  "pnl_summary": {
    "realized_pnl": "100.00",
    "unrealized_pnl": "-50.00",
    "total_pnl": "50.00",
    "closed_trades": 5,
    "open_trades": 2
  },
  "ltp_store": {
    "NIFTY:2024-11-07:OPT:24250:PE": {
      "ltp": 185.50,
      "timestamp": "2024-10-29T09:15:00+05:30"
    }
  },
  "candle_data": {...}
}
```

**Issue:** Sending full positions array every tick (~5-50KB) is heavy

### 2. **Node Event** (When Node Executes)
**File:** `live_backtest_runner.py` line ~582

```json
{
  "execution_id": "exec_entry-2_20241029_091900_51380c",
  "parent_execution_id": "exec_entry-condition-1_20241029_091900_112a10",
  "timestamp": "2024-10-29T09:19:00+05:30",
  "node_type": "EntryNode",
  "node_id": "entry-2",
  "node_name": "Entry 2 - Bullish",
  "action": {
    "type": "place_order",
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity": 1,
    "price": 181.60
  },
  "position": {
    "position_id": "entry-2-pos1",
    "entry_price": 181.60,
    "entry_time": "2024-10-29T09:19:00+05:30"
  },
  "entry_config": {
    "position_num": 1,
    "re_entry_num": 0
  }
}
```

**Good:** Already incremental (only new events)

### 3. **Trade Update** (Position Closes)
**File:** `live_backtest_runner.py` line ~556

```json
{
  "trade_id": "entry-2-pos1",
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  "side": "SELL",
  "quantity": 1,
  "entry_price": "181.60",
  "exit_price": "260.05",
  "pnl": "-78.45",
  "entry_flow_ids": ["exec_strategy-controller_...", "exec_entry-2_..."],
  "exit_flow_ids": ["exec_strategy-controller_...", "exec_exit-3_..."]
}
```

**Issue:** Only emitted on full close, not on entry or partial close

---

## New Data Structure Design

### 1. **Position Event** (On Entry/Exit/Partial)

#### **On Entry:**
```json
{
  "event_type": "position_update",
  "action": "entry",
  "timestamp": "2024-10-29T09:19:00+05:30",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity": 1,
    "lot_size": 50,  // NEW: For options qty calculation
    "effective_quantity": 50,  // NEW: qty × lot_size
    "quantity_entered": 50,  // NEW: Total entered
    "quantity_closed": 0,  // NEW: Total closed
    "quantity_remaining": 50,  // NEW: Still open
    "entry_price": "181.60",
    "entry_time": "2024-10-29T09:19:00+05:30",
    "status": "OPEN",
    "entry_flow_ids": ["exec_strategy-controller_...", "exec_entry-2_..."]
  },
  "pnl": {
    "realized": 0.00,  // From closed qty
    "unrealized": 0.00,  // From remaining qty at current LTP
    "total": 0.00
  }
}
```

#### **On Partial Exit:**
```json
{
  "event_type": "position_update",
  "action": "partial_exit",
  "timestamp": "2024-10-29T10:30:00+05:30",
  "execution_id": "exec_exit-3_20241029_103000_abc123",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity_entered": 50,  // Original
    "quantity_closed": 25,  // Closed so far
    "quantity_remaining": 25,  // Still open
    "entry_price": "181.60",
    "exit_price_partial": "200.00",  // Price for this partial exit
    "exit_time_partial": "2024-10-29T10:30:00+05:30",
    "status": "PARTIAL",
    "partial_exits": [  // NEW: Track each partial exit
      {
        "execution_id": "exec_exit-3_20241029_103000_abc123",
        "qty_closed": 25,
        "exit_price": "200.00",
        "exit_time": "2024-10-29T10:30:00+05:30",
        "pnl": -460.00,  // (181.60 - 200.00) × 25
        "exit_flow_ids": ["exec_strategy-controller_...", "exec_exit-3_..."]
      }
    ]
  },
  "pnl": {
    "realized": -460.00,  // From closed 25 qty
    "unrealized": -460.00,  // From remaining 25 qty at current LTP
    "total": -920.00
  }
}
```

#### **On Full Close:**
```json
{
  "event_type": "position_update",
  "action": "full_close",
  "timestamp": "2024-10-29T10:48:00+05:30",
  "execution_id": "exec_exit-3_20241029_104800_xyz789",
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "quantity_entered": 50,
    "quantity_closed": 50,  // Fully closed
    "quantity_remaining": 0,
    "exit_price_final": "260.05",  // Final exit price
    "exit_time_final": "2024-10-29T10:48:00+05:30",
    "status": "CLOSED"
  },
  "pnl": {
    "realized": -3922.50,  // Total realized from all exits
    "unrealized": 0.00,  // No remaining qty
    "total": -3922.50
  }
}
```

### 2. **Tick Update** (Lightweight - No Positions)
```json
{
  "event_type": "tick_update",
  "timestamp": "2024-10-29T09:15:00+05:30",
  "active_nodes": ["entry-1", "exit-condition-2"],
  "ltp_updates": {  // Only changed symbols (delta)
    "NIFTY:2024-11-07:OPT:24250:PE": 185.50
  },
  "pnl_summary": {
    "realized": 100.00,
    "unrealized": -50.00,
    "total": 50.00
  }
}
```

### 3. **Node Event** (Unchanged)
Current structure is good - no changes needed.

---

## UI Data Store Design

### **Position Store** (Map)
```typescript
interface Position {
  position_id: string;
  re_entry_num: number;
  symbol: string;
  side: string;
  quantity_entered: number;  // Total entered
  quantity_closed: number;  // Total closed
  quantity_remaining: number;  // Still open
  lot_size: number;  // For options
  effective_quantity: number;  // qty × lot_size
  entry_price: number;
  entry_time: string;
  status: 'OPEN' | 'PARTIAL' | 'CLOSED';
  entry_flow_ids: string[];
  partial_exits: Array<{
    execution_id: string;
    qty_closed: number;
    exit_price: number;
    exit_time: string;
    pnl: number;
    exit_flow_ids: string[];
  }>;
  exit_price_final?: number;  // Final exit (full close)
  exit_time_final?: string;
  realized_pnl: number;  // From closed qty
  unrealized_pnl: number;  // From remaining qty
  total_pnl: number;
}

const positions = new Map<string, Position>(); // Key: `${position_id}-${re_entry_num}`
```

### **Update Logic**

#### On `position_update` event:
```typescript
const key = `${position.position_id}-${position.re_entry_num}`;

if (action === 'entry') {
  // New position
  positions.set(key, {
    ...position,
    realized_pnl: 0,
    unrealized_pnl: 0,
    total_pnl: 0,
    partial_exits: []
  });
}
else if (action === 'partial_exit') {
  // Update existing position
  const pos = positions.get(key);
  if (pos) {
    pos.quantity_closed = position.quantity_closed;
    pos.quantity_remaining = position.quantity_remaining;
    pos.status = 'PARTIAL';
    pos.partial_exits.push(position.partial_exits[0]);  // Add new partial exit
    pos.realized_pnl = pnl.realized;
    pos.unrealized_pnl = pnl.unrealized;
    pos.total_pnl = pnl.total;
  }
}
else if (action === 'full_close') {
  // Close position
  const pos = positions.get(key);
  if (pos) {
    pos.quantity_closed = position.quantity_closed;
    pos.quantity_remaining = 0;
    pos.status = 'CLOSED';
    pos.exit_price_final = position.exit_price_final;
    pos.exit_time_final = position.exit_time_final;
    pos.realized_pnl = pnl.realized;
    pos.unrealized_pnl = 0;
    pos.total_pnl = pnl.realized;
  }
}
```

#### On `tick_update` (LTP change):
```typescript
// Recalculate unrealized P&L for open positions
for (const [key, pos] of positions.entries()) {
  if (pos.quantity_remaining > 0) {
    const currentLTP = ltpUpdates[pos.symbol];
    if (currentLTP) {
      const entryPrice = pos.entry_price;
      const qty = pos.quantity_remaining;
      
      pos.unrealized_pnl = pos.side === 'SELL'
        ? (entryPrice - currentLTP) * qty
        : (currentLTP - entryPrice) * qty;
      
      pos.total_pnl = pos.realized_pnl + pos.unrealized_pnl;
    }
  }
}
```

---

## UI Display

### **Position Table**
```
| Symbol              | Side | Qty        | Entry   | Current | P&L     | Status  |
|--------------------|------|------------|---------|---------|---------|---------|
| NIFTY:...:24250:PE | SELL | 25/50      | 181.60  | 190.00  | -920.00 | PARTIAL |
| NIFTY:...:24300:CE | SELL | Closed:Full| 262.05  | 287.80  | -25.75  | CLOSED  |
| NIFTY:...:24350:PE | SELL | 50         | 254.65  | 260.00  | -267.50 | OPEN    |
```

**Qty Column Logic:**
- Open: `50` (quantity_remaining)
- Partial: `25/50` (quantity_closed / quantity_entered)
- Closed: `Closed: Full`

### **Dashboard P&L Cards**
```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Unrealized P&L   │  │ Realized P&L     │  │ Total P&L        │
│                  │  │                  │  │                  │
│    -267.50       │  │    -920.00       │  │   -1,187.50      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### **Flow Display** (Click on position row)
```
Entry Flow:
├── strategy-controller (StartNode)
├── entry-condition-1 (EntrySignalNode)
└── entry-2 (EntryNode) ← Click for node details

Exit Flow 1 (Partial - 25 qty):
├── strategy-controller (StartNode)
├── exit-condition-2 (ExitSignalNode)
└── exit-3 (ExitNode) ← Click for node details

Exit Flow 2 (Final - 25 qty):
├── strategy-controller (StartNode)
├── exit-condition-2 (ExitSignalNode)
└── exit-3 (ExitNode) ← Click for node details
```

---

## Implementation Phases (Revised)

### **Phase 1: Backend - Position Tracking with Qty**
**Goal:** Track quantity_entered, quantity_closed, quantity_remaining

**Changes:**
1. Modify GPS to track qty splits (partial closes)
2. Add lot_size to position data
3. Track partial_exits array in position

**File:** `src/core/gps.py`, `live_backtest_runner.py`

### **Phase 2: Backend - Position Update Events on Entry**
**Goal:** Emit position_update event when entry completes

**Changes:**
1. Add `emit_position_update()` method
2. Detect newly opened positions
3. Emit with action='entry'

**File:** `live_backtest_runner.py`, `live_simulation_sse.py`

### **Phase 3: Backend - Position Update Events on Partial Exit**
**Goal:** Emit position_update event on partial close

**Changes:**
1. Detect partial closes (qty_closed < qty_entered)
2. Track partial_exits array
3. Emit with action='partial_exit'

**File:** `live_backtest_runner.py`

### **Phase 4: Backend - Position Update Events on Full Close**
**Goal:** Emit position_update event on full close

**Changes:**
1. Detect full closes (qty_closed == qty_entered)
2. Emit with action='full_close'

**File:** `live_backtest_runner.py`

### **Phase 5: Backend - P&L Calculation**
**Goal:** Calculate realized + unrealized P&L correctly

**Changes:**
1. Realized P&L: Sum of all partial exits
2. Unrealized P&L: Remaining qty × (current_ltp - entry_price)
3. Total P&L: realized + unrealized

**File:** `live_backtest_runner.py`

### **Phase 6: Backend - Lightweight Tick Updates**
**Goal:** Remove positions from tick_update, only send LTP deltas

**Changes:**
1. Remove positions array from tick_state
2. Send only changed LTP values
3. Send P&L summary only

**File:** `live_backtest_runner.py`

### **Phase 7: UI - Position Store**
**Goal:** Create position store in UI

**Changes:**
1. Add Map<string, Position>
2. Handle position_update events
3. Update on entry/partial/full_close

**File:** `useSSELiveData.ts` or similar

### **Phase 8: UI - Live P&L Calculation**
**Goal:** Recalculate unrealized P&L on LTP updates

**Changes:**
1. Listen to ltp_updates
2. Recalculate unrealized_pnl for open positions
3. Update dashboard cards

**File:** `useSSELiveData.ts`

### **Phase 9: UI - Position Table Display**
**Goal:** Show positions with qty, P&L, status

**Changes:**
1. Render position table
2. Show qty column logic (25/50, Closed:Full)
3. Show P&L (live updating for open)

**File:** Positions component

### **Phase 10: UI - Flow Display**
**Goal:** Show entry/exit flows with node details

**Changes:**
1. Render entry_flow_ids
2. Render multiple exit_flow_ids (for partial exits)
3. Reuse existing node detail popup

**File:** Flow component

---

## Testing Strategy

Each phase:
1. Run backtest
2. Check console logs / SSE events
3. Verify data structure
4. Test with UI (if UI phase)
5. Confirm no breaking changes

---

## Questions:

1. **GPS Support**: Does GPS already support partial closes? Or do we need to add qty tracking?
2. **Lot Size**: Where do we get lot_size from? Is it in symbol metadata?
3. **Start with Phase 1?** Backend position tracking with qty?
4. **UI Framework**: What UI framework are you using? React? Next.js?

Let me know and I'll start implementation phase by phase!
