# Phased Implementation Plan: Trade Events on Entry + Exit

## Goal
Emit `trade_update` events on BOTH entry and exit (currently only on exit)

---

## Phase 1: Track Open Positions (Backend Foundation)

### **Change:**
Add tracking for newly opened positions (similar to existing closed tracking)

### **File:** `live_backtest_runner.py`

### **What to Add:**
```python
# In __init__ method (around line 100)
self.previous_open_positions = set()  # Track open positions

# In _feed_tick_update_to_sse (around line 550)
# After building all_positions, add:

# Track newly opened positions
current_open_positions = {(p['position_id'], p['re_entry_num']) 
                          for p in all_positions if p['status'] == 'OPEN'}
newly_opened = current_open_positions - self.previous_open_positions

# Debug logging
if len(newly_opened) > 0:
    print(f"\n[Position Tracking] Detected {len(newly_opened)} newly opened positions")
    for pos_id, re_entry in newly_opened:
        print(f"  - {pos_id} (re_entry: {re_entry})")

# Update tracking (at the end)
self.previous_open_positions = current_open_positions
```

### **Test:**
1. Run backtest
2. Check console output for "newly opened positions" messages
3. Should see debug prints when EntryNode executes

### **Expected Output:**
```
[Position Tracking] Detected 1 newly opened positions
  - entry-2-pos1 (re_entry: 0)
```

### **Verification:**
- ✅ No errors
- ✅ Debug prints appear on entry
- ✅ Existing closed trade events still work
- ✅ No UI changes needed

---

## Phase 2: Build Trade Payload for Open Positions

### **Change:**
Create trade event payload for newly opened positions (don't emit yet, just print)

### **File:** `live_backtest_runner.py`

### **What to Add:**
```python
# In _feed_tick_update_to_sse, after newly_opened detection:

# Build trade events for newly opened positions (DEBUG ONLY)
for pos_key in newly_opened:
    pos_id, re_entry = pos_key
    
    # Find the position in all_positions
    for pos in all_positions:
        if pos['position_id'] == pos_id and pos['re_entry_num'] == re_entry:
            # Build trade event payload
            trade_event = {
                'trade_id': f"{pos_id}" if re_entry == 0 else f"{pos_id}-r{re_entry}",
                'position_id': pos_id,
                're_entry_num': re_entry,
                'symbol': pos['symbol'],
                'side': pos['side'],
                'quantity': pos['quantity'],
                'entry_price': pos['entry_price'],
                'entry_time': pos['entry_time'],
                'exit_price': None,
                'exit_time': None,
                'pnl': '0.00',
                'status': 'OPEN',
                'entry_flow_ids': pos.get('entry_flow_ids', []),
                'exit_flow_ids': [],
                'entry_trigger': pos.get('entry_trigger', '')
            }
            
            # DEBUG: Print payload (don't emit yet)
            print(f"\n[Trade Event Payload - OPEN]")
            print(f"  trade_id: {trade_event['trade_id']}")
            print(f"  symbol: {trade_event['symbol']}")
            print(f"  entry_price: {trade_event['entry_price']}")
            print(f"  status: {trade_event['status']}")
            break
```

### **Test:**
1. Run backtest
2. Check console for trade payload prints
3. Verify all fields are correct

### **Expected Output:**
```
[Trade Event Payload - OPEN]
  trade_id: entry-2-pos1
  symbol: NIFTY:2024-11-07:OPT:24250:PE
  entry_price: 181.60
  status: OPEN
```

### **Verification:**
- ✅ Payload structure matches closed trades
- ✅ status = 'OPEN'
- ✅ exit_price = None
- ✅ pnl = '0.00'
- ✅ Still no emit, just debug
- ✅ No UI changes needed

---

## Phase 3: Add Status Field to Closed Trades

### **Change:**
Add `status: 'CLOSED'` to existing closed trade events (for consistency)

### **File:** `live_backtest_runner.py`

### **What to Change:**
```python
# In _extract_trades_from_events method (around line 1015)
# Find where we build the trade object for closed positions:

trade = {
    'trade_id': trade_id,
    'position_id': position_id,
    're_entry_num': re_entry_num,
    'symbol': symbol,
    'side': side,
    'quantity': entry_qty,
    'entry_price': f"{entry_price:.2f}",
    'entry_time': entry_time,
    'exit_price': f"{exit_price:.2f}" if exit_price else None,
    'exit_time': exit_time,
    'pnl': f"{trade_pnl:.2f}",
    'pnl_percent': f"{pnl_percent:.2f}",
    'duration_minutes': duration_minutes,
    'status': status,  # Already exists
    'entry_trigger': entry_event.get('node_name', ''),
    'exit_reason': exit_reason
}

# Change line ~1006:
status = 'CLOSED' if exit_price else 'OPEN'
```

### **Test:**
1. Run backtest
2. Check existing closed trade events
3. Verify `status: 'CLOSED'` field appears

### **Expected Output:**
```
[Trade Emit] ✅ Emitted: entry-2-pos1 | NIFTY:... | PnL: -78.45 | Re-entry: 0
  status: CLOSED  ← Should see this in logs
```

### **Verification:**
- ✅ Closed trades have `status: 'CLOSED'`
- ✅ Existing UI still works (new field ignored if not used)
- ✅ No breaking changes
- ✅ Backward compatible

---

## Phase 4: Emit Trade Events for Open Positions

### **Change:**
Actually emit the trade_update events for newly opened positions

### **File:** `live_backtest_runner.py`

### **What to Change:**
```python
# In _feed_tick_update_to_sse, replace Phase 2 debug prints with actual emit:

# Emit trade events for newly opened positions
for pos_key in newly_opened:
    pos_id, re_entry = pos_key
    
    # Find the position in all_positions
    for pos in all_positions:
        if pos['position_id'] == pos_id and pos['re_entry_num'] == re_entry:
            # Build trade event payload
            trade_event = {
                'trade_id': f"{pos_id}" if re_entry == 0 else f"{pos_id}-r{re_entry}",
                'position_id': pos_id,
                're_entry_num': re_entry,
                'symbol': pos['symbol'],
                'side': pos['side'],
                'quantity': pos['quantity'],
                'entry_price': pos['entry_price'],
                'entry_time': pos['entry_time'],
                'exit_price': None,
                'exit_time': None,
                'pnl': '0.00',
                'status': 'OPEN',
                'entry_flow_ids': pos.get('entry_flow_ids', []),
                'exit_flow_ids': [],
                'entry_trigger': pos.get('entry_trigger', '')
            }
            
            # EMIT the event (NEW!)
            self.session.emit_trade_update(trade_event)
            
            # Also add to simple stream manager
            simple_session = simple_stream_manager.get_session(self.session_id)
            if simple_session:
                simple_session.add_trade(trade_event)
            
            print(f"[Trade Emit] ✅ Emitted OPEN: {trade_event['trade_id']} | {trade_event['symbol']} | Entry: {trade_event['entry_price']}")
            break
```

### **Test:**
1. Run backtest
2. Check SSE stream for trade_update events
3. Should see events on BOTH entry and exit

### **Expected Output:**
```
[Trade Emit] ✅ Emitted OPEN: entry-2-pos1 | NIFTY:... | Entry: 181.60
... (time passes) ...
[Trade Emit] ✅ Emitted: entry-2-pos1 | NIFTY:... | PnL: -78.45 | Re-entry: 0
```

### **Verification:**
- ✅ Trade events emitted on entry
- ✅ Trade events still emitted on exit
- ✅ Both have correct status field
- ✅ SSE stream works
- ✅ Ready for UI integration

---

## Phase 5: UI Integration (Optional - If You Want)

### **Change:**
Update UI to handle open positions separately

### **File:** `useSSELiveData.ts` (or wherever you handle trade events)

### **What to Add:**
```typescript
// Add state for open positions
const [openPositions, setOpenPositions] = useState<Map<string, Trade>>(new Map());
const [closedTrades, setClosedTrades] = useState<Trade[]>([]);

// Handle trade update events
const handleTradeUpdate = (trade: Trade) => {
  const key = `${trade.position_id}-${trade.re_entry_num}`;
  
  if (trade.status === 'OPEN') {
    // Add to open positions
    setOpenPositions(prev => {
      const updated = new Map(prev);
      updated.set(key, trade);
      return updated;
    });
  } 
  else if (trade.status === 'CLOSED') {
    // Remove from open, add to closed
    setOpenPositions(prev => {
      const updated = new Map(prev);
      updated.delete(key);
      return updated;
    });
    
    setClosedTrades(prev => [...prev, trade]);
  }
};

// Calculate unrealized P&L when LTP updates
const calculateUnrealizedPnL = (position: Trade, currentLTP: number) => {
  const entryPrice = parseFloat(position.entry_price);
  const qty = position.quantity;
  const side = position.side;
  
  return side === 'SELL'
    ? (entryPrice - currentLTP) * qty
    : (currentLTP - entryPrice) * qty;
};
```

### **Test:**
1. Run backtest with UI
2. Check if open positions appear
3. Verify they move to closed trades when exit completes

### **Verification:**
- ✅ Open positions visible in real-time
- ✅ Live P&L updates on LTP change
- ✅ Positions move to closed trades on exit
- ✅ No breaking changes to existing display

---

## Summary of Phases

| Phase | Change | Lines | Test | UI Impact |
|-------|--------|-------|------|-----------|
| **1** | Track open positions | ~15 | Debug prints | None |
| **2** | Build trade payload | ~25 | Payload prints | None |
| **3** | Add status to closed | ~2 | Field appears | None (ignored) |
| **4** | Emit on entry | ~5 | SSE events | None (if UI ignores status) |
| **5** | UI integration | ~40 | Open positions tab | New feature |

---

## Rollback Plan

Each phase is independent. If something breaks:

- **Phase 1 Issue**: Remove tracking code, no impact
- **Phase 2 Issue**: Remove payload building, no impact
- **Phase 3 Issue**: Remove status field, no impact (optional field)
- **Phase 4 Issue**: Comment out emit, falls back to Phase 3
- **Phase 5 Issue**: UI ignores status field, works as before

---

## Testing Checklist (Per Phase)

After each phase:
- [ ] Run backtest successfully
- [ ] Check console logs
- [ ] Verify no errors
- [ ] Confirm expected output
- [ ] Ensure existing functionality works
- [ ] Document any issues

---

## Timeline Estimate

- **Phase 1**: 5 minutes (tracking)
- **Phase 2**: 10 minutes (payload building)
- **Phase 3**: 2 minutes (add field)
- **Phase 4**: 5 minutes (emit events)
- **Phase 5**: 30 minutes (UI - optional)

**Total Backend**: ~20 minutes
**Total with UI**: ~50 minutes

---

## Questions Before Starting:

1. Should I start with Phase 1?
2. After each phase, do you want to test before moving to next?
3. Do you want Phase 5 (UI integration) or just backend (Phases 1-4)?

Let me know and I'll implement phase by phase!
