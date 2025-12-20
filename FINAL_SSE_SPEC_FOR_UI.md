# SSE Backend Specification - Final Implementation

**Date:** December 15, 2024  
**Status:** READY FOR UI INTEGRATION

---

## Overview

Backend sends **complete state in every tick_update** - no accumulation needed on UI side.

**Philosophy:** Full data every tick, consume and discard. Size doesn't matter.

---

## Connection

### Endpoint
```
GET /api/backtest/{session_id}/stream
Content-Type: text/event-stream
```

### Event Format
```
event: tick_update
data: {json_payload}
id: 241

```

---

## Events Overview

| Event | When | Compressed | Purpose |
|-------|------|------------|---------|
| `initial_state` | Connection start | ✅ Yes | Bootstrap with existing state |
| `tick_update` | Every data update | ❌ No | **Real-time complete state** |
| `node_event` | Node completes | ❌ No | Notification/logging |
| `trade_update` | Trade closes | ❌ No | Notification (also in tick_update) |
| `backtest_complete` | Session end | ✅ Yes | Final snapshot |

**Most important:** `tick_update` - contains everything UI needs to render.

---

## tick_update - Complete Structure

**This is what you'll receive every tick (~1/second historical, multiple/second live):**

```json
{
  "event_id": 241,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "tick": 241,
  "timestamp": "2024-10-29 09:19:00+05:30",
  "execution_count": 3,
  
  "ltp": {
    "NIFTY": {
      "ltp": 24361.9,
      "timestamp": "2024-10-29 09:19:00.000000",
      "volume": 0,
      "oi": 0
    }
  },
  
  "open_positions": [
    {
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 50,
      "entry_price": 181.6,
      "current_price": 185.5,
      "unrealized_pnl": -195.0,
      "entry_time": "2024-10-29T09:19:00+05:30",
      "status": "OPEN"
    }
  ],
  
  "closed_positions": [
    {
      "trade_id": "entry-2-pos1",
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 50,
      "entry_price": 181.6,
      "entry_time": "2024-10-29T09:19:00+05:30",
      "exit_price": 260.05,
      "exit_time": "2024-10-29T10:48:00+05:30",
      "pnl": -3922.5,
      "pnl_percent": -43.2,
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
    }
  ],
  
  "pnl_summary": {
    "realized_pnl": -3922.5,
    "unrealized_pnl": -195.0,
    "total_pnl": -4117.5,
    "closed_trades": 1,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 1,
    "win_rate": 0.0
  },
  
  "node_executions": {
    "exec_entry-condition-1_20241029_091900_1abff6": {
      "execution_id": "exec_entry-condition-1_20241029_091900_1abff6",
      "parent_execution_id": "exec_strategy-controller_20241029_091500_6baf48",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "node_executing",
      "node_id": "entry-condition-1",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "children_nodes": [
        {"id": "entry-2"}
      ],
      "condition_type": "entry_conditions",
      "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30",
      "signal_emitted": true,
      "logic_completed": true,
      "evaluated_conditions": {
        "conditions_evaluated": [
          {
            "lhs_expression": {
              "type": "current_time"
            },
            "rhs_expression": {
              "type": "time_function",
              "timeValue": "09:17"
            },
            "lhs_value": 1730173740.0,
            "rhs_value": 1730173620.0,
            "operator": ">=",
            "timestamp": "2024-10-29 09:19:00+05:30",
            "condition_type": "non_live",
            "result": true,
            "result_icon": "✓",
            "raw": "Current Time >= 09:17",
            "evaluated": "09:19:00 >= 09:17:00",
            "condition_text": "Current Time >= 09:17  [09:19:00 >= 09:17:00] ✓"
          }
        ],
        "expression_values": {},
        "candle_data": {
          "NIFTY": {
            "current": {
              "timestamp": "2024-10-29 09:19:00+05:30",
              "open": 24350.0,
              "high": 24365.5,
              "low": 24348.0,
              "close": 24361.9,
              "volume": 0
            },
            "previous": {
              "timestamp": "2024-10-29 09:18:00+05:30",
              "open": 24345.0,
              "high": 24350.0,
              "low": 24340.0,
              "close": 24348.5,
              "volume": 0
            }
          }
        }
      }
    }
  },
  
  "active_nodes": ["entry-condition-1", "entry-condition-2", "square-off-1"]
}
```

---

## Data Types - CRITICAL

### All Numeric Values Are Numbers

**Never strings. Always numbers.**

```typescript
// ✅ CORRECT
{
  "entry_price": 181.6,        // number
  "pnl": -3922.5,              // number
  "win_rate": 65.5,            // number
  "quantity": 50               // number
}

// ❌ WRONG
{
  "entry_price": "181.60",     // string - NO!
  "pnl": "-3922.50",           // string - NO!
  "win_rate": "65.50",         // string - NO!
  "quantity": "50"             // string - NO!
}
```

### Timestamps Are ISO 8601 Strings

```typescript
// ✅ CORRECT
"timestamp": "2024-10-29 09:19:00+05:30"  // string, ISO 8601

// ❌ WRONG
"timestamp": 1730173740.0  // unix timestamp - NO!
```

### Field Type Reference

| Field Category | Type | Example |
|---------------|------|---------|
| Prices (entry_price, exit_price, current_price, ltp) | **number** | `181.6` |
| P&L (pnl, realized_pnl, unrealized_pnl, total_pnl) | **number** | `-3922.5` |
| Percentages (pnl_percent, win_rate) | **number** | `43.2` |
| Quantities | **number (int)** | `50` |
| Counts (closed_trades, open_trades, winning_trades) | **number (int)** | `9` |
| Durations | **number** | `89.0` |
| Timestamps | **string** | `"2024-10-29 09:19:00+05:30"` |
| Symbols | **string** | `"NIFTY:2024-11-07:OPT:24250:PE"` |
| IDs | **string** | `"entry-2-pos1"` |

---

## What UI Needs To Do

### 1. Connect to SSE
```javascript
const eventSource = new EventSource(
  `/api/backtest/${sessionId}/stream`
);

eventSource.addEventListener('tick_update', (event) => {
  const data = JSON.parse(event.data);
  updateUI(data);  // Replace entire state
});
```

### 2. Consume tick_update
**Do NOT accumulate state. Replace everything on each tick.**

```javascript
function updateUI(tickData) {
  // Update positions table
  setOpenPositions(tickData.open_positions);
  setClosedPositions(tickData.closed_positions);
  
  // Update P&L display
  setPnLSummary(tickData.pnl_summary);
  
  // Update LTP display
  setLTP(tickData.ltp);
  
  // Update node status
  setActiveNodes(tickData.active_nodes);
  
  // Update node details (if expanded)
  setNodeExecutions(tickData.node_executions);
}
```

### 3. Throttle Rendering (Optional)
If events come too fast (live trading: 10-50/sec):

```javascript
let latestData = null;

eventSource.addEventListener('tick_update', (event) => {
  latestData = JSON.parse(event.data);
});

// Render loop
function render() {
  if (latestData) {
    updateUI(latestData);
    latestData = null;
  }
  requestAnimationFrame(render);
}

render();
```

### 4. Handle Other Events (Optional)
```javascript
// For notifications
eventSource.addEventListener('node_event', (event) => {
  const data = JSON.parse(event.data);
  if (data.signal_emitted) {
    showNotification(`${data.node_name} triggered`);
  }
});

eventSource.addEventListener('trade_update', (event) => {
  const data = JSON.parse(event.data);
  showNotification(`Trade closed: ${data.trade.pnl} P&L`);
});

eventSource.addEventListener('backtest_complete', (event) => {
  showNotification('Backtest complete');
  // Optionally download final report
});
```

---

## Field Descriptions

### open_positions[]
| Field | Type | Description |
|-------|------|-------------|
| `position_id` | string | Unique position identifier |
| `symbol` | string | Universal format (convert to display name on UI) |
| `side` | string | "buy" or "sell" |
| `quantity` | number | Position size |
| `entry_price` | number | Entry price |
| `current_price` | number | Current market price |
| `unrealized_pnl` | number | Current unrealized P&L |
| `entry_time` | string | ISO 8601 timestamp |
| `status` | string | "OPEN" |

### closed_positions[]
| Field | Type | Description |
|-------|------|-------------|
| `trade_id` | string | Unique trade identifier |
| `position_id` | string | Position identifier |
| `re_entry_num` | number | Re-entry counter (0 = first entry) |
| `symbol` | string | Universal format |
| `side` | string | "buy" or "sell" |
| `quantity` | number | Position size |
| `entry_price` | number | Entry price |
| `entry_time` | string | ISO 8601 timestamp |
| `exit_price` | number | Exit price |
| `exit_time` | string | ISO 8601 timestamp |
| `pnl` | number | Realized P&L |
| `pnl_percent` | number | Percentage gain/loss |
| `duration_minutes` | number | Trade duration in minutes |
| `status` | string | "CLOSED" |
| `entry_flow_ids` | string[] | Execution flow for entry (for canvas viz) |
| `exit_flow_ids` | string[] | Execution flow for exit (for canvas viz) |
| `entry_trigger` | string | Node that triggered entry |
| `exit_reason` | string | Why position closed |

### pnl_summary
| Field | Type | Description |
|-------|------|-------------|
| `realized_pnl` | number | Total P&L from closed trades |
| `unrealized_pnl` | number | Total P&L from open positions |
| `total_pnl` | number | realized_pnl + unrealized_pnl |
| `closed_trades` | number | Count of closed trades |
| `open_trades` | number | Count of open positions |
| `winning_trades` | number | Count of profitable closed trades |
| `losing_trades` | number | Count of loss-making closed trades |
| `win_rate` | number | Percentage (0-100) |

### ltp
| Field | Type | Description |
|-------|------|-------------|
| `{symbol}` | object | Key is symbol name (e.g., "NIFTY") |
| `ltp` | number | Last traded price |
| `timestamp` | string | Price timestamp |
| `volume` | number | Volume (if available) |
| `oi` | number | Open interest (if available) |

### node_executions
**Object with execution_id as key.**

Each execution contains:
- Basic info: `execution_id`, `node_id`, `node_name`, `node_type`, `timestamp`
- Status: `signal_emitted`, `logic_completed`
- Details: `evaluated_conditions` (full condition breakdown)
- Context: `candle_data`, `expression_values`

**Use for:**
- Showing node status on canvas
- Displaying condition evaluations in sidebar
- Debugging/tracing execution flow

---

## Decompression (initial_state & backtest_complete)

These events are gzip + base64 encoded.

```javascript
import pako from 'pako';

eventSource.addEventListener('initial_state', (event) => {
  const data = JSON.parse(event.data);
  
  // Decompress diagnostics
  const diagnosticsCompressed = atob(data.diagnostics);
  const diagnosticsBytes = Uint8Array.from(diagnosticsCompressed, c => c.charCodeAt(0));
  const diagnosticsJson = pako.ungzip(diagnosticsBytes, { to: 'string' });
  const diagnostics = JSON.parse(diagnosticsJson);
  
  // Decompress trades
  const tradesCompressed = atob(data.trades);
  const tradesBytes = Uint8Array.from(tradesCompressed, c => c.charCodeAt(0));
  const tradesJson = pako.ungzip(tradesBytes, { to: 'string' });
  const trades = JSON.parse(tradesJson);
  
  // Initialize UI
  initializeUI(diagnostics, trades);
});
```

---

## Bandwidth

### Historical Backtest
- **Ticks:** 22,351 over 6 hours
- **Frequency:** ~1 per second
- **Size per tick:** ~5-7 KB (with full details)
- **Total:** ~120-150 MB over 6 hours
- **Rate:** ~5 KB/sec average

### Live Trading
- **Frequency:** 1-50 events per second (variable)
- **Conservative (10/sec):** 50-70 KB/sec = 180-252 MB/hour
- **High volatility (50/sec):** 250-350 KB/sec = 900-1260 MB/hour

**Modern networks handle this easily.**

---

## Error Handling

### Reconnection
EventSource automatically reconnects with `Last-Event-ID` header.

**Backend behavior:** Sends fresh `initial_state` on reconnect.

```javascript
eventSource.addEventListener('error', (event) => {
  console.log('Connection lost, reconnecting...');
  // EventSource handles reconnection automatically
});

eventSource.addEventListener('open', (event) => {
  console.log('Connected/Reconnected');
});
```

### Missing Events
If `event_id` jumps (e.g., 100 → 150), you missed 49 events.

**Solution:** Backend sends complete state in every `tick_update`, so missing events doesn't matter. You always have current state.

---

## Testing Checklist

- [ ] Can connect to SSE endpoint
- [ ] Receive `initial_state` and decompress successfully
- [ ] Receive `tick_update` every second
- [ ] Parse all numeric fields as numbers (not strings)
- [ ] Display open positions with current P&L
- [ ] Display closed positions (trades list)
- [ ] Display P&L summary (realized/unrealized/total)
- [ ] Display LTP for symbols
- [ ] Show active nodes on canvas
- [ ] Show node details when expanded
- [ ] Handle reconnection gracefully
- [ ] UI responsive at 10 events/sec
- [ ] UI responsive at 50 events/sec (with throttling)

---

## Sample Session for Testing

**Session ID:** `sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29`

**Expected data:**
- 22,351 ticks
- 9 closed trades
- Max 2 open positions simultaneously
- Total P&L: -168.4
- Win rate: 11.11%

---

## Summary

**Backend sends:**
- ✅ Complete state in every `tick_update`
- ✅ All numeric values as numbers (not strings)
- ✅ All timestamps as ISO 8601 strings
- ✅ Full node execution details (evaluated_conditions, candle_data)
- ✅ Open positions with current P&L
- ✅ Closed positions (full trade history)
- ✅ P&L summary (realized, unrealized, totals)
- ✅ LTP for all symbols
- ✅ Active node status

**UI should:**
- ✅ Connect to SSE endpoint
- ✅ Consume `tick_update` events
- ✅ Replace entire state on each tick (no accumulation)
- ✅ Parse JSON directly (all correct types)
- ✅ Optionally throttle rendering if needed
- ✅ Convert symbol format to display names
- ✅ Handle reconnection (EventSource auto-handles)

**No state management complexity on UI side** - just consume and render.

---

## Questions?

Contact backend team for:
- Session ID format issues
- Data type mismatches
- Missing fields
- Performance issues
- Additional data requirements

---

**Ready for integration. Good luck! 🚀**
