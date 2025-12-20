# Live Simulation SSE Integration Guide for UI

## Overview

This guide provides comprehensive instructions for UI developers to integrate with the Live Simulation API using Server-Sent Events (SSE). The API streams real-time trading simulation data with exact JSON structures matching the backtesting system.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Endpoints](#api-endpoints)
3. [SSE Event Types](#sse-event-types)
4. [JSON Data Structures](#json-data-structures)
5. [Implementation Examples](#implementation-examples)
6. [Data Decompression](#data-decompression)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Architecture Overview

### Data Flow

```
Client → POST /api/v2/live/start
       ← {session_id, stream_url}

Client → GET /api/v2/live/stream/{session_id} (EventSource)
       ← initial_state (gzip)
       ← tick_update (JSON)
       ← node_events (gzip)
       ← trade_update (gzip)
       ← heartbeat

Client → POST /api/v2/live/stop/{session_id}
       ← {status: "stopped"}
```

### Event Types

| Event | Frequency | Compression | Size | Purpose |
|-------|-----------|-------------|------|---------|
| `initial_state` | Once on connect | gzip | Large | Full diagnostics + trades snapshot |
| `tick_update` | Every tick (~1/sec) | None | Small | Node status, positions, P&L |
| `node_events` | On node completion | gzip | Large | Full diagnostics update |
| `trade_update` | On trade close | gzip | Medium | Full trades list |
| `heartbeat` | Every 1 sec (if idle) | None | Tiny | Keep-alive |

---

## How UI Receives Data - Step by Step

### Phase 1: Connect and Get Initial State

**1. UI starts simulation:**
```javascript
POST /api/v1/live/start
{
  "user_id": "user_xxx",
  "strategy_id": "strategy_xxx",
  "broker_connection_id": "broker_xxx"
}

Response:
{
  "session_id": "sim-abc123",
  "stream_url": "/api/v1/live/stream/sim-abc123",
  "status": "starting"
}
```

**2. UI connects to SSE stream:**
```javascript
const eventSource = new EventSource('/api/v1/live/stream/sim-abc123');
```

**3. IMMEDIATELY, UI receives `initial_state` event:**
```javascript
eventSource.addEventListener('initial_state', (event) => {
  const data = JSON.parse(event.data);
  // data = {
  //   "diagnostics": "<base64-gzip>",  // Full diagnostics_export.json
  //   "trades": "<base64-gzip>"         // Full trades_daily.json
  // }
  
  // Decompress both
  const diagnostics = decompressGzip(data.diagnostics);
  const trades = decompressGzip(data.trades);
  
  // NOW YOU HAVE:
  // diagnostics.events_history = {} (empty at start)
  // diagnostics.current_state = {} (empty at start)
  // trades.date = "2024-10-28"
  // trades.summary = {total_trades: 0, ...}
  // trades.trades = [] (empty at start)
  
  // Store in UI state
  setDiagnostics(diagnostics);
  setTrades(trades);
});
```

**Purpose:** This gives UI the **baseline state** to build upon. Even if simulation hasn't started yet, UI has the initial structure.

---

### Phase 2: Receive Live Events (Streaming)

After `initial_state`, the server starts sending **three types of live events** as the simulation runs:

#### Event Flow Timeline

```
Time 0s: [initial_state] → UI gets empty diagnostics + trades
         |
Time 1s: [tick_update] → Node "strategy-controller" becomes Active
         |
Time 2s: [tick_update] → Node "entry-condition-1" becomes Active
         |
Time 5s: [tick_update] → Signal emitted, "entry-2" becomes Pending
         | [node_events] → Full diagnostics update (entry signal completed)
         |
Time 6s: [tick_update] → "entry-2" becomes Active (order placed)
         | [node_events] → Full diagnostics update (entry node completed)
         |
Time 7s: [tick_update] → Position opened, unrealized P&L shown
         |
         ... (many tick_updates showing position P&L changes)
         |
Time 45s: [tick_update] → Exit triggered
          | [node_events] → Full diagnostics update (exit node completed)
          | [trade_update] → Full trades list (trade closed, added to list)
          |
Time 46s: [tick_update] → Position closed, realized P&L updated
          |
          ... (simulation continues)
```

---

### Event Type 1: `tick_update` (Every ~1 second)

**What UI receives:**
```javascript
eventSource.addEventListener('tick_update', (event) => {
  const tick = JSON.parse(event.data);  // NO decompression needed!
  
  // tick = {
  //   "timestamp": "2024-10-28 09:15:30+05:30",
  //   "progress": {
  //     "ticks_processed": 30,
  //     "total_ticks": 44260,
  //     "progress_percentage": 0.07
  //   },
  //   "active_nodes": [
  //     {node_id: "entry-condition-1", status: "active", ...}
  //   ],
  //   "pending_nodes": [
  //     {node_id: "entry-2", status: "pending", ...}
  //   ],
  //   "completed_nodes_this_tick": [
  //     {node_id: "exit-3", event_type: "logic_completed", ...}
  //   ],
  //   "open_positions": [
  //     {position_id: "entry-2-pos1", unrealized_pnl: "-76.70", ...}
  //   ],
  //   "pnl_summary": {
  //     "realized_pnl": "0.00",
  //     "unrealized_pnl": "-76.70",
  //     "total_pnl": "-76.70"
  //   }
  // }
  
  // Update UI IMMEDIATELY (real-time)
  setTickUpdate(tick);
  updateProgressBar(tick.progress.progress_percentage);
  updatePnLDisplay(tick.pnl_summary);
  updateActiveNodeIndicators(tick.active_nodes);
  updatePositionsTable(tick.open_positions);
  
  // Show notification for completed nodes
  if (tick.completed_nodes_this_tick.length > 0) {
    showNotification("Node completed!", tick.completed_nodes_this_tick);
  }
});
```

**Use for:**
- ✅ Progress bar
- ✅ Current P&L display
- ✅ Active/Pending node indicators
- ✅ Open positions table
- ✅ "Just completed" notifications

**DO NOT use for:**
- ❌ Full node history (use diagnostics)
- ❌ Full trades list (use trades)

---

### Event Type 2: `node_events` (When any node completes)

**What UI receives:**
```javascript
eventSource.addEventListener('node_events', (event) => {
  const compressedData = event.data;  // Base64-gzip string
  const diagnostics = decompressGzip(compressedData);
  
  // diagnostics = {
  //   "events_history": {
  //     "exec_strategy-controller_20241028_091500_abc": {...},
  //     "exec_entry-condition-1_20241028_091900_def": {...},
  //     "exec_entry-2_20241028_091900_ghi": {...},
  //     ... (grows over time)
  //   },
  //   "current_state": {
  //     "strategy-controller": {status: "inactive", ...},
  //     "entry-condition-1": {status: "active", ...},
  //     "entry-2": {status: "completed", ...}
  //   }
  // }
  
  // REPLACE entire diagnostics state
  setDiagnostics(diagnostics);
  
  // Update diagnostics panel
  updateNodeTree(diagnostics.current_state);
  updateEventHistory(diagnostics.events_history);
});
```

**When does this fire?**
- Entry signal node completes → `node_events` sent
- Entry action node completes → `node_events` sent  
- Exit signal node completes → `node_events` sent
- Exit action node completes → `node_events` sent
- Square-off node completes → `node_events` sent

**Use for:**
- ✅ Full node execution tree
- ✅ Detailed node diagnostics panel
- ✅ Execution lineage/flow visualization
- ✅ Node-specific data (indicators, conditions, etc.)

**Important:** This is the **full diagnostics state**, not a delta. Replace your entire diagnostics object.

---

### Event Type 3: `trade_update` (When a trade closes)

**What UI receives:**
```javascript
eventSource.addEventListener('trade_update', (event) => {
  const compressedData = event.data;  // Base64-gzip string
  const trades = decompressGzip(compressedData);
  
  // trades = {
  //   "date": "2024-10-28",
  //   "summary": {
  //     "total_trades": 5,
  //     "total_pnl": "-234.50",
  //     "winning_trades": 2,
  //     "losing_trades": 3,
  //     "win_rate": "40.00"
  //   },
  //   "trades": [
  //     {
  //       "trade_id": "entry-2-pos1-r0",
  //       "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  //       "pnl": "-78.45",
  //       "entry_time": "2024-10-28 09:19:00+05:30",
  //       "exit_time": "2024-10-28 10:48:00+05:30",
  //       ...
  //     },
  //     ... (5 trades total)
  //   ]
  // }
  
  // REPLACE entire trades state
  setTrades(trades);
  
  // Update trades panel
  updateTradesList(trades.trades);
  updateTradesSummary(trades.summary);
  
  // Show notification
  const latestTrade = trades.trades[trades.trades.length - 1];
  showNotification(`Trade closed: ${latestTrade.pnl}`);
});
```

**When does this fire?**
- Exit node closes a position → `trade_update` sent
- Square-off node closes positions → `trade_update` sent
- Multiple trades can close at once (you get full list)

**Use for:**
- ✅ Trades history table
- ✅ Trades summary (total P&L, win rate, etc.)
- ✅ Trade details modal
- ✅ Performance charts

**Important:** This is the **full trades list**, not a delta. Replace your entire trades object.

---

### Event Type 4: `heartbeat` (Keep-alive)

**What UI receives:**
```javascript
eventSource.addEventListener('heartbeat', (event) => {
  const data = JSON.parse(event.data);
  // data = {"timestamp": "2024-10-28T09:15:30.123456"}
  
  // Just to confirm connection is alive
  console.log('Heartbeat:', data.timestamp);
  updateConnectionStatus('connected');
});
```

**When does this fire?**
- Every 1 second if no other events are sent
- Keeps SSE connection alive

**Use for:**
- ✅ Connection health indicator
- ✅ Detecting disconnections

---

## Complete Data Flow Example

### Scenario: User Starts Simulation

```javascript
// ============================================================
// STEP 1: START SIMULATION
// ============================================================
const response = await fetch('/api/v1/live/start', {
  method: 'POST',
  body: JSON.stringify({
    user_id: 'user_xxx',
    strategy_id: 'strategy_xxx',
    broker_connection_id: 'broker_xxx'
  })
});
const {session_id, stream_url} = await response.json();

// ============================================================
// STEP 2: CONNECT TO SSE STREAM
// ============================================================
const eventSource = new EventSource(stream_url);

// ============================================================
// STEP 3: RECEIVE INITIAL STATE (ONCE)
// ============================================================
eventSource.addEventListener('initial_state', (event) => {
  const data = JSON.parse(event.data);
  
  // Decompress
  const diagnostics = decompressGzip(data.diagnostics);
  const trades = decompressGzip(data.trades);
  
  console.log('📦 Initial State Received');
  console.log('Events History:', Object.keys(diagnostics.events_history).length); // 0
  console.log('Current State:', Object.keys(diagnostics.current_state).length);   // 0
  console.log('Trades:', trades.trades.length);                                    // 0
  
  // Store in React state
  setDiagnostics(diagnostics);
  setTrades(trades);
  setInitialized(true);
});

// ============================================================
// STEP 4: RECEIVE LIVE EVENTS (CONTINUOUS)
// ============================================================

// Every ~1 second (lightweight, real-time)
eventSource.addEventListener('tick_update', (event) => {
  const tick = JSON.parse(event.data);
  
  console.log('⚡ Tick Update:', tick.timestamp);
  console.log('Progress:', tick.progress.progress_percentage + '%');
  console.log('Active Nodes:', tick.active_nodes.length);
  console.log('Total P&L:', tick.pnl_summary.total_pnl);
  
  // Update UI
  setTickUpdate(tick);
  setProgress(tick.progress.progress_percentage);
  setPnL(tick.pnl_summary.total_pnl);
  
  // Show completed nodes
  tick.completed_nodes_this_tick.forEach(node => {
    toast.success(`${node.node_name} completed`);
  });
});

// When any node completes (heavy, full diagnostics)
eventSource.addEventListener('node_events', (event) => {
  const diagnostics = decompressGzip(event.data);
  
  console.log('🔧 Node Events Update');
  console.log('Events History:', Object.keys(diagnostics.events_history).length);
  console.log('Current State:', Object.keys(diagnostics.current_state).length);
  
  // REPLACE entire diagnostics
  setDiagnostics(diagnostics);
});

// When trade closes (medium, full trades list)
eventSource.addEventListener('trade_update', (event) => {
  const trades = decompressGzip(event.data);
  
  console.log('💰 Trade Update');
  console.log('Total Trades:', trades.summary.total_trades);
  console.log('Total P&L:', trades.summary.total_pnl);
  
  // REPLACE entire trades list
  setTrades(trades);
  
  // Notify user
  const latestTrade = trades.trades[trades.trades.length - 1];
  toast.info(`Trade closed: ${latestTrade.symbol} | P&L: ${latestTrade.pnl}`);
});

// Keep-alive
eventSource.addEventListener('heartbeat', (event) => {
  console.log('💓 Heartbeat');
  setConnectionStatus('connected');
});

// Errors
eventSource.onerror = (error) => {
  console.error('❌ SSE Error:', error);
  setConnectionStatus('disconnected');
};
```

---

## UI State Management Strategy

### Three Separate State Objects

```javascript
const [diagnostics, setDiagnostics] = useState({
  events_history: {},
  current_state: {}
});

const [trades, setTrades] = useState({
  date: '',
  summary: {},
  trades: []
});

const [tickUpdate, setTickUpdate] = useState({
  timestamp: '',
  progress: {},
  active_nodes: [],
  pending_nodes: [],
  completed_nodes_this_tick: [],
  open_positions: [],
  pnl_summary: {}
});
```

### Update Pattern

| Event | State Update | Strategy |
|-------|--------------|----------|
| `initial_state` | Set `diagnostics` + `trades` | **Initialize** with baseline |
| `tick_update` | Set `tickUpdate` | **Update** real-time display |
| `node_events` | **Replace** `diagnostics` | **Full replacement** (not merge!) |
| `trade_update` | **Replace** `trades` | **Full replacement** (not merge!) |

**Critical:** For `node_events` and `trade_update`, always **REPLACE** the entire state object, never merge or append.

---

## Visual Timeline of Events

```
Connection Timeline:
====================

0ms     [CONNECT] EventSource opened
        ↓
10ms    [initial_state] ← Empty diagnostics + empty trades
        UI State: {diagnostics: {}, trades: {}, tick: null}
        ↓
1000ms  [tick_update] ← StartNode active, progress 0.02%
        UI State: {diagnostics: {}, trades: {}, tick: {...}}
        ↓
2000ms  [tick_update] ← EntrySignalNode active, progress 0.05%
        ↓
5000ms  [tick_update] ← Signal emitted, EntryNode pending
        [node_events] ← diagnostics updated (signal node completed)
        UI State: {diagnostics: {1 event}, trades: {}, tick: {...}}
        ↓
6000ms  [tick_update] ← EntryNode active, order placed
        [node_events] ← diagnostics updated (entry node completed)
        UI State: {diagnostics: {2 events}, trades: {}, tick: {...}}
        ↓
7000ms  [tick_update] ← Position opened, unrealized P&L -5.20
        ↓
        ... (many tick_updates with changing P&L)
        ↓
45000ms [tick_update] ← Exit triggered
        [node_events] ← diagnostics updated (exit node completed)
        [trade_update] ← trades updated (1 trade added)
        UI State: {diagnostics: {4 events}, trades: {1 trade}, tick: {...}}
        ↓
46000ms [tick_update] ← Position closed, realized P&L -78.45
        ↓
        ... (simulation continues)
```

---

## API Endpoints

### 1. Start Live Simulation

**Endpoint:** `POST /api/v2/live/start`

**Request Body:**
```json
{
  "user_id": "user-uuid",
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-29",
  "speed_multiplier": 1.0
}
```

**Response:**
```json
{
  "session_id": "sim-a1b2c3d4e5f6g7h8",
  "stream_url": "/api/v2/live/stream/sim-a1b2c3d4e5f6g7h8",
  "status": "running",
  "start_date": "2024-10-29",
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104"
}
```

### 2. Connect to SSE Stream

**Endpoint:** `GET /api/v2/live/stream/{session_id}`

**Headers:**
- `Accept: text/event-stream`
- `Cache-Control: no-cache`

**Connection:** Keep-alive, auto-reconnects on disconnect

### 3. Get Simulation Status

**Endpoint:** `GET /api/v2/live/status/{session_id}`

**Response:**
```json
{
  "session_id": "sim-a1b2c3d4e5f6g7h8",
  "status": "running",
  "progress": {
    "ticks_processed": 15000,
    "total_ticks": 44260,
    "progress_percentage": 33.89
  },
  "pnl_summary": {
    "realized_pnl": "-78.45",
    "unrealized_pnl": "-13.85",
    "total_pnl": "-92.30"
  }
}
```

### 4. Stop Simulation

**Endpoint:** `POST /api/v2/live/stop/{session_id}`

**Response:**
```json
{
  "session_id": "sim-a1b2c3d4e5f6g7h8",
  "status": "stopped"
}
```

---

## SSE Event Types

### Event 1: `initial_state`

**When:** Sent once immediately after SSE connection established

**Format:**
```
event: initial_state
data: {"diagnostics": "<base64-gzip-json>", "trades": "<base64-gzip-json>"}
```

**Payload Structure:**
```javascript
{
  "diagnostics": "<base64-encoded-gzip-compressed-json>",  // diagnostics_export.json
  "trades": "<base64-encoded-gzip-compressed-json>"        // trades_daily.json
}
```

**Decompressed `diagnostics` structure:**
```json
{
  "events_history": {
    "exec_strategy-controller_20241029_091500_6e6acf": { /* node event */ },
    "exec_entry-condition-1_20241029_091900_c8d81d": { /* node event */ }
  },
  "current_state": {
    "strategy-controller": { /* latest node state */ },
    "entry-condition-1": { /* latest node state */ }
  }
}
```

**Decompressed `trades` structure:**
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
  "trades": [
    {
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
    }
  ]
}
```

---

### Event 2: `node_events`

**When:** Sent when any node completes execution (Entry, Exit, Signal, SquareOff, etc.)

**Format:**
```
event: node_events
data: <base64-gzip-json>
```

**Payload:** Base64-encoded gzip-compressed JSON matching `diagnostics_export.json` structure (full `events_history` + `current_state`)

**Usage:** Replace entire diagnostics state with this payload.

---

### Event 3: `trade_update`

**When:** Sent when a trade is closed (position exited)

**Format:**
```
event: trade_update
data: <base64-gzip-json>
```

**Payload:** Base64-encoded gzip-compressed JSON matching `trades_daily.json` structure (full `date` + `summary` + `trades[]`)

**Usage:** Replace entire trades state with this payload.

---

### Event 4: `tick_update`

**When:** Sent every tick (~1 second during simulation)

**Format:**
```
event: tick_update
data: <json-string>
```

**Payload:** Uncompressed JSON

**Structure:**
```json
{
  "timestamp": "2024-10-29 10:47:30+05:30",
  "current_time": "10:47:30",
  "progress": {
    "ticks_processed": 5550,
    "total_ticks": 44260,
    "progress_percentage": 12.54
  },
  "active_nodes": [
    {
      "node_id": "entry-condition-1",
      "execution_id": "exec_entry-condition-1_20241029_091900_c8d81d",
      "parent_execution_id": "exec_strategy-controller_20241029_091500_6e6acf",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "status": "active",
      "last_evaluation": "2024-10-29 10:47:30+05:30",
      "signal_emitted": false
    }
  ],
  "pending_nodes": [
    {
      "node_id": "entry-2",
      "execution_id": null,
      "parent_execution_id": null,
      "node_name": "Entry 2 -Bullish",
      "node_type": "EntryNode",
      "status": "pending",
      "waiting_for": "entry-condition-1"
    }
  ],
  "completed_nodes_this_tick": [
    {
      "node_id": "exit-3",
      "execution_id": "exec_exit-3_20241029_104800_19aea3",
      "parent_execution_id": "exec_exit-condition-2_20241029_104800_dd8b20",
      "node_name": "Exit 3 - SL",
      "node_type": "ExitNode",
      "event_type": "logic_completed",
      "timestamp": "2024-10-29 10:48:00+05:30",
      "result": "position_closed",
      "positions_closed": 1,
      "exit_price": "260.05",
      "pnl": "-78.45"
    }
  ],
  "open_positions": [
    {
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": "181.60",
      "entry_time": "2024-10-29 09:19:00+05:30",
      "current_ltp": "258.30",
      "unrealized_pnl": "-76.70",
      "unrealized_pnl_percent": "-42.24",
      "duration_minutes": 88,
      "node_id": "entry-2",
      "re_entry_num": 0
    }
  ],
  "pnl_summary": {
    "realized_pnl": "0.00",
    "unrealized_pnl": "-76.70",
    "total_pnl": "-76.70",
    "closed_trades": 0,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": "0.00"
  },
  "ltp_store": {
    "NIFTY": {
      "ltp": 24144.8,
      "timestamp": "2024-10-29 10:47:30.000000",
      "volume": 0,
      "oi": 0
    },
    "NIFTY:2024-11-07:OPT:24250:PE": {
      "ltp": 258.3,
      "timestamp": "2024-10-29 10:47:29.500000",
      "volume": 0,
      "oi": 83225
    }
  },
  "candle_data": {
    "NIFTY": {
      "1m": {
        "current": {
          "timestamp": "2024-10-29 10:47:00+05:30",
          "open": 24153.0,
          "high": 24153.75,
          "low": 24140.85,
          "close": 24144.45,
          "volume": 0
        },
        "previous": {
          "timestamp": "2024-10-29 10:46:00+05:30",
          "open": 24160.2,
          "high": 24162.5,
          "low": 24150.0,
          "close": 24152.8,
          "volume": 0,
          "indicators": {
            "rsi(14,close)": 28.15
          }
        }
      }
    }
  }
}
```

**Note:** `completed_nodes_this_tick` array is cleared every tick, so it only shows what happened in the current tick.

---

### Event 5: `heartbeat`

**When:** Sent every 1 second if no other events are emitted

**Format:**
```
event: heartbeat
data: {"timestamp": "2024-10-29T10:47:30.123456"}
```

**Purpose:** Keep connection alive, detect disconnections

---

## JSON Data Structures

### Critical Data Type Rules

⚠️ **IMPORTANT:** The following fields are **strings** (not numbers):

**In `trades_daily.json`:**
- `summary.total_pnl`
- `summary.win_rate`
- `trade.entry_price`
- `trade.exit_price`
- `trade.pnl`
- `trade.pnl_percent`

**In `tick_update`:**
- `pnl_summary.realized_pnl`
- `pnl_summary.unrealized_pnl`
- `pnl_summary.total_pnl`
- `pnl_summary.win_rate`
- `open_positions[].entry_price`
- `open_positions[].unrealized_pnl`
- `open_positions[].unrealized_pnl_percent`

**Timestamp Formats:**
- Trade times: `"YYYY-MM-DD HH:MM:SS+05:30"` (space-separated with timezone)
- Position entry_time: `"YYYY-MM-DDT HH:MM:SS+05:30"` (ISO format with T)
- LTP store timestamps: `"YYYY-MM-DD HH:MM:SS.ffffff"` (no timezone)

### Node Status Values

- `"active"` - Node is actively executing (Entry/Exit conditions checking)
- `"pending"` - Node waiting for parent signal
- `"completed"` - Node finished execution
- `"failed"` - Node encountered error

### Execution Lineage

Every node event includes:
- `execution_id`: Unique ID for this execution
- `parent_execution_id`: ID of parent node execution (forms chain)

This creates execution flow chains visible in:
- `trade.entry_flow_ids[]` - Chain from StartNode to Entry
- `trade.exit_flow_ids[]` - Chain from StartNode to Exit

---

## Implementation Examples

### JavaScript/TypeScript Example

```typescript
// 1. Install dependencies
// npm install pako  // For gzip decompression

import pako from 'pako';

interface LiveSimulationState {
  diagnostics: any;
  trades: any;
  tickUpdate: any;
}

class LiveSimulationClient {
  private eventSource: EventSource | null = null;
  private state: LiveSimulationState = {
    diagnostics: null,
    trades: null,
    tickUpdate: null
  };

  // Start simulation
  async startSimulation(strategyId: string, startDate: string): Promise<string> {
    const response = await fetch('/api/v2/live/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user-123',
        strategy_id: strategyId,
        start_date: startDate,
        speed_multiplier: 1.0
      })
    });

    const data = await response.json();
    return data.session_id;
  }

  // Connect to SSE stream
  connectToStream(sessionId: string, callbacks: {
    onInitialState?: (diagnostics: any, trades: any) => void;
    onNodeEvents?: (diagnostics: any) => void;
    onTradeUpdate?: (trades: any) => void;
    onTickUpdate?: (tick: any) => void;
    onError?: (error: string) => void;
  }) {
    this.eventSource = new EventSource(`/api/v2/live/stream/${sessionId}`);

    // Initial state
    this.eventSource.addEventListener('initial_state', (event) => {
      const data = JSON.parse(event.data);
      this.state.diagnostics = this.decompressGzip(data.diagnostics);
      this.state.trades = this.decompressGzip(data.trades);
      
      callbacks.onInitialState?.(this.state.diagnostics, this.state.trades);
    });

    // Node events (compressed)
    this.eventSource.addEventListener('node_events', (event) => {
      this.state.diagnostics = this.decompressGzip(event.data);
      callbacks.onNodeEvents?.(this.state.diagnostics);
    });

    // Trade updates (compressed)
    this.eventSource.addEventListener('trade_update', (event) => {
      this.state.trades = this.decompressGzip(event.data);
      callbacks.onTradeUpdate?.(this.state.trades);
    });

    // Tick updates (uncompressed)
    this.eventSource.addEventListener('tick_update', (event) => {
      this.state.tickUpdate = JSON.parse(event.data);
      callbacks.onTickUpdate?.(this.state.tickUpdate);
    });

    // Heartbeat
    this.eventSource.addEventListener('heartbeat', (event) => {
      console.log('Heartbeat:', JSON.parse(event.data).timestamp);
    });

    // Errors
    this.eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      callbacks.onError?.('Connection error');
    };
  }

  // Decompress gzip base64
  private decompressGzip(base64Data: string): any {
    try {
      // Decode base64
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Decompress gzip
      const decompressed = pako.ungzip(bytes, { to: 'string' });
      
      // Parse JSON
      return JSON.parse(decompressed);
    } catch (error) {
      console.error('Decompression error:', error);
      throw error;
    }
  }

  // Stop simulation
  async stopSimulation(sessionId: string) {
    await fetch(`/api/v2/live/stop/${sessionId}`, { method: 'POST' });
    this.eventSource?.close();
  }

  // Get current state
  getState(): LiveSimulationState {
    return this.state;
  }
}

// Usage
const client = new LiveSimulationClient();

// Start
const sessionId = await client.startSimulation(
  '5708424d-5962-4629-978c-05b3a174e104',
  '2024-10-29'
);

// Connect
client.connectToStream(sessionId, {
  onInitialState: (diagnostics, trades) => {
    console.log('Initial diagnostics:', diagnostics);
    console.log('Initial trades:', trades);
    // Update UI with full state
  },
  
  onNodeEvents: (diagnostics) => {
    console.log('Node completed:', diagnostics);
    // Update diagnostics panel
  },
  
  onTradeUpdate: (trades) => {
    console.log('Trade closed:', trades);
    // Update trades list
  },
  
  onTickUpdate: (tick) => {
    console.log('Tick update:', tick);
    // Update live status, positions, P&L
    // Show active/pending nodes
    // Highlight completed_nodes_this_tick
  },
  
  onError: (error) => {
    console.error('Error:', error);
    // Show error to user
  }
});

// Later: Stop
await client.stopSimulation(sessionId);
```

---

### React Example

```tsx
import React, { useEffect, useState } from 'react';
import pako from 'pako';

interface DiagnosticsState {
  events_history: Record<string, any>;
  current_state: Record<string, any>;
}

interface TradesState {
  date: string;
  summary: any;
  trades: any[];
}

interface TickUpdate {
  timestamp: string;
  active_nodes: any[];
  pending_nodes: any[];
  completed_nodes_this_tick: any[];
  open_positions: any[];
  pnl_summary: any;
}

function LiveSimulation({ strategyId, startDate }: Props) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsState | null>(null);
  const [trades, setTrades] = useState<TradesState | null>(null);
  const [tickUpdate, setTickUpdate] = useState<TickUpdate | null>(null);
  const [status, setStatus] = useState<string>('idle');

  // Decompress helper
  const decompressGzip = (base64Data: string): any => {
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const decompressed = pako.ungzip(bytes, { to: 'string' });
    return JSON.parse(decompressed);
  };

  // Start simulation
  const startSimulation = async () => {
    const response = await fetch('/api/v2/live/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user-123',
        strategy_id: strategyId,
        start_date: startDate,
        speed_multiplier: 1.0
      })
    });
    const data = await response.json();
    setSessionId(data.session_id);
    setStatus('running');
  };

  // Connect to SSE
  useEffect(() => {
    if (!sessionId) return;

    const eventSource = new EventSource(`/api/v2/live/stream/${sessionId}`);

    eventSource.addEventListener('initial_state', (event) => {
      const data = JSON.parse(event.data);
      setDiagnostics(decompressGzip(data.diagnostics));
      setTrades(decompressGzip(data.trades));
    });

    eventSource.addEventListener('node_events', (event) => {
      setDiagnostics(decompressGzip(event.data));
    });

    eventSource.addEventListener('trade_update', (event) => {
      setTrades(decompressGzip(event.data));
    });

    eventSource.addEventListener('tick_update', (event) => {
      setTickUpdate(JSON.parse(event.data));
    });

    eventSource.onerror = () => {
      setStatus('error');
    };

    return () => eventSource.close();
  }, [sessionId]);

  // Stop simulation
  const stopSimulation = async () => {
    if (!sessionId) return;
    await fetch(`/api/v2/live/stop/${sessionId}`, { method: 'POST' });
    setStatus('stopped');
  };

  return (
    <div>
      <button onClick={startSimulation} disabled={status === 'running'}>
        Start Simulation
      </button>
      <button onClick={stopSimulation} disabled={status !== 'running'}>
        Stop Simulation
      </button>

      {tickUpdate && (
        <div>
          <h3>Progress: {tickUpdate.progress?.progress_percentage?.toFixed(2)}%</h3>
          <h3>P&L: {tickUpdate.pnl_summary?.total_pnl}</h3>
          
          <h4>Active Nodes:</h4>
          {tickUpdate.active_nodes.map(node => (
            <div key={node.node_id}>{node.node_name} - {node.status}</div>
          ))}

          <h4>Open Positions:</h4>
          {tickUpdate.open_positions.map(pos => (
            <div key={pos.position_id}>
              {pos.symbol}: {pos.unrealized_pnl}
            </div>
          ))}

          {tickUpdate.completed_nodes_this_tick.length > 0 && (
            <div>
              <h4>Just Completed:</h4>
              {tickUpdate.completed_nodes_this_tick.map(node => (
                <div key={node.execution_id}>
                  {node.node_name} - {node.result}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {trades && (
        <div>
          <h3>Trades: {trades.summary.total_trades}</h3>
          <h3>Win Rate: {trades.summary.win_rate}%</h3>
        </div>
      )}
    </div>
  );
}
```

---

## Data Decompression

### JavaScript (pako library)

```javascript
import pako from 'pako';

function decompressGzip(base64Data) {
  // Step 1: Decode base64 to binary
  const binaryString = atob(base64Data);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // Step 2: Decompress gzip
  const decompressed = pako.ungzip(bytes, { to: 'string' });
  
  // Step 3: Parse JSON
  return JSON.parse(decompressed);
}
```

### Python

```python
import gzip
import base64
import json

def decompress_gzip(base64_data: str) -> dict:
    # Decode base64
    compressed = base64.b64decode(base64_data)
    
    # Decompress gzip
    decompressed = gzip.decompress(compressed)
    
    # Parse JSON
    return json.loads(decompressed.decode('utf-8'))
```

---

## Error Handling

### Connection Errors

```javascript
eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  
  // Auto-reconnect
  setTimeout(() => {
    eventSource = new EventSource(streamUrl);
  }, 5000);
};
```

### Decompression Errors

```javascript
try {
  const data = decompressGzip(compressedData);
} catch (error) {
  console.error('Failed to decompress data:', error);
  // Request full state refresh
  await fetch(`/api/v2/live/status/${sessionId}`);
}
```

### Session Not Found

```javascript
const response = await fetch(`/api/v2/live/stream/${sessionId}`);
if (response.status === 404) {
  console.error('Session not found - may have expired');
  // Restart simulation
}
```

---

## Best Practices

### 1. State Management

- Keep **three separate state objects**: `diagnostics`, `trades`, `tickUpdate`
- Replace entire `diagnostics` on `node_events` (don't merge)
- Replace entire `trades` on `trade_update` (don't merge)
- Update `tickUpdate` on every `tick_update`

### 2. Performance Optimization

- Use `tick_update` for real-time UI (lightweight, uncompressed)
- Use `node_events` for detailed diagnostics panel (heavy, compressed)
- Use `trade_update` for trades list (medium, compressed)
- Throttle UI updates if `speed_multiplier > 1`

### 3. UI Updates

**Lightweight (every tick):**
- Progress bar
- Current P&L
- Active node indicators
- Open positions list

**Heavy (on event):**
- Full diagnostics tree
- Complete trades history
- Node execution details

### 4. Memory Management

- Clear old `completed_nodes_this_tick` after displaying
- Limit diagnostics `events_history` display to recent N events
- Paginate trades list

### 5. Reconnection Strategy

```javascript
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

eventSource.onerror = () => {
  if (reconnectAttempts < maxReconnectAttempts) {
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
    setTimeout(() => {
      reconnectAttempts++;
      // Reconnect
    }, delay);
  } else {
    // Show error to user
  }
};
```

---

## Testing

### Manual Testing with curl

```bash
# 1. Start simulation
curl -X POST http://localhost:8000/api/v2/live/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "speed_multiplier": 1.0
  }'

# Response: {"session_id": "sim-abc123", ...}

# 2. Connect to stream
curl -N http://localhost:8000/api/v2/live/stream/sim-abc123

# 3. Stop simulation
curl -X POST http://localhost:8000/api/v2/live/stop/sim-abc123
```

### Browser Testing

```javascript
// Open browser console
const es = new EventSource('/api/v2/live/stream/sim-abc123');
es.addEventListener('tick_update', e => console.log(JSON.parse(e.data)));
es.addEventListener('node_events', e => console.log('Node event:', e.data.length, 'bytes'));
```

---

## Support

For issues or questions:
1. Check API documentation: `http://localhost:8000/docs`
2. Verify session exists: `GET /api/v2/live/status/{session_id}`
3. Check server logs for errors
4. Verify gzip decompression with test data

---

## Summary

**Key Points:**
1. Use SSE EventSource for real-time streaming
2. Decompress `node_events` and `trade_update` with gzip
3. `tick_update` is uncompressed JSON
4. Match exact backtesting JSON structures
5. Keep numeric-looking P&L fields as strings
6. Handle reconnections gracefully
7. Use `completed_nodes_this_tick` for immediate feedback

**Event Flow:**
```
Connect → initial_state → [tick_update, node_events, trade_update, heartbeat]* → Disconnect
```

**UI Updates:**
- Every tick: Progress, P&L, node status
- On node completion: Full diagnostics
- On trade close: Full trades list
