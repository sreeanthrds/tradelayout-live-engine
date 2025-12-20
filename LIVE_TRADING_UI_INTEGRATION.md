# Live Trading UI Integration Guide

## 🎯 Overview

This guide provides complete instructions for integrating the Live Trading Dashboard with the backend API. The system uses a **hybrid model** combining HTTP endpoints (for initial load) and Server-Sent Events (for real-time updates).

---

## 📐 Architecture

### Data Flow Model

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIAL LOAD (HTTP GET - Pull)                          │
│                                                             │
│ User opens dashboard                                        │
│     ↓                                                       │
│ GET /api/live-trading/dashboard/{user_id}                  │
│     ↓                                                       │
│ Server returns current state of all user's strategies      │
│     ↓                                                       │
│ UI displays strategy cards with current positions/P&L      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 2. LIVE UPDATES (SSE - Push)                                │
│                                                             │
│ EventSource('/api/live-trading/stream/{user_id}')          │
│     ↓                                                       │
│ Server PUSHES events when data changes:                    │
│   • node_events - Node execution completed                 │
│   • trade_update - Position closed (trade completed)       │
│   • tick_update - Per-tick P&L/position updates            │
│   • heartbeat - Keep-alive every 30s if idle               │
│     ↓                                                       │
│ UI updates dashboard in real-time                          │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

✅ **One SSE per User** - Single connection receives events for ALL user's strategies  
✅ **Push Only on Change** - No duplicate/static data sent  
✅ **Per-Tick Updates** - Real-time P&L, positions, LTP, candles  
✅ **Multi-Strategy Support** - Each event tagged with `session_id`  
✅ **Existing Backtesting Format** - Uses same event structure (node_events, trade_update, tick_update)

---

## 🔌 API Endpoints

### 1. Start Strategy (POST)

**Endpoint:** `POST /api/v2/live/start`

**Purpose:** Start a new live trading session

**Request:**
```json
{
  "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
  "strategy_id": "64c2c932-0e0b-462a-9a36-7cda4371d102",
  "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4",
  "speed_multiplier": 1.0
}
```

**Response:**
```json
{
  "session_id": "sim-abc123def456",
  "stream_url": "/api/v2/live/stream/sim-abc123def456",
  "status": "running"
}
```

**Usage:**
```typescript
const response = await fetch('/api/v2/live/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: currentUserId,
    strategy_id: selectedStrategyId,
    broker_connection_id: selectedBrokerId,
    speed_multiplier: 1.0
  })
});

const { session_id } = await response.json();
// Now connect to SSE stream for this user
```

---

### 2. Dashboard - All Sessions (GET)

**Endpoint:** `GET /api/live-trading/dashboard/{user_id}`

**Purpose:** Get current state of all user's strategies (initial load, reconnection, fallback)

**Response:**
```json
{
  "total_sessions": 3,
  "active_sessions": 2,
  "cache_time": "2025-12-14T05:30:00Z",
  "sessions": {
    "sim-abc123": {
      "session_id": "sim-abc123",
      "strategy_name": "NIFTY Straddle",
      "broker_info": {
        "broker_type": "angel-one",
        "account_id": "K492935"
      },
      "status": "running",
      "data": {
        "timestamp": "2025-12-14T05:30:15Z",
        "is_fresh": true,
        "gps_data": {
          "positions": [
            {
              "symbol": "NIFTY28DEC2525000CE",
              "qty": 50,
              "entry_price": 150.00,
              "current_price": 175.00,
              "unrealized_pnl": 1250.00
            }
          ],
          "trades": [],
          "pnl": {
            "realized_pnl": "5000.00",
            "unrealized_pnl": "1250.00",
            "total_pnl": "6250.00",
            "closed_trades": 2,
            "open_trades": 1
          }
        },
        "broker_data": {
          "orders": [],
          "account_info": {
            "available_margin": 50000.00,
            "used_margin": 25000.00,
            "total_value": 75000.00
          }
        },
        "market_data": {
          "ltp_store": {
            "NIFTY": 25100.00,
            "NIFTY28DEC2525000CE": 175.00
          },
          "candle_data": {
            "NIFTY": {
              "timestamp": "2025-12-14T05:30:00Z",
              "open": 25000.00,
              "high": 25150.00,
              "low": 24950.00,
              "close": 25100.00,
              "volume": 1000000
            }
          }
        }
      }
    },
    "sim-def456": {
      "session_id": "sim-def456",
      "strategy_name": "BANKNIFTY Iron Condor",
      "status": "running",
      "data": { /* ... similar structure ... */ }
    }
  }
}
```

**Usage:**
```typescript
// Initial page load
const dashboard = await fetch(`/api/live-trading/dashboard/${userId}`);
const data = await dashboard.json();

// Display all strategy cards
Object.values(data.sessions).forEach(session => {
  renderStrategyCard(session);
});
```

---

### 3. Single Session (GET)

**Endpoint:** `GET /api/live-trading/session/{session_id}`

**Purpose:** Get current state of ONE specific strategy (direct URL, single card refresh)

**Response:** Same structure as single session in dashboard response

**Usage:**
```typescript
// Refresh single card without fetching all sessions
const session = await fetch(`/api/live-trading/session/${sessionId}`);
const data = await session.json();
updateStrategyCard(sessionId, data);
```

---

### 4. User SSE Stream (GET - EventSource)

**Endpoint:** `GET /api/live-trading/stream/{user_id}`

**Purpose:** Real-time event stream for ALL user's strategies

**Event Types:**

#### Event 1: `initial_state`
Sent once per session when SSE connects.

```json
{
  "event": "initial_state",
  "data": {
    "session_id": "sim-abc123",
    "strategy_id": "64c2c932-0e0b-462a-9a36-7cda4371d102",
    "diagnostics": "H4sIAAAAAAAA...",  // gzip + base64 compressed
    "trades": "H4sIAAAAAAAA..."         // gzip + base64 compressed
  }
}
```

#### Event 2: `node_events`
Sent when node completes execution (entry placed, exit triggered, etc.)

```json
{
  "event": "node_events",
  "data": {
    "session_id": "sim-abc123",
    "diagnostics": "H4sIAAAAAAAA..."  // gzip + base64 compressed diagnostics_export
  }
}
```

**Decompressed Structure:**
```json
{
  "events_history": {
    "exec-001": {
      "node_id": "entry-condition-1",
      "node_type": "EntryNode",
      "timestamp": "2025-12-14T05:30:00Z",
      "event_type": "logic_completed",
      "evaluation_data": { /* node-specific data */ }
    }
  },
  "current_state": {
    "entry-condition-1": {
      "status": "active",
      "last_execution": "2025-12-14T05:30:00Z"
    }
  }
}
```

#### Event 3: `trade_update`
Sent when position closes (trade completed).

```json
{
  "event": "trade_update",
  "data": {
    "session_id": "sim-abc123",
    "trades": "H4sIAAAAAAAA..."  // gzip + base64 compressed trades_daily
  }
}
```

**Decompressed Structure:**
```json
{
  "date": "2025-12-14",
  "summary": {
    "total_trades": 5,
    "total_pnl": "12500.00",
    "winning_trades": 3,
    "losing_trades": 2,
    "win_rate": "60.00"
  },
  "trades": [
    {
      "trade_id": "trade-001",
      "symbol": "NIFTY28DEC2525000CE",
      "entry_time": "2025-12-14T05:00:00Z",
      "exit_time": "2025-12-14T05:30:00Z",
      "entry_price": 150.00,
      "exit_price": 175.00,
      "quantity": 50,
      "pnl": "1250.00",
      "pnl_percentage": "16.67"
    }
  ]
}
```

#### Event 4: `tick_update`
Sent EVERY TICK (~1 second) when positions/P&L changes.

```json
{
  "event": "tick_update",
  "data": {
    "session_id": "sim-abc123",
    "tick_state": {
      "timestamp": "2025-12-14T05:30:15Z",
      "current_time": "2025-12-14T05:30:15+05:30",
      "progress": {
        "ticks_processed": 1543,
        "total_ticks": 23400,
        "progress_percentage": 6.59
      },
      "active_nodes": ["entry-condition-1"],
      "pending_nodes": [],
      "completed_nodes_this_tick": [],
      "open_positions": [
        {
          "position_id": "pos-001",
          "symbol": "NIFTY28DEC2525000CE",
          "exchange": "NFO",
          "quantity": 50,
          "entry_price": 150.00,
          "current_price": 175.00,
          "unrealized_pnl": 1250.00,
          "entry_time": "2025-12-14T05:00:00Z"
        }
      ],
      "pnl_summary": {
        "realized_pnl": "5000.00",
        "unrealized_pnl": "1250.00",
        "total_pnl": "6250.00",
        "closed_trades": 2,
        "open_trades": 1,
        "winning_trades": 2,
        "losing_trades": 0,
        "win_rate": "100.00"
      },
      "ltp_store": {
        "NIFTY": 25100.00,
        "NIFTY28DEC2525000CE": 175.00,
        "NIFTY28DEC2525000PE": 120.00
      },
      "candle_data": {
        "NIFTY": {
          "timestamp": "2025-12-14T05:30:00Z",
          "open": 25000.00,
          "high": 25150.00,
          "low": 24950.00,
          "close": 25100.00,
          "volume": 1000000
        }
      }
    }
  }
}
```

#### Event 5: `heartbeat`
Sent every 30 seconds if no other events (keeps connection alive).

```json
{
  "event": "heartbeat",
  "data": {
    "timestamp": "2025-12-14T05:30:45Z"
  }
}
```

---

### 5. Control Endpoints - Stop Sessions

#### 5A. Stop Individual Session (POST)

**Endpoint:** `POST /api/v2/live/stop/{session_id}`

**Purpose:** Stop a single running strategy session

**Use Cases:**
- User clicks "Stop" button on strategy card
- Strategy completes naturally
- Error recovery for single strategy

**Response:**
```json
{
  "session_id": "sim-abc123def456",
  "status": "stopped",
  "message": "Session stopped successfully"
}
```

**Usage:**
```typescript
async function stopStrategy(sessionId: string) {
  const response = await fetch(`/api/v2/live/stop/${sessionId}`, {
    method: 'POST'
  });
  const result = await response.json();
  
  if (result.status === 'stopped') {
    // Remove card from UI or mark as stopped
    updateCardStatus(sessionId, 'stopped');
  }
}
```

---

#### 5B. Stop All User Sessions (POST)

**Endpoint:** `POST /api/v2/live/stop/user/{user_id}`

**Purpose:** Stop ALL sessions for a specific user

**Use Cases:**
- User logs out
- User clicks "Stop All Strategies"
- User account suspension
- Emergency stop for user

**Response:**
```json
{
  "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
  "sessions_stopped": 3,
  "stopped_sessions": [
    "sim-abc123",
    "sim-def456",
    "sim-ghi789"
  ],
  "message": "Stopped 3 session(s) for user user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
}
```

**Usage:**
```typescript
async function stopAllUserStrategies(userId: string) {
  const response = await fetch(`/api/v2/live/stop/user/${userId}`, {
    method: 'POST'
  });
  const result = await response.json();
  
  console.log(`Stopped ${result.sessions_stopped} strategies`);
  
  // Clear all cards from UI
  result.stopped_sessions.forEach(sessionId => {
    removeCard(sessionId);
  });
}

// Call on logout
function handleLogout() {
  await stopAllUserStrategies(currentUserId);
  // Disconnect SSE
  eventSource.close();
  // Redirect to login
}
```

---

#### 5C. Stop All Sessions - System Wide (POST)

**Endpoint:** `POST /api/v2/live/stop/all`

**Purpose:** Stop ALL active sessions for ALL users

⚠️ **WARNING:** This is a system-wide operation affecting all users!

**Use Cases:**
- Server shutdown/maintenance
- Emergency system stop
- System-level cleanup
- Admin operations only

**Response:**
```json
{
  "sessions_stopped": 15,
  "stopped_sessions": [
    {
      "session_id": "sim-abc123",
      "user_id": "user_001",
      "strategy_id": "strat-001"
    },
    {
      "session_id": "sim-def456",
      "user_id": "user_002",
      "strategy_id": "strat-002"
    }
    // ... more sessions
  ],
  "message": "Stopped all 15 active session(s)"
}
```

**Usage:**
```typescript
// Admin only - requires authentication
async function emergencyStopAll() {
  const confirmed = confirm(
    'WARNING: This will stop ALL active strategies for ALL users. Continue?'
  );
  
  if (!confirmed) return;
  
  const response = await fetch('/api/v2/live/stop/all', {
    method: 'POST',
    headers: { 
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  const result = await response.json();
  console.log(`Emergency stop: ${result.sessions_stopped} sessions stopped`);
  
  // Notify all users
  broadcastSystemMessage('All strategies stopped for maintenance');
}
```

---

## 💻 Frontend Implementation

### 1. Initial Page Load

```typescript
async function loadDashboard(userId: string) {
  // Step 1: Get current state via HTTP
  const response = await fetch(`/api/live-trading/dashboard/${userId}`);
  const dashboard = await response.json();
  
  // Step 2: Render all strategy cards
  renderStrategyCards(dashboard.sessions);
  
  // Step 3: Connect to SSE for live updates
  connectToSSE(userId);
}
```

### 2. SSE Connection

```typescript
function connectToSSE(userId: string) {
  const eventSource = new EventSource(`/api/live-trading/stream/${userId}`);
  
  // Handle initial state (sent once per session on connect)
  eventSource.addEventListener('initial_state', (event) => {
    const data = JSON.parse(event.data);
    const sessionId = data.session_id;
    
    // Decompress diagnostics and trades if needed
    const diagnostics = decompressGzip(data.diagnostics);
    const trades = decompressGzip(data.trades);
    
    console.log(`Initial state received for ${sessionId}`);
  });
  
  // Handle node events (position opened, exit triggered, etc.)
  eventSource.addEventListener('node_events', (event) => {
    const data = JSON.parse(event.data);
    const sessionId = data.session_id;
    const diagnostics = decompressGzip(data.diagnostics);
    
    // Update UI with node execution status
    updateNodeStatus(sessionId, diagnostics);
  });
  
  // Handle trade updates (position closed)
  eventSource.addEventListener('trade_update', (event) => {
    const data = JSON.parse(event.data);
    const sessionId = data.session_id;
    const trades = decompressGzip(data.trades);
    
    // Update UI with completed trades
    updateTrades(sessionId, trades);
  });
  
  // Handle tick updates (P&L, positions, LTP)
  eventSource.addEventListener('tick_update', (event) => {
    const data = JSON.parse(event.data);
    const sessionId = data.session_id;
    const tickState = data.tick_state;
    
    // Update strategy card with live data
    updateStrategyCard(sessionId, {
      positions: tickState.open_positions,
      pnl: tickState.pnl_summary,
      ltp: tickState.ltp_store,
      candles: tickState.candle_data,
      progress: tickState.progress
    });
  });
  
  // Handle heartbeat (keep-alive)
  eventSource.addEventListener('heartbeat', (event) => {
    console.log('Heartbeat received:', event.data);
  });
  
  // Handle errors
  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
    
    // Reconnect after 5 seconds
    setTimeout(() => {
      connectToSSE(userId);
    }, 5000);
  };
  
  return eventSource;
}
```

### 3. Gzip Decompression Utility

```typescript
import pako from 'pako';

function decompressGzip(base64String: string): any {
  try {
    // Decode base64
    const binaryString = atob(base64String);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Decompress gzip
    const decompressed = pako.inflate(bytes, { to: 'string' });
    
    // Parse JSON
    return JSON.parse(decompressed);
  } catch (error) {
    console.error('Decompression error:', error);
    return null;
  }
}
```

### 4. Strategy Card Update

```typescript
function updateStrategyCard(sessionId: string, data: any) {
  const card = document.querySelector(`[data-session-id="${sessionId}"]`);
  if (!card) return;
  
  // Update P&L
  card.querySelector('.total-pnl').textContent = 
    formatCurrency(data.pnl.total_pnl);
  
  card.querySelector('.realized-pnl').textContent = 
    formatCurrency(data.pnl.realized_pnl);
  
  card.querySelector('.unrealized-pnl').textContent = 
    formatCurrency(data.pnl.unrealized_pnl);
  
  // Update positions count
  card.querySelector('.open-positions').textContent = 
    data.positions.length;
  
  // Update progress bar (if applicable)
  if (data.progress) {
    card.querySelector('.progress-bar').style.width = 
      `${data.progress.progress_percentage}%`;
  }
  
  // Update position details
  const positionsList = card.querySelector('.positions-list');
  positionsList.innerHTML = data.positions.map(pos => `
    <div class="position">
      <span class="symbol">${pos.symbol}</span>
      <span class="qty">${pos.quantity}</span>
      <span class="pnl ${pos.unrealized_pnl >= 0 ? 'positive' : 'negative'}">
        ${formatCurrency(pos.unrealized_pnl)}
      </span>
    </div>
  `).join('');
}
```

---

## 🔄 Complete User Flow

### Scenario: User Opens Dashboard with 2 Running Strategies

```
Step 1: Page Load
  ↓
GET /api/live-trading/dashboard/user_123
  ↓
Response: 2 sessions (sim-abc123, sim-def456)
  ↓
Render 2 strategy cards with current P&L/positions

Step 2: Connect SSE
  ↓
EventSource('/api/live-trading/stream/user_123')
  ↓
Event: initial_state (sim-abc123)
Event: initial_state (sim-def456)

Step 3: Live Updates (Every ~1 second)
  ↓
Event: tick_update (sim-abc123)
  └─> Update card: P&L changed, position LTP updated
  
Event: tick_update (sim-def456)
  └─> Update card: P&L changed, new candle data

Step 4: Position Opens (Event-Driven)
  ↓
Event: node_events (sim-abc123)
  └─> Show notification: "Entry placed - NIFTY CE"

Step 5: Position Closes (Event-Driven)
  ↓
Event: trade_update (sim-def456)
  └─> Show notification: "Trade closed - P&L: +₹1250"
  └─> Update closed trades count

Step 6: Idle (No Changes for 30s)
  ↓
Event: heartbeat
  └─> Connection alive, no UI update needed
```

---

## 📊 Data Payload Sizes

| Event Type | Frequency | Payload Size | Compressed |
|------------|-----------|--------------|------------|
| `initial_state` | Once on connect | ~50-100 KB | ~5-10 KB (gzip) |
| `node_events` | On node completion | ~10-30 KB | ~2-5 KB (gzip) |
| `trade_update` | On position close | ~5-15 KB | ~1-3 KB (gzip) |
| `tick_update` | Every tick (~1s) | ~2-5 KB | Uncompressed |
| `heartbeat` | Every 30s if idle | ~50 bytes | Uncompressed |

**Bandwidth Estimate:**
- Active trading: ~3-5 KB/sec (tick updates)
- Idle: ~50 bytes/30sec (heartbeat only)

---

## ✅ Implementation Checklist

### Backend (Completed)
- [x] Add `user_id` to `LiveSimulationState`
- [x] Update `create_session()` to accept `user_id`
- [x] Update `/api/v2/live/start` to pass `user_id`
- [x] Create `/api/live-trading/stream/{user_id}` (user-level SSE)
- [x] Update `/api/live-trading/dashboard/{user_id}` (read from `sse_manager`)
- [x] Update `/api/live-trading/session/{session_id}` (read from `sse_manager`)
- [x] Include `ltp_store` and `candle_data` in `tick_update`

### Frontend (To Implement)
- [ ] Initial dashboard load using `/api/live-trading/dashboard/{user_id}`
- [ ] SSE connection to `/api/live-trading/stream/{user_id}`
- [ ] Event handlers for all event types
- [ ] Gzip decompression for `initial_state`, `node_events`, `trade_update`
- [ ] Real-time card updates on `tick_update`
- [ ] Reconnection logic on SSE disconnect
- [ ] Error handling and notifications

---

## 🚀 Server Status

**Backend Server:** `http://localhost:8000`  
**API Docs:** `http://localhost:8000/docs`  
**Status:** ✅ RUNNING

All endpoints are live and ready for frontend integration!
