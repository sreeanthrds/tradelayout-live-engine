# Live Trading UI Data Requirements Analysis

## Overview
The UI expects live trading data to **exactly match** the backtest report format. The View Trade Modal uses the same components for both backtest and live trading.

---

## 🎯 Key Finding: Data Format Must Match Backtest

### Components Used (Same for Both)
1. **SummaryDashboard** - Shows P&L, win rate, trade count
2. **TradesTable** - Shows all closed trades with execution flow
3. **NodeDetailModal** - Shows detailed node execution data

---

## 📊 Required Data Structure

### 1. Trades Array
**Format:** Array of Trade objects (same as `trades_daily.json`)

```typescript
interface Trade {
  trade_id: string;              // Unique trade identifier
  symbol: string;                // Trading symbol
  entry_time: string;            // Entry timestamp
  exit_time: string;             // Exit timestamp
  entry_price: number;           // Entry price
  exit_price: number;            // Exit price
  quantity: number;              // Trade quantity
  side: 'buy' | 'sell';          // Trade direction
  pnl: number;                   // Profit/Loss
  pnl_percentage: number;        // P&L percentage
  charges: number;               // Transaction charges
  net_pnl: number;               // Net P&L after charges
  
  // Execution flow (for node visualization)
  execution_ids?: string[];      // Node execution IDs
}
```

**Source:** `trades_daily.json.gz` → `trades` array

---

### 2. Events History (Node Execution Records)
**Format:** Dictionary of execution_id → ExecutionNode

```typescript
interface ExecutionNode {
  execution_id: string;          // Unique execution ID
  node_id: string;               // Node identifier
  node_name: string;             // Node display name
  node_type: string;             // start|entry|exit|condition|etc
  timestamp: string;             // Execution timestamp
  status: string;                // Node status
  
  // Node evaluation data (context-specific)
  evaluation_data?: {
    // Entry node
    entry_condition?: {
      condition_met: boolean;
      indicator_values: Record<string, any>;
    };
    
    // Exit node
    exit_condition?: {
      exit_type: string;
      trigger_values: Record<string, any>;
    };
    
    // Condition node
    condition_result?: boolean;
    
    // Any other node-specific data
    [key: string]: any;
  };
  
  // Parent/child relationships
  parent_id?: string;
  children?: string[];
}
```

**Source:** `diagnostics_export.json.gz` → `events_history` object

---

### 3. Summary (Daily Summary)
**Format:** DailySummary object

```typescript
interface DailySummary {
  total_trades: number;          // Total closed trades
  total_pnl: string;             // Total P&L (formatted)
  winning_trades: number;        // Number of winning trades
  losing_trades: number;         // Number of losing trades
  win_rate: string;              // Win rate percentage
  
  // Optional additional metrics
  avg_win?: number;
  avg_loss?: number;
  max_drawdown?: number;
  sharpe_ratio?: number;
}
```

**Source:** `trades_daily.json.gz` → `summary` object

---

### 4. Current Time (Backtest Time)
**Format:** ISO timestamp string

```typescript
currentTime: string;  // "2024-10-29T10:15:30"
```

This shows the current simulation time (for live backtest replay).

---

## 🔄 SSE Stream Events

### Current Implementation
The frontend connects to: `http://localhost:8000/api/simple/live/stream/{session_id}`

### Expected SSE Events

#### 1. `data` Event (Main Update)
```json
{
  "status": "running" | "completed",
  "timestamp": "2024-12-25T10:15:30",
  "current_time": "2024-10-29T10:15:30",  // Backtest time
  "accumulated": {
    "trades": [...],           // All trades so far
    "events_history": {...},   // All node executions
    "summary": {...}           // Current summary stats
  }
}
```

#### 2. `completed` Event (Session End)
```json
{
  "status": "completed",
  "timestamp": "2024-12-25T10:30:00",
  "accumulated": {
    "trades": [...],           // Final trades
    "events_history": {...},   // Final node executions
    "summary": {...}           // Final summary
  }
}
```

---

## 🗄️ Backend Files Structure

### Current Backtest Format
```
backtest_results/{strategy_id}/{date}/
  ├── trades_daily.json.gz       # Trades + Summary
  └── diagnostics_export.json.gz # Events History
```

### trades_daily.json.gz
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 10,
    "total_pnl": "5234.50",
    "winning_trades": 7,
    "losing_trades": 3,
    "win_rate": "70.0"
  },
  "trades": [
    {
      "trade_id": "trade_1",
      "symbol": "NIFTY:2024-11-07:OPT:24250:CE",
      "entry_time": "2024-10-29T09:30:00",
      "exit_time": "2024-10-29T10:15:30",
      "entry_price": 267.80,
      "exit_price": 285.50,
      "quantity": 50,
      "side": "buy",
      "pnl": 885.00,
      "pnl_percentage": 6.61,
      "execution_ids": ["exec_entry_1", "exec_exit_1"]
    }
  ]
}
```

### diagnostics_export.json.gz
```json
{
  "events_history": {
    "exec_entry_1": {
      "execution_id": "exec_entry_1",
      "node_id": "entry-1",
      "node_name": "Entry Condition 1",
      "node_type": "entry",
      "timestamp": "2024-10-29T09:30:00",
      "status": "executed",
      "evaluation_data": {
        "entry_condition": {
          "condition_met": true,
          "indicator_values": {
            "rsi": 35.2,
            "ema_20": 24250.5
          }
        }
      }
    }
  }
}
```

---

## 📋 Required API Endpoints

### 1. Add Session to Execution Dictionary
```
POST /api/v1/live/session/add-to-execution
{
  "session_id": "user_123_strategy_456_broker_789",
  "user_id": "user_123",
  "strategy_id": "strategy_456",
  "broker_connection_id": "broker_789",
  "scale": 1.0
}

Response:
{
  "success": true,
  "session_id": "user_123_strategy_456_broker_789",
  "status": "added_to_execution"
}
```

### 2. Remove Session from Execution Dictionary
```
POST /api/v1/live/session/remove-from-execution
{
  "session_id": "user_123_strategy_456_broker_789"
}

Response:
{
  "success": true,
  "session_id": "user_123_strategy_456_broker_789",
  "status": "removed_from_execution"
}
```

### 3. Get Session Data (Live Report)
```
GET /api/v1/live/session/{session_id}/report

Response:
{
  "session_id": "user_123_strategy_456_broker_789",
  "status": "running" | "completed",
  "current_time": "2024-10-29T10:15:30",
  "trades": [...],           // Same format as trades_daily.json
  "events_history": {...},   // Same format as diagnostics_export.json
  "summary": {...}           // DailySummary format
}
```

---

## 🔄 Data Flow

### Backend → Frontend
```
1. Session Start (API Call)
   POST /api/v1/live/session/add-to-execution
   ↓
2. Session Execution (Background Thread)
   - Engine processes ticks
   - GPS tracks positions
   - OutputWriter logs events
   ↓
3. SSE Stream (Real-time Updates)
   GET /api/simple/live/stream/{session_id}
   - Sends accumulated trades
   - Sends events_history
   - Sends summary stats
   ↓
4. UI Display (Same Components as Backtest)
   - SummaryDashboard
   - TradesTable
   - NodeDetailModal
```

---

## ✅ What's Already Working

1. **SSE Infrastructure** ✅
   - SSE streaming endpoint exists
   - Position updates streaming
   - LTP updates streaming

2. **Data Generation** ✅
   - GPS tracks positions
   - StrategyOutputWriter logs events
   - trades_daily.json.gz created
   - diagnostics_export.json.gz created

3. **Frontend Components** ✅
   - SimpleLiveDashboard uses backtest components
   - useSSELiveData hook ready

---

## ❌ What's Missing

### 1. Execution Dictionary Management
Need endpoints to:
- Add session to execution dict
- Remove session from execution dict
- Query execution dict status

### 2. Data Format Conversion for SSE
Current SSE sends:
- position_update (GPS format)
- ltp_snapshot (LTP store format)

**Need to add:**
- trades_update (trades_daily.json format)
- events_update (diagnostics_export.json format)
- summary_update (DailySummary format)

### 3. Accumulated State Tracking
SSE needs to send **accumulated** data:
- All trades so far (not just deltas)
- All events_history so far
- Current summary stats

---

## 🛠️ Implementation Plan

### Phase 1: Add/Remove Execution Endpoints ✅
```python
@app.post("/api/v1/live/session/add-to-execution")
@app.post("/api/v1/live/session/remove-from-execution")
```

### Phase 2: Enhance SSE to Send Backtest-Format Data
Modify `centralized_tick_processor.py`:
```python
# Get trades from GPS
trades = gps.get_closed_trades()  # Format as trades_daily.json

# Get events from output_writer
events_history = output_writer.get_events_history()

# Calculate summary
summary = calculate_summary(trades)

# Send via SSE
sse_session.add_trades_update(trades, summary, events_history)
```

### Phase 3: Update Frontend Hook (Already Done)
`useSSELiveData.ts` already handles:
- trades array
- eventsHistory
- summary calculation

---

## 📝 Additional Questions Needed

1. **Session ID Format:**
   - Confirm format: `{user_id}_{strategy_id}_{broker_connection_id}`?
   - Max length considerations?

2. **Execution Dict Location:**
   - In-memory dict in `live_session_manager`?
   - Or separate execution tracker?

3. **Data Persistence:**
   - Should live session data persist to files like backtest?
   - If yes, when? (real-time vs end-of-session)

4. **Multiple Sessions:**
   - How to handle same user running multiple strategies?
   - Session isolation important?

---

## 🎯 Summary

**Core Requirement:** Live trading UI must display data in **exact same format** as backtest report.

**Key Data Structures:**
1. `trades` - Array of Trade objects (from GPS)
2. `events_history` - Dict of node executions (from OutputWriter)
3. `summary` - DailySummary stats (calculated from trades)
4. `current_time` - Backtest simulation time

**Missing Pieces:**
1. Execution dict add/remove endpoints
2. SSE enhancement to send backtest-format data
3. Accumulated state tracking in SSE

**Ready to implement once confirmed!** 🚀
