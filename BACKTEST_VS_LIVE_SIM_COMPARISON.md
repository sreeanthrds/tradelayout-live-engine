# Backtest vs Live Simulation JSON Comparison

## Actual Output Comparison (2024-10-29 Strategy)

---

## 1. TRADES DATA COMPARISON

### ✅ Backtest `trades_daily.json` (COMPLETE)
**Source:** `/tradelayout-engine/trades_daily.json`

```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30",
    "winning_trades": 1,
    "losing_trades": 8,
    "win_rate": "11.11"
  },
  "trades": [{
    "trade_id": "entry-2-pos1-r0",
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",
    "quantity": 1,
    "entry_price": "181.60",
    "entry_time": "2024-10-29 09:19:00+05:30",
    "exit_price": "260.05",
    "exit_time": "2024-10-29 10:48:00+05:30",
    "pnl": "-78.45",
    "pnl_percent": "-43.20",
    "duration_minutes": 89,
    "status": "closed",
    "entry_flow_ids": [
      "exec_strategy-controller_20241029_091500_6e6acf",
      "exec_entry-condition-1_20241029_091900_c8d81d",
      "exec_entry-2_20241029_091900_bc5118"
    ],
    "exit_flow_ids": [
      "exec_strategy-controller_20241029_091500_6e6acf",
      "exec_entry-condition-1_20241029_091900_c8d81d",
      "exec_entry-2_20241029_091900_bc5118",
      "exec_exit-condition-2_20241029_104800_dd8b20",
      "exec_exit-3_20241029_104800_19aea3"
    ],
    "entry_trigger": "Entry condition - Bullish",
    "exit_reason": "Exit 3 - SL"
  }]
}
```

### 🔴 Live Simulation SSE `open_positions` (INCOMPLETE)
**Source:** Live SSE stream `tick_state.open_positions`

```json
{
  "open_positions": [{
    "position_id": "entry-2-pos1",
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "sell",                              // ❌ lowercase (backtest: uppercase "SELL")
    "quantity": 1,
    "entry_price": 181.6,                        // ❌ number (backtest: string "181.60")
    "current_price": 176.25,                     // ✅ Live updating price
    "unrealized_pnl": 5.35,                      // ✅ Live calculated P&L
    "entry_time": "2024-10-29T09:19:00+05:30",  // ❌ ISO format (backtest: space format)
    "node_id": "entry-2",                        // ✅ Has node_id
    "entry_execution_id": "exec_entry-2_20241029_091900_bdc928"  // ✅ Has execution_id
  }]
}
```

### 🚨 Missing Keys in Live Simulation:
1. **`trade_id`** - Not in SSE (only after position closes)
2. **`re_entry_num`** - Not in SSE
3. **`exit_price`** - Not in SSE (only for closed positions)
4. **`exit_time`** - Not in SSE (only for closed positions)
5. **`pnl`** - Not in SSE (has `unrealized_pnl` instead)
6. **`pnl_percent`** - Not in SSE
7. **`duration_minutes`** - Not in SSE
8. **`status`** - Not in SSE (implicitly "open")
9. **`entry_flow_ids`** - Not in SSE
10. **`exit_flow_ids`** - Not in SSE
11. **`entry_trigger`** - Not in SSE (has `node_id` instead)
12. **`exit_reason`** - Not in SSE

### 🔧 Format Differences:
1. **`side`**: Backtest uses uppercase "SELL"/"BUY", SSE uses lowercase "sell"/"buy"
2. **`entry_price`**: Backtest uses string "181.60", SSE uses number 181.6
3. **`entry_time`**: Backtest uses space format "2024-10-29 09:19:00+05:30", SSE uses ISO "2024-10-29T09:19:00+05:30"

---

## 2. DIAGNOSTICS/NODE EVENTS COMPARISON

### ✅ Backtest `diagnostics_export.json` (COMPLETE)
**Source:** `/tradelayout-engine/diagnostics_export.json`

```json
{
  "events_history": {
    "exec_entry-condition-1_20241029_091900_c8d81d": {
      "execution_id": "exec_entry-condition-1_20241029_091900_c8d81d",
      "parent_execution_id": "exec_strategy-controller_20241029_091500_6e6acf",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "logic_completed",
      "node_id": "entry-condition-1",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "children_nodes": [{"id": "entry-2"}],
      "condition_type": "entry_conditions",
      "conditions_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30 AND TI.underlying_ltp > Previous[TI.1m.High]",
      "signal_emitted": true,
      "evaluated_conditions": {
        "conditions_evaluated": [{
          "lhs_expression": {"type": "current_time"},
          "rhs_expression": {"type": "time_function", "timeValue": "09:17"},
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
        }],
        "expression_values": {},
        "candle_data": {
          "NIFTY": {
            "current": {...},
            "previous": {
              "indicators": {"rsi(14,close)": 26.968}
            }
          }
        }
      },
      "signal_time": "2024-10-29T09:19:00+05:30",
      "variables_calculated": ["SignalLow"],
      "ltp_store": {
        "NIFTY": 24272.2,
        "NIFTY:2024-11-07:OPT:24250:PE": 181.6
      }
    }
  }
}
```

### 🔴 Live Simulation SSE `active_node_states` (INCOMPLETE)
**Source:** Live SSE stream `tick_state.active_node_states`

```json
{
  "active_node_states": [{
    "node_id": "exit-condition-1",
    "node_name": "exit-condition-1",         // ❌ Same as node_id (not human-readable)
    "node_type": "Unknown",                  // ❌ Should be "ExitSignalNode"
    "status": "Active",
    "timestamp": "2024-10-29T09:19:27+05:30",
    "current_evaluation": {}                 // ❌ Empty (should have condition data)
  }]
}
```

### 🚨 Missing Keys in Live Simulation SSE:
1. **`execution_id`** - Not in `active_node_states`
2. **`parent_execution_id`** - Not in `active_node_states`
3. **`event_type`** - Not in `active_node_states`
4. **`children_nodes`** - Not in `active_node_states`
5. **`condition_type`** - Not in `active_node_states`
6. **`conditions_preview`** - Not in `active_node_states`
7. **`signal_emitted`** - Not in `active_node_states`
8. **`evaluated_conditions`** - Empty in `current_evaluation`
9. **`signal_time`** - Not in `active_node_states`
10. **`variables_calculated`** - Not in `active_node_states`
11. **`ltp_store`** - Not per-node (exists at tick level)
12. **`position`** - Not in `active_node_states` (for EntryNode)
13. **`legs`** - Not in `active_node_states` (for EntryNode)
14. **`exit_result`** - Not in `active_node_states` (for ExitNode)

### 🔧 Data Issues in Live Simulation:
1. **`node_name`**: SSE shows same as `node_id` ("exit-condition-1"), Backtest shows human-readable ("Entry condition - Bullish")
2. **`node_type`**: SSE shows "Unknown", Backtest shows correct types ("EntrySignalNode", "ExitNode", etc.)
3. **`current_evaluation`**: SSE shows empty `{}`, should contain live condition evaluation data

---

## 3. LTP STORE COMPARISON

### ✅ Live Simulation SSE (COMPLETE - NOW WORKING!)
```json
{
  "ltp_store": {
    "NIFTY": {
      "ltp": 24294.85,
      "timestamp": "2024-10-29 09:19:27.000000",
      "volume": 0,
      "oi": 0
    },
    "NIFTY:2024-11-07:OPT:24250:PE": {
      "ltp": 176.25,
      "timestamp": "2024-10-29 09:19:27.000000",
      "volume": 0,
      "oi": 66075
    }
  }
}
```

### ✅ Backtest diagnostics (per event)
```json
{
  "ltp_store": {
    "NIFTY": 24272.2,
    "NIFTY:2024-11-07:OPT:24250:PE": 181.6
  }
}
```

**Status:** ✅ Format matches! SSE now includes full details (ltp, timestamp, volume, oi).

---

## 4. SUMMARY OF ISSUES

### For Simulator Report Generation:

#### ❌ **Issue 1: Position Data Format Mismatch**
Live simulation `open_positions` uses different formats than backtest `trades`:
- Need to standardize: uppercase side, string prices, space-separated timestamps
- Missing trade metadata: `re_entry_num`, `entry_flow_ids`, `exit_flow_ids`, `entry_trigger`

#### ❌ **Issue 2: No Closed Position Events**
Live simulation only shows `open_positions`. When position closes, it should emit:
- Complete trade record matching backtest format
- Include `exit_price`, `exit_time`, `pnl`, `pnl_percent`, `duration_minutes`, `exit_reason`

#### ❌ **Issue 3: Active Node States Too Simple**
`active_node_states` missing critical diagnostic information:
- No condition evaluation data
- Incorrect node_type ("Unknown")
- No parent/child relationships
- No execution chain tracking

#### ❌ **Issue 4: No Complete Node Event History**
SSE doesn't emit `node_events` like backtest `diagnostics_export.json`:
- Missing EntrySignalNode/ExitSignalNode evaluation details
- Missing EntryNode/ExitNode position details
- Missing execution flow chain

---

## 5. REQUIRED FIXES

### Fix 1: Emit Complete Trade Event on Position Close
When position closes, emit:
```json
{
  "event": "trade_update",
  "data": {
    "trade_id": "entry-2-pos1-r0",
    "position_id": "entry-2-pos1",
    "re_entry_num": 0,
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "SELL",                          // Uppercase
    "quantity": 1,
    "entry_price": "181.60",                 // String
    "entry_time": "2024-10-29 09:19:00+05:30",  // Space format
    "exit_price": "260.05",
    "exit_time": "2024-10-29 10:48:00+05:30",
    "pnl": "-78.45",
    "pnl_percent": "-43.20",
    "duration_minutes": 89,
    "status": "closed",
    "entry_flow_ids": [...],
    "exit_flow_ids": [...],
    "entry_trigger": "Entry condition - Bullish",
    "exit_reason": "Exit 3 - SL"
  }
}
```

### Fix 2: Standardize Position Format in tick_update
Match backtest format:
```json
{
  "open_positions": [{
    "side": "SELL",                          // Uppercase
    "entry_price": "181.60",                 // String
    "entry_time": "2024-10-29 09:19:00+05:30",  // Space format
    "re_entry_num": 0,                       // Add
    "entry_flow_ids": [...],                 // Add
    "entry_trigger": "Entry condition - Bullish"  // Add (not just node_id)
  }]
}
```

### Fix 3: Emit Complete Node Events
When node executes, emit full diagnostic event:
```json
{
  "event": "node_event",
  "data": {
    "execution_id": "exec_entry-condition-1_20241029_091900_c8d81d",
    "parent_execution_id": "exec_strategy-controller_20241029_091500_6e6acf",
    "timestamp": "2024-10-29 09:19:00+05:30",
    "event_type": "logic_completed",
    "node_id": "entry-condition-1",
    "node_name": "Entry condition - Bullish",  // Human-readable
    "node_type": "EntrySignalNode",            // Correct type
    "children_nodes": [{"id": "entry-2"}],
    "condition_type": "entry_conditions",
    "conditions_preview": "...",
    "signal_emitted": true,
    "evaluated_conditions": {...},             // Full evaluation
    "ltp_store": {...}
  }
}
```

### Fix 4: Enhance active_node_states
Include more diagnostic data:
```json
{
  "active_node_states": [{
    "node_id": "exit-condition-1",
    "node_name": "Exit condition 1 - Target",  // Human-readable
    "node_type": "ExitSignalNode",             // Correct type
    "execution_id": "exec_exit-condition-1_...",  // Add
    "parent_execution_id": "...",              // Add
    "status": "Active",
    "timestamp": "2024-10-29T09:19:27+05:30",
    "current_evaluation": {                    // Full evaluation data
      "conditions_evaluated": [...],
      "candle_data": {...}
    }
  }]
}
```

---

## 6. ROOT CAUSE ANALYSIS

### Why Simulator Can't Build Reports:

1. **Missing Trade Completion Events** - Simulator never receives full trade records with exit data
2. **Format Inconsistencies** - Data types and formats don't match between live sim and backtest
3. **Incomplete Node Diagnostics** - Can't trace execution flow or understand why trades happened
4. **No Event History** - SSE doesn't build cumulative `events_history` like backtest

### Solution Approach:

The live simulation SSE needs to emit **THREE event types** that match backtest structure:

1. **`tick_update`** - Current state (positions, P&L, LTP) ✅ Mostly working
2. **`trade_update`** - Complete trade record when position closes ❌ **MISSING**
3. **`node_event`** - Full diagnostic when node executes ❌ **MISSING**

These three events together should provide ALL data that backtest `trades_daily.json` and `diagnostics_export.json` contain.
