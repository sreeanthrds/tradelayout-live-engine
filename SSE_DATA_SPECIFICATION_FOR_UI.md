# SSE Data Specification for UI Team

**Backend to UI Data Contract**  
All structures verified from actual backtest output files.

---

## Table of Contents
1. [Connection Protocol](#connection-protocol)
2. [Event Frequency Model](#event-frequency-model)
3. [Event Types Overview](#event-types-overview)
4. [Event 1: initial_state](#event-1-initial_state)
5. [Event 2: tick_update](#event-2-tick_update)
6. [Event 3: node_event](#event-3-node_event)
7. [Event 4: trade_update](#event-4-trade_update)
8. [Event 5: backtest_complete](#event-5-backtest_complete)
9. [Data Types](#data-types)
10. [Questions for UI Team](#questions-for-ui-team)

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

**IMPORTANT: Events are data-driven, NOT time-driven.**

### Historical Backtest
- Engine processes historical tick data (1-second granularity)
- **`tick_update` frequency:** ~1 per second (~22,351 per day)
- **Limitation:** Historical data resolution, not backend design

### Live Trading
- Engine receives real-time market ticks (sub-second updates)
- **`tick_update` frequency:** Variable, multiple per second
- **Triggers:**
  - New market tick received
  - Order execution confirmation
  - Position update (entry/exit/modification)
  - LTP change
- **Expected rate:** 1-50+ events per second (depends on market volatility)

### Other Events
- **`node_event`**: Emitted immediately when node completes logic
- **`trade_update`**: Emitted immediately when position closes
- **No batching or throttling** on backend

---

## Event Types Overview

| Event | When | Frequency | Compressed | Size | Purpose |
|-------|------|-----------|------------|------|---------|
| `initial_state` | Session start | 1× | ✅ Yes | ~15 KB | Initialize with empty/existing state |
| `tick_update` | Data update | Variable | ❌ No | 3-5 KB | Real-time positions, P&L, nodes |
| `node_event` | Node completes | ~38×/day | ❌ No | 1 KB | Significant milestones |
| `trade_update` | Trade closes | ~7×/day | ❌ No | 1 KB | Individual trade details |
| `backtest_complete` | Session end | 1× | ✅ Yes | ~15 KB | Final snapshot |

---

## Event 1: initial_state

**When:** Client connects to session  
**Frequency:** Once per session  
**Compression:** gzip + base64

### SSE Message
```
event: initial_state
data: {json_below}
id: 0
```

### JSON Payload
```json
{
  "event_id": 0,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "diagnostics": "H4sIAAAAAAAA...",
  "trades": "H4sIAAAAAAAA...",
  "uncompressed_sizes": {
    "diagnostics": 0,
    "trades": 0
  },
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-29",
  "end_date": "2024-10-29"
}
```

### After Decompression: diagnostics
```json
{
  "events_history": {
    "exec_strategy-controller_20241029_091500_950284": {
      "execution_id": "exec_strategy-controller_20241029_091500_950284",
      "parent_execution_id": null,
      "timestamp": "2024-10-29 09:15:00+05:30",
      "event_type": "logic_completed",
      "node_id": "strategy-controller",
      "node_name": "Start",
      "node_type": "StartNode",
      "children_nodes": [
        {"id": "entry-condition-1"},
        {"id": "entry-condition-2"},
        {"id": "square-off-1"}
      ],
      "strategy_config": {
        "symbol": "NIFTY",
        "timeframe": "1m",
        "exchange": "NSE",
        "trading_instrument": {
          "type": "options",
          "underlyingType": "index"
        },
        "end_conditions_configured": 0
      }
    }
  }
}
```

### After Decompression: trades
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 0,
    "total_pnl": 0.0,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": 0.0
  },
  "trades": []
}
```

**Note:** At session start, both are minimal/empty. As backtest progresses, these accumulate data.

---

## Event 2: tick_update

**When:** On every data update (not time-bound)  
**Frequency:** Variable (1/sec historical, multiple/sec live)  
**Compression:** None

### SSE Message
```
event: tick_update
data: {json_below}
id: 241
```

### JSON Payload
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
      "entry_time": "2024-10-29T09:19:05+05:30",
      "status": "open"
    }
  ],
  
  "pnl_summary": {
    "realized_pnl": 0.0,
    "unrealized_pnl": -195.0,
    "total_pnl": -195.0,
    "closed_trades": 0,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 0,
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
      },
      "logic_completed": true
    }
  },
  
  "active_nodes": ["entry-condition-1", "entry-condition-2", "square-off-1"],
  "indicators": {},
  "position_count": 1
}
```

### Field Descriptions

**ltp** (object)
- Key: Symbol name
- Value: Object with `ltp`, `timestamp`, `volume`, `oi`

**open_positions** (array)
- `position_id` (string): Unique identifier
- `symbol` (string): Universal format (e.g., "NIFTY:2024-11-07:OPT:24250:PE")
- `side` (string): "buy" or "sell"
- `quantity` (number): Position size
- `entry_price` (number): Entry price
- `current_price` (number): Current market price
- `unrealized_pnl` (number): Unrealized P&L
- `entry_time` (string, optional): ISO 8601 format
- `status` (string): "open"

**pnl_summary** (object)
- `realized_pnl` (number): Total P&L from closed trades
- `unrealized_pnl` (number): Total P&L from open positions
- `total_pnl` (number): realized_pnl + unrealized_pnl
- `closed_trades` (number): Count of closed trades
- `open_trades` (number): Count of open positions
- `winning_trades` (number): Count of profitable closed trades
- `losing_trades` (number): Count of loss-making closed trades
- `win_rate` (number): Percentage (e.g., 65.5)

**node_executions** (object)
- Key: execution_id
- Value: Full node execution details
- Includes `evaluated_conditions` with detailed breakdown
- Includes `candle_data` with current and previous candles
- Includes `signal_emitted` boolean

**active_nodes** (array)
- List of node IDs currently in active state

---

## Event 3: node_event

**When:** Node completes logic (signal emitted, order placed)  
**Frequency:** ~38 times per day  
**Compression:** None

### SSE Message
```
event: node_event
data: {json_below}
id: 242
```

### JSON Payload
```json
{
  "event_id": 242,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "execution_id": "exec_entry-condition-1_20241029_091900_f0eff6",
  "parent_execution_id": "exec_strategy-controller_20241029_091500_950284",
  "timestamp": "2024-10-29 09:19:00+05:30",
  "event_type": "logic_completed",
  "node_id": "entry-condition-1",
  "node_name": "Entry condition - Bullish",
  "node_type": "EntrySignalNode",
  "children_nodes": [
    {"id": "entry-2"}
  ],
  "condition_type": "entry_conditions",
  "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30",
  "signal_emitted": true
}
```

**Purpose:** Log significant events, show notifications for milestones.

---

## Event 4: trade_update

**When:** Position closes  
**Frequency:** ~7 times per day  
**Compression:** None

### SSE Message
```
event: trade_update
data: {json_below}
id: 243
```

### JSON Payload
```json
{
  "event_id": 243,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "trade": {
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
  },
  "summary": {
    "total_trades": 1,
    "total_pnl": -3922.5,
    "winning_trades": 0,
    "losing_trades": 1,
    "win_rate": 0.0
  }
}
```

### Trade Fields
- `trade_id` (string): Unique identifier
- `re_entry_num` (number): Re-entry counter (0 = first entry)
- `symbol` (string): Universal format
- `side` (string): "buy" or "sell"
- `quantity` (number): Position size
- `entry_price` (number): Entry price
- `entry_time` (string): ISO 8601 format
- `exit_price` (number): Exit price
- `exit_time` (string): ISO 8601 format
- `pnl` (number): Profit/loss
- `pnl_percent` (number): Percentage gain/loss
- `duration_minutes` (number): Trade duration
- `status` (string): "CLOSED"
- `entry_flow_ids` (array): Execution flow for entry
- `exit_flow_ids` (array): Execution flow for exit
- `entry_trigger` (string): Which node triggered entry
- `exit_reason` (string): Why position closed

**Purpose:** Add to trades list, show notification, update summary.

---

## Event 5: backtest_complete

**When:** Backtest finishes  
**Frequency:** Once per session  
**Compression:** gzip + base64

### SSE Message
```
event: backtest_complete
data: {json_below}
id: 22351
```

### JSON Payload
```json
{
  "event_id": 22351,
  "session_id": "sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29",
  "diagnostics": "H4sIAAAAAAAA...",
  "trades": "H4sIAAAAAAAA...",
  "uncompressed_sizes": {
    "diagnostics": 106000,
    "trades": 10000
  },
  "total_ticks": 22351
}
```

**After decompression:** Same structure as `initial_state`, but with full data:
- Complete `events_history` with all node executions
- Complete `trades` array with all closed trades

**Purpose:** Save final state, enable report download, show completion message.

---

## Data Types

### CRITICAL: All Numeric Values are Numbers

**Positions:**
- `entry_price`, `current_price`, `unrealized_pnl` → **number** (e.g., 181.6, -195.0)
- `quantity` → **number** (e.g., 50)

**P&L Summary:**
- `realized_pnl`, `unrealized_pnl`, `total_pnl`, `win_rate` → **number** (e.g., -195.0, 65.5)
- `closed_trades`, `open_trades`, `winning_trades`, `losing_trades` → **number** (integer)

**Trades:**
- `entry_price`, `exit_price`, `pnl`, `pnl_percent` → **number** (e.g., 181.6, -3922.5, -43.2)
- `quantity`, `duration_minutes`, `re_entry_num` → **number** (integer)

**Timestamps:**
- Always **string** in ISO 8601 format: `"2024-10-29 09:19:00+05:30"`
- Never unix timestamp numbers

**Prices:**
- All market prices, LTP values → **number** (e.g., 24361.9)

---

## Decompression

**Compressed events:** `initial_state`, `backtest_complete`  
**Encoding:** gzip → base64

**Steps to decompress:**
1. Base64 decode the string
2. Gunzip the binary data
3. Parse as JSON

**JavaScript libraries:** `pako` (npm package)  
**Python libraries:** `gzip` + `base64` (standard library)

---

## Questions for UI Team

To ensure we send the right data, please confirm:

### 1. Position Display
Do you need additional fields in `open_positions`?
- ✅ Currently sent: position_id, symbol, side, quantity, entry_price, current_price, unrealized_pnl, entry_time, status
- ❓ Need: entry_node_id, target_profit, stop_loss, position_age, symbol_display_name?

### 2. Symbol Format
How should symbols be displayed?
- ✅ Backend sends: "NIFTY:2024-11-07:OPT:24250:PE" (universal format)
- ❓ Need: Display name conversion like "NIFTY 24250 PE Nov 07"?
- ❓ Should backend send both formats, or UI converts?

### 3. Timestamp Display
Is the timestamp format acceptable?
- ✅ Current: "2024-10-29 09:19:00+05:30"
- ❓ Need: Different format like "09:19:00 AM" or "2024-10-29T09:19:00+05:30"?
- ❓ Should backend send both, or UI converts?

### 4. Node Diagnostics Detail Level
Do you need full `evaluated_conditions` in every `tick_update`?
- ✅ Currently sent: Full condition breakdown with lhs/rhs expressions, values, operators, results
- ❓ Too much data for real-time display?
- ❓ Should we send simplified version in tick_update, full details only in node_event?

### 5. Indicator Data
What indicators should we send in `tick_update`?
- ✅ Currently: All indicators cached for strategy (can be large)
- ❓ Only specific ones needed for charting?
- ❓ Send indicator names list, UI requests specific ones?

### 6. Event Update Frequency
How should UI handle high-frequency updates in live trading?
- ✅ Backend: Sends events as they occur (1-50+ per second possible)
- ❓ Should backend throttle to max rate (e.g., 10/second)?
- ❓ Or UI implements rendering throttle/buffering?

### 7. Reconnection Strategy
How should reconnection work?
- ✅ EventSource sends `Last-Event-ID` header automatically
- ❓ Should server replay missed events (if gap < 100)?
- ❓ Or always send fresh `initial_state` on reconnect?
- ❓ What's acceptable gap threshold?

### 8. P&L Precision
Is 2 decimal places sufficient for all P&L values?
- ✅ Currently: All P&L rounded to 2 decimals (e.g., -3922.5)
- ❓ Need more precision for certain instruments?

### 9. Candle Data
Do you need candle data in every `tick_update`?
- ✅ Currently sent: current and previous candles in `node_executions.evaluated_conditions.candle_data`
- ❓ Too much data if sent every tick?
- ❓ Send only when candle changes (once per minute for 1m timeframe)?

### 10. Trade Flow IDs
Are `entry_flow_ids` and `exit_flow_ids` needed in UI?
- ✅ Currently sent: Full execution flow showing which nodes were involved
- ❓ Used for debugging/audit trail?
- ❓ Or can we omit to reduce payload size?

---

## Bandwidth Estimation

### Historical Backtest (22,351 ticks/day)
- `initial_state`: 15 KB × 1 = 15 KB
- `tick_update`: 4 KB × 22,351 = ~89 MB
- `node_event`: 1 KB × 38 = 38 KB
- `trade_update`: 1 KB × 7 = 7 KB
- `backtest_complete`: 15 KB × 1 = 15 KB
- **Total:** ~89 MB over 6 hours = ~4 KB/second

### Live Trading (Conservative: 10 events/second)
- `tick_update`: 4 KB × 10/sec = 40 KB/sec = 144 MB/hour

### Live Trading (High volatility: 50 events/second)
- `tick_update`: 4 KB × 50/sec = 200 KB/sec = 720 MB/hour

**SSE can handle this bandwidth.** UI may want rendering throttle.

---

## Testing Session

**Sample data for testing:**
- Session ID: `sse-5708424d-5962-4629-978c-05b3a174e104-2024-10-29`
- Strategy: Straddle with re-entry
- Date: 2024-10-29
- Ticks: 22,351
- Trades: 9 closed (1 winning, 8 losing)
- Total P&L: -168.4

Backend can emit all event types with real data from this session for UI testing.

---

## Summary

**What backend sends:**
- ✅ 5 event types via SSE
- ✅ All numeric values as numbers (not strings)
- ✅ Timestamps in ISO 8601 format (not unix)
- ✅ Individual positions with P&L
- ✅ Aggregated P&L summary with statistics
- ✅ Node execution details with condition evaluations
- ✅ Trade history (incremental)
- ✅ Compressed snapshots (initial + final)
- ✅ Data-driven frequency (multiple per second possible in live)

**What UI needs to handle:**
- Connect to SSE endpoint
- Decompress gzip+base64 for compressed events
- Parse JSON for each event type
- Display positions, P&L, trades, node activity
- Handle reconnection (EventSource auto-handles)
- Consider rendering throttle for high-frequency updates

**Next steps:**
1. UI team reviews this specification
2. Answers the 10 questions above
3. Backend adjusts implementation based on feedback
4. Testing with sample session data
5. Integration and live testing
