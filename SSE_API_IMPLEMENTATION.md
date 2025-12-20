# SSE-Based Backtest API Implementation

## ✅ Implementation Complete

### **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (UI)                             │
├─────────────────────────────────────────────────────────────────┤
│  1. POST /api/v1/backtest/start → returns backtest_id           │
│  2. GET /api/v1/backtest/{id}/stream → SSE daily summaries      │
│  3. GET /api/v1/backtest/{id}/day/{date} → download ZIP         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 **File Structure**

```
backtest_results/
├── {strategy_id}/
│   ├── 2024-10-24/
│   │   ├── trades_daily.json.gz
│   │   └── diagnostics_export.json.gz
│   ├── 2024-10-25/
│   │   ├── trades_daily.json.gz
│   │   └── diagnostics_export.json.gz
│   └── ...
```

**Key Points:**
- ✅ Files organized by `{strategy_id}/{date}/`
- ✅ Gzip compressed JSON files (70-80% size reduction)
- ✅ New backtest replaces old files for same strategy
- ⏰ Cleanup after 4+ hours (to be implemented later)

---

## 🔧 **API Endpoints**

### **1. Start Backtest**

**Endpoint:** `POST /api/v1/backtest/start`

**Request:**
```json
{
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-24",
  "end_date": "2024-10-31",
  "initial_capital": 100000,
  "slippage_percentage": 0.05,
  "commission_percentage": 0.01
}
```

**Response:**
```json
{
  "backtest_id": "5708424d-5962-4629-978c-05b3a174e104_2024-10-24_2024-10-31",
  "total_days": 8,
  "status": "ready",
  "stream_url": "/api/v1/backtest/5708424d..._2024-10-24_2024-10-31/stream"
}
```

**backtest_id Format:**
```
{strategy_id}_{start_date}_{end_date}
```

---

### **2. Stream Backtest Progress (SSE)**

**Endpoint:** `GET /api/v1/backtest/{backtest_id}/stream`

**SSE Event Types:**

#### **a) day_started**
```json
{
  "event": "day_started",
  "data": {
    "date": "2024-10-24",
    "day_number": 1,
    "total_days": 8
  }
}
```

#### **b) day_completed**
```json
{
  "event": "day_completed",
  "data": {
    "date": "2024-10-24",
    "day_number": 1,
    "total_days": 8,
    "summary": {
      "total_trades": 5,
      "total_pnl": "2450.50",
      "winning_trades": 3,
      "losing_trades": 2,
      "win_rate": "60.00"
    },
    "has_detail_data": true
  }
}
```

#### **c) backtest_completed**
```json
{
  "event": "backtest_completed",
  "data": {
    "backtest_id": "5708424d...978c_2024-10-24_2024-10-31",
    "overall_summary": {
      "total_days": 8,
      "total_trades": 42,
      "total_pnl": "-215.50",
      "win_rate": "21.43",
      "largest_win": "54.05",
      "largest_loss": "-78.45"
    }
  }
}
```

#### **d) error**
```json
{
  "event": "error",
  "data": {
    "date": "2024-10-25",
    "error": "Failed to fetch market data"
  }
}
```

---

### **3. Download Day Details**

**Endpoint:** `GET /api/v1/backtest/{backtest_id}/day/{date}`

**Example:** `GET /api/v1/backtest/5708424d...978c_2024-10-24_2024-10-31/day/2024-10-25`

**Response:** ZIP file containing:
- `trades_daily.json.gz`
- `diagnostics_export.json.gz`

**Content-Type:** `application/zip`

**Filename:** `backtest_2024-10-25.zip`

---

## 📦 **File Formats**

### **trades_daily.json**

```json
{
  "date": "2024-10-24",
  "summary": {
    "total_trades": 1,
    "total_pnl": "38.70",
    "winning_trades": 1,
    "losing_trades": 0,
    "win_rate": "100.00"
  },
  "trades": [
    {
      "trade_id": "entry-2-pos1",
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-10-31:OPT:24350:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": "154.70",
      "entry_time": "2024-10-24T09:44:28+05:30",
      "exit_price": "116.00",
      "exit_time": "2024-10-24T15:25:00+05:30",
      "pnl": "38.70",
      "pnl_percent": "25.02",
      "duration_minutes": 340.53,
      "status": "closed",
      "entry_flow_ids": ["exec_001", "exec_002"],
      "exit_flow_ids": ["exec_010"],
      "entry_trigger": "entry-2",
      "exit_reason": "square_off"
    }
  ]
}
```

**Key Addition:** `entry_flow_ids` and `exit_flow_ids` link trades to diagnostic events.

---

### **diagnostics_export.json**

```json
{
  "events_history": {
    "exec_001": {
      "execution_id": "exec_001",
      "parent_execution_id": null,
      "timestamp": "2024-10-24T09:44:28",
      "event_type": "ENTRY",
      "node_id": "entry-2",
      "node_name": "Entry Node",
      "node_type": "EntryNode",
      "signal_emitted": true,
      "conditions_preview": "RSI(14) > 30",
      "evaluated_conditions": {...}
    },
    "exec_002": {...},
    "exec_010": {...}
  }
}
```

---

## 🔗 **Diagnostic Linking System**

### **How Flow IDs Work:**

1. **Trade Execution:**
   - Entry at `09:44:28` triggers nodes
   - Exit at `15:25:00` triggers nodes

2. **Event Matching:**
   - `extract_flow_ids_from_diagnostics()` finds matching events
   - Matches by: `node_id` + `timestamp` (HH:MM precision)

3. **Result:**
   ```json
   {
     "entry_flow_ids": ["exec_001", "exec_002", "exec_003"],
     "exit_flow_ids": ["exec_010", "exec_011"]
   }
   ```

4. **UI Usage:**
   - User clicks trade → fetches diagnostic events using flow_ids
   - Shows detailed condition evaluations for that specific trade

---

## 🚀 **Usage Example**

### **Frontend Flow:**

```javascript
// 1. Start backtest
const response = await fetch('/api/v1/backtest/start', {
  method: 'POST',
  body: JSON.stringify({
    strategy_id: '5708424d...',
    start_date: '2024-10-24',
    end_date: '2024-10-31'
  })
});

const { backtest_id, stream_url } = await response.json();

// 2. Connect to SSE stream
const eventSource = new EventSource(stream_url);

eventSource.addEventListener('day_started', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Day ${data.day_number} started: ${data.date}`);
});

eventSource.addEventListener('day_completed', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Day ${data.date} complete:`, data.summary);
  // Update UI with daily summary
});

eventSource.addEventListener('backtest_completed', (e) => {
  const data = JSON.parse(e.data);
  console.log('Backtest complete!', data.overall_summary);
  eventSource.close();
});

// 3. Download day details when user clicks
async function downloadDayDetails(date) {
  const url = `/api/v1/backtest/${backtest_id}/day/${date}`;
  const response = await fetch(url);
  const blob = await response.blob();
  
  // Unzip and extract trades + diagnostics
  // ...
}
```

---

## ✅ **Implementation Checklist**

- [x] Helper functions for backtest_id parsing
- [x] File management functions (save, compress)
- [x] Trade → Diagnostic linking (`entry_flow_ids`, `exit_flow_ids`)
- [x] POST `/api/v1/backtest/start` endpoint
- [x] GET `/api/v1/backtest/{id}/stream` with SSE
- [x] GET `/api/v1/backtest/{id}/day/{date}` download
- [x] Install `sse-starlette` package
- [x] Server import test successful

---

## 🔄 **Backward Compatibility**

Old endpoint still available:
- `POST /api/v1/backtest` - Returns all days in one response (legacy)

New endpoints:
- `POST /api/v1/backtest/start` - Async with SSE streaming
- `GET /api/v1/backtest/{id}/stream` - Real-time progress
- `GET /api/v1/backtest/{id}/day/{date}` - On-demand downloads

---

## 📊 **Performance Benefits**

| Aspect | Before | After |
|--------|--------|-------|
| Initial Response | 87 KB (all days) | 0.5 KB (backtest_id) |
| Progress Updates | None | Real-time (SSE) |
| Day Details | Included | On-demand (gzipped) |
| File Size | N/A | 70-80% smaller (gzip) |
| Storage | None | Organized by strategy/date |

---

## 🧹 **Future Enhancements**

- [ ] Cleanup mechanism (delete files older than 4 hours)
- [ ] Rate limiting on download endpoint
- [ ] Concurrent backtest support (different strategies)
- [ ] Progress percentage per day
- [ ] Pause/resume backtest capability

---

## 🎯 **Testing**

```bash
# Start server
python backtest_api_server.py

# Test endpoints
curl -X POST http://localhost:8000/api/v1/backtest/start \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-24",
    "end_date": "2024-10-31"
  }'

# Connect to SSE stream
curl -N http://localhost:8000/api/v1/backtest/{backtest_id}/stream

# Download day details
curl -O http://localhost:8000/api/v1/backtest/{backtest_id}/day/2024-10-24
```

---

**Implementation Status:** ✅ **COMPLETE**
**Ready for Testing:** ✅ **YES**
