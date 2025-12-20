# Trading Strategy UI - Data Structure Guide

## Overview
You are building a UI for a trading strategy platform that displays both backtesting results and live trading data. The backend provides 3 types of JSON data structures. This guide explains each structure, its purpose, and how to use it in the UI.

---

## **1. SESSION_SUMMARY.json - Trade Summary Data**

### Purpose
Provides aggregated, trade-level data focused on P&L and position details. This is the **primary data source** for displaying trades and summary statistics.

### When to Use
- Trade table/list view
- P&L charts and summary cards
- Per-trade detail view
- Day-wise aggregate statistics

### Structure
```json
{
  "metadata": {
    "session_date": "2024-10-29",
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "session_type": "backtest",          // "backtest" or "live"
    "session_status": "completed",        // "completed" or "in_progress"
    "last_updated": "2025-12-08T20:50:36.039486",
    "generated_from": "diagnostics_export.json"
  },
  "summary": {
    "total_positions": 9,
    "closed_positions": 9,
    "open_positions": 0,
    "total_pnl": -834.45,
    "win_rate_percent": 0.0,
    "winning_trades": 0,
    "losing_trades": 9,
    "nodes_with_events": 13,
    "active_nodes_remaining": 4
  },
  "positions": [
    {
      "position_number": 1,
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": 181.6,
      "exit_price": 260.05,
      "entry_time": "2024-10-29T09:19:00+05:30",
      "exit_time": "2024-10-29 10:48:00+05:30",
      "pnl": -78.45,
      "pnl_percent": -43.2,
      "re_entry_num": 0,
      "position_num": 1,
      "entry_node": "entry-2",
      "exit_node": "exit-3"
    }
  ]
}
```

### UI Display Guidelines

#### Summary Cards
Display at the top of the page:
```
┌─────────────────────────────────────────────────────────┐
│  Total P&L: ₹-834.45 (RED)   Win Rate: 0.0%             │
│  Trades: 9 (0W / 9L)          Open Positions: 0         │
│  Session: 2024-10-29          Status: ●COMPLETED        │
└─────────────────────────────────────────────────────────┘
```

#### Positions Table
```
┌──────┬────────────┬──────┬──────┬───────┬───────┬──────────┬──────────┬─────────┐
│  #   │   Symbol   │ Side │  Qty │ Entry │ Exit  │   P&L    │   P&L%   │ Re-Entry│
├──────┼────────────┼──────┼──────┼───────┼───────┼──────────┼──────────┼─────────┤
│  1   │ 24250 PE   │ SELL │   1  │ 181.6 │ 260.05│ -78.45 ❌│  -43.2%  │   0     │
│  2   │ 24250 CE   │ SELL │   1  │ 262.05│ 262.90│ -94.50 ❌│  -36.1%  │   0     │
└──────┴────────────┴──────┴──────┴───────┴───────┴──────────┴──────────┴─────────┘
```

#### Color Coding
- **P&L**: Green (positive), Red (negative)
- **Session Status**: 
  - `completed`: Gray circle ●
  - `in_progress`: Green blinking circle ●

#### Click Actions
- Click on a row → Show detailed drill-down view
- Drill-down includes: Entry/exit times, node details, link to diagnostics

---

## **2. diagnostics_export.json - Node Execution Timeline**

### Purpose
Provides detailed, node-level diagnostic data showing **why and how** trades happened. Includes condition evaluations, order placements, and LTP snapshots.

### When to Use
- "Why did this trade happen?" analysis
- Node graph/timeline visualization
- Debugging strategy logic
- Condition evaluation drill-down

### Structure
```json
{
  "events_history": {
    "entry-condition-1": [
      {
        "timestamp": "2024-10-29 09:19:00+05:30",
        "event_type": "logic_completed",
        "node_id": "entry-condition-1",
        "node_name": "Entry condition - Bullish",
        "node_type": "EntrySignalNode",
        "children_nodes": [
          { "id": "entry-2", "name": "Entry 2 -Bullish", "type": "EntryNode" }
        ],
        "conditions_evaluated": [
          {
            "lhs_expression": { "type": "current_time" },
            "rhs_expression": { "type": "time_function", "timeValue": "09:17" },
            "lhs_value": "2024-10-29 09:19:00",
            "rhs_value": "2024-10-29 09:17:00",
            "operator": ">=",
            "result": true
          },
          {
            "lhs_expression": { "name": "rsi_1764509210372", "type": "indicator" },
            "rhs_expression": { "type": "number", "value": 30.0 },
            "lhs_value": 28.39,
            "rhs_value": 30.0,
            "operator": "<",
            "result": true
          }
        ],
        "condition_substitution": "\"2024-10-29 09:19:00\" >= \"2024-10-29 09:17:00\" AND 28.39 < 30.0",
        "condition_preview": "Time >= 09:17 AND RSI(14) < 30"
      }
    ],
    "entry-2": [
      {
        "timestamp": "2024-10-29 09:19:00+05:30",
        "event_type": "logic_completed",
        "node_id": "entry-2",
        "node_name": "Entry 2 -Bullish",
        "node_type": "EntryNode",
        "action": {
          "type": "place_order",
          "action_type": "entry",
          "order_id": "ENTRY_entry-2_20251208_191425",
          "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
          "side": "SELL",
          "quantity": 1,
          "price": 181.6,
          "order_type": "MARKET",
          "exchange": "NFO",
          "status": "COMPLETE"
        },
        "position": {
          "position_id": "entry-2-pos1",
          "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
          "side": "sell",
          "quantity": 1,
          "entry_price": 181.6,
          "entry_time": "2024-10-29T09:19:00+05:30",
          "node_id": "entry-2"
        },
        "entry_config": {
          "max_entries": 9,
          "position_num": 1,
          "re_entry_num": 0,
          "positions_config": [ ... ]
        },
        "ltp_store": {
          "NIFTY": { "ltp": 24469.25, "timestamp": "..." },
          "NIFTY:2024-11-07:OPT:24250:PE": { "ltp": 122.6, "timestamp": "..." }
        }
      }
    ],
    "exit-3": [
      {
        "timestamp": "2024-10-29 10:48:00+05:30",
        "event_type": "logic_completed",
        "node_id": "exit-3",
        "node_name": "Exit 3 - SL",
        "node_type": "ExitNode",
        "action": {
          "type": "exit_order",
          "target_position_id": "entry-2-pos1",
          "exit_type": "market",
          "order_type": "MARKET"
        },
        "exit_result": {
          "positions_closed": 1,
          "exit_price": 260.05,
          "pnl": -78.45,
          "exit_time": "2024-10-29 10:48:00+05:30"
        },
        "exit_config": { ... },
        "ltp_store": { ... }
      }
    ]
  },
  "current_state": {
    "exit-condition-4": {
      "timestamp": "2024-10-29 15:25:00+05:30",
      "status": "active",
      "node_id": "exit-condition-4",
      "node_name": "Exit condition - SL",
      "node_type": "ExitSignalNode",
      "children_nodes": [ ... ]
    }
  }
}
```

### UI Display Guidelines

#### Node Timeline View
Display events chronologically as a vertical timeline:

```
┌─────────────────────────────────────────────────────────────┐
│ 09:19:00 ● Entry Condition - Bullish (TRIGGERED)           │
│          ├─ ✓ Time >= 09:17 (09:19:00 >= 09:17:00)        │
│          └─ ✓ RSI(14) < 30 (28.39 < 30.0)                 │
│                                                             │
│ 09:19:00 ● Entry 2 - Bullish (ORDER PLACED)               │
│          ├─ Symbol: NIFTY 24250 PE                         │
│          ├─ Side: SELL                                     │
│          ├─ Quantity: 1                                    │
│          ├─ Price: ₹181.6                                  │
│          └─ Position ID: entry-2-pos1                      │
│                                                             │
│ 10:48:00 ● Exit 3 - SL (POSITION CLOSED)                  │
│          ├─ Exit Price: ₹260.05                            │
│          ├─ P&L: -₹78.45 ❌                                │
│          └─ Target: entry-2-pos1                           │
└─────────────────────────────────────────────────────────────┘
```

#### Condition Details (Expandable)
When user clicks on a condition node:
```
Entry condition - Bullish
├─ Condition 1: ✓ PASSED
│  Expression: Time >= 09:17
│  Evaluated: "2024-10-29 09:19:00" >= "2024-10-29 09:17:00"
│  Result: TRUE
│
├─ Condition 2: ✓ PASSED
│  Expression: RSI(14) < 30
│  Evaluated: 28.39 < 30.0
│  Result: TRUE
│
└─ Final: ALL CONDITIONS MET → TRIGGERED
```

#### Action Node Details
When user clicks on an entry/exit node:
```
Entry 2 - Bullish
├─ Action: Place Order (MARKET)
├─ Symbol: NIFTY:2024-11-07:OPT:24250:PE
├─ Side: SELL
├─ Quantity: 1
├─ Entry Price: ₹181.6
├─ Order ID: ENTRY_entry-2_20251208_191425
├─ Status: COMPLETE ✓
└─ Position Created: entry-2-pos1
```

#### Data Loading Strategy
- **Lazy Load**: Load diagnostics only when user clicks "View Timeline"
- **Decompress**: Client must decompress gzipped data before parsing
- **Cache**: Cache diagnostics client-side after first load

---

## **3. node_current_state - Live Node Status**

### Purpose
Provides **real-time snapshot** of currently active/pending/completed nodes. Used ONLY for live trading to show "what's happening right now".

### When to Use
- Live trading dashboard (poll every 1 second)
- Real-time node status indicators
- "Why didn't it trigger?" analysis (show latest condition values)
- Live order status monitoring

### Structure
```json
{
  "node_current_state": {
    "entry-condition-1": {
      "timestamp": "2024-12-08 14:32:15+05:30",
      "status": "active",
      "node_id": "entry-condition-1",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "children_nodes": [
        { "id": "entry-2", "name": "Entry 2 -Bullish", "type": "EntryNode" }
      ],
      "conditions_evaluated": [
        {
          "lhs_value": "2024-12-08 14:32:15",
          "rhs_value": "2024-12-08 09:17:00",
          "operator": ">=",
          "result": true
        },
        {
          "lhs_value": 31.2,
          "rhs_value": 30.0,
          "operator": "<",
          "result": false
        }
      ],
      "condition_substitution": "\"2024-12-08 14:32:15\" >= \"2024-12-08 09:17:00\" AND 31.2 < 30.0",
      "condition_preview": "Time >= 09:17 AND RSI(14) < 30"
    },
    "entry-2": {
      "timestamp": "2024-12-08 14:32:10+05:30",
      "status": "pending",
      "node_id": "entry-2",
      "node_name": "Entry 2 -Bullish",
      "node_type": "EntryNode",
      "children_nodes": [ ... ],
      "pending_reason": "Waiting for order fill",
      "action": {
        "type": "place_order",
        "action_type": "entry",
        "order_id": "ENTRY_entry-2_20251208_143210",
        "symbol": "NIFTY:2024-12-12:OPT:24500:PE",
        "side": "SELL",
        "quantity": 50,
        "price": 0,
        "order_type": "MARKET",
        "status": "PENDING"
      }
    },
    "exit-3": {
      "timestamp": "2024-12-08 14:30:00+05:30",
      "status": "completed",
      "node_id": "exit-3",
      "node_name": "Exit 3 - SL",
      "node_type": "ExitNode",
      "children_nodes": [],
      "action": {
        "type": "exit_order",
        "target_position_id": "entry-2-pos1"
      },
      "exit_result": {
        "positions_closed": 1,
        "exit_price": 260.05,
        "pnl": -78.45,
        "exit_time": "2024-12-08 14:30:00+05:30"
      }
    },
    "exit-7": {
      "timestamp": "2024-12-08 14:30:05+05:30",
      "status": "completed",
      "node_id": "exit-7",
      "node_name": "Exit 7 - Target",
      "node_type": "ExitNode",
      "skip_reason": {
        "executed": true,
        "skipped": true,
        "reason": "Position entry-2-pos1 already closed by another exit node",
        "exit_reason": "position_already_closed"
      }
    }
  }
}
```

### UI Display Guidelines

#### Live Node Status Dashboard
Display nodes grouped by status:

```
┌─────────────────────────────────────────────────────────────┐
│ 🟡 ACTIVE NODES (Evaluating Conditions)                    │
├─────────────────────────────────────────────────────────────┤
│ Entry condition - Bullish                                   │
│ ├─ ✓ Time >= 09:17 (14:32:15 >= 09:17:00)                 │
│ └─ ✗ RSI(14) < 30 (31.2 < 30.0) ← WHY IT'S NOT TRIGGERING │
│                                                             │
│ Exit condition - SL                                         │
│ ├─ ✗ P&L% <= -5% (-3.2% <= -5.0%) ← STILL WAITING         │
│ └─ Status: Monitoring position entry-2-pos1                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔵 PENDING NODES (Waiting for Action)                      │
├─────────────────────────────────────────────────────────────┤
│ Entry 2 - Bullish                                           │
│ ├─ Status: Waiting for order fill                          │
│ ├─ Order: SELL 50 NIFTY 24500 PE @ MARKET                 │
│ └─ Order ID: ENTRY_entry-2_20251208_143210                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🟢 COMPLETED NODES (Just Finished - Auto-hide after 5s)    │
├─────────────────────────────────────────────────────────────┤
│ Exit 3 - SL                                                 │
│ ├─ Position Closed: entry-2-pos1                           │
│ ├─ Exit Price: ₹260.05                                     │
│ └─ P&L: -₹78.45 ❌                                         │
│                                                             │
│ Exit 7 - Target (SKIPPED)                                  │
│ └─ Reason: Position already closed by Exit 3               │
└─────────────────────────────────────────────────────────────┘
```

#### Node Status Colors
- **Active (🟡 Yellow)**: Currently evaluating, show latest condition values
- **Pending (🔵 Blue)**: Waiting for async operation (order fill)
- **Completed (🟢 Green)**: Just finished, fade out after 5 seconds

#### Polling Strategy
```javascript
// Poll every 1 second
setInterval(async () => {
  const response = await fetch('/api/live/node-state?strategy_id=X');
  const data = await response.json();
  
  // Update UI with latest node states
  updateNodeDashboard(data.node_current_state);
}, 1000);
```

#### Auto-Hide Completed Nodes
```javascript
// After 5 seconds, fade out completed nodes
setTimeout(() => {
  document.querySelectorAll('.node-completed').forEach(el => {
    el.style.opacity = '0.5';
    setTimeout(() => el.remove(), 1000); // Remove after fade
  });
}, 5000);
```

---

## **Data Flow Summary**

### Backtesting Flow

#### **Option 1: Run New Backtest**
1. **User Action**: Click "Run Backtest" button
2. **Show Form**: Date range picker (from_date / to_date)
3. **Submit**: `POST /api/backtest/run` with `user_id`, `session_id`, `from_date`, `to_date` → Get `job_id`
4. **Show Progress Modal**: Display progress bar and status
5. **Poll Status**: Call `/api/backtest/status/{job_id}` every 2s
   - Update progress bar with `percent_complete`
   - Show current date being processed
6. **On Complete**: Redirect to results view with `results_url`
7. **View Results**: Load sessions from the backtest run

#### **Option 2: View Existing Backtest Results**
1. **Initial Load**: Call `/api/backtest/sessions` → Display day-wise table (from previous runs)
2. **Day Click**: Call `/api/backtest/session-detail?date=X` → Show trades (from `SESSION_SUMMARY`)
3. **Timeline Click**: Call `/api/backtest/diagnostics?date=X` → Show node timeline (from `diagnostics_export`)

#### **UI Components Needed:**
- ✅ **Run Backtest Button** → Opens form modal
- ✅ **Backtest Config Form** → Simple date range picker (from_date, to_date)
- ✅ **Progress Modal** → Progress bar, current status, elapsed time
- ✅ **Sessions Table** → Shows all backtested days
- ✅ **Error Alert** → Shows failure reason if backtest fails

### Live Trading Flow
1. **Initial Load**: Call `/api/live/session-summary` → Show positions table (from `SESSION_SUMMARY`)
2. **Start Polling**: Call `/api/live/node-state` every 1s → Update node status indicators (from `node_current_state`)
3. **Refresh Positions**: Call `/api/live/session-summary` every 5-10s → Update P&L (from `SESSION_SUMMARY`)
4. **Timeline Click**: Call `/api/live/diagnostics` → Show node timeline (from `diagnostics_export`)

---

## **Key Differences: Backtest vs Live**

| Aspect | Backtest | Live |
|--------|----------|------|
| **SESSION_SUMMARY** | Static (pre-generated) | Dynamic (continuously updated) |
| **diagnostics_export** | Static (full session) | Dynamic (growing during session) |
| **node_current_state** | Not used | Polled every 1s |
| **Data Size** | Fixed | Growing |
| **UI Updates** | On-demand only | Real-time polling |

---

## **Implementation Checklist**

### Required Libraries
- **Decompression**: `pako.js` or `fflate.js` (for gzipped diagnostics)
- **Charts**: Chart.js or Recharts (for P&L visualization)
- **Date/Time**: Day.js or date-fns (for timestamp formatting)

### UI Components to Build

#### **Backtesting Components:**
1. ✅ **Run Backtest Button & Modal** (simple form with date range only)
2. ✅ **Progress Modal** (progress bar, status, elapsed time)
3. ✅ **Sessions Table** (uses `SESSION_SUMMARY.summary`)
4. ✅ **Positions Table** (uses `SESSION_SUMMARY.positions`)
5. ✅ **P&L Summary Cards** (uses `SESSION_SUMMARY.summary`)
6. ✅ **Node Timeline View** (uses `diagnostics_export.events_history`)
7. ✅ **Condition Details Modal** (uses `conditions_evaluated` from diagnostics)

#### **Live Trading Components:**
8. ✅ **Live Node Dashboard** (uses `node_current_state`)
9. ✅ **Real-time Status Indicators** (uses `node_current_state.status`)
10. ✅ **Connection Status Indicator** (WebSocket status)

### Responsive Design
- Desktop: Show all 3 columns (Sessions | Positions | Timeline)
- Tablet: Show 2 columns (Sessions | Positions), Timeline in modal
- Mobile: Show 1 column, stacked views

---

## **Code Implementation Examples**

### Run Backtest Flow (React/TypeScript)

```typescript
// 1. Backtest Config Form Component
interface BacktestConfig {
  user_id: string;
  session_id: string;
  from_date: string;
  to_date: string;
}

function RunBacktestModal({ userId, sessionId, onClose }: { userId: string, sessionId: string, onClose: () => void }) {
  const [config, setConfig] = useState<BacktestConfig>({
    user_id: userId,
    session_id: sessionId,
    from_date: '2024-10-01',
    to_date: '2024-10-31'
  });
  
  const handleSubmit = async () => {
    // Start backtest
    const response = await fetch('/api/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    
    const { job_id } = await response.json();
    
    // Show progress modal and start polling
    showProgressModal(job_id);
    onClose();
  };
  
  return (
    <Modal>
      <h2>Run Backtest</h2>
      <form onSubmit={handleSubmit}>
        <DateRangePicker
          fromDate={config.from_date}
          toDate={config.to_date}
          onChange={(from, to) => setConfig({...config, from_date: from, to_date: to})}
        />
        <Button type="submit">Run Backtest</Button>
      </form>
    </Modal>
  );
}

// 2. Progress Modal Component
function BacktestProgressModal({ jobId }: { jobId: string }) {
  const [progress, setProgress] = useState({
    percent_complete: 0,
    current_date: '',
    status: 'running',
    error: null as string | null
  });
  
  useEffect(() => {
    const pollInterval = setInterval(async () => {
      const response = await fetch(`/api/backtest/status/${jobId}`);
      const data = await response.json();
      
      setProgress({
        percent_complete: data.progress?.percent_complete || 0,
        current_date: data.progress?.current_date || '',
        status: data.status,
        error: data.error || null
      });
      
      if (data.status === 'completed') {
        clearInterval(pollInterval);
        // Redirect to results
        setTimeout(() => {
          window.location.href = data.results_url;
        }, 1000);
      } else if (data.status === 'failed') {
        clearInterval(pollInterval);
      }
    }, 2000);
    
    return () => clearInterval(pollInterval);
  }, [jobId]);
  
  return (
    <Modal>
      <h2>Running Backtest...</h2>
      
      {progress.status === 'running' && (
        <>
          <ProgressBar value={progress.percent_complete} max={100} />
          <p>{progress.percent_complete.toFixed(1)}% complete</p>
          <p>Processing: {progress.current_date}</p>
        </>
      )}
      
      {progress.status === 'completed' && (
        <SuccessMessage>
          ✅ Backtest completed! Redirecting to results...
        </SuccessMessage>
      )}
      
      {progress.status === 'failed' && (
        <ErrorMessage>
          ❌ Backtest failed: {progress.error}
        </ErrorMessage>
      )}
    </Modal>
  );
}

// 3. Sessions Table Component
function BacktestSessionsTable({ sessions }: { sessions: any[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>P&L</th>
          <th>Trades</th>
          <th>Win Rate</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((session) => (
          <tr key={session.session_date}>
            <td>{session.session_date}</td>
            <td className={session.total_pnl >= 0 ? 'text-green' : 'text-red'}>
              ₹{session.total_pnl.toFixed(2)}
            </td>
            <td>{session.total_positions}</td>
            <td>{session.win_rate_percent.toFixed(1)}%</td>
            <td>
              <Button onClick={() => viewDayDetail(session.session_date)}>
                View Details
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## **Error Handling**

### Backtest Errors
- **Invalid Date Range**: Show "From date must be before To date"
- **Backtest Failed**: Display error message from `error_details.message`
- **Job Not Found**: Show "Backtest job not found, may have expired"
- **Timeout**: If backtest takes > 10 min, show "Taking longer than expected, check status"
- **Network Error**: Retry polling with exponential backoff (2s, 4s, 8s...)

### Missing Data
- If `exit_price` is `null` → Show "Position Open" badge
- If `diagnostics_export` is missing → Show "Diagnostics unavailable"
- If `node_current_state` is empty → Show "No active nodes"

### Live Connection Loss
- If polling fails → Show "Connection Lost" indicator
- Retry with exponential backoff (1s, 2s, 4s, 8s...)
- Show last successful update timestamp

### Large Datasets
- If `diagnostics_export` > 1MB → Show warning "Large dataset, may take time to load"
- Use virtual scrolling for large position tables
- Paginate node timeline (show 50 events at a time)

---

## **Testing Scenarios**

### Backtesting
1. **Run Backtest**: Submit form → See progress modal → Progress updates every 2s
2. **Backtest Completes**: Progress reaches 100% → Show success message → Redirect to results
3. **Backtest Fails**: Show error message with reason (e.g., "Invalid date range")
4. **View Existing Results**: Load sessions table → Click day → View trades
5. **Empty Backtest**: 0 positions → Show "No trades generated"
6. **Long-Running Backtest**: Takes > 5 min → Progress bar keeps updating

### Common Scenarios
7. **Empty Session**: 0 positions → Show "No trades yet"
8. **In-Progress Session**: Some positions open → Show "Session In Progress" badge
9. **All Losses**: Win rate 0% → Show in red
10. **Position Already Closed**: Show skip reason in timeline
11. **Network Failure**: Polling stops → Show reconnection indicator

---

## **Performance Optimization**

- **Lazy Load Diagnostics**: Only load when user clicks
- **Debounce Polling**: If user switches tabs, pause polling
- **Cache Backtest Data**: Immutable, cache indefinitely
- **Compress Responses**: All large JSON should be gzipped
- **Virtual Scrolling**: For tables with 100+ rows

---

## **Accessibility**

- Use semantic HTML (`<table>`, `<th>`, `<td>` for tables)
- Add ARIA labels for status indicators (`aria-label="Active"`)
- Keyboard navigation for timeline
- Color-blind friendly: Use icons + colors (✓/✗ + green/red)

---

## **Final Notes**

- **All timestamps** are in IST (UTC+5:30), format as `DD MMM YYYY HH:mm:ss`
- **Currency**: Always prefix with ₹ symbol
- **Percentages**: Show 1 decimal place (e.g., "43.2%")
- **Node Names**: Truncate if > 30 chars, show full on hover
- **Position IDs**: Hide by default, show in details modal

---

## **Transaction Timeline View** ⚠️ CRITICAL

### **5-Step Flow**
```
🟢 Entry Signal → 📥 Entry → 🔔 Exit Signal → 📤 Exit → 🔄 Re-Entry
   (Why enter)    (Open)    (Why exit)     (Close)   (Next?)
```

### **Key Points**
1. **Link by position_id**: Track same position across nodes
2. **Exit Signal is CRITICAL**: Shows WHY (SL/Target/TSL)
3. **Use re_entry_num**: Group re-entries together
4. **Follow children_nodes**: Navigate parent-child chain

### **See TRANSACTION_UI_DESIGN.md for complete implementation**

Good luck building the UI! 🚀
