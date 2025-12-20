# SSE Data Specification - Corrected

Based on actual output files from tick capture system.

---

## Data Sources

All structures verified from:
- `tick_capture_output/diagnostics_export.json`
- `tick_capture_output/trades_daily.json`
- `tick_capture_output/tick_events.jsonl`

---

## Event 1: initial_state (Compressed)

**Structure after decompression:**

### diagnostics_export.json
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
    },
    "exec_entry-condition-1_20241029_091900_f0eff6": {
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
      "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30 AND TI.underlying_ltp > Previous[TI.1m.High]",
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
        "candle_data": {}
      }
    }
  }
}
```

### trades_daily.json
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-168.40",
    "winning_trades": 1,
    "losing_trades": 8,
    "win_rate": "11.11"
  },
  "trades": [
    {
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
    }
  ]
}
```

**Note:** At session start, both will have minimal/empty data.

---

## Event 2: tick_update (Every Tick)

**Actual structure from tick_events.jsonl:**

```json
{
  "tick": 241,
  "timestamp": "2024-10-29 09:19:00+05:30",
  
  "ltp": {
    "NIFTY": {
      "ltp": 24361.9,
      "timestamp": "2024-10-29 09:15:00.000000",
      "volume": 0,
      "oi": 0
    }
  },
  
  "indicators": {},
  
  "open_positions": [
    {
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": 181.6,
      "current_price": 185.5,
      "pnl": -3.9,
      "status": "open"
    }
  ],
  
  "pnl_summary": {
    "realized_pnl": 0.0,
    "unrealized_pnl": -3.9,
    "total_pnl": -3.9,
    "closed_trades": 0,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": 0.0
  },
  
  "active_nodes": [
    {
      "node_id": "entry-condition-1",
      "status": "active"
    }
  ],
  
  "position_count": 1,
  
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
      "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30 AND TI.underlying_ltp > Previous[TI.1m.High]",
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
  
  "execution_count": 1
}
```

### Field Descriptions

#### ltp (object)
- Key: symbol name
- Value: object with `ltp`, `timestamp`, `volume`, `oi`

#### open_positions (array)
- `position_id` (string)
- `symbol` (string): Universal format
- `side` (string): "buy" or "sell"
- `quantity` (number)
- `entry_price` (number): NOT string
- `current_price` (number): NOT string
- `pnl` (number): NOT string (unrealized P&L)
- `status` (string): "open"

#### pnl_summary (object) - **NEW**
- `realized_pnl` (string): "0.00"
- `unrealized_pnl` (string): "-3.90"
- `total_pnl` (string): "-3.90"
- `closed_trades` (number): 0
- `open_trades` (number): 1
- `winning_trades` (number): 0
- `losing_trades` (number): 0
- `win_rate` (string): "0.00"

#### node_executions (object)
- Key: execution_id
- Value: Full node execution details including:
  - `evaluated_conditions` with detailed breakdown
  - `candle_data` with current and previous candles
  - `expression_values` for variables
  - `signal_emitted` boolean
  - `logic_completed` boolean

---

## Event 3: node_event (Incremental)

**Sends single event from diagnostics when node completes:**

```json
{
  "event_id": 242,
  "session_id": "...",
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
  "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30 AND TI.underlying_ltp > Previous[TI.1m.High]",
  "signal_emitted": true
}
```

---

## Event 4: trade_update (Incremental)

**Sends single trade from trades list:**

```json
{
  "event_id": 243,
  "session_id": "...",
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
```

---

## Event 5: backtest_complete (Compressed)

**Same as initial_state but with full data:**
- Full `events_history` from diagnostics_export.json
- Full `trades` array from trades_daily.json

---

## Key Corrections

### 1. Data Types - ALL NUMBERS

**CRITICAL: All numeric values are numbers, NOT strings**

**open_positions:**
- `entry_price`, `current_price`, `pnl` → **number** (e.g., 181.6, -3.9)
- `quantity` → **number** (e.g., 50)

**pnl_summary:**
- `realized_pnl`, `unrealized_pnl`, `total_pnl`, `win_rate` → **number** (e.g., -3.9, 65.5)
- `closed_trades`, `open_trades`, `winning_trades`, `losing_trades` → **number** (integer)

**trades:**
- `entry_price`, `exit_price`, `pnl`, `pnl_percent` → **number** (e.g., 181.6, -78.45)
- `quantity`, `duration_minutes`, `re_entry_num` → **number** (integer)

**timestamps:**
- Always ISO 8601 format string: "2024-10-29 09:19:00+05:30"
- Never unix timestamp numbers

### 2. Node Execution Details

**Much more detailed than specified:**
- `evaluated_conditions` contains full breakdown with:
  - `lhs_expression` and `rhs_expression` objects
  - `lhs_value` and `rhs_value`
  - `operator`, `result`, `result_icon`
  - `raw`, `evaluated`, `condition_text`
- `candle_data` contains current and previous candles
- `expression_values` for calculated variables

### 3. Trade Details

**Additional fields not in initial spec:**
- `re_entry_num`: Re-entry counter
- `pnl_percent`: Percentage gain/loss
- `duration_minutes`: Trade duration
- `entry_flow_ids`: Full execution flow for entry
- `exit_flow_ids`: Full execution flow for exit
- `entry_trigger`: Which node triggered entry
- `exit_reason`: Why position closed

### 4. LTP Structure

**More fields than specified:**
- `ltp`: Price value
- `timestamp`: Price timestamp
- `volume`: Volume (if available)
- `oi`: Open interest (if available)

---

## Summary

**Corrected based on actual files:**
- ✅ diagnostics_export.json structure verified
- ✅ trades_daily.json structure verified
- ✅ tick_events.jsonl structure verified (with new pnl_summary)
- ✅ Data types corrected (numbers vs strings)
- ✅ Additional fields documented

**UI can now reference actual structures from these output files.**
