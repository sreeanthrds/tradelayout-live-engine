# Live Simulation UI Integration Guide

## Overview
The Live Simulation feature provides real-time backtesting with per-second state updates via a polling-based REST API. The UI polls the backend every 1 second to retrieve the current state of the simulation.

---

## API Endpoints

### 1. Start Simulation
**POST** `/api/v1/simulation/start`

**Request Body:**
```json
{
  "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-29",
  "broker_connection_id": "clickhouse",
  "speed_multiplier": 4.0
}
```

**Parameters:**
- `user_id` (string, required): User identifier
- `strategy_id` (string, required): Strategy UUID to simulate
- `start_date` (string, required): Date to run simulation (format: YYYY-MM-DD)
- `broker_connection_id` (string, required): Broker data source (e.g., "clickhouse")
- `speed_multiplier` (float, optional): Simulation speed (default: 1.0)
  - `1.0` = real-time (1 simulated second = 1 real second)
  - `4.0` = 4x speed (1 simulated second = 0.25 real seconds)
  - `10.0` = 10x speed (1 simulated second = 0.1 real seconds)

**Response:**
```json
{
  "session_id": "c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c",
  "status": "starting",
  "message": "Live simulation session created and starting"
}
```

**Response Fields:**
- `session_id`: Unique identifier for this simulation session (use for polling and stopping)
- `status`: Current status ("starting", "running", "completed", "error", "stopped")
- `message`: Human-readable status message

---

### 2. Poll Simulation State
**GET** `/api/v1/simulation/{session_id}/state`

**Example:** `GET /api/v1/simulation/c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c/state`

**Response:**
```json
{
  "session_id": "c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c",
  "status": "running",
  "timestamp": "2024-10-29T09:15:23+05:30",
  "active_nodes": [
    {
      "node_id": "entry_signal_1",
      "node_type": "EntrySignalNode",
      "node_name": "Entry Signal",
      "status": "Active",
      "visited": false,
      "re_entry_num": 0,
      "conditions": [...],
      "diagnostic_data": {...},
      "condition_result": true
    },
    {
      "node_id": "reentry_signal_1",
      "node_type": "ReEntrySignalNode",
      "node_name": "Re-Entry Signal",
      "status": "Active",
      "visited": false,
      "re_entry_num": 2,
      "explicit_conditions": [...],
      "implicit_checks": {
        "has_open_position": false,
        "target_node_active": false,
        "max_entries_reached": false
      },
      "condition_result": false
    }
  ],
  "latest_candles": {
    "NIFTY-I": {
      "1min": {
        "current": {
          "time": "2024-10-29T09:15:00+05:30",
          "open": 24580.5,
          "high": 24585.0,
          "low": 24578.0,
          "close": 24582.5,
          "volume": 15000
        },
        "previous": {
          "time": "2024-10-29T09:14:00+05:30",
          "open": 24575.0,
          "high": 24581.0,
          "low": 24574.5,
          "close": 24580.5,
          "volume": 14500
        }
      }
    }
  },
  "ltp_store": {
    "NIFTY-I": 24582.5,
    "BANKNIFTY-I": 52345.75
  },
  "open_positions": [
    {
      "position_id": "entry_1_P1",
      "symbol": "NIFTY-I",
      "quantity": 50,
      "side": "BUY",
      "entry_price": 24550.0,
      "current_price": 24582.5,
      "unrealized_pnl": 1625.0,
      "entry_time": "2024-10-29T09:10:15+05:30"
    }
  ],
  "total_unrealized_pnl": 1625.0,
  "stats": {
    "progress_percentage": 45.5,
    "elapsed_seconds": 10285,
    "total_seconds": 22351,
    "estimated_remaining_seconds": 12066
  }
}
```

**Response Fields:**

#### Top Level
- `session_id`: Simulation session identifier
- `status`: Current status ("running", "completed", "error", "stopped")
- `timestamp`: Current simulation timestamp (ISO format)
- `stats`: Progress and timing statistics

#### active_nodes (Array)
List of nodes currently in Active or Pending status. Each node contains:
- `node_id`: Unique node identifier
- `node_type`: Type of node (EntrySignalNode, ReEntrySignalNode, EntryNode, ExitNode, etc.)
- `node_name`: Human-readable node name
- `status`: "Active" or "Pending"
- `visited`: Whether node was visited this tick
- `re_entry_num`: Re-entry count for this node
- `conditions`: (EntrySignalNode) Array of explicit condition definitions
- `explicit_conditions`: (ReEntrySignalNode) Array of user-configured conditions
- `implicit_checks`: (ReEntrySignalNode) Object containing implicit condition states
- `diagnostic_data`: Detailed condition evaluation data (if available)
- `condition_result`: Boolean result of condition evaluation
- `order_status`: Order execution status (for action nodes)

#### latest_candles (Object)
Nested object containing the current and previous candle for each symbol/timeframe:
- Format: `{symbol: {timeframe: {current: {...}, previous: {...}}}}`
- Only includes last 2 candles to minimize payload size

#### ltp_store (Object)
Current Last Traded Price for each symbol:
- Format: `{symbol: price}`

#### open_positions (Array)
List of currently open positions with unrealized PNL:
- `position_id`: Position identifier
- `symbol`: Trading symbol
- `quantity`: Position size
- `side`: "BUY" or "SELL"
- `entry_price`: Entry price
- `current_price`: Current market price (from LTP)
- `unrealized_pnl`: Unrealized profit/loss
- `entry_time`: Position entry timestamp

#### stats (Object)
Progress and timing information:
- `progress_percentage`: Simulation completion percentage (0-100)
- `elapsed_seconds`: Simulated seconds elapsed
- `total_seconds`: Total simulated seconds in the trading day
- `estimated_remaining_seconds`: Estimated remaining simulated seconds

---

### 3. Stop Simulation
**POST** `/api/v1/simulation/{session_id}/stop`

**Example:** `POST /api/v1/simulation/c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c/stop`

**Response:**
```json
{
  "session_id": "c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c",
  "status": "stopped",
  "message": "Simulation stopped successfully"
}
```

---

### 4. List Active Sessions
**GET** `/api/v1/simulation/sessions`

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "c5e8f7a3-4b2d-4c9e-8a7f-3d2e1f0a9b8c",
      "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
      "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
      "status": "running",
      "backtest_date": "2024-10-29",
      "speed_multiplier": 4.0,
      "started_at": "2025-12-06T20:18:17.123456"
    }
  ]
}
```

---

## UI Implementation Flow

### 1. Start Simulation
```javascript
async function startSimulation() {
  const response = await fetch('http://localhost:8000/api/v1/simulation/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc',
      strategy_id: '5708424d-5962-4629-978c-05b3a174e104',
      backtest_date: '2024-10-29',
      broker_connection_id: 'clickhouse',
      speed_multiplier: 4.0
    })
  });
  
  const data = await response.json();
  return data.session_id; // Store this for polling
}
```

### 2. Poll for Updates (Every 1 Second)
```javascript
async function pollSimulationState(sessionId) {
  const response = await fetch(
    `http://localhost:8000/api/v1/simulation/${sessionId}/state`
  );
  
  const state = await response.json();
  
  // Update UI with new state
  updateActiveNodes(state.active_nodes);
  updatePositions(state.open_positions, state.total_unrealized_pnl);
  updateCandles(state.latest_candles);
  updateProgress(state.stats);
  
  // Check if simulation is complete
  if (state.status === 'completed' || state.status === 'error') {
    stopPolling();
    handleSimulationComplete(state);
  }
  
  return state;
}

// Set up polling interval
const sessionId = await startSimulation();
const pollInterval = setInterval(() => {
  pollSimulationState(sessionId);
}, 1000); // Poll every 1 second

function stopPolling() {
  clearInterval(pollInterval);
}
```

### 3. Stop Simulation (Manual)
```javascript
async function stopSimulation(sessionId) {
  await fetch(`http://localhost:8000/api/v1/simulation/${sessionId}/stop`, {
    method: 'POST'
  });
  stopPolling();
}
```

---

## Key Implementation Notes

### Polling Frequency
- **Recommended: 1 second** (matches simulation update rate)
- At 4x speed, you'll see state changes approximately every 0.25 seconds
- Faster polling (e.g., 0.1s) provides smoother updates but increases server load

### Speed Multiplier
- `1.0x`: Real-time (6 hours trading day = 6 hours simulation time)
- `4.0x`: **Recommended** for UI (6 hours = ~1.5 hours simulation time)
- `10.0x`: Fast mode (6 hours = ~36 minutes simulation time)
- Higher speeds may make UI updates harder to follow

### Payload Size Optimization
The API response is optimized to minimize bandwidth:
- Only **active/pending nodes** are included (inactive nodes omitted)
- Only **last 2 candles** per timeframe (not full 20-candle history)
- Only **open positions** with unrealized PNL (closed positions omitted during simulation)

### Auto-Stop Conditions
The simulation automatically stops when:
1. All nodes are inactive
2. No open positions remain
3. Simulation date range is complete
4. An error occurs

### Error Handling
```javascript
async function pollSimulationState(sessionId) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/v1/simulation/${sessionId}/state`
    );
    
    if (!response.ok) {
      console.error('Polling failed:', response.status);
      return null;
    }
    
    const state = await response.json();
    
    if (state.status === 'error') {
      console.error('Simulation error:', state.error);
      stopPolling();
      return state;
    }
    
    return state;
  } catch (error) {
    console.error('Network error:', error);
    // Continue polling or stop based on error type
  }
}
```

---

## Example: React Implementation

```jsx
import { useState, useEffect } from 'react';

function LiveSimulation() {
  const [sessionId, setSessionId] = useState(null);
  const [state, setState] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // Start simulation
  const startSimulation = async () => {
    const response = await fetch('http://localhost:8000/api/v1/simulation/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc',
        strategy_id: '5708424d-5962-4629-978c-05b3a174e104',
        backtest_date: '2024-10-29',
        broker_connection_id: 'clickhouse',
        speed_multiplier: 4.0
      })
    });
    
    const data = await response.json();
    setSessionId(data.session_id);
    setIsRunning(true);
  };

  // Polling effect
  useEffect(() => {
    if (!sessionId || !isRunning) return;

    const pollInterval = setInterval(async () => {
      const response = await fetch(
        `http://localhost:8000/api/v1/simulation/${sessionId}/state`
      );
      const newState = await response.json();
      setState(newState);

      // Auto-stop on completion
      if (['completed', 'error', 'stopped'].includes(newState.status)) {
        setIsRunning(false);
        clearInterval(pollInterval);
      }
    }, 1000);

    return () => clearInterval(pollInterval);
  }, [sessionId, isRunning]);

  // Stop simulation
  const stopSimulation = async () => {
    if (!sessionId) return;
    
    await fetch(`http://localhost:8000/api/v1/simulation/${sessionId}/stop`, {
      method: 'POST'
    });
    setIsRunning(false);
  };

  return (
    <div>
      <button onClick={startSimulation} disabled={isRunning}>
        Start Simulation
      </button>
      <button onClick={stopSimulation} disabled={!isRunning}>
        Stop Simulation
      </button>

      {state && (
        <div>
          <h3>Status: {state.status}</h3>
          <p>Time: {state.timestamp}</p>
          <p>Progress: {state.stats?.progress_percentage?.toFixed(1)}%</p>
          <p>Active Nodes: {state.active_nodes?.length || 0}</p>
          <p>Open Positions: {state.open_positions?.length || 0}</p>
          <p>Unrealized PNL: ₹{state.total_unrealized_pnl?.toFixed(2) || 0}</p>
        </div>
      )}
    </div>
  );
}
```

---

## Testing
A test client is available at `test_live_simulation_fast.py` that demonstrates:
- Starting a simulation
- Polling every 0.1 seconds (10x per second)
- Saving all snapshots to a JSON file
- Handling completion/errors

Run it with:
```bash
python test_live_simulation_fast.py
```

---

## Performance Considerations

### Server Load
- Each active session consumes 1 background thread
- Memory usage: ~50-100 MB per session (depending on strategy complexity)
- CPU usage: Varies with speed multiplier (10x uses ~10% of 1 core)

### Recommended Limits
- **Max concurrent sessions**: 10-20 (depending on server resources)
- **Polling frequency**: 1 second (avoid sub-100ms polling)
- **Speed multiplier**: 1x-10x (higher speeds may overwhelm UI updates)

### Cleanup
- Sessions are automatically cleaned up when stopped or completed
- Orphaned sessions persist in memory until server restart
- Use `/api/v1/simulation/sessions` endpoint to monitor active sessions

---

## Next Steps
1. Build UI components for:
   - Simulation controls (Start/Stop/Speed)
   - Node state visualization
   - Position tracking with PNL
   - Candle charts
   - Progress timeline
2. Implement WebSocket (optional future enhancement for push-based updates)
3. Add historical session playback (replay saved snapshots)
