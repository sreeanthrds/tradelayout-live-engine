# Backend SSE Data Specification

**For UI Team**: This document specifies exactly what data the backend sends via SSE events. No implementation code - just the data contract.

---

## Connection Protocol

### SSE Endpoint
```
GET /api/backtest/{session_id}/stream
Content-Type: text/event-stream
Cache-Control: no-cache
```

### SSE Message Format
```
event: {event_type}
data: {json_payload}
id: {event_id}

```

**Note:** Empty line separates each event.

---

## Event Frequency Model

**Important:** Events are **data-driven**, not time-driven.

### Historical Backtest
- Engine processes historical tick data (1-second granularity)
- **`tick_update` emitted:** ~1 per second
- **Reason:** Historical data is pre-aggregated to 1-second intervals

### Live Trading
- Engine receives real-time market ticks (sub-second updates)
- **`tick_update` emitted:** Multiple per second possible
- **Triggers:**
  - New market tick received
  - Order execution confirmation
  - Position update (entry/exit/modification)
  - LTP change
- **Frequency:** Variable (1-50+ per second depending on market volatility and strategy activity)

### Other Events
- **`node_event`**: Emitted immediately when node completes logic
- **`trade_update`**: Emitted immediately when position closes
- **No batching or throttling** on backend - UI receives events as they occur

---

## Event Sequence

```
1. Client connects → Server sends initial_state (compressed)
2. Backtest runs → Server sends tick_update (every second, uncompressed)
3. Node completes → Server sends node_event (when signal emitted)
4. Position closes → Server sends trade_update (when trade closes)
5. Backtest ends → Server sends backtest_complete (compressed)
```

---

## Event 1: initial_state (Compressed)

**When:** Session starts, client connects  
**Frequency:** Once  
**Compression:** gzip + base64

### Raw SSE Message
```
event: initial_state
data: {"event_id":0,"session_id":"sse-strategy-2024-10-29","diagnostics":"H4sIAAAAAAAA...","trades":"H4sIAAAAAAAA...","uncompressed_sizes":{"diagnostics":0,"trades":0},"strategy_id":"5708424d-...","start_date":"2024-10-29","end_date":"2024-10-29"}
id: 0
```

### JSON Structure
```json
{
  "event_id": 0,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "diagnostics": "H4sIAAAAAAAA...",  // gzip + base64 encoded JSON
  "trades": "H4sIAAAAAAAA...",       // gzip + base64 encoded JSON
  "uncompressed_sizes": {
    "diagnostics": 0,
    "trades": 0
  },
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-29",
  "end_date": "2024-10-29"
}
```

### After Decompression (diagnostics)
```json
{
  "events_history": {},  // Empty at start
  "current_state": {}
}
```

### After Decompression (trades)
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 0,
    "total_pnl": "0.00",
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": "0.00"
  },
  "trades": []
}
```

**Purpose:** Initialize UI with empty state.

---

## Event 2: tick_update (Most Important)

**When:** On every data update (not time-bound)  
**Frequency:** Variable based on data updates
- **Historical backtest:** ~1 per second (~22,351 per day) - limited by historical data granularity
- **Live trading:** Multiple per second possible - driven by live tick data, order updates, position changes
**Compression:** None  
**Size:** ~3-5 KB per event

### Raw SSE Message
```
event: tick_update
data: {full_json_below}
id: 241
```

### Complete JSON Structure
```json
{
  "event_id": 241,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "tick": 241,
  "timestamp": "2024-10-29 09:19:00+05:30",
  "execution_count": 3,
  
  "node_executions": {
    "exec_entry-condition-1_20241029_091900_0153a0": {
      "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
      "node_id": "entry-condition-1",
      "node_name": "Entry Bullish",
      "node_type": "EntrySignalNode",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "logic_completed",
      "signal_emitted": true,
      "evaluated_conditions": [
        {
          "condition_id": "cond_1",
          "expression": "Current Time >= 09:17",
          "result": true,
          "left_value": "09:19:00",
          "operator": ">=",
          "right_value": "09:17:00"
        }
      ],
      "node_variables": {
        "strike_price": 24000
      },
      "children_nodes": ["entry-2"]
    }
  },
  
  "open_positions": [
    {
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
      "side": "sell",
      "quantity": 50,
      "entry_price": "215.00",
      "current_price": "220.50",
      "unrealized_pnl": "-275.00",
      "entry_time": "2024-10-29 09:19:05+05:30",
      "status": "open"
    }
  ],
  
  "pnl_summary": {
    "realized_pnl": "0.00",
    "unrealized_pnl": "-275.00",
    "total_pnl": "-275.00",
    "closed_trades": 0,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": "0.00"
  },
  
  "ltp": {
    "NIFTY": {
      "ltp": 24350.5,
      "timestamp": "2024-10-29 09:19:00.000000"
    }
  },
  
  "indicators": {
    "NIFTY:1m": {
      "sma_20": 24340.25,
      "ema_50": 24335.75
    }
  },
  
  "active_nodes": ["entry-condition-1", "entry-condition-2", "square-off-1"]
}
```

### Field Descriptions

#### open_positions (Array)
Each position object contains:
- `position_id` (string): Unique position identifier
- `symbol` (string): Trading symbol in universal format
- `side` (string): "buy" or "sell"
- `quantity` (number): Position size
- `entry_price` (string): Entry price as string (e.g., "215.00")
- `current_price` (string): Current market price
- `unrealized_pnl` (string): Unrealized P&L as string (e.g., "-275.00")
- `entry_time` (string, optional): Entry timestamp
- `status` (string): Always "open" for open positions

#### pnl_summary (Object)
- `realized_pnl` (string): Total P&L from closed trades
- `unrealized_pnl` (string): Total P&L from open positions
- `total_pnl` (string): realized_pnl + unrealized_pnl
- `closed_trades` (number): Count of closed trades
- `open_trades` (number): Count of open positions
- `winning_trades` (number): Count of profitable closed trades
- `losing_trades` (number): Count of loss-making closed trades
- `win_rate` (string): Percentage as string (e.g., "100.00")

#### node_executions (Object)
Key = execution_id, Value = node execution details:
- `execution_id` (string): Unique execution identifier
- `node_id` (string): Node identifier
- `node_name` (string): Human-readable node name
- `node_type` (string): Node type (EntrySignalNode, ExitNode, etc.)
- `timestamp` (string): Execution timestamp
- `event_type` (string): "node_executing" or "logic_completed"
- `signal_emitted` (boolean, optional): Whether node emitted signal
- `evaluated_conditions` (array, optional): Array of condition evaluations
- `node_variables` (object, optional): Variables calculated by node
- `children_nodes` (array, optional): Child node IDs

#### ltp (Object)
Key = symbol, Value = LTP data:
- `ltp` (number): Last traded price
- `timestamp` (string): Price timestamp

#### active_nodes (Array)
List of node IDs currently in active state.

---

## Event 3: node_event (Incremental)

**When:** Node completes logic (signal emitted, order placed)  
**Frequency:** ~38 times per day  
**Compression:** None  
**Size:** ~1 KB

### Raw SSE Message
```
event: node_event
data: {"event_id":242,"session_id":"...","execution_id":"exec_entry-condition-1_...","node_id":"entry-condition-1","node_name":"Entry Bullish","node_type":"EntrySignalNode","timestamp":"2024-10-29 09:19:00+05:30","event_type":"logic_completed","signal_emitted":true,"conditions_preview":"Current Time >= 09:17 AND NIFTY > 24000"}
id: 242
```

### JSON Structure
```json
{
  "event_id": 242,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
  "node_id": "entry-condition-1",
  "node_name": "Entry Bullish",
  "node_type": "EntrySignalNode",
  "timestamp": "2024-10-29 09:19:00+05:30",
  "event_type": "logic_completed",
  "signal_emitted": true,
  "conditions_preview": "Current Time >= 09:17 AND NIFTY > 24000"
}
```

**Purpose:** Log significant node events (for activity feed or notifications).

---

## Event 4: trade_update (Incremental)

**When:** Position closes  
**Frequency:** ~7 times per day  
**Compression:** None  
**Size:** ~1 KB

### Raw SSE Message
```
event: trade_update
data: {"event_id":243,"session_id":"...","trade":{...},"summary":{...}}
id: 243
```

### JSON Structure
```json
{
  "event_id": 243,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "trade": {
    "trade_id": "entry-2-pos1",
    "position_id": "entry-2-pos1",
    "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
    "side": "sell",
    "quantity": 50,
    "entry_price": "215.00",
    "entry_time": "2024-10-29 09:19:05+05:30",
    "exit_price": "185.75",
    "exit_time": "2024-10-29 10:48:00+05:30",
    "pnl": "29.25",
    "status": "CLOSED"
  },
  "summary": {
    "total_trades": 1,
    "total_pnl": "29.25",
    "winning_trades": 1,
    "losing_trades": 0,
    "win_rate": "100.00"
  }
}
```

**Purpose:** Add closed trade to history, update summary metrics.

---

## Event 5: backtest_complete (Compressed)

**When:** Backtest finishes  
**Frequency:** Once  
**Compression:** gzip + base64  
**Size:** ~15 KB compressed (~100 KB uncompressed)

### Raw SSE Message
```
event: backtest_complete
data: {"event_id":22351,"session_id":"...","diagnostics":"H4sIAAAAAAAA...","trades":"H4sIAAAAAAAA...","uncompressed_sizes":{"diagnostics":106000,"trades":10000},"total_ticks":22351}
id: 22351
```

### JSON Structure
```json
{
  "event_id": 22351,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "diagnostics": "H4sIAAAAAAAA...",  // gzip + base64 encoded JSON
  "trades": "H4sIAAAAAAAA...",       // gzip + base64 encoded JSON
  "uncompressed_sizes": {
    "diagnostics": 106000,
    "trades": 10000
  },
  "total_ticks": 22351
}
```

### After Decompression (diagnostics)
```json
{
  "events_history": {
    "exec_entry-condition-1_20241029_091900_0153a0": {
      "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
      "node_id": "entry-condition-1",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "signal_emitted": true,
      // ... full details
    }
    // ... all 38 node events
  }
}
```

### After Decompression (trades)
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 7,
    "total_pnl": "34.75",
    "winning_trades": 5,
    "losing_trades": 2,
    "win_rate": "71.43"
  },
  "trades": [
    // ... all 7 closed trades
  ]
}
```

**Purpose:** Final snapshot for report generation.

---

## Decompression Requirement

**Compressed events:** `initial_state`, `backtest_complete`  
**Encoding:** gzip → base64

**Decompression steps:**
1. Base64 decode the string
2. Gunzip the binary data
3. Parse as JSON

**Libraries:**
- JavaScript: `pako` (npm package)
- Python: `gzip` + `base64` (standard library)

---

## Data Types & Formats

### Numbers as Strings
All P&L and price values are **strings** to preserve precision:
```json
{
  "entry_price": "215.00",     // string, not number
  "pnl": "-275.00",            // string, not number
  "win_rate": "100.00"         // string, not number
}
```

**Reason:** Avoid floating-point precision issues. UI should parse as needed.

### Timestamps
Format: `"YYYY-MM-DD HH:MM:SS+05:30"`  
Example: `"2024-10-29 09:19:00+05:30"`

### Symbols
Format: Universal format  
Example: `"NIFTY:2024-11-07:OPT:24000:PE"`

---

## Event Timing

### Typical Sequence (Example Tick 241)

```
09:19:00.000 - tick_update event_id=241
             (includes: 1 open position, P&L=-275.00, 3 node executions)

09:19:00.001 - node_event event_id=242
             (entry-condition-1 emitted signal)

(60+ ticks later...)

10:48:00.000 - tick_update event_id=1500
             (position closed, now 0 open positions)

10:48:00.001 - trade_update event_id=1501
             (trade details: P&L=+29.25)
```

**Note:** Multiple events can occur at same timestamp (milliseconds apart).

---

## Bandwidth Estimation

| Event Type | Count | Size | Total |
|------------|-------|------|-------|
| initial_state | 1 | 15 KB | 15 KB |
| tick_update | 22,351 | 4 KB | 89 MB |
| node_event | 38 | 1 KB | 38 KB |
| trade_update | 7 | 1 KB | 7 KB |
| backtest_complete | 1 | 15 KB | 15 KB |
| **Total** | | | **~89 MB** |

**For 6-hour trading day:** ~89 MB streamed over ~6 hours = ~4 KB/second average.

---

## Questions for UI Team

To ensure we send the right data, please confirm:

### 1. Position Details
Do you need additional fields in `open_positions`?
- ✅ Currently sent: position_id, symbol, side, quantity, entry_price, current_price, unrealized_pnl, entry_time
- ❓ Need: entry_node_id, target_profit, stop_loss, position_age?

### 2. P&L Display
How do you want to display P&L?
- ✅ We send strings: "29.25", "-275.00"
- ❓ Should we send absolute values separately? (pnl_value, pnl_display)

### 3. Node Diagnostics
Do you need more node details in `node_executions`?
- ✅ Currently sent: execution_id, node_id, node_name, node_type, signal_emitted, evaluated_conditions
- ❓ Need: parent_node_id, execution_time_ms, error_messages?

### 4. Timestamp Format
Is the timestamp format acceptable?
- ✅ Current: "2024-10-29 09:19:00+05:30"
- ❓ Prefer: ISO 8601 "2024-10-29T09:19:00+05:30"?

### 5. Symbol Format
Do you need symbol in different format?
- ✅ Current: "NIFTY:2024-11-07:OPT:24000:PE"
- ❓ Need: Display name like "NIFTY 24000 PE Nov 07"?

### 6. Indicator Data
What indicators should we send in `tick_update`?
- ✅ Currently: All indicators cached for strategy
- ❓ Only specific ones for charting?

### 7. Event Frequency
**Clarified:** Events are **data-driven**, not time-driven.
- ✅ **Historical backtest:** ~1 per second (limited by historical data granularity)
- ✅ **Live trading:** Multiple per second (as ticks arrive, positions update, orders execute)
- ❓ Should UI throttle rendering if updates are too frequent (e.g., >10/second)?

### 8. Reconnection
Do you need event replay after reconnection?
- ✅ EventSource sends `Last-Event-ID` header automatically
- ❓ Should server replay missed events or send fresh `initial_state`?

---

## Testing Data

Sample session for testing:
- **Session ID:** `sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29`
- **Strategy:** Straddle strategy with re-entry
- **Date:** 2024-10-29
- **Ticks:** 22,351 (09:15:00 to 15:30:00)
- **Trades:** 7 closed trades
- **Total P&L:** +34.75

Backend will emit all 5 event types with real data from this session.

---

## Summary

**What backend sends:**
1. ✅ 5 event types via SSE
2. ✅ Individual positions with P&L
3. ✅ Aggregated P&L summary
4. ✅ Node execution details
5. ✅ Trade history (incremental)
6. ✅ Compressed snapshots (initial + final)

**What UI needs to handle:**
1. Connect to SSE endpoint
2. Decompress gzip+base64 for compressed events
3. Parse JSON for each event type
4. Display positions, P&L, and trades
5. Handle reconnection (EventSource auto-handles)

**No implementation details provided** - UI team can build with their own architecture.
