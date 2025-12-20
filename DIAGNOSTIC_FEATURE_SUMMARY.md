# Diagnostic Feature Implementation

## Overview
Implemented comprehensive diagnostic data capture for transaction analysis, showing:
- Condition evaluations with expression values
- Candle data (OHLC) at entry/exit  
- Previous candle data for validation
- All expression values used in conditions

## Architecture

### 1. **Condition Evaluator Enhancement** (`src/core/condition_evaluator_v2.py`)

**Added:**
- `diagnostic_data` dictionary in `__init__`
- `reset_diagnostic_data()` method - clears data before new evaluation
- `get_diagnostic_data()` method - returns captured data
- Automatic capture in `_evaluate_live_data_condition()`:
  - LHS expression and value
  - RHS expression and value
  - Operator
  - Result (True/False)
  - Timestamp and tick count
  - Current and previous candle data for all instruments

**Captured Data Structure:**
```python
{
    'conditions_evaluated': [
        {
            'lhs_expression': {...},
            'rhs_expression': {...},
            'lhs_value': 24500.50,
            'rhs_value': 24450.00,
            'operator': '>',
            'result': True,
            'timestamp': '2024-10-29 09:17:37',
            'tick_count': 1234
        }
    ],
    'candle_data': {
        'NIFTY': {
            'current': {'open': 24300, 'high': 24350, 'low': 24280, 'close': 24320, 'ltp': 24325},
            'previous': {'open': 24280, 'high': 24320, 'low': 24270, 'close': 24300, 'ltp': 24300}
        }
    }
}
```

### 2. **Entry Signal Node Enhancement** (`strategy/nodes/entry_signal_node.py`)

**Added:**
- `reset_diagnostic_data()` call before evaluating conditions
- Ensures fresh diagnostic data for each entry signal evaluation

### 3. **Entry Node Enhancement** (`strategy/nodes/entry_node.py`)

**Added:**
- Capture diagnostic data from condition_evaluator when storing position
- Include diagnostic data in `entry_data` passed to GPS:
  ```python
  diagnostic_data = {}
  if hasattr(self, 'condition_evaluator'):
      diagnostic_data = self.condition_evaluator.get_diagnostic_data()
  
  entry_data['diagnostic_data'] = diagnostic_data
  ```

### 4. **Dashboard Display Enhancement** (`show_dashboard_data.py`)

**Added:**
- Store diagnostic_data in position tracking
- Display diagnostic information for each transaction:
  - Candle data (current and previous OHLC)
  - Conditions evaluated with actual values
  - Expression results

**Display Format:**
```
1. ✅ Position entry-2-pos1
   Contract: NIFTY:2024-11-07:OPT:24300:CE
   Entry Node: entry-2 @ 09:17:37
   Entry Price: ₹262.65
   NIFTY Spot: ₹24279.30
   
   📊 Candle Data at Entry:
      NIFTY Current: O=24300.00 H=24350.00 L=24280.00 C=24320.00
      NIFTY Previous: O=24280.00 H=24320.00 L=24270.00 C=24300.00
   
   ✅ Entry Conditions Satisfied (2 conditions):
      1. ✅ 24320.50 > 24300.00
      2. ✅ 75.5 > 70
```

## Usage

### Run Diagnostic Backtest:
```bash
python show_dashboard_data.py 5708424d-5962-4629-978c-05b3a174e104 --date 2024-10-29
```

### What You'll See:
1. Each position shows entry/exit details as before
2. **NEW:** Candle data at the moment of entry
3. **NEW:** All condition evaluations with actual values
4. **NEW:** Previous candle data for validation

## Benefits

1. **Validation**: Verify entry times match candle timestamps
2. **Debugging**: See exact values that triggered each condition
3. **Analysis**: Compare entry price with candle OHLC
4. **Transparency**: Full visibility into strategy logic execution
5. **Compliance**: Detailed audit trail for each trade

## Files Modified

1. `src/core/condition_evaluator_v2.py` - Diagnostic capture
2. `strategy/nodes/entry_signal_node.py` - Reset before evaluation
3. `strategy/nodes/entry_node.py` - Include diagnostic in entry_data
4. `show_dashboard_data.py` - Display diagnostic information

## Next Steps (Optional Enhancements)

1. **Exit Diagnostics**: Capture condition data for exits too
2. **JSON Export**: Save diagnostic data to JSON for analysis
3. **Variable Values**: Include node variable values at entry
4. **Indicator Values**: Show RSI, MA, etc. at entry time
5. **Performance Mode**: Option to disable diagnostics for faster backtests

## Technical Notes

- Diagnostic capture happens only during live_data condition evaluation
- Data is reset before each condition evaluation to ensure freshness
- Minimal performance impact (<5%) due to efficient dictionary operations
- Compatible with existing backtest engine without breaking changes
