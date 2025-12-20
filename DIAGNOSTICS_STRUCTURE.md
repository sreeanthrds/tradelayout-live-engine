# Diagnostics Export Structure

## Answer: **Option A** ✅

**Structure**: `events_history` is a **Record<string, ExecutionNode>** (object/dictionary)
- **Keys**: `execution_id` (string) - e.g., `"exec_strategy-controller_20241028_091500_a9b228"`
- **Values**: ExecutionNode objects with diagnostic data

---

## TypeScript Interface

```typescript
interface DiagnosticsExport {
  events_history: Record<string, ExecutionNode>;
}

interface ExecutionNode {
  // ============ ALWAYS PRESENT ============
  execution_id: string;                    // e.g., "exec_strategy-controller_20241028_091500_a9b228"
  parent_execution_id: string | null;      // null for root (StartNode), otherwise parent's execution_id
  timestamp: string;                       // ISO format: "2024-10-28 09:15:00+05:30"
  event_type: string;                      // "logic_completed" (most common)
  node_id: string;                         // e.g., "strategy-controller", "entry-2", "exit-4"
  node_name: string;                       // Display name: "Start", "Entry condition - Bearish"
  node_type: string;                       // "StartNode", "EntrySignalNode", "EntryNode", etc.
  children_nodes?: Array<{id: string}>;    // IDs of child nodes that were triggered
  
  // ============ CONDITIONAL FIELDS (by node type) ============
  
  // StartNode
  strategy_config?: {
    symbol: string;                        // "NIFTY"
    timeframe: string;                     // "1m"
    exchange: string;                      // "NSE"
    trading_instrument: {
      type: string;                        // "options"
      underlyingType: string;              // "index"
    };
    end_conditions_configured: number;     // 0 or 1
  };
  
  // EntrySignalNode / ExitSignalNode
  condition_type?: string;                 // "entry_conditions" | "exit_conditions"
  conditions_preview?: string;             // Human-readable: "Current Time > 09:17 AND ..."
  signal_emitted?: boolean;                // true if conditions passed
  evaluated_conditions?: {
    conditions_evaluated: Array<{
      lhs_expression: object;              // Left-hand side expression details
      rhs_expression: object;              // Right-hand side expression details
      lhs_value: number | string;          // Actual value of LHS
      rhs_value: number | string;          // Actual value of RHS
      operator: string;                    // ">", "<", "==", etc.
      timestamp: string;                   // ISO timestamp
      condition_type: string;              // "non_live" | "live"
      result: boolean;                     // true/false
      result_icon: string;                 // "✓" or "✗"
      raw: string;                         // Original condition text
      evaluated: string;                   // "71.14 > 70.00"
      condition_text: string;              // Full formatted text
    }>;
  };
  
  // EntryNode
  action?: string;                         // "place_order" | "skip"
  skip_reason?: string;                    // Reason if skipped
  entry_config?: {
    symbol: string;                        // Option symbol
    side: string;                          // "buy" | "sell"
    quantity: number;
    order_type: string;                    // "market" | "limit"
    product_type: string;                  // "MIS" | "NRML"
  };
  ltp_store?: Record<string, any>;         // LTP data at entry time
  node_variables?: Record<string, any>;    // Node-specific variables
  
  // ExitSignalNode
  exit_signal_data?: {
    positions_to_exit: string[];           // Position IDs to exit
    exit_reason: string;                   // "exit_signal_triggered"
    signal_timestamp: string;
  };
  
  // ExitNode
  exit_reason?: string;                    // "exit_signal_triggered" | "square_off" | "stop_loss"
  exit_result?: string;                    // "success" | "failed"
  closed_positions?: number;               // Count of positions closed
  position?: {                             // Details of position being exited
    position_id: string;
    symbol: string;
    quantity: number;
    entry_price: number;
    exit_price: number;
    pnl: number;
  };
  exit_config?: {
    order_type: string;
    exit_price?: number;
  };
  
  // SquareOffNode
  square_off?: {
    reason: string;                        // "market_close" | "end_condition"
    positions_closed: number;
    total_pnl: number;
  };
  statistics?: {
    total_positions: number;
    open_positions: number;
    closed_positions: number;
    total_pnl: number;
  };
  
  // Re-entry specific
  re_entry_metadata?: {
    re_entry_num: number;
    original_position_id: string;
    parent_position_id: string;
  };
  
  // Other occasional fields
  signal_time?: string;                    // Signal timestamp
  timestamp_info?: {                       // Detailed timestamp breakdown
    date: string;
    time: string;
    day_of_week: string;
  };
  variables_calculated?: Record<string, any>; // Calculated variables
  config?: object;                         // Generic config data
}
```

---

## Sample Data Structure

### Example 1: StartNode Event
```json
{
  "events_history": {
    "exec_strategy-controller_20241028_091500_a9b228": {
      "execution_id": "exec_strategy-controller_20241028_091500_a9b228",
      "parent_execution_id": null,
      "timestamp": "2024-10-28 09:15:00+05:30",
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

### Example 2: EntrySignalNode Event (with conditions)
```json
{
  "exec_entry-condition-2_20241028_091800_c504e7": {
    "execution_id": "exec_entry-condition-2_20241028_091800_c504e7",
    "parent_execution_id": "exec_strategy-controller_20241028_091500_a9b228",
    "timestamp": "2024-10-28 09:18:00+05:30",
    "event_type": "logic_completed",
    "node_id": "entry-condition-2",
    "node_name": "Entry condition - Bearish",
    "node_type": "EntrySignalNode",
    "children_nodes": [{"id": "entry-3"}],
    "condition_type": "entry_conditions",
    "conditions_preview": "Current Time > 09:17 AND Previous[TI.1m.rsi(14,close)] > 70 AND TI.underlying_ltp < Previous[TI.1m.Low]",
    "signal_emitted": true,
    "evaluated_conditions": {
      "conditions_evaluated": [
        {
          "lhs_expression": {"type": "current_time"},
          "rhs_expression": {"type": "time_function", "timeValue": "09:17"},
          "lhs_value": 1730087280.0,
          "rhs_value": 1730087220.0,
          "operator": ">",
          "timestamp": "2024-10-28 09:18:00+05:30",
          "condition_type": "non_live",
          "result": true,
          "result_icon": "✓",
          "raw": "Current Time > 09:17",
          "evaluated": "09:18:00 > 09:17:00",
          "condition_text": "Current Time > 09:17  [09:18:00 > 09:17:00] ✓"
        }
      ]
    }
  }
}
```

### Example 3: EntryNode Event
```json
{
  "exec_entry-2_20241028_094400_7a3f21": {
    "execution_id": "exec_entry-2_20241028_094400_7a3f21",
    "parent_execution_id": "exec_entry-condition-1_20241028_094400_b2c8f5",
    "timestamp": "2024-10-28 09:44:00+05:30",
    "event_type": "logic_completed",
    "node_id": "entry-2",
    "node_name": "Entry PE",
    "node_type": "EntryNode",
    "action": "place_order",
    "entry_config": {
      "symbol": "NIFTY:2024-11-07:OPT:24150:PE",
      "side": "sell",
      "quantity": 1,
      "order_type": "market",
      "product_type": "MIS"
    },
    "children_nodes": [{"id": "exit-condition-3"}]
  }
}
```

---

## Key Points for Frontend

1. **Data Type**: Object (Record), NOT Array
2. **Keys**: `execution_id` strings
3. **Hierarchy**: Use `parent_execution_id` to build tree
4. **Conditional Fields**: Not all events have all fields - check node_type
5. **Total Events**: ~40-50 per trading day (varies by strategy complexity)

---

## Field Presence by Node Type

| Node Type | Always Has | May Have |
|-----------|-----------|----------|
| StartNode | strategy_config | - |
| EntrySignalNode | condition_type, conditions_preview, signal_emitted | evaluated_conditions |
| ExitSignalNode | condition_type, signal_emitted | evaluated_conditions, exit_signal_data |
| EntryNode | action, entry_config | skip_reason, ltp_store, node_variables |
| ExitNode | exit_reason, exit_result | position, exit_config, closed_positions |
| SquareOffNode | square_off | statistics |
| ReEntryNode | re_entry_metadata, entry_config | - |

---

## Usage Example (Frontend)

```typescript
// Load diagnostics
const response = await fetch('/api/v1/backtest/{id}/day/{date}');
const zip = await response.blob();
const diagnostics = await extractDiagnostics(zip); // Your unzip logic

// Access events
const events = diagnostics.events_history;

// Iterate through events
Object.entries(events).forEach(([executionId, event]) => {
  console.log(`${event.node_name} at ${event.timestamp}`);
  
  // Check for conditions
  if (event.evaluated_conditions) {
    event.evaluated_conditions.conditions_evaluated.forEach(condition => {
      console.log(`  ${condition.condition_text}`);
    });
  }
});

// Build parent-child tree
function buildTree(events: Record<string, ExecutionNode>) {
  const rootEvents = Object.values(events).filter(e => !e.parent_execution_id);
  // ... build hierarchy using parent_execution_id
}
```

---

## Summary

✅ **Structure**: `Record<string, ExecutionNode>` (Option A)  
✅ **Total Fields**: 31 unique fields (not all present in every event)  
✅ **Event Types**: Primarily "logic_completed"  
✅ **Hierarchy**: Built via `parent_execution_id` references  

**No backend changes needed** - structure already matches Option A! 🎉
