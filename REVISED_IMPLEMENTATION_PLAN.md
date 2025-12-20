# Revised Implementation Plan - Trade Events on All Action Nodes

## Key Clarifications

### Event Names (Keep Existing)
- ✅ **`trade_update`** - Emit on ALL action nodes (Entry, Exit, SquareOff)
- ✅ **`node_event`** - Emit on ALL nodes (already working) → UI eventHistory
- ✅ **`tick_update`** - Keep FULL diagnostics (don't reduce data)

### Implementation Strategy
- **Single Code Change**: One logic that emits `trade_update` on any action node completion
- **Incremental Testing**: Test entry, then partial exit, then full close (same code, different scenarios)

---

## Current Behavior

### What Works ✅
1. **Node Events** - All nodes emit diagnostics to `node_event`
   - UI stores in eventHistory
   - Shows execution flow
   - Node details on click

2. **Tick Updates** - Full diagnostics every tick
   - Active nodes
   - Positions (open + closed)
   - P&L summary
   - LTP store
   - Candle data

3. **Trade Events** - Only on position close
   - Emits when ExitNode/SquareOffNode completes
   - Shows full trade with entry/exit flows

### What Needs to Change ❌
1. **Trade Events Timing**
   - Current: Only on exit/square-off
   - Needed: On entry, exit, AND square-off

---

## New Behavior (After Implementation)

### `trade_update` Event (Extended)

**Emit When:**
1. ✅ EntryNode completes
2. ✅ ExitNode completes (already working)
3. ✅ SquareOffNode completes (already working)

**Event Structure:**

#### On Entry (NEW):
```json
{
  "trade_id": "entry-2-pos1",
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  "side": "SELL",
  "quantity": 1,
  "lot_size": 50,
  "effective_quantity": 50,
  "entry_price": "181.60",
  "entry_time": "2024-10-29T09:19:00+05:30",
  "exit_price": null,
  "exit_time": null,
  "pnl": "0.00",
  "pnl_percent": "0.00",
  "status": "OPEN",
  "entry_flow_ids": ["exec_strategy-controller_...", "exec_entry-2_..."],
  "exit_flow_ids": [],
  "entry_trigger": "Entry 2 - Bullish",
  "exit_reason": null
}
```

#### On Partial Exit (NEW):
```json
{
  "trade_id": "entry-2-pos1",
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  "side": "SELL",
  "quantity_entered": 50,
  "quantity_closed": 25,
  "quantity_remaining": 25,
  "entry_price": "181.60",
  "exit_price": "200.00",
  "exit_time": "2024-10-29T10:30:00+05:30",
  "pnl": "-460.00",
  "pnl_percent": "-5.07",
  "realized_pnl": "-460.00",
  "unrealized_pnl": "-460.00",
  "status": "PARTIAL",
  "partial_exits": [
    {
      "execution_id": "exec_exit-3_20241029_103000_abc123",
      "qty_closed": 25,
      "exit_price": "200.00",
      "pnl": "-460.00",
      "exit_flow_ids": ["exec_strategy-controller_...", "exec_exit-3_..."]
    }
  ],
  "exit_reason": "Exit - Target"
}
```

#### On Full Close (EXISTING - Add Fields):
```json
{
  "trade_id": "entry-2-pos1",
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  "side": "SELL",
  "quantity_entered": 50,
  "quantity_closed": 50,
  "quantity_remaining": 0,
  "entry_price": "181.60",
  "exit_price": "260.05",
  "exit_time": "2024-10-29T10:48:00+05:30",
  "pnl": "-3922.50",
  "pnl_percent": "-43.20",
  "realized_pnl": "-3922.50",
  "unrealized_pnl": "0.00",
  "status": "CLOSED",
  "exit_flow_ids": ["exec_strategy-controller_...", "exec_exit-3_..."],
  "exit_reason": "Exit - SL Hit"
}
```

---

## Implementation (Single Code Change)

### File: `live_backtest_runner.py`

### Current Code (Lines ~516-567):
```python
# Extract trades from events (EXACT backtesting logic)
trades_data = self._extract_trades_from_events(node_events_history)
all_closed_trades = trades_data.get('trades', [])

# Track trades by (position_id, re_entry_num) tuple
current_closed_trades = {(trade['position_id'], trade['re_entry_num']) for trade in all_closed_trades}
newly_closed_trades = current_closed_trades - self.previous_closed_trades

# Emit newly closed trades
for trade_key in newly_closed_trades:
    trade_position_id, trade_re_entry = trade_key
    
    # Find the trade record
    for trade in all_closed_trades:
        if trade['position_id'] == trade_position_id and trade['re_entry_num'] == trade_re_entry:
            # Emit trade_update event
            self.session.emit_trade_update(trade)
            break

# Update tracking
self.previous_closed_trades = current_closed_trades
```

### New Code (Replace Above):
```python
# ========================================================================
# EMIT TRADE_UPDATE ON ALL ACTION NODES (Entry, Exit, SquareOff)
# ========================================================================

# Build ALL trades (open + closed) from events
all_trades = self._build_trades_from_events(node_events_history)

# Separate by status
open_trades = [t for t in all_trades if t['status'] == 'OPEN']
partial_trades = [t for t in all_trades if t['status'] == 'PARTIAL']
closed_trades = [t for t in all_trades if t['status'] == 'CLOSED']

# Track all trades by key
current_all_trades = {(t['position_id'], t['re_entry_num']): t for t in all_trades}
previous_all_trades = getattr(self, 'previous_all_trades', {})

# Detect changes (new or updated trades)
for trade_key, trade in current_all_trades.items():
    previous_trade = previous_all_trades.get(trade_key)
    
    # New trade OR status changed OR exit data updated
    is_new = previous_trade is None
    status_changed = previous_trade and previous_trade['status'] != trade['status']
    exit_updated = previous_trade and previous_trade.get('exit_time') != trade.get('exit_time')
    
    if is_new or status_changed or exit_updated:
        # Emit trade_update event
        self.session.emit_trade_update(trade)
        
        # Also add to simple stream manager
        simple_session = simple_stream_manager.get_session(self.session_id)
        if simple_session:
            simple_session.add_trade(trade)
        
        # Log
        action = 'NEW' if is_new else 'UPDATED'
        print(f"[Trade Emit] ✅ {action}: {trade['trade_id']} | {trade['status']} | PnL: {trade.get('pnl', 'N/A')}")

# Update tracking
self.previous_all_trades = current_all_trades
```

### New Method: `_build_trades_from_events`
```python
def _build_trades_from_events(self, node_events_history):
    """
    Build ALL trades (open, partial, closed) from node events.
    Similar to _extract_trades_from_events but includes OPEN positions.
    """
    from collections import defaultdict
    from datetime import datetime
    
    # Index entry and exit events
    position_index = defaultdict(lambda: {
        'entry_event': None,
        'exit_events': []
    })
    
    for exec_id, event in node_events_history.items():
        node_type = event.get('node_type', '')
        
        if node_type == 'EntryNode':
            position = event.get('position', {})
            position_id = position.get('position_id')
            re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
            
            if position_id:
                key = (position_id, re_entry_num)
                position_index[key]['entry_event'] = event
        
        elif node_type in ['ExitNode', 'SquareOffNode']:
            position = event.get('position', {})
            position_id = position.get('position_id')
            re_entry_num = position.get('re_entry_num', 0)
            
            if position_id:
                key = (position_id, re_entry_num)
                timestamp = event.get('timestamp')
                position_index[key]['exit_events'].append((timestamp, exec_id, event))
    
    # Build trades list
    trades = []
    
    for (position_id, re_entry_num), data in position_index.items():
        entry_event = data['entry_event']
        exit_events = sorted(data['exit_events'], key=lambda x: x[0])
        
        if not entry_event:
            continue
        
        # Extract entry data
        position = entry_event.get('position', {})
        action = entry_event.get('action', {})
        
        symbol = action.get('symbol', position.get('symbol', ''))
        side = action.get('side', position.get('side', '')).upper()
        quantity = int(action.get('quantity', 1))
        entry_price = float(action.get('price', 0))
        entry_time = entry_event.get('timestamp', '')
        
        # Get lot_size (if options)
        lot_size = self._get_lot_size(symbol)
        effective_quantity = quantity * lot_size if lot_size > 1 else quantity
        
        # Determine status and exit data
        if len(exit_events) == 0:
            # OPEN position
            trade = {
                'trade_id': f"{position_id}" if re_entry_num == 0 else f"{position_id}-r{re_entry_num}",
                'position_id': position_id,
                're_entry_num': re_entry_num,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'lot_size': lot_size,
                'effective_quantity': effective_quantity,
                'entry_price': f"{entry_price:.2f}",
                'entry_time': entry_time,
                'exit_price': None,
                'exit_time': None,
                'pnl': "0.00",
                'pnl_percent': "0.00",
                'status': 'OPEN',
                'entry_flow_ids': self._build_flow_ids(entry_event, node_events_history),
                'exit_flow_ids': [],
                'entry_trigger': entry_event.get('node_name', '')
            }
            trades.append(trade)
        
        else:
            # PARTIAL or CLOSED
            # Calculate from exit events
            total_pnl = 0
            qty_closed = 0
            partial_exits_list = []
            last_exit_price = None
            last_exit_time = None
            exit_reason = None
            
            for timestamp, exec_id, exit_event in exit_events:
                node_type = exit_event.get('node_type')
                
                if node_type == 'ExitNode':
                    exit_result = exit_event.get('exit_result', {})
                    exit_price_val = float(exit_result.get('exit_price', 0))
                    pnl_val = float(exit_result.get('pnl', 0))
                    
                    total_pnl += pnl_val
                    qty_closed += 1  # Assume 1 qty per exit (adjust if needed)
                    last_exit_price = exit_price_val
                    last_exit_time = exit_event.get('timestamp', '')
                    exit_reason = exit_event.get('node_name', '')
                    
                    partial_exits_list.append({
                        'execution_id': exec_id,
                        'qty_closed': 1,
                        'exit_price': f"{exit_price_val:.2f}",
                        'pnl': f"{pnl_val:.2f}",
                        'exit_flow_ids': self._build_flow_ids(exit_event, node_events_history)
                    })
            
            qty_remaining = quantity - qty_closed
            status = 'CLOSED' if qty_remaining == 0 else 'PARTIAL'
            
            # Calculate unrealized P&L for remaining qty
            unrealized_pnl = 0
            if qty_remaining > 0:
                current_ltp = self._get_current_ltp(symbol)
                if current_ltp:
                    unrealized_pnl = (entry_price - current_ltp) * qty_remaining * lot_size if side == 'SELL' else (current_ltp - entry_price) * qty_remaining * lot_size
            
            pnl_percent = (total_pnl / (entry_price * effective_quantity)) * 100 if entry_price > 0 else 0
            
            trade = {
                'trade_id': f"{position_id}" if re_entry_num == 0 else f"{position_id}-r{re_entry_num}",
                'position_id': position_id,
                're_entry_num': re_entry_num,
                'symbol': symbol,
                'side': side,
                'quantity_entered': effective_quantity,
                'quantity_closed': qty_closed * lot_size,
                'quantity_remaining': qty_remaining * lot_size,
                'entry_price': f"{entry_price:.2f}",
                'entry_time': entry_time,
                'exit_price': f"{last_exit_price:.2f}" if last_exit_price else None,
                'exit_time': last_exit_time,
                'pnl': f"{total_pnl:.2f}",
                'pnl_percent': f"{pnl_percent:.2f}",
                'realized_pnl': f"{total_pnl:.2f}",
                'unrealized_pnl': f"{unrealized_pnl:.2f}",
                'status': status,
                'entry_flow_ids': self._build_flow_ids(entry_event, node_events_history),
                'exit_flow_ids': self._build_flow_ids(exit_events[-1][2], node_events_history) if exit_events else [],
                'entry_trigger': entry_event.get('node_name', ''),
                'exit_reason': exit_reason,
                'partial_exits': partial_exits_list if status == 'PARTIAL' else None
            }
            trades.append(trade)
    
    return trades

def _get_lot_size(self, symbol):
    """Get lot size for options symbols."""
    # For options: NIFTY has lot_size 50, BANKNIFTY has 15, etc.
    if ':OPT:' in symbol or ':FUT:' in symbol:
        if 'NIFTY' in symbol and 'BANK' not in symbol:
            return 50
        elif 'BANKNIFTY' in symbol:
            return 15
        elif 'FINNIFTY' in symbol:
            return 40
    return 1  # Equity

def _get_current_ltp(self, symbol):
    """Get current LTP from context."""
    try:
        strategy_state = next(iter(self.centralized_processor.strategy_manager.active_strategies.values()), None)
        if strategy_state:
            context = strategy_state.get('context', {})
            ltp_store = context.get('ltp_store', {})
            symbol_data = ltp_store.get(symbol, {})
            return float(symbol_data.get('ltp', 0)) if isinstance(symbol_data, dict) else 0
    except:
        return 0

def _build_flow_ids(self, event, events_history):
    """Build flow IDs by traversing parent chain."""
    flow_ids = []
    current_exec_id = event.get('execution_id')
    visited = set()
    
    while current_exec_id and current_exec_id not in visited:
        flow_ids.insert(0, current_exec_id)
        visited.add(current_exec_id)
        current_event = events_history.get(current_exec_id, {})
        current_exec_id = current_event.get('parent_execution_id')
    
    return flow_ids
```

---

## Testing Phases (Incremental)

### Phase 1: Test Entry Detection
**Run backtest and verify:**
- [ ] Console shows "NEW: entry-2-pos1 | OPEN"
- [ ] SSE emits `trade_update` with status='OPEN'
- [ ] Entry flow_ids populated
- [ ] Exit fields are null

**Expected Console:**
```
[Trade Emit] ✅ NEW: entry-2-pos1 | OPEN | PnL: 0.00
```

### Phase 2: Test Partial Exit Detection
**If strategy supports partial exits, verify:**
- [ ] Console shows "UPDATED: entry-2-pos1 | PARTIAL"
- [ ] SSE emits `trade_update` with status='PARTIAL'
- [ ] quantity_closed < quantity_entered
- [ ] partial_exits array populated
- [ ] Both realized_pnl and unrealized_pnl present

**Expected Console:**
```
[Trade Emit] ✅ UPDATED: entry-2-pos1 | PARTIAL | PnL: -460.00
```

### Phase 3: Test Full Close Detection
**Run backtest and verify:**
- [ ] Console shows "UPDATED: entry-2-pos1 | CLOSED"
- [ ] SSE emits `trade_update` with status='CLOSED'
- [ ] quantity_remaining = 0
- [ ] Exit flow_ids populated
- [ ] Matches existing behavior

**Expected Console:**
```
[Trade Emit] ✅ UPDATED: entry-2-pos1 | CLOSED | PnL: -78.45
```

### Phase 4: Test Tick Updates (No Changes)
**Verify tick updates still have full data:**
- [ ] positions array present
- [ ] pnl_summary present
- [ ] ltp_store present
- [ ] candle_data present
- [ ] active_nodes present

### Phase 5: UI Integration
**Create position store in UI:**
- [ ] Map<string, Trade> initialized
- [ ] Handle trade_update events (open/partial/closed)
- [ ] Recalculate unrealized P&L on ltp updates
- [ ] Display position table
- [ ] Display dashboard P&L cards

---

## Summary

### Single Code Change
- Add `_build_trades_from_events()` method (includes OPEN positions)
- Modify trade emission logic to detect NEW or UPDATED trades
- Emit `trade_update` on any status change (OPEN, PARTIAL, CLOSED)

### No Breaking Changes
- ✅ Keep existing `trade_update` event name
- ✅ Keep existing `node_event` (eventHistory)
- ✅ Keep full diagnostics in `tick_update`
- ✅ Backward compatible (new fields ignored if not used)

### Testing Strategy
- Same code, test 5 scenarios incrementally
- Verify each scenario before moving to next
- Console logs + SSE events inspection

---

## Ready to Implement?

This is now a **single code change** with **incremental testing**. Should I proceed with implementation?
