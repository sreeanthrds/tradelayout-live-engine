# SSE Streaming Guide

## Overview

Complete SSE (Server-Sent Events) streaming infrastructure for real-time event delivery during live simulation backtests.

## Architecture

### Components Created

1. **`live_simulation_sse.py`** - Core SSE Manager
   - `SSESession`: Per-session event queues (node, trade, position, LTP, candle)
   - `SSEManager`: Global singleton managing all sessions
   - Thread-safe with sequence numbering for client-side ordering

2. **`StrategyOutputWriter` (Enhanced)** - Automatic SSE Push
   - Auto-pushes events to SSE when `session_id` provided
   - Works seamlessly with existing `write_event()`, `write_trade()`, etc.
   - New methods: `write_ltp_snapshot()`, `write_candle_update()`, `write_node_diagnostic()`

3. **Existing Integrations** - Already Wired
   - `NodeDiagnostics.record_event()` → SSE push (node events)
   - `GPS.close_position()` → SSE push (trade events)

## Event Types

### 1. **Node Events** (`diagnostics_export.json.gz` format)
```python
{
    'execution_id': 'exec_entry-2_20241029091800_a1b2c3',
    'parent_execution_id': 'exec_entry-condition-1_...',
    'timestamp': '2024-10-29T09:18:00',
    'event_type': 'logic_completed',
    'node_id': 'entry-2',
    'node_name': 'Entry 2',
    'node_type': 'entryNode',
    'action': {...},  # Order details
    'position': {...}  # Position details
}
```

**Source:** `NodeDiagnostics.record_event()` (already integrated)

### 2. **Trade Events** (`trades_daily.json.gz` format)
```python
{
    'trade_id': 'entry-2-pos1',
    'symbol': 'NIFTY:2024-11-07:OPT:24250:PE',
    'side': 'BUY',
    'quantity': 1,
    'entry_price': 181.60,
    'entry_time': '2024-10-29T09:18:00',
    'exit_price': 45.20,
    'exit_time': '2024-10-29T15:25:00',
    'pnl': -136.40,
    'status': 'closed'
}
```

**Source:** `GPS.close_position()` (already integrated), `StrategyOutputWriter.write_trade()`

### 3. **Position Updates** (Per-tick P&L)
```python
{
    'position_id': 'entry-2-pos1',
    'symbol': 'NIFTY:2024-11-07:OPT:24250:PE',
    'current_price': 150.25,
    'unrealized_pnl': -31.35,
    'timestamp': '2024-10-29T10:00:00'
}
```

**Source:** `StrategyOutputWriter.write_position_update()` (new SSE hook added)

### 4. **LTP Snapshots** (Configurable frequency)
```python
{
    'NIFTY': {'ltp': 24850.50},
    'NIFTY:2024-11-07:OPT:24250:PE': {'ltp': 150.25},
    'NIFTY:2024-11-07:OPT:25000:CE': {'ltp': 35.40}
}
```

**Source:** `StrategyOutputWriter.write_ltp_snapshot()` (new method)

### 5. **Candle Updates** (On completion)
```python
{
    'symbol': 'NIFTY',
    'timeframe': '1m',
    'timestamp': '2024-10-29T09:19:00',
    'open': 24850.00,
    'high': 24860.50,
    'low': 24845.00,
    'close': 24855.25,
    'volume': 15230,
    'rsi_14': 58.32
}
```

**Source:** `StrategyOutputWriter.write_candle_update()` (new method)

### 6. **Per-Tick Node Diagnostics** (Active nodes)
Same format as node events, but captured every tick for ACTIVE nodes (not just on completion).

**Source:** `StrategyOutputWriter.write_node_diagnostic()` (new method)

## Usage

### 1. Initialize with Session ID

```python
# In centralized_backtest_engine.py _subscribe_strategy_to_cache()
output_writer = StrategyOutputWriter(
    user_id=strategy.user_id,
    strategy_id=strategy.strategy_id,
    broker_connection_id='backtest',
    mode=self.mode,  # 'live_simulation' for SSE
    base_dir="backtest_data",
    session_id=session_id  # ✅ Enable SSE streaming
)
```

### 2. Events Auto-Push to SSE

All existing code automatically pushes to SSE when `session_id` is set:

```python
# Node events (already working via NodeDiagnostics)
diagnostics.record_event(node, context, 'logic_completed', {...})
# → Auto-pushed to SSE ✅

# Trade events (already working via GPS)
gps.close_position(position_id, exit_data)
# → Auto-pushed to SSE ✅

# Position updates (manual call needed)
output_writer.write_position_update({
    'position_id': pos_id,
    'current_price': ltp,
    'unrealized_pnl': pnl
})
# → Auto-pushed to SSE ✅
```

### 3. Optional: LTP/Candle Snapshots

```python
# In centralized_tick_processor.py _process_strategy()

# Every N ticks, capture LTP snapshot
if tick_count % 10 == 0:  # Every 10 ticks
    output_writer.write_ltp_snapshot(
        ltp_store=context['ltp_store'],
        timestamp=context['current_timestamp']
    )

# On candle completion
output_writer.write_candle_update({
    'symbol': symbol,
    'timeframe': timeframe,
    'timestamp': candle['timestamp'],
    'open': candle['open'],
    'high': candle['high'],
    'low': candle['low'],
    'close': candle['close'],
    'volume': candle['volume'],
    'rsi_14': candle.get('rsi_14')
})
```

### 4. Optional: Per-Tick Node Diagnostics

```python
# In base_node.py execute() for ACTIVE nodes
if node_state.get('status') == 'Active':
    execution_id = f"tick_{node.id}_{tick_count}"
    output_writer.write_node_diagnostic(execution_id, {
        'node_id': node.id,
        'timestamp': current_timestamp,
        'status': 'active',
        'tick_count': tick_count,
        'evaluation_data': {...}  # Current condition values
    })
```

## SSE Endpoint Example

```python
# In live_trading_api_server.py or backtest_api_server.py

from sse_starlette.sse import EventSourceResponse
from live_simulation_sse import sse_manager

@app.get("/api/v1/sse/{session_id}")
async def stream_events(session_id: str, event_type: str = 'all'):
    """
    Stream real-time events via SSE.
    
    Args:
        session_id: Live simulation session ID
        event_type: Filter events ('all', 'node', 'trade', 'position', 'ltp', 'candle')
    """
    session = sse_manager.get_session(session_id)
    if not session:
        return {"error": "Session not found"}
    
    async def event_generator():
        last_seq = 0
        while True:
            # Get new events since last sequence
            events = session.get_events(event_type, since_seq=last_seq)
            
            for event in events:
                yield {
                    "event": event['event_type'],
                    "id": str(event['seq']),
                    "data": json.dumps(event['data'])
                }
                last_seq = max(last_seq, event['seq'])
            
            await asyncio.sleep(0.1)  # Poll every 100ms
    
    return EventSourceResponse(event_generator())
```

## Client-Side (Frontend)

```javascript
const eventSource = new EventSource('/api/v1/sse/sim-abc123?event_type=all');

eventSource.addEventListener('node_event', (e) => {
    const data = JSON.parse(e.data);
    console.log('Node event:', data.execution_id, data.node_id);
    // Update UI with node execution
});

eventSource.addEventListener('trade_event', (e) => {
    const data = JSON.parse(e.data);
    console.log('Trade closed:', data.trade_id, data.pnl);
    // Update trade table
});

eventSource.addEventListener('position_update', (e) => {
    const data = JSON.parse(e.data);
    console.log('Position P&L:', data.position_id, data.unrealized_pnl);
    // Update P&L display
});
```

## File Output vs SSE

| Format | Backtest | Live Simulation |
|--------|----------|-----------------|
| **Node Events** | `events.jsonl` (simple) | SSE stream + `diagnostics_export.json.gz` |
| **Trades** | `trades.json` (simple) | SSE stream + `trades_daily.json.gz` |
| **Positions** | `positions.json` (simple) | SSE stream + `positions.json` |
| **LTP Snapshots** | N/A | SSE stream only |
| **Candle Updates** | N/A | SSE stream only |

## Sequence Tracking

Each event type has independent sequence numbers:
- `node_seq`: Node execution events
- `trade_seq`: Trade open/close events
- `position_seq`: Position P&L updates
- `ltp_seq`: LTP snapshots
- `candle_seq`: Candle completions

Clients can track `since_seq` to only fetch new events (efficient polling/streaming).

## Thread Safety

All SSE operations are thread-safe:
- `SSESession` uses `threading.Lock()` for queue operations
- `SSEManager` uses `threading.Lock()` for session registry
- Safe for concurrent executor and API access

## Performance

- **Max queue size:** 1000 events per queue (configurable)
- **Circular buffer:** Old events auto-dropped (LRU)
- **Minimal overhead:** Only serializes events when clients poll
- **No blocking:** Async/non-blocking event generation

## Summary

✅ **Zero code changes needed** for existing node/trade events (NodeDiagnostics, GPS already integrated)  
✅ **Opt-in SSE streaming** by passing `session_id` to `StrategyOutputWriter`  
✅ **Unified interface** for all event types  
✅ **Thread-safe** for live simulation  
✅ **Compatible** with existing `diagnostics_export.json.gz` and `trades_daily.json.gz` formats  

**Next Steps:**
1. Add SSE endpoint to `live_trading_api_server.py`
2. Add LTP/candle snapshot hooks in `centralized_tick_processor.py`
3. Add per-tick node diagnostics in `base_node.py` (optional)
4. Test with live simulation session
