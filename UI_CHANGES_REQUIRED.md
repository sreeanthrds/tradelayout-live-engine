# UI Changes Required for Live Trading Dashboard

## Backend Status: ✅ COMPLETE
All endpoints operational on port 8000. SSE streaming provides all required data.

---

## Frontend Changes Required

### 1. **Live Trade Dashboard Cards (Top Row)**

#### ❌ **REMOVE These Cards:**
- "CLOSED TRADES" card (showing count: 0)
- "OPEN POSITIONS" card (showing count: 0)

#### ✅ **ADD These Cards:**

**Card 1: LTP STORE**
```tsx
<DashboardCard>
  <Icon>📈</Icon>
  <Label>LTP UPDATES</Label>
  <Value>{ltpCount}</Value>
  <SubLabel>{ltpCount} symbols streaming</SubLabel>
</DashboardCard>
```

**Card 2: POSITION STORE**
```tsx
<DashboardCard>
  <Icon>📊</Icon>
  <Label>OPEN POSITIONS</Label>
  <Value>{positionCount}</Value>
  <SubLabel>{positionCount} active positions</SubLabel>
</DashboardCard>
```

**Data Source:**
```typescript
// From SSE stream: /api/live-trading/stream/{user_id}
const streamData = await eventSource.on('data', (event) => {
  const data = JSON.parse(event.data);
  
  // For each running session
  data.sessions.forEach(session => {
    if (session.live_data) {
      // Count LTP updates
      const ltpCount = session.live_data.ltp_store 
        ? Object.keys(session.live_data.ltp_store).length 
        : 0;
      
      // Count positions
      const positionCount = session.live_data.positions 
        ? session.live_data.positions.length 
        : 0;
    }
  });
});
```

---

### 2. **Strategy Card (Bottom) - Update Display**

#### Current Issues:
- Shows "Total P&L: Loading..."
- Shows "Trades: --"
- No timestamp visible

#### ✅ **Update to Show:**

```tsx
<StrategyCard>
  {/* Header */}
  <div className="header">
    <h3>My strategy 5</h3>
    <Badge color="blue">● RUNNING</Badge>
    <Badge color="green">🔴 LIVE</Badge>
  </div>
  
  {/* NEW: Last Update Indicator */}
  <div className="live-indicator">
    <span className={isRecent ? "pulse" : "stale"}>●</span>
    Last Update: {formatTimeAgo(lastUpdate)}
  </div>
  
  {/* Stats Row */}
  <div className="stats">
    <div className="stat">
      <label>Total P&L</label>
      <value className={pnl >= 0 ? "positive" : "negative"}>
        {pnl !== null ? `₹${pnl}` : "Waiting..."}
      </value>
    </div>
    
    <div className="stat">
      <label>Trades</label>
      <value>{tradeCount}</value>
    </div>
    
    {/* NEW: Add these */}
    <div className="stat">
      <label>Events</label>
      <value>{eventCount}</value>
    </div>
    
    <div className="stat">
      <label>LTP Updates</label>
      <value>{ltpCount}</value>
    </div>
  </div>
  
  {/* Broker Info */}
  <div className="broker-info">
    <label>Broker Connection</label>
    <value>ClickHouse Simulation (...)</value>
  </div>
  
  {/* Scale */}
  <div className="scale-info">
    <label>Scale</label>
    <value>1</value>
  </div>
  
  {/* Action Button */}
  <Button onClick={openModal}>View Trades</Button>
</StrategyCard>
```

**Data Source:**
```typescript
// From SSE stream
const session = data.sessions[0];
const liveData = session.live_data;

const stats = {
  pnl: liveData?.summary?.total_pnl || null,
  tradeCount: liveData?.trade_count || 0,
  eventCount: liveData?.event_count || 0,
  ltpCount: liveData?.ltp_store ? Object.keys(liveData.ltp_store).length : 0,
  lastUpdate: liveData?.last_update || session.started_at,
  isRunning: liveData?.is_running || false
};

// Check if data is fresh (updated within last 5 seconds)
const isRecent = (Date.now() - new Date(stats.lastUpdate).getTime()) < 5000;
```

**Helper Function:**
```typescript
function formatTimeAgo(timestamp: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(timestamp).getTime()) / 1000
  );
  
  if (seconds < 5) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}
```

---

### 3. **Live Trading Report Modal - NO CHANGES**

The modal already works correctly with the backtest format. Keep it as-is.

**Current flow works:**
1. Click "View Trades" button
2. UI calls `/api/simple/live/initial-state/{user_id}/{strategy_id}`
3. UI opens modal with initial data
4. UI connects to `/api/simple/live/stream/{session_id}`
5. Modal displays: Summary, Trades, Events tabs

**Note:** Backend provides `ltp_store` and `positions` in the stream, but modal doesn't need to display them (per user's requirement).

---

## Data Flow Summary

```
User opens Live Trade Dashboard
  ↓
UI connects to: GET /api/live-trading/stream/{user_id}
  ↓
Backend returns SSE stream with:
{
  sessions: [{
    session_id: "...",
    status: "running",
    live_data: {
      trades: [...],
      summary: { total_pnl: "0.00" },
      ltp_store: { "NIFTY": 25500, ... },
      positions: [{...}],
      trade_count: 0,
      event_count: 0,
      last_update: "2025-12-25T07:08:24",
      is_running: true,
      has_ltp_data: true,
      has_position_data: false
    }
  }]
}
  ↓
UI updates dashboard cards every 2 seconds
```

---

## Implementation Checklist

### Dashboard Header Cards:
- [ ] Remove "CLOSED TRADES" card
- [ ] Remove "OPEN POSITIONS" card  
- [ ] Add "LTP UPDATES" card showing live LTP count
- [ ] Add "POSITION STORE" card showing active positions count

### Strategy Card:
- [ ] Replace "Loading..." with actual P&L value or "Waiting..."
- [ ] Replace "Trades: --" with actual count or "0"
- [ ] Add "Last Update: X seconds ago" indicator
- [ ] Add visual pulse/dot that animates when data is fresh (<5s old)
- [ ] Add "Events" count display
- [ ] Add "LTP Updates" count display
- [ ] Ensure card updates every 2 seconds from SSE stream

### Data Integration:
- [ ] Connect to `/api/live-trading/stream/{user_id}` on page load
- [ ] Parse SSE events and extract session data
- [ ] Update all dashboard elements every 2 seconds
- [ ] Handle null values gracefully (show "Waiting..." or "0")
- [ ] Show stale data indicator if last_update > 10 seconds ago

---

## Testing Checklist

### After Implementation:
1. [ ] Open Live Trade dashboard
2. [ ] Submit a strategy to queue
3. [ ] Click "Start All" to execute
4. [ ] Verify "LTP UPDATES" card shows count (starts at 0)
5. [ ] Verify "POSITION STORE" card shows count (starts at 0)
6. [ ] Verify strategy card shows "Last Update: Just now"
7. [ ] Verify "Last Update" changes every 2 seconds (2s, 4s, 6s...)
8. [ ] Verify pulse dot animates when data is fresh
9. [ ] Verify P&L shows "Waiting..." or actual value (not "Loading...")
10. [ ] Verify Trades count shows "0" (not "--")
11. [ ] Click "View Trades" and verify modal still works

---

## Notes for Frontend Team

- **Backend is 100% complete** - All endpoints working
- **Port 8000** - UI should connect here, not 8001
- **SSE updates every 2 seconds** - UI should handle this gracefully
- **Null values are expected** - Show "Waiting..." or "0" initially
- **last_update field** - Use this to show data freshness
- **Modal doesn't need changes** - Keep existing implementation

---

## Questions?

If any backend changes are needed, please provide:
1. Exact endpoint path being called
2. Expected response format
3. Error message or unexpected behavior

Backend team will respond within 24 hours.
