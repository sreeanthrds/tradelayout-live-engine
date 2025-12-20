# API Implementation Summary

## ✅ Overview

The Backtest API is **fully implemented and ready** for UI integration. The API now automatically generates `trades_daily.json` and `diagnostics_export.json` files after each backtest run for reference and debugging.

---

## 🚀 Quick Start

### 1. Start the API Server

```bash
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine
python backtest_api_server.py
```

**Server Info:**
- URL: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 2. Run a Backtest

```bash
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "mode": "backtesting",
    "include_diagnostics": true
  }'
```

### 3. Get Generated Files

```bash
# Get trades_daily.json
curl "http://localhost:8000/api/v1/backtest/files/trades_daily"

# Get diagnostics_export.json
curl "http://localhost:8000/api/v1/backtest/files/diagnostics_export"
```

---

## 📋 Key Changes Implemented

### 1. **Automatic UI Files Generation**

After each backtest run, the API now automatically generates:
- ✅ `trades_daily.json` - Trade list with flow IDs
- ✅ `diagnostics_export.json` - Full execution diagnostics

**Implementation:**
- Created `generate_ui_files_from_diagnostics()` helper function
- Calls `view_diagnostics.py`, `extract_trades_simplified.py`, and `format_diagnostics_prices.py`
- Runs after both regular and streaming backtest endpoints

**Files Modified:**
- `/backtest_api_server.py` (lines 30-82)

### 2. **Removed `current_state` from Backtest Diagnostics**

**What Changed:**
- `current_state` is NO LONGER included in `diagnostics_export.json` for backtesting
- Only `events_history` is included

**Why:**
- `current_state` is only relevant for **live simulation** (real-time state tracking)
- For backtesting, we only need historical events for UI diagnostics
- Reduces file size and improves clarity

**Files Modified:**
- `/show_dashboard_data.py` (lines 195-209)

**Before:**
```json
{
  "events_history": {...},
  "current_state": {...}  // ❌ Not needed for backtesting
}
```

**After:**
```json
{
  "events_history": {...}  // ✅ Only what's needed
}
```

### 3. **Enhanced Diagnostic Condition Format** ⭐ NEW

**Simplified Condition Structure:**
All signal nodes (Entry, Exit, Re-Entry) now use a clean, UI-friendly format:

```json
{
  "raw": "Previous[TI.1m.rsi(14,close)] > 70",
  "evaluated": "73.49 > 70.00",
  "result": true,
  "result_icon": "✓"
}
```

**Key Changes:**
- ✅ Separate `raw` (expression formula) and `evaluated` (computed values)
- ✅ Time values formatted as HH:MM:SS (not Unix timestamps)
- ✅ Price values formatted to 2 decimals
- ✅ Backward compatible (still includes `condition_text` for legacy)

**Files Modified:**
- `/src/core/condition_evaluator_v2.py` (lines 480-500, 827-846, 887-927)

**Example from diagnostics_export.json:**
```json
"evaluated_conditions": {
  "conditions_evaluated": [
    {
      "raw": "Current Time >= 09:17",
      "evaluated": "09:19:00 >= 09:17:00",
      "result": true,
      "result_icon": "✓"
    }
  ]
}
```

### 4. **ReEntrySignalNode Diagnostics** ⭐ NEW

**What Changed:**
ReEntrySignalNode now includes full diagnostic data just like EntrySignalNode and ExitSignalNode.

**New Fields:**
- ✅ `evaluated_conditions` - Conditions with raw/evaluated format
- ✅ `re_entry_metadata` - Re-entry attempt tracking
- ✅ `condition_type` - Always set to "re_entry_conditions"
- ✅ `node_variables` - Calculated variables for re-entry

**Files Modified:**
- `/strategy/nodes/re_entry_signal_node.py` (lines 181-196, 296-360)

**Example:**
```json
{
  "node_type": "ReEntrySignalNode",
  "signal_emitted": true,
  "condition_type": "re_entry_conditions",
  "evaluated_conditions": {
    "conditions_evaluated": [
      {
        "raw": "Previous[TI.1m.rsi(14,close)] > 70",
        "evaluated": "73.49 > 70.00",
        "result": true,
        "result_icon": "✓"
      }
    ]
  },
  "re_entry_metadata": {
    "current_re_entry_num": 1,
    "max_re_entries": 10,
    "remaining_attempts": 9
  }
}
```

### 5. **New API Endpoints**

Added two new endpoints to serve the generated files:

#### GET `/api/v1/backtest/files/trades_daily`
Returns the generated `trades_daily.json` file.

**Response:**
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30"
  },
  "trades": [...]
}
```

#### GET `/api/v1/backtest/files/diagnostics_export`
Returns the generated `diagnostics_export.json` file.

**Response:**
```json
{
  "events_history": {
    "exec_id_1": {...},
    "exec_id_2": {...}
  }
}
```

**Files Modified:**
- `/backtest_api_server.py` (lines 636-674)

---

## 🎯 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/api/v1/backtest` | POST | Run backtest (with UI files generation) |
| `/api/v1/backtest/stream` | POST | Stream backtest results (with UI files generation) |
| `/api/v1/backtest/status` | GET | Get service status |
| `/api/v1/backtest/files/trades_daily` | GET | **NEW**: Get trades_daily.json |
| `/api/v1/backtest/files/diagnostics_export` | GET | **NEW**: Get diagnostics_export.json |
| `/api/v1/simulation/start` | POST | Start live simulation (uses current_state) |
| `/api/v1/simulation/{session_id}/state` | GET | Get live simulation state |
| `/api/v1/simulation/{session_id}/stop` | POST | Stop live simulation |

---

## 📊 Response Structure

### Backtest Response

```json
{
  "success": true,
  "data": {
    "strategy_id": "...",
    "date_range": {
      "start": "2024-10-29",
      "end": "2024-10-29"
    },
    "mode": "backtesting",
    "daily_results": [...],
    "overall_summary": {
      "total_positions": 9,
      "total_pnl": -483.30,
      "total_winning_trades": 1,
      "total_losing_trades": 8,
      "overall_win_rate": 11.11
    },
    "metadata": {
      "total_days": 1,
      "diagnostics_included": true,
      "generated_at": "2024-12-10T10:30:00",
      "ui_files_generated": true  // ✅ NEW FIELD
    }
  }
}
```

---

## 🔄 Workflow

### For Backtesting (No current_state needed)

```
1. UI → POST /api/v1/backtest
          ↓
2. API runs backtest
          ↓
3. API generates trades_daily.json ✅
          ↓
4. API generates diagnostics_export.json ✅ (WITHOUT current_state)
          ↓
5. API returns JSON response
          ↓
6. UI receives data immediately
          ↓
7. UI can optionally fetch:
   - GET /api/v1/backtest/files/trades_daily
   - GET /api/v1/backtest/files/diagnostics_export
```

### For Live Simulation (current_state IS needed)

```
1. UI → POST /api/v1/simulation/start
          ↓
2. API starts live simulation session
          ↓
3. UI polls GET /api/v1/simulation/{session_id}/state every 1 second
          ↓
4. API returns current_state with:
   - Active nodes
   - Latest candles
   - LTP store
   - Open positions
   - Real-time P&L
```

---

## 🧪 Testing

### Test Script
```bash
python test_api_with_ui_files.py
```

This script tests:
1. ✅ API status check
2. ✅ Run backtest via API
3. ✅ Retrieve trades_daily.json
4. ✅ Retrieve diagnostics_export.json
5. ✅ Verify current_state is NOT included

---

## 📁 Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `backtest_api_server.py` | Added UI files generation + new endpoints | 30-82, 386-388, 589-590, 636-674 |
| `show_dashboard_data.py` | Removed current_state from backtesting | 195-209 |
| `src/core/condition_evaluator_v2.py` | **NEW**: Added raw/evaluated format + time formatting | 480-500, 827-846, 887-927 |
| `strategy/nodes/re_entry_signal_node.py` | **NEW**: Added diagnostic data capture | 181-196, 296-360 |
| `test_api_with_ui_files.py` | **NEW**: Test script for API with UI files | All |
| `API_IMPLEMENTATION_SUMMARY.md` | **NEW**: This documentation | All |

---

## 💡 Key Design Decisions

### 1. **Why Generate Files Even for API?**
- **For Reference**: Developers can inspect files directly
- **For Debugging**: Easier to debug issues with static files
- **For Compatibility**: Existing tools/scripts can still work
- **Minimal Overhead**: File generation is fast (~1-2 seconds)

### 2. **Why Remove current_state from Backtesting?**
- **Not Needed**: Backtests are historical, no real-time state
- **File Size**: Reduces diagnostics_export.json size
- **Clarity**: Separates concerns (backtesting vs. live simulation)
- **Performance**: Faster JSON parsing in UI

### 3. **Why Keep current_state for Live Simulation?**
- **Real-Time Tracking**: UI needs to show live state
- **Active Nodes**: Show which nodes are currently executing
- **Current Candles**: Display latest market data
- **Open Positions**: Track unrealized P&L in real-time

---

## 🎨 UI Integration Guide

### Option 1: Direct API Response (Recommended)
```javascript
// Get data directly from API response
const response = await fetch('https://635ca493f8ef.ngrok-free.app/api/v1/backtest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    strategy_id: '5708424d-5962-4629-978c-05b3a174e104',
    start_date: '2024-10-29',
    mode: 'backtesting',
    include_diagnostics: true
  })
});

const data = await response.json();
// Use data.data.daily_results, data.data.overall_summary
```

### Rendering Conditions in UI
```typescript
// Render conditions with the new format
const Condition = ({ condition }) => (
  <div className="condition">
    <span className="raw">{condition.raw}</span>
    <span className="evaluated">[{condition.evaluated}]</span>
    <span className="icon">{condition.result_icon}</span>
  </div>
);

// Example output:
// Current Time >= 09:17 [09:19:00 >= 09:17:00] ✓
```

### Option 2: Fetch Generated Files
```javascript
// Get pre-generated files for caching/offline use
const tradesData = await fetch('/api/v1/backtest/files/trades_daily');
const diagnosticsData = await fetch('/api/v1/backtest/files/diagnostics_export');
```

### Option 3: Hybrid Approach
```javascript
// 1. Get quick summary from API
const quickData = await fetch('/api/v1/backtest', {...});

// 2. Lazy load full diagnostics when user clicks trade
const diagnostics = await fetch('/api/v1/backtest/files/diagnostics_export');
```

---

## ✅ Status

| Feature | Status | Notes |
|---------|--------|-------|
| API Server | ✅ Ready | Both regular and streaming endpoints |
| UI Files Generation | ✅ Ready | Automatic after each backtest |
| trades_daily.json endpoint | ✅ Ready | GET /api/v1/backtest/files/trades_daily |
| diagnostics_export.json endpoint | ✅ Ready | GET /api/v1/backtest/files/diagnostics_export |
| Remove current_state | ✅ Done | Only for backtesting |
| Keep current_state for live sim | ✅ Done | For real-time state tracking |
| Test script | ✅ Ready | test_api_with_ui_files.py |
| Documentation | ✅ Done | API_DOCUMENTATION.md, API_QUICK_REFERENCE.md, this file |
| CORS enabled | ✅ Ready | All origins allowed |
| GZip compression | ✅ Ready | Automatic compression |

---

## 🚦 Next Steps

1. **Start the API server**: `python backtest_api_server.py`
2. **Run the test script**: `python test_api_with_ui_files.py`
3. **Integrate with UI**: Use the endpoints in your frontend
4. **Test with your strategy**: Update strategy_id in requests
5. **Deploy**: When ready, deploy to production

---

## 📞 Support

For questions or issues:
- Check API docs: `http://localhost:8000/docs`
- View test script: `test_api_with_ui_files.py`
- Refer to: `API_DOCUMENTATION.md`, `API_QUICK_REFERENCE.md`

---

**✅ READY FOR UI INTEGRATION!**
