# UI SSE Fix Instructions - December 2024

## Problem Identified

The UI has **TWO SSE hooks** and is using the **WRONG one** in `LiveDashboardLayout.tsx`:

### ✅ Correct Hook (Already Exists)
**File:** `src/hooks/use-user-sse.ts`
- **Endpoint:** `/api/live-trading/stream/{userId}`
- **Status:** Working correctly ✅
- **Features:**
  - Multi-session support
  - Incremental `node_events` merging
  - Incremental `trade_update` appending
  - Handles `initial_state`, `tick_update`, `heartbeat`

### ❌ Broken Hook (Currently in Use)
**File:** `src/hooks/use-live-report-sse.ts`
- **Endpoint:** `/api/live-trading/session/{sessionId}/stream` 
- **Status:** THIS ENDPOINT DOESN'T EXIST ❌
- **Result:** Connection errors, no data

### Current Bug
`LiveDashboardLayout.tsx` imports and uses the **broken hook** (`use-live-report-sse.ts`), which tries to connect to a non-existent session-specific endpoint.

---

## The Fix

Replace the broken session-specific hook with the working user-level hook in `LiveDashboardLayout.tsx`.

---

## Step-by-Step Changes

### Change 1: Update Import Statement

**File:** `src/components/live-trade/dashboard/LiveDashboardLayout.tsx`

**Line ~4** - Replace this import:
```typescript
import { useLiveReportSSE } from '@/hooks/use-live-report-sse';
```

**With:**
```typescript
import { useUserSSE } from '@/hooks/use-user-sse';
```

---

### Change 2: Add API Base URL State

**File:** `src/components/live-trade/dashboard/LiveDashboardLayout.tsx`

**After line ~93** (after the `useLivePolling` hook), add:

```typescript
// Get API base URL
const [apiBaseUrl, setApiBaseUrl] = useState<string | null>(null);
useEffect(() => {
  const initUrl = async () => {
    try {
      const url = await (await import('@/lib/api-config')).getApiBaseUrl(userId || undefined);
      setApiBaseUrl(url);
    } catch (err) {
      console.error('Failed to get API base URL:', err);
      setApiBaseUrl('https://api.tradelayout.com');
    }
  };
  initUrl();
}, [userId]);
```

---

### Change 3: Replace SSE Hook Usage

**File:** `src/components/live-trade/dashboard/LiveDashboardLayout.tsx`

**Find these lines (~107-116):**
```typescript
// Get session ID for SSE connection
const sessionId = selectedStrategy?.backendSessionId || selectedStrategy?.id || null;

// SSE hook for real-time updates (includes eventsHistory for flow diagrams)
const { 
  tickData: sseTickData,
  eventsHistory: sseEventsHistory,
  isConnected: isSSEConnected,
  error: sseError
} = useLiveReportSSE(sessionId, userId || undefined);
```

**Replace with:**
```typescript
// Get session ID for selected strategy
const sessionId = selectedStrategy?.backendSessionId || selectedStrategy?.id || null;

// User-level SSE hook for all sessions (includes eventsHistory for flow diagrams)
const { 
  sessionTicks,
  sessionDiagnostics,
  sessionTrades,
  isConnected: isSSEConnected,
  error: sseError,
  connect: connectSSE
} = useUserSSE(userId || null, apiBaseUrl, true);

// Extract data for selected session
const sseEventsHistory = sessionId ? (sessionDiagnostics[sessionId]?.events_history || {}) : {};
const sseTickData = sessionId ? sessionTicks[sessionId]?.tickState : null;
```

---

### Change 4: Fix Node States Mapping

**File:** `src/components/live-trade/dashboard/LiveDashboardLayout.tsx`

**Find these lines (~139-150):**
```typescript
// Get node states from SSE tick data for canvas (if available)
const nodeStates = sseTickData?.node_executions ? 
  Object.fromEntries(
    Object.entries(sseTickData.node_executions).map(([id, exec]: [string, any]) => [
      exec.node_id,
      {
        nodeId: exec.node_id,
        status: exec.signal_emitted ? 'completed' : exec.logic_completed ? 'active' : 'pending',
        lastUpdate: exec.timestamp,
        data: exec
      }
    ])
  ) : {};
```

**Replace with:**
```typescript
// Get node states from SSE tick data for canvas (if available)
// Map active/pending nodes from tick_update to node states
const nodeStates = sseTickData ? 
  Object.fromEntries([
    ...(sseTickData.active_nodes || []).map(nodeId => [
      nodeId,
      {
        nodeId,
        status: 'active' as const,
        lastUpdate: sseTickData.timestamp,
        data: {}
      }
    ]),
    ...(sseTickData.pending_nodes || []).map(nodeId => [
      nodeId,
      {
        nodeId,
        status: 'pending' as const,
        lastUpdate: sseTickData.timestamp,
        data: {}
      }
    ])
  ])
  : {};
```

---

## Why This Fixes the Issue

### Before (Broken)
```
LiveDashboardLayout 
  → use-live-report-sse 
    → /api/live-trading/session/{sessionId}/stream ❌ (doesn't exist)
      → Connection error
```

### After (Fixed)
```
LiveDashboardLayout 
  → use-user-sse 
    → /api/live-trading/stream/{userId} ✅ (correct endpoint)
      → Receives all session data
        → Extract selected session's eventsHistory and tickData
          → Flow diagrams work correctly ✅
```

---

## Data Flow After Fix

1. **SSE Connection:**
   - Connects to `/api/live-trading/stream/{userId}` (user-level stream)
   - Receives data for ALL user sessions simultaneously

2. **Multi-Session Cache:**
   - `sessionDiagnostics[sessionId].events_history` - Events for each session
   - `sessionTicks[sessionId].tickState` - Real-time tick data for each session
   - `sessionTrades[sessionId]` - Trades for each session

3. **Selected Session Extraction:**
   - When user selects a session, extract that session's data from cache
   - `sseEventsHistory` = events_history for selected session
   - `sseTickData` = tick data for selected session

4. **LiveReportPanel:**
   - Receives `eventsHistory` from SSE
   - Receives `pollingData` (trades, pnl) from REST polling
   - Builds flow diagrams using `entry_flow_ids` and `exit_flow_ids`
   - **Flow diagrams now work because eventsHistory has the correct data**

---

## Expected SSE Events (For Reference)

### initial_state
```json
{
  "session_id": "sim-abc123",
  "diagnostics": {
    "events_history": {
      "exec-001": { "node_name": "StartNode", "timestamp": "...", ... },
      "exec-002": { "node_name": "EntryNode", "timestamp": "...", ... }
    }
  },
  "trades": {
    "trades": [...],
    "summary": {...}
  }
}
```

### node_events (Incremental)
```json
{
  "session_id": "sim-abc123",
  "events": {
    "exec-003": { "node_name": "ConditionNode", "timestamp": "...", ... }
  }
}
```

### trade_update (Incremental)
```json
{
  "session_id": "sim-abc123",
  "trade": {
    "trade_id": "...",
    "entry_flow_ids": ["exec-001", "exec-002"],
    "exit_flow_ids": ["exec-003", "exec-004"],
    "pnl": 150.50,
    ...
  },
  "summary": {...}
}
```

### tick_update
```json
{
  "session_id": "sim-abc123",
  "tick_state": {
    "timestamp": "...",
    "active_nodes": ["node-123"],
    "pending_nodes": ["node-456"],
    "open_positions": [...],
    "pnl_summary": {...}
  }
}
```

---

## Testing After Fix

1. **Start a live session** from your backend
2. **Open Live Dashboard** in UI
3. **Select the session** from sidebar
4. **Check browser console** - should see:
   ```
   ✅ User SSE: Connected to /api/live-trading/stream/{userId}
   📦 LiveSSE: Loaded 50 events from initial_state
   📊 SSE eventsHistory: 50 events cached
   ```
5. **Close a trade** - trade should appear with flow diagrams
6. **Click a node in the flow diagram** - should highlight in events history

---

## Summary

**One file to change:** `src/components/live-trade/dashboard/LiveDashboardLayout.tsx`

**Four edits:**
1. Import `useUserSSE` instead of `useLiveReportSSE`
2. Add `apiBaseUrl` state initialization
3. Replace hook usage and extract session data
4. Fix `nodeStates` mapping to use `active_nodes`/`pending_nodes`

**Result:** SSE connects to correct endpoint, flow diagrams link properly to events history.
