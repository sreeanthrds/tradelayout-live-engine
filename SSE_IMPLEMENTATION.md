# SSE Implementation for Backtest Streaming

## Architecture: Hybrid SSE Model

Based on industry best practices (Zerodha, Interactive Brokers, Binance), this implementation uses a **hybrid approach**:

1. **Initial State**: Compressed full snapshot on connect
2. **Updates**: Incremental uncompressed deltas during session
3. **Reconnection**: Event ID tracking for gap detection

---

## Event Types

### 1. `initial_state` (On Connect)

**When:** Session start, client connects  
**Frequency:** Once per session  
**Compression:** Gzip + Base64  
**Size:** ~15 KB compressed (from ~100 KB uncompressed)

```json
{
  "event": "initial_state",
  "data": {
    "event_id": 0,
    "session_id": "sse-strategy-2024-10-29",
    "diagnostics": "H4sIAAAAAAAA...",  // gzip + base64
    "trades": "H4sIAAAAAAAA...",       // gzip + base64
    "uncompressed_sizes": {
      "diagnostics": 106000,
      "trades": 10000
    },
    "strategy_id": "...",
    "start_date": "2024-10-29",
    "end_date": "2024-10-29"
  }
}
```

**Client decompresses:**
```javascript
const compressed = atob(event.data.diagnostics);  // Base64 decode
const decompressed = pako.ungzip(compressed, { to: 'string' });  // Gunzip
const diagnostics = JSON.parse(decompressed);
```

---

### 2. `tick_update` (Every Second)

**When:** Each tick/second during backtest  
**Frequency:** ~22,000 per day  
**Compression:** None (small payload, needs speed)  
**Size:** ~3-5 KB per event

```json
{
  "event": "tick_update",
  "data": {
    "event_id": 241,
    "session_id": "...",
    "tick": 241,
    "timestamp": "2024-10-29 09:19:00+05:30",
    "execution_count": 4,
    "node_executions": {
      "exec_entry-condition-1_...": {
        "node_id": "entry-condition-1",
        "signal_emitted": false,
        "evaluated_conditions": {...}
      }
    },
    "open_positions": [
      {
        "position_id": "entry-2-pos1",
        "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
        "side": "sell",
        "quantity": 1,
        "entry_price": "215.00",
        "current_price": "220.50",
        "unrealized_pnl": "-5.50"
      }
    ],
    "pnl_summary": {
      "realized_pnl": "0.00",
      "unrealized_pnl": "-5.50",
      "total_pnl": "-5.50",
      "closed_trades": 0,
      "open_trades": 1
    },
    "ltp": {
      "NIFTY": {
        "ltp": 24350.5,
        "timestamp": "2024-10-29 09:19:00.000000"
      }
    },
    "active_nodes": ["entry-condition-1", "entry-condition-2", "square-off-1"]
  }
}
```

---

### 3. `node_event` (On Node Completion)

**When:** Node logic completes (signal emitted, order placed)  
**Frequency:** ~38 per day (significant milestones only)  
**Compression:** None (small, infrequent)  
**Size:** ~1 KB per event

```json
{
  "event": "node_event",
  "data": {
    "event_id": 242,
    "session_id": "...",
    "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
    "node_id": "entry-condition-1",
    "node_name": "Entry condition - Bullish",
    "node_type": "EntrySignalNode",
    "timestamp": "2024-10-29 09:19:00+05:30",
    "event_type": "logic_completed",
    "signal_emitted": true,
    "conditions_preview": "Current Time >= 09:17 AND..."
  }
}
```

---

### 4. `trade_update` (On Trade Close)

**When:** Position closes  
**Frequency:** ~7 per day  
**Compression:** None (small, infrequent)  
**Size:** ~1 KB per event

```json
{
  "event": "trade_update",
  "data": {
    "event_id": 243,
    "session_id": "...",
    "trade": {
      "trade_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
      "side": "sell",
      "quantity": 1,
      "entry_price": "215.00",
      "entry_time": "2024-10-29 09:19:05+05:30",
      "exit_price": "185.75",
      "exit_time": "2024-10-29 10:48:00+05:30",
      "pnl": "29.25",
      "status": "CLOSED"
    },
    "summary": {
      "total_trades": 1,
      "total_pnl": "29.25",
      "winning_trades": 1,
      "losing_trades": 0,
      "win_rate": "100.00"
    }
  }
}
```

---

### 5. `backtest_complete` (At End)

**When:** Backtest finishes  
**Frequency:** Once per session  
**Compression:** Gzip + Base64  
**Size:** ~15 KB compressed

```json
{
  "event": "backtest_complete",
  "data": {
    "event_id": 22351,
    "session_id": "...",
    "diagnostics": "H4sIAAAAAAAA...",  // Final compressed snapshot
    "trades": "H4sIAAAAAAAA...",       // Final compressed snapshot
    "uncompressed_sizes": {
      "diagnostics": 106000,
      "trades": 10000
    },
    "total_ticks": 22351
  }
}
```

---

## Bandwidth Comparison

| Approach | Initial Load | Per Tick | Total for 22K ticks |
|----------|-------------|----------|---------------------|
| **Full snapshots** | 15 KB | 100 KB | ~2.2 GB |
| **Hybrid (recommended)** | 15 KB | 3-5 KB | ~70-110 MB |
| **Savings** | - | 95% | ~95% |

---

## Reconnection Resilience

Uses HTTP `Last-Event-ID` header for gap detection:

```
Client disconnects at event_id: 1000
Client reconnects with Last-Event-ID: 1000

Server logic:
  gap = current_event_id - last_event_id
  
  if gap < 100:
    # Send missed events (1001-1500)
    for event in missed_events:
      emit(event)
  else:
    # Gap too large, send new initial_state
    emit("initial_state", compressed_full_snapshot)
```

**Client implementation:**
```typescript
const eventSource = new EventSource(
  `/api/backtest/${sessionId}/stream`,
  { 
    headers: { 
      'Last-Event-ID': lastSeenEventId 
    } 
  }
);
```

---

## Fire-and-Forget Architecture

**Server doesn't track client state:**

```python
# Server just broadcasts events
emitter.emit("tick_update", data)  # Broadcast to all callbacks
emitter.emit("node_event", data)   # Fire and forget

# No per-client tracking:
# ❌ for client in clients: client.send(data)
# ✅ emit(data)  # All registered callbacks receive it
```

**Benefits:**
- Server doesn't care about disconnections
- No client state management
- Better scalability
- Client handles reconnection logic
- Matches existing SSE hook architecture

---

## Implementation Files

### Engine
- **`centralized_backtest_engine_with_sse.py`** - SSE-enabled engine
  - Extends `CentralizedBacktestEngine`
  - Emits events via `SSEEventEmitter`
  - Tracks state for incremental updates
  - Compresses initial/final snapshots

### Event Emitter
- **`SSEEventEmitter`** class - Fire-and-forget broadcaster
  - Maintains event ID counter
  - Registers callbacks (no client tracking)
  - Compresses JSON with gzip + base64
  - Broadcasts to all callbacks

### Test Runner
- **`run_backtest_with_sse.py`** - Demo script
  - Registers logger callback
  - Writes events to JSONL streams
  - Shows event counts and timing

---

## Usage

### 1. Basic Usage (Console Logging)

```python
from centralized_backtest_engine_with_sse import CentralizedBacktestEngineWithSSE

# Create engine
engine = CentralizedBacktestEngineWithSSE(
    config=backtest_config,
    session_id="my-session-123"
)

# Register callback
def my_callback(event):
    print(f"[{event['event']}] Event ID: {event['data']['event_id']}")

engine.register_sse_callback(my_callback)

# Run (emits events to callback)
result = engine.run()
```

### 2. FastAPI Integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from centralized_backtest_engine_with_sse import CentralizedBacktestEngineWithSSE

app = FastAPI()

@app.get("/api/backtest/{session_id}/stream")
async def stream_backtest(session_id: str):
    async def event_generator():
        # Create engine
        engine = CentralizedBacktestEngineWithSSE(...)
        
        # Queue for events
        import asyncio
        queue = asyncio.Queue()
        
        # Callback adds to queue
        def callback(event):
            queue.put_nowait(event)
        
        engine.register_sse_callback(callback)
        
        # Start backtest in background
        import threading
        thread = threading.Thread(target=engine.run)
        thread.start()
        
        # Yield events as SSE
        while thread.is_alive() or not queue.empty():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield f"event: {event['event']}\n"
                yield f"data: {json.dumps(event['data'])}\n"
                yield f"id: {event['data']['event_id']}\n\n"
            except asyncio.TimeoutError:
                continue
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### 3. File-based Logging (Testing)

```bash
python run_backtest_with_sse.py
```

**Output:**
```
sse_backtest_output/
  ├── initial_state.json          # Compressed initial snapshot
  ├── tick_updates_stream.jsonl   # One line per tick
  ├── node_events_stream.jsonl    # One line per node event
  ├── trade_updates_stream.jsonl  # One line per trade
  └── final_state.json             # Compressed final snapshot
```

---

## Testing

```bash
# Run with SSE event logging
python run_backtest_with_sse.py

# Expected output:
# [Event 0] initial_state
#   Diagnostics: 0 bytes (compressed)
#   Trades: 0 bytes (compressed)
# [Event 1] tick_update #1: 4 nodes, 0 positions
# [Event 100] tick_update #100: 3 nodes, 0 positions
# [Event 242] node_event: entry-condition-1 (signal=True)
# [Event 243] trade_update: NIFTY:...:PE P&L=29.25
# ...
# [Event 22351] backtest_complete
#   Total ticks: 22,351
#   Final diagnostics: 106,000 bytes (compressed)
```

---

## Client Implementation (React/TypeScript)

```typescript
import { useEffect, useState } from 'react';
import pako from 'pako';

function useBacktestSSE(sessionId: string) {
  const [state, setState] = useState({
    diagnostics: null,
    trades: null,
    currentTick: null,
    lastEventId: 0
  });

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/backtest/${sessionId}/stream`,
      { headers: { 'Last-Event-ID': state.lastEventId.toString() } }
    );

    // Handle initial_state
    eventSource.addEventListener('initial_state', (e) => {
      const data = JSON.parse(e.data);
      
      // Decompress diagnostics
      const diagCompressed = atob(data.diagnostics);
      const diagDecompressed = pako.ungzip(diagCompressed, { to: 'string' });
      const diagnostics = JSON.parse(diagDecompressed);
      
      // Decompress trades
      const tradesCompressed = atob(data.trades);
      const tradesDecompressed = pako.ungzip(tradesCompressed, { to: 'string' });
      const trades = JSON.parse(tradesDecompressed);
      
      setState(s => ({ ...s, diagnostics, trades, lastEventId: data.event_id }));
    });

    // Handle tick_update (no decompression needed)
    eventSource.addEventListener('tick_update', (e) => {
      const data = JSON.parse(e.data);
      setState(s => ({ ...s, currentTick: data, lastEventId: data.event_id }));
    });

    // Handle node_event (incremental)
    eventSource.addEventListener('node_event', (e) => {
      const data = JSON.parse(e.data);
      // Append to diagnostics
      setState(s => ({
        ...s,
        diagnostics: {
          ...s.diagnostics,
          events_history: {
            ...s.diagnostics.events_history,
            [data.execution_id]: data
          }
        },
        lastEventId: data.event_id
      }));
    });

    // Handle trade_update (incremental)
    eventSource.addEventListener('trade_update', (e) => {
      const data = JSON.parse(e.data);
      // Append trade and update summary
      setState(s => ({
        ...s,
        trades: {
          ...s.trades,
          trades: [...s.trades.trades, data.trade],
          summary: data.summary
        },
        lastEventId: data.event_id
      }));
    });

    return () => eventSource.close();
  }, [sessionId]);

  return state;
}
```

---

## Performance Metrics

For 2024-10-29 backtest (22,351 ticks):

| Metric | Value |
|--------|-------|
| Total events | ~22,400 |
| Initial state | 15 KB (compressed) |
| Tick updates | ~70 MB (uncompressed, 3 KB/tick) |
| Node events | ~38 KB (38 events × 1 KB) |
| Trade updates | ~7 KB (7 trades × 1 KB) |
| Final state | 15 KB (compressed) |
| **Total bandwidth** | **~70 MB** vs ~2.2 GB (full snapshots) |
| **Savings** | **~97%** |

---

## Summary

✅ **Hybrid model** = Best of both worlds  
✅ **Fire-and-forget** = Simple, scalable  
✅ **Event ID tracking** = Reconnection resilient  
✅ **Compression** = Only where it matters (initial/final)  
✅ **Incremental** = Minimal bandwidth during session  
✅ **Industry standard** = Matches Zerodha, IB, Binance  

This implementation provides the optimal balance between **performance, reliability, and ease of use** for real-time backtest streaming.
