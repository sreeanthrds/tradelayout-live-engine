# JSON Structure Comparison: Simulator Report Issues

## Problem
The simulator cannot build reports from the current backtest output JSONs because they're missing critical keys that exist in the reference structure.

---

## 1. `trades_daily.json` Comparison

### ❌ Smoke Test Output (INCOMPLETE)
```json
{
  "date": "2025-12-14",
  "summary": {
    "total_trades": 1,
    "total_pnl": "2000.00",
    "winning_trades": 1,
    "losing_trades": 0,
    "win_rate": "100.00"
  },
  "trades": [{
    "trade_id": "trade-001",
    "symbol": "NIFTY28DEC2525000CE",
    "entry_time": "2024-12-14T09:15:00",
    "exit_time": "2024-12-14T09:23:19",
    "entry_price": 150.0,
    "exit_price": 190.0,
    "quantity": 50,
    "pnl": "2000.00",
    "pnl_percentage": "26.67"
  }]
}
```

### ✅ Real Backtest Output (COMPLETE)
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
  "trades": [{
    "trade_id": "entry-2-pos1",
    "position_id": "entry-2-pos1",            // ✅ REQUIRED
    "re_entry_num": 0,                        // ✅ REQUIRED
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "sell",                           // ✅ REQUIRED
    "quantity": 1,
    "entry_price": "181.60",
    "entry_time": "2024-10-29T09:19:00+05:30",
    "exit_price": "260.05",
    "exit_time": "2024-10-29T10:48:00+05:30",
    "pnl": "-78.45",
    "pnl_percent": "-43.20",
    "duration_minutes": 89.0,                 // ✅ REQUIRED
    "status": "CLOSED",                       // ✅ REQUIRED
    "entry_flow_ids": [                       // ✅ REQUIRED - Links to diagnostics
      "exec_strategy-controller_20241029_091500_411f28",
      "exec_entry-condition-1_20241029_091900_7c6eda",
      "exec_entry-2_20241029_091900_1c1c59"
    ],
    "exit_flow_ids": [                        // ✅ REQUIRED - Links to diagnostics
      "exec_strategy-controller_20241029_091500_411f28",
      "exec_entry-condition-1_20241029_091900_7c6eda",
      "exec_entry-2_20241029_091900_1c1c59",
      "exec_exit-condition-2_20241029_104800_74f293",
      "exec_exit-3_20241029_104800_469a1b"
    ],
    "entry_trigger": "entry-2",               // ✅ REQUIRED
    "exit_reason": "exit_condition_met"       // ✅ REQUIRED
  }]
}
```

### 🚨 Missing Keys in Smoke Test `trades_daily.json`:
1. **`position_id`** - Unique position identifier
2. **`re_entry_num`** - Re-entry counter (0 for first entry)
3. **`side`** - "buy" or "sell"
4. **`duration_minutes`** - Trade duration in minutes
5. **`status`** - "OPEN", "CLOSED", "REJECTED"
6. **`entry_flow_ids`** - Array linking to node execution chain (diagnostics)
7. **`exit_flow_ids`** - Array linking to exit execution chain (diagnostics)
8. **`entry_trigger`** - Node ID that triggered entry
9. **`exit_reason`** - Reason for exit ("exit_condition_met", "stop_loss", "target", etc.)
10. **`pnl_percent`** - Should be "pnl_percent" not "pnl_percentage"

---

## 2. `diagnostics_export.json` Comparison

### ❌ Smoke Test Output (INCOMPLETE)
```json
{
  "events_history": {
    "exec-100-Entry": {
      "execution_id": "exec-100-Entry",
      "node_id": "entry-condition-1",
      "node_type": "EntryNode",
      "timestamp": "2024-12-14T09:16:39",
      "event_type": "logic_completed",
      "evaluation_data": {
        "action": "entry_placed",
        "symbol": "NIFTY28DEC2525000CE",
        "quantity": 50,
        "price": 150.0
      }
    }
  },
  "current_state": {
    // Same structure as events_history
  }
}
```

### ✅ Real Backtest Output (COMPLETE)
```json
{
  "events_history": {
    "exec_entry-condition-1_20241029_091900_7c6eda": {
      "execution_id": "exec_entry-condition-1_20241029_091900_7c6eda",
      "parent_execution_id": "exec_strategy-controller_20241029_091500_411f28",  // ✅ REQUIRED
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "logic_completed",
      "node_id": "entry-condition-1",
      "node_name": "Entry condition - Bullish",                                  // ✅ REQUIRED
      "node_type": "EntrySignalNode",
      "children_nodes": [                                                         // ✅ REQUIRED
        {"id": "entry-2"}
      ],
      "condition_type": "entry_conditions",                                      // ✅ REQUIRED
      "conditions_preview": "Current Time >= 09:17 AND ...",                     // ✅ REQUIRED
      "signal_emitted": true,                                                    // ✅ REQUIRED
      "evaluated_conditions": {                                                  // ✅ REQUIRED
        "conditions_evaluated": [
          {
            "lhs_expression": {...},
            "rhs_expression": {...},
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
        "candle_data": {                                                         // ✅ REQUIRED
          "NIFTY": {
            "current": {...},
            "previous": {
              "indicators": {
                "rsi(14,close)": 26.968
              }
            }
          }
        }
      },
      "signal_time": "2024-10-29T09:19:00+05:30",
      "variables_calculated": ["SignalLow"],
      "ltp_store": {                                                             // ✅ REQUIRED
        "NIFTY": 24272.2,
        "NIFTY:2024-11-07:OPT:24250:PE": 181.6
      }
    },
    "exec_entry-2_20241029_091900_1c1c59": {
      "execution_id": "exec_entry-2_20241029_091900_1c1c59",
      "parent_execution_id": "exec_entry-condition-1_20241029_091900_7c6eda",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "logic_completed",
      "node_id": "entry-2",
      "node_name": "Entry - Short Strangle",
      "node_type": "EntryNode",
      "position": {                                                              // ✅ REQUIRED
        "position_id": "entry-2-pos1",
        "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
        "side": "sell",
        "quantity": 1,
        "entry_price": 181.6,
        "entry_time": "2024-10-29T09:19:00+05:30",
        "node_id": "entry-2",
        "re_entry_num": 0,
        "status": "open"
      },
      "legs": [...],                                                             // ✅ REQUIRED
      "ltp_store": {...}
    },
    "exec_exit-3_20241029_104800_469a1b": {
      "execution_id": "exec_exit-3_20241029_104800_469a1b",
      "parent_execution_id": "exec_exit-condition-2_20241029_104800_74f293",
      "timestamp": "2024-10-29 10:48:00+05:30",
      "event_type": "logic_completed",
      "node_id": "exit-3",
      "node_name": "Exit SL",
      "node_type": "ExitNode",
      "position": {                                                              // ✅ REQUIRED
        "position_id": "entry-2-pos1",
        "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
        "side": "sell",
        "quantity": 1,
        "entry_price": 181.6,
        "entry_time": "2024-10-29T09:19:00+05:30",
        "node_id": "entry-2",
        "re_entry_num": 0,
        "status": "closed"
      },
      "exit_result": {                                                           // ✅ REQUIRED
        "exit_price": 260.05,
        "exit_time": "2024-10-29T10:48:00+05:30",
        "pnl": -78.45,
        "pnl_percent": -43.20,
        "exit_reason": "exit_condition_met",
        "exit_trigger": "exit-3"
      },
      "ltp_store": {...}
    }
  }
}
```

### 🚨 Missing Keys in Smoke Test `diagnostics_export.json`:

#### For ALL Node Events:
1. **`parent_execution_id`** - Links to parent node in execution chain
2. **`node_name`** - Human-readable node name
3. **`children_nodes`** - Array of child node IDs

#### For EntrySignalNode / ExitSignalNode:
4. **`condition_type`** - "entry_conditions" or "exit_conditions"
5. **`conditions_preview`** - Human-readable condition summary
6. **`signal_emitted`** - Boolean indicating if signal was triggered
7. **`evaluated_conditions`** - Detailed condition evaluation:
   - `conditions_evaluated` array with:
     - `lhs_expression`, `rhs_expression`
     - `lhs_value`, `rhs_value`
     - `operator`, `result`, `result_icon`
     - `raw`, `evaluated`, `condition_text`
   - `candle_data` object with current/previous candles + indicators
   - `expression_values` object
8. **`signal_time`** - When signal was emitted
9. **`variables_calculated`** - Array of calculated variables (e.g., ["SignalLow"])

#### For EntryNode:
10. **`position`** - Complete position object:
    - `position_id`, `symbol`, `side`, `quantity`
    - `entry_price`, `entry_time`
    - `node_id`, `re_entry_num`, `status`
11. **`legs`** - Array of order legs (for multi-leg strategies)
12. **`ltp_store`** - LTP data at time of entry

#### For ExitNode:
13. **`position`** - Position being closed
14. **`exit_result`** - Complete exit details:
    - `exit_price`, `exit_time`
    - `pnl`, `pnl_percent`
    - `exit_reason`, `exit_trigger`
15. **`ltp_store`** - LTP data at time of exit

#### For StartNode:
16. **`strategy_config`** - Strategy configuration object:
    - `symbol`, `timeframe`, `exchange`
    - `trading_instrument` object
    - `end_conditions_configured`

---

## 3. Structural Issues

### Issue 1: `current_state` Should NOT Duplicate `events_history`
The smoke test has a `current_state` object that duplicates `events_history`. The real backtest does NOT have this. The `events_history` IS the complete record.

**Remove:** `current_state` key from smoke test output

### Issue 2: Execution ID Format
- **Smoke Test:** `"exec-100-Entry"` (simple, non-standard)
- **Real Backtest:** `"exec_entry-2_20241029_091900_1c1c59"` (standard format: `exec_{node_id}_{date}_{time}_{random}`)

**Fix:** Use standard execution ID format: `exec_{node_id}_{YYYYMMDD}_{HHMMSS}_{6_char_hex}`

### Issue 3: Timestamp Format
- **Smoke Test:** `"2024-12-14T09:16:39"` (ISO without timezone)
- **Real Backtest:** `"2024-10-29 09:19:00+05:30"` (with timezone)

**Fix:** Include timezone in all timestamps

---

## 4. Required Structure for Simulator

The simulator expects the following minimum structure:

### `trades_daily.json`
```typescript
{
  date: string,                    // "YYYY-MM-DD"
  summary: {
    total_trades: number,
    total_pnl: string,             // Decimal string
    winning_trades: number,
    losing_trades: number,
    win_rate: string               // Percentage string
  },
  trades: [{
    trade_id: string,
    position_id: string,           // REQUIRED
    re_entry_num: number,          // REQUIRED
    symbol: string,
    side: "buy" | "sell",          // REQUIRED
    quantity: number,
    entry_price: string,
    entry_time: string,            // ISO with timezone
    exit_price: string,
    exit_time: string,
    pnl: string,
    pnl_percent: string,           // REQUIRED (not "pnl_percentage")
    duration_minutes: number,      // REQUIRED
    status: string,                // REQUIRED
    entry_flow_ids: string[],      // REQUIRED - Links to diagnostics
    exit_flow_ids: string[],       // REQUIRED - Links to diagnostics
    entry_trigger: string,         // REQUIRED - Node ID
    exit_reason: string            // REQUIRED
  }]
}
```

### `diagnostics_export.json`
```typescript
{
  events_history: {
    [execution_id: string]: {
      execution_id: string,
      parent_execution_id: string | null,     // REQUIRED
      timestamp: string,                       // With timezone
      event_type: "logic_completed" | "activated" | "deactivated",
      node_id: string,
      node_name: string,                       // REQUIRED
      node_type: "StartNode" | "EntrySignalNode" | "EntryNode" | "ExitSignalNode" | "ExitNode",
      children_nodes?: [{id: string}],         // REQUIRED for parent nodes
      
      // For Signal Nodes (EntrySignalNode, ExitSignalNode):
      condition_type?: string,                 // REQUIRED
      conditions_preview?: string,             // REQUIRED
      signal_emitted?: boolean,                // REQUIRED
      evaluated_conditions?: {                 // REQUIRED
        conditions_evaluated: [...],
        candle_data: {...},
        expression_values: {...}
      },
      signal_time?: string,
      variables_calculated?: string[],
      
      // For Entry/Exit Nodes:
      position?: {...},                        // REQUIRED
      legs?: [...],
      exit_result?: {...},                     // REQUIRED for ExitNode
      ltp_store?: {...}                        // REQUIRED
    }
  }
}
```

---

## 5. Recommendations

### Immediate Fixes:
1. **Update smoke test generator** to output full structure matching real backtest
2. **Add all missing keys** listed above
3. **Remove `current_state`** duplicate
4. **Use standard execution ID format**
5. **Include timezone in all timestamps**

### Code Files to Update:
- Smoke test generator (wherever it creates the JSON output)
- Trade journal export logic
- Diagnostics export logic

### Testing:
1. Generate new smoke test output with complete structure
2. Verify simulator can parse and build reports
3. Compare with real backtest output byte-by-byte if needed
