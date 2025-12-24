# Node Evaluation Analysis: Position at 09:17:01

## Issue Found

**Position timestamp (09:17:01) does NOT match signal timestamp in diagnostics**

### Position Record (from backtest_dashboard_data_2024-10-29.json)
```json
{
  "position_id": "entry-4-pos1",
  "entry_node_id": "entry-4",
  "entry_time": "2024-10-29T09:17:01",
  "entry_timestamp": "09:17:01",
  "symbol": "NIFTY:2024-10-31:OPT:24250:PE",
  "entry_price": 90.35,
  "re_entry_num": 0
}
```

### Diagnostics Files Checked

1. **diagnostics_export.json** (current engine)
   - Date range: 2024-10-29 09:15:00 to 15:25:00
   - Total events: 38
   - **NO events at 09:17:01** ❌

2. **Old diagnostics_export.json** (tradelayout-engine)
   - Date range: 2024-10-29 09:15:00+05:30 to 15:25:00+05:30
   - Total events: 38
   - **NO events at 09:17:01** ❌

### Earliest Entry Signal Found

**Entry Condition Signal at 09:19:00:**

```
Node: entry-condition-1 (EntrySignalNode)
Node Name: "Entry condition - Bullish"
Timestamp: 2024-10-29 09:19:00
Signal Emitted: True
Children: [entry-2]

Conditions Evaluated:
1. Current Time >= 09:17
   → Evaluated: 09:19:00 >= 09:17:00 ✓
   
2. Previous[TI.1m.rsi(14,close)] < 30
   → Evaluated: 26.97 < 30.00 ✓
   
3. TI.underlying_ltp > Previous[TI.1m.High]
   → Evaluated: (value) > (value) ✓

All Conditions Met: True
```

## Problem Analysis

### Possible Causes:

1. **Timestamp Recording Issue:**
   - Position may have been recorded with wrong timestamp
   - Actual entry happened at 09:19:00, recorded as 09:17:01

2. **Missing Diagnostics:**
   - Node events at 09:17:01 were not captured in diagnostics
   - Event logging may have started after 09:15:00

3. **Pre-market Execution:**
   - Entry-4 may have triggered based on conditions checked before market open
   - But diagnostics only capture events from 09:15:00 onwards

4. **Different Strategy Version:**
   - The 09:17:01 entry may be from a different strategy configuration
   - Current strategy diagnostics don't show this entry

## What We Know

**From Position Data:**
- 4 positions total on 2024-10-29
- First position (entry-4): 09:17:01
- Second position (entry-3): 09:19:00
- Third position (entry-4 re-entry): 09:27:09
- Fourth position (entry-3 re-entry): 09:31:02

**From Diagnostics:**
- Earliest signal: 09:19:00 (entry-condition-1 → entry-2)
- NO signals or node events at 09:17:01
- NO events between 09:15:00 and 09:19:00

## Recommendation

**To understand the 09:17:01 entry, we need to:**

1. Check if there's a different diagnostics file with events before 09:19:00
2. Verify the actual strategy configuration used for the old backtest
3. Look for initialization events or pre-market condition checks
4. Compare the current strategy with the one that produced 4 positions

**The key issue is:** We cannot find the node evaluation details for 09:17:01 because no node events were recorded at that timestamp in available diagnostics.
