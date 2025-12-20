# Queue Toggle & P&L API Integration Fix

## Issues Fixed

### 1. Queue Toggle Not Enabling ✅
**Problem:** Queue toggle checkbox was disabled for running strategies.

**Root Cause:** Backend only enabled `show_queue_toggle` for "ready" and "starting" statuses, excluding "running".

**Fix:** Updated both API endpoints to enable queue toggle for "ready", "starting", AND "running" sessions.

```python
# Before
show_queue_toggle = status in ["ready", "starting"]

# After
show_queue_toggle = status in ["ready", "starting", "running"]
```

### 2. Aggregated P&L Missing ✅
**Problem:** Dashboard didn't show total P&L across all strategies.

**Root Cause:** Backend returned individual strategy P&L but didn't calculate aggregated totals.

**Fix:** Added aggregated P&L calculation to `/api/live-trading/dashboard/{user_id}` endpoint.

### 3. Individual Strategy P&L Display ✅
**Problem:** Individual strategy cards may not show P&L correctly.

**Root Cause:** P&L data structure was correct but frontend needed clear path documentation.

**Fix:** Documented exact API response structure for frontend integration.

---

## API Response Structure

### `/api/live-trading/dashboard/{user_id}`

**Response Format:**
```json
{
  "total_sessions": 3,
  "active_sessions": 2,
  "cache_time": "2024-12-20T11:30:00Z",
  
  // ✨ NEW: Aggregated P&L across all strategies
  "aggregated_pnl": {
    "realized_pnl": "1250.50",
    "unrealized_pnl": "340.20",
    "total_pnl": "1590.70",
    "closed_trades": 15,
    "open_trades": 3
  },
  
  "sessions": {
    "session_123": {
      "session_id": "session_123",
      "strategy_name": "Strategy A",
      "status": "running",
      "show_queue_toggle": true,    // ✨ Now true for running sessions
      "is_queued": false,
      "data": {
        "gps_data": {
          // Individual strategy P&L
          "pnl": {
            "realized_pnl": "850.30",
            "unrealized_pnl": "120.10",
            "total_pnl": "970.40",
            "closed_trades": 10,
            "open_trades": 2
          },
          "positions": [...],
          "trades": [...]
        }
      }
    },
    "session_456": {
      // Another strategy...
    }
  }
}
```

### `/api/live-trading/strategies/{user_id}`

**Response Format:**
```json
{
  "total_strategies": 5,
  "strategies": [
    {
      "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
      "strategy_name": "My Strategy",
      "status": "running",
      "show_queue_toggle": true,    // ✨ Now true for running status
      "is_queued": false,
      "has_trades": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-12-20T10:00:00Z"
    }
  ]
}
```

---

## Frontend Integration Guide

### 1. Queue Toggle Checkbox

**Read from API:**
```javascript
const strategy = apiResponse.sessions[sessionId];
const showToggle = strategy.show_queue_toggle;  // Boolean
const isQueued = strategy.is_queued;             // Boolean

// Enable/disable checkbox
<Checkbox 
  disabled={!showToggle}
  checked={isQueued}
  onChange={handleQueueToggle}
/>
```

**When to show toggle:**
- ✅ Status: "ready", "starting", "running"
- ❌ Status: "completed", "stopped", "error"

### 2. Aggregated P&L Display (Top of Dashboard)

**Read from API:**
```javascript
const dashboard = apiResponse;
const aggPnl = dashboard.aggregated_pnl;

// Display in header/summary card
Total P&L: ₹{aggPnl.total_pnl}
Realized: ₹{aggPnl.realized_pnl}
Unrealized: ₹{aggPnl.unrealized_pnl}
Trades: {aggPnl.closed_trades} closed, {aggPnl.open_trades} open
```

### 3. Individual Strategy P&L (On Each Card)

**Read from API:**
```javascript
const session = apiResponse.sessions[sessionId];
const pnl = session.data.gps_data.pnl;

// Display on strategy card
Strategy P&L: ₹{pnl.total_pnl}
Realized: ₹{pnl.realized_pnl}
Unrealized: ₹{pnl.unrealized_pnl}
```

**Color Coding:**
```javascript
const pnlColor = parseFloat(pnl.total_pnl) >= 0 ? 'green' : 'red';
const pnlIcon = parseFloat(pnl.total_pnl) >= 0 ? '🟢' : '🔴';
```

---

## Testing Checklist

### Backend Tests ✅
- [x] Queue toggle enabled for running sessions
- [x] Aggregated P&L calculated correctly
- [x] Individual strategy P&L present in response
- [x] Both endpoints consistent

### Frontend Tests (To Be Done)
- [ ] Queue toggle checkbox appears for all strategies
- [ ] Queue toggle checkbox enables for ready/starting/running
- [ ] Queue toggle checkbox disables for completed/stopped/error
- [ ] Aggregated P&L displays in dashboard header
- [ ] Individual strategy P&L displays on each card
- [ ] P&L values update in real-time via SSE
- [ ] P&L color coding works (green/red)

---

## API Endpoints Summary

| Endpoint | Purpose | Queue Toggle | P&L Data |
|----------|---------|--------------|----------|
| `/api/live-trading/dashboard/{user_id}` | Active sessions + aggregated P&L | ✅ | ✅ Aggregated + Individual |
| `/api/live-trading/strategies/{user_id}` | All strategies (with/without sessions) | ✅ | ❌ (Use dashboard for P&L) |
| `/api/queue/submit` | Add strategy to queue | - | - |
| `/api/queue/status/admin_tester` | Check queue status | - | - |
| `/api/queue/execute` | Execute queued strategies | - | - |

---

## Files Modified

1. `backtest_api_server.py`
   - Lines 1256-1263: Added aggregated P&L tracking
   - Lines 1294-1313: Extract and aggregate P&L from each session
   - Lines 1356-1369: Return aggregated P&L in response
   - Lines 1168-1169: Fixed queue toggle for strategies endpoint
   - Lines 1294-1296: Fixed queue toggle for dashboard endpoint

---

## Example Frontend Implementation

```typescript
// Fetch dashboard data
const response = await fetch(`/api/live-trading/dashboard/${userId}`);
const data = await response.json();

// Display aggregated P&L (top of page)
<SummaryCard>
  <h3>Total Portfolio P&L</h3>
  <div className={data.aggregated_pnl.total_pnl >= 0 ? 'profit' : 'loss'}>
    ₹{data.aggregated_pnl.total_pnl}
  </div>
  <div>
    Realized: ₹{data.aggregated_pnl.realized_pnl} | 
    Unrealized: ₹{data.aggregated_pnl.unrealized_pnl}
  </div>
  <div>
    {data.aggregated_pnl.closed_trades} closed, 
    {data.aggregated_pnl.open_trades} open
  </div>
</SummaryCard>

// Display strategy grid
{Object.entries(data.sessions).map(([sessionId, session]) => (
  <StrategyCard key={sessionId}>
    <h4>{session.strategy_name}</h4>
    <div className="status">{session.status}</div>
    
    {/* Queue Toggle */}
    <Checkbox
      label="Add to Queue"
      disabled={!session.show_queue_toggle}
      checked={session.is_queued}
      onChange={() => handleQueueToggle(session.strategy_id)}
    />
    
    {/* Individual Strategy P&L */}
    <div className="pnl">
      <span className={session.data.gps_data.pnl.total_pnl >= 0 ? 'profit' : 'loss'}>
        ₹{session.data.gps_data.pnl.total_pnl}
      </span>
      <small>
        Realized: ₹{session.data.gps_data.pnl.realized_pnl} | 
        Unrealized: ₹{session.data.gps_data.pnl.unrealized_pnl}
      </small>
    </div>
  </StrategyCard>
))}
```

---

## Troubleshooting

### Issue: Queue toggle still disabled
**Check:**
1. Session status is "running", "starting", or "ready"
2. API response includes `show_queue_toggle: true`
3. Frontend reads correct field from API response

### Issue: Aggregated P&L shows zero
**Check:**
1. Sessions exist with status not in ["completed", "stopped", "error"]
2. Sessions have `tick_state.pnl_summary` populated
3. Backend properly summing across all sessions

### Issue: Individual strategy P&L shows zero
**Check:**
1. Strategy has executed trades (closed or open positions)
2. `tick_state.pnl_summary` is being updated by backend
3. Frontend reads from `session.data.gps_data.pnl` path

---

## Status: ✅ COMPLETE

**Backend fixes deployed. Frontend integration required.**

Contact backend team if issues persist with API responses.
