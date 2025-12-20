# Trading Strategy API Endpoints

## Overview
This document defines the API endpoints for accessing backtesting results and live trading data.

## **All Endpoints Summary**

| # | Method | Endpoint | Parameters | Purpose |
|---|--------|----------|------------|---------|
| **Backtesting** |
| 1 | POST | `/api/backtest/run` | user_id, session_id, from_date, to_date | Run a backtest for a date range |
| 2 | GET | `/api/backtest/status/{job_id}` | job_id | Check backtest run status |
| 3 | GET | `/api/backtest/sessions` | user_id, session_id | Get all backtest sessions |
| 4 | GET | `/api/backtest/session-detail` | user_id, session_id, date | Get single day detail |
| 5 | GET | `/api/backtest/diagnostics` | user_id, session_id, date | Get node diagnostics (gzipped) |
| **Live Trading** |
| 6 | GET | `/api/live/node-state` | user_id, session_id | Get current node state (poll 1s) |
| 7 | GET | `/api/live/session-summary` | user_id, session_id | Get live session summary |
| 8 | GET | `/api/live/diagnostics` | user_id, session_id | Get live diagnostics (gzipped) |

---

## **Backtesting APIs**

### 1. Run Backtest
**Endpoint:** `POST /api/backtest/run`

**Request Body:**
```json
{
  "user_id": "user_123",
  "session_id": "5708424d-5962-4629-978c-05b3a174e104",
  "from_date": "2024-10-01",
  "to_date": "2024-10-31"
}
```

**Response:**
```json
{
  "job_id": "backtest_20251208_211530",
  "status": "running",
  "user_id": "user_123",
  "session_id": "5708424d-5962-4629-978c-05b3a174e104",
  "from_date": "2024-10-01",
  "to_date": "2024-10-31",
  "total_days": 31,
  "started_at": "2025-12-08T21:15:30+05:30",
  "estimated_completion": "2025-12-08T21:20:00+05:30"
}
```

**Use Case:** Trigger a backtest run for a strategy over a date range

**Note:** This is an async operation. Use the `job_id` to poll for status.

---

### 2. Check Backtest Status
**Endpoint:** `GET /api/backtest/status/{job_id}`

**Response (Running):**
```json
{
  "job_id": "backtest_20251208_211530",
  "status": "running",
  "progress": {
    "current_date": "2024-10-15",
    "completed_days": 15,
    "total_days": 31,
    "percent_complete": 48.4
  },
  "started_at": "2025-12-08T21:15:30+05:30",
  "estimated_completion": "2025-12-08T21:20:00+05:30"
}
```

**Response (Completed):**
```json
{
  "job_id": "backtest_20251208_211530",
  "status": "completed",
  "user_id": "user_123",
  "session_id": "5708424d-5962-4629-978c-05b3a174e104",
  "from_date": "2024-10-01",
  "to_date": "2024-10-31",
  "progress": {
    "completed_days": 31,
    "total_days": 31,
    "percent_complete": 100
  },
  "started_at": "2025-12-08T21:15:30+05:30",
  "completed_at": "2025-12-08T21:18:45+05:30",
  "duration_seconds": 195,
  "results_url": "/api/backtest/sessions?user_id=user_123&session_id=5708424d-5962-4629-978c-05b3a174e104&from=2024-10-01&to=2024-10-31"
}
```

**Response (Failed):**
```json
{
  "job_id": "backtest_20251208_211530",
  "status": "failed",
  "error": "Invalid date range",
  "error_details": {
    "message": "from_date must be before to_date",
    "from_date": "2024-10-31",
    "to_date": "2024-10-01"
  },
  "started_at": "2025-12-08T21:15:30+05:30",
  "failed_at": "2025-12-08T21:15:35+05:30"
}
```

**Use Case:** Poll for backtest completion status (poll every 2-3 seconds)

---

### 3. Get All Backtest Sessions
**Endpoint:** `GET /api/backtest/sessions`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID
- `from_date` (optional): Start date (ISO format: YYYY-MM-DD)
- `to_date` (optional): End date (ISO format: YYYY-MM-DD)

**Response:**
```json
{
  "user_id": "user_123",
  "session_id": "5708424d-5962-4629-978c-05b3a174e104",
  "from_date": "2024-10-01",
  "to_date": "2024-10-31",
  "sessions": [
    {
      "session_date": "2024-10-01",
      "total_pnl": 250.0,
      "total_positions": 5,
      "win_rate_percent": 60.0,
      "session_status": "completed"
    },
    {
      "session_date": "2024-10-02",
      "total_pnl": -120.0,
      "total_positions": 3,
      "win_rate_percent": 33.3,
      "session_status": "completed"
    }
  ],
  "aggregate": {
    "total_sessions": 31,
    "total_pnl": 1520.50,
    "total_positions": 125,
    "avg_win_rate": 55.2
  }
}
```

**Use Case:** Display all backtested days in a table/list view

---

### 4. Get Session Detail (Backtest)
**Endpoint:** `GET /api/backtest/session-detail`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID
- `date` (required): Session date (ISO format: YYYY-MM-DD)

**Response:**
```json
{
  "session_summary": {
    "metadata": {
      "session_date": "2024-10-29",
      "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
      "session_type": "backtest",
      "session_status": "completed",
      "last_updated": "2025-12-08T20:50:36.039486"
    },
    "summary": {
      "total_positions": 9,
      "closed_positions": 9,
      "open_positions": 0,
      "total_pnl": -834.45,
      "win_rate_percent": 0.0,
      "winning_trades": 0,
      "losing_trades": 9
    },
    "positions": [ ... ]
  },
  "diagnostics_url": "/api/backtest/diagnostics?user_id=user_123&session_id=5708424d-5962-4629-978c-05b3a174e104&date=2024-10-29"
}
```

**Use Case:** Display trade details when user clicks on a specific day

---

### 5. Get Session Diagnostics (Backtest)
**Endpoint:** `GET /api/backtest/diagnostics`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID
- `date` (required): Session date (ISO format: YYYY-MM-DD)

**Response:** (Gzipped JSON)
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
        "conditions_evaluated": [ ... ],
        "condition_substitution": "...",
        "condition_preview": "..."
      }
    ]
  },
  "current_state": { ... }
}
```

**Response Headers:**
- `Content-Type: application/json`
- `Content-Encoding: gzip`

**Use Case:** Display node timeline and diagnostic details (loaded on-demand)

---

## **Live Trading APIs**

### 6. Get Current Node State (Live Polling)
**Endpoint:** `GET /api/live/node-state`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID

**Polling Interval:** 1 second

**Response:**
```json
{
  "user_id": "user_123",
  "session_id": "5708424d-5962-4629-978c-05b3a174e104",
  "session_date": "2024-12-08",
  "last_updated": "2024-12-08T14:32:15+05:30",
  "node_current_state": {
    "entry-condition-1": {
      "timestamp": "2024-12-08 14:32:15+05:30",
      "status": "active",
      "node_id": "entry-condition-1",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "conditions_evaluated": [ ... ],
      "condition_substitution": "...",
      "condition_preview": "..."
    },
    "entry-2": {
      "timestamp": "2024-12-08 14:32:10+05:30",
      "status": "pending",
      "node_id": "entry-2",
      "pending_reason": "Waiting for order fill",
      "action": { ... }
    },
    "exit-3": {
      "timestamp": "2024-12-08 14:30:00+05:30",
      "status": "completed",
      "node_id": "exit-3",
      "exit_result": { ... }
    }
  }
}
```

**Use Case:** Real-time node status dashboard (poll every 1s)

---

### 7. Get Live Session Summary
**Endpoint:** `GET /api/live/session-summary`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID

**Polling Interval:** 5-10 seconds (or on-demand when user clicks "Positions" tab)

**Response:**
```json
{
  "session_summary": {
    "metadata": {
      "session_date": "2024-12-08",
      "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
      "session_type": "live",
      "session_status": "in_progress",
      "last_updated": "2024-12-08T14:32:15+05:30"
    },
    "summary": {
      "total_positions": 3,
      "closed_positions": 2,
      "open_positions": 1,
      "total_pnl": 125.50,
      "win_rate_percent": 50.0,
      "winning_trades": 1,
      "losing_trades": 1
    },
    "positions": [ ... ]
  },
  "diagnostics_url": "/api/live/diagnostics?user_id=user_123&session_id=X"
}
```

**Use Case:** Display live positions and P&L (poll every 5-10s or on-demand)

---

### 8. Get Live Session Diagnostics
**Endpoint:** `GET /api/live/diagnostics`

**Query Parameters:**
- `user_id` (required): User ID
- `session_id` (required): Session UUID

**Response:** (Gzipped JSON)
```json
{
  "events_history": { ... },
  "current_state": { ... }
}
```

**Use Case:** Display node timeline for current live session (loaded on-demand)

---

## **Error Responses**

All endpoints return standard error responses:

```json
{
  "error": "session_not_found",
  "message": "No session found for date 2024-10-29",
  "details": {
    "strategy_id": "...",
    "date": "2024-10-29"
  }
}
```

**HTTP Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Session/strategy not found
- `500 Internal Server Error` - Server error

---

## **Implementation Notes**

### File Storage Structure
```
data/
  backtesting_results/
    strategy_5708424d/
      SESSION_SUMMARY_2024-10-01.json
      diagnostics_2024-10-01.json.gz
      SESSION_SUMMARY_2024-10-02.json
      diagnostics_2024-10-02.json.gz
      ...
  
  live_trading/
    strategy_5708424d/
      SESSION_SUMMARY_2024-12-08.json     ← Continuously updated
      diagnostics_2024-12-08.json.gz      ← Continuously updated
```

### Caching Strategy
- **Backtest data**: Cache indefinitely (immutable)
- **Live data**: No caching (always fresh)
- **Diagnostics**: Cache client-side after first load

### Compression
- All `diagnostics_export.json` files should be gzipped
- Reduces size from ~58KB to ~8KB (85% reduction)
- Client must decompress before parsing

---

## **Client Implementation Example**

### Run Backtest Flow
```javascript
// 1. User clicks "Run Backtest" button
async function runBacktest(userId, sessionId, fromDate, toDate) {
  // Start backtest
  const response = await fetch('/api/backtest/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      session_id: sessionId,
      from_date: fromDate,
      to_date: toDate
    })
  });
  
  const { job_id } = await response.json();
  
  // Show progress modal
  showProgressModal(job_id);
  
  // Poll for status every 2 seconds
  const pollInterval = setInterval(async () => {
    const status = await fetch(`/api/backtest/status/${job_id}`);
    const data = await status.json();
    
    // Update progress bar
    updateProgress(data.progress.percent_complete);
    
    if (data.status === 'completed') {
      clearInterval(pollInterval);
      hideProgressModal();
      // Load results
      window.location.href = data.results_url;
    } else if (data.status === 'failed') {
      clearInterval(pollInterval);
      showError(data.error_details.message);
    }
  }, 2000);
}
```

### Backtest View
```javascript
// 1. Load all sessions (from existing backtest runs)
const sessions = await fetch(`/api/backtest/sessions?user_id=${userId}&session_id=${sessionId}&from=2024-10-01&to=2024-10-31`);

// 2. User clicks on a day
const detail = await fetch(`/api/backtest/session-detail?user_id=${userId}&session_id=${sessionId}&date=2024-10-29`);
showPositions(detail.session_summary.positions);

// 3. User clicks "View Timeline"
const diagnostics = await fetch(`/api/backtest/diagnostics?user_id=${userId}&session_id=${sessionId}&date=2024-10-29`)
  .then(res => res.arrayBuffer())
  .then(buf => pako.ungzip(buf, { to: 'string' }))
  .then(str => JSON.parse(str));
showNodeTimeline(diagnostics.events_history);
```

### Live View
```javascript
// 1. Load initial session summary
const session = await fetch(`/api/live/session-summary?user_id=${userId}&session_id=${sessionId}`);
showPositions(session.session_summary.positions);

// 2. Start polling node state (every 1s)
setInterval(async () => {
  const nodeState = await fetch(`/api/live/node-state?user_id=${userId}&session_id=${sessionId}`);
  updateNodeIndicators(nodeState.node_current_state);
}, 1000);

// 3. Refresh positions table (every 5s, optional)
setInterval(async () => {
  const session = await fetch(`/api/live/session-summary?user_id=${userId}&session_id=${sessionId}`);
  updatePositionsTable(session.session_summary.positions);
}, 5000);
```
