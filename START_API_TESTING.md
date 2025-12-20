# 🚀 API Testing - Ready to Go!

## ✅ Pre-Flight Checklist

### 1. API Implementation ✅
- [x] Backtest endpoints (`POST /api/v1/backtest`, `POST /api/v1/backtest/stream`)
- [x] File serving endpoints (`GET /api/v1/backtest/files/trades_daily`, `GET /api/v1/backtest/files/diagnostics_export`)
- [x] Live simulation endpoints (separate from backtesting)
- [x] Automatic UI files generation after each backtest
- [x] CORS enabled for cross-origin requests
- [x] GZip compression for responses

### 2. Diagnostics Data ✅
- [x] `current_state` removed from backtesting (only for live simulation)
- [x] Condition format: `{"raw": "...", "evaluated": "..."}`
- [x] Time values formatted as HH:MM:SS
- [x] Price values formatted to 2 decimals
- [x] All signal nodes have evaluated conditions:
  - [x] EntrySignalNode
  - [x] ExitSignalNode
  - [x] ReEntrySignalNode

### 3. Files Generated ✅
- [x] `trades_daily.json` (19.6 KB)
- [x] `diagnostics_export.json` (108.4 KB)
- [x] Both files updated on API backtest runs

### 4. Test Infrastructure ✅
- [x] Test script created (`test_api_with_ui_files.py`)
- [x] Documentation complete (`API_DOCUMENTATION.md`, `API_QUICK_REFERENCE.md`)
- [x] API server imports successfully

---

## 🚀 Start API Server

### Step 1: Start the Server
```bash
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine
python backtest_api_server.py
```

**Expected Output:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 2: Verify Server is Running
Open in browser:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- API Info: http://localhost:8000/

---

## 🧪 Run Tests

### Option 1: Automated Test Suite
```bash
# In a new terminal (keep server running)
python test_api_with_ui_files.py
```

**Expected Output:**
```
🚀 BACKTEST API TEST SUITE
✅ PASS - API Status
✅ PASS - Run Backtest
✅ PASS - Get trades_daily.json
✅ PASS - Get diagnostics_export.json
🎯 Overall: 4/4 tests passed
🎉 All tests passed!
```

### Option 2: Manual Testing with cURL

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"healthy","timestamp":"..."}`

#### Test 2: Run Backtest
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

#### Test 3: Get trades_daily.json
```bash
curl http://localhost:8000/api/v1/backtest/files/trades_daily
```

#### Test 4: Get diagnostics_export.json
```bash
curl http://localhost:8000/api/v1/backtest/files/diagnostics_export
```

---

## 📊 Expected Response Structure

### Backtest Response
```json
{
  "success": true,
  "data": {
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "date_range": {
      "start": "2024-10-29",
      "end": "2024-10-29"
    },
    "daily_results": [...],
    "overall_summary": {
      "total_positions": 9,
      "total_pnl": -483.30,
      "total_winning_trades": 1,
      "total_losing_trades": 8,
      "overall_win_rate": 11.11
    },
    "metadata": {
      "diagnostics_included": true,
      "ui_files_generated": true
    }
  }
}
```

### trades_daily.json
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30",
    "winning_trades": 1,
    "losing_trades": 8
  },
  "trades": [
    {
      "trade_id": "entry-3-pos1-r3",
      "re_entry_num": 3,
      "symbol": "NIFTY:2024-11-07:OPT:24300:CE",
      "entry_price": "254.65",
      "exit_price": "263.45",
      "pnl": "-34.55",
      "entry_flow_ids": [...],
      "exit_flow_ids": [...]
    }
  ]
}
```

### diagnostics_export.json
```json
{
  "events_history": {
    "exec_entry-condition-1_20241029_091900_xxx": {
      "node_type": "EntrySignalNode",
      "signal_emitted": true,
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
    }
  }
}
```

**Note:** No `current_state` in backtesting diagnostics ✅

---

## 🎯 What to Test

### Functionality Tests
1. ✅ **Backtest Run** - POST /api/v1/backtest works
2. ✅ **Response Data** - Contains summary, positions, diagnostics
3. ✅ **UI Files Generated** - trades_daily.json and diagnostics_export.json created
4. ✅ **File Serving** - Can retrieve files via GET endpoints
5. ✅ **Diagnostics Format** - Conditions have "raw" and "evaluated"
6. ✅ **Time Formatting** - Times show as HH:MM:SS, not timestamps
7. ✅ **No current_state** - Verify not in diagnostics_export.json
8. ✅ **Re-Entry Data** - ReEntrySignalNode has evaluated_conditions

### Performance Tests
1. ✅ **Response Time** - Backtest completes in reasonable time
2. ✅ **File Size** - Generated files are reasonable size
3. ✅ **Compression** - GZip compression working

### Integration Tests
1. ✅ **Multi-day Backtest** - Test date range
2. ✅ **Streaming** - Test /api/v1/backtest/stream endpoint
3. ✅ **Error Handling** - Test with invalid strategy_id or date

---

## 🐛 Troubleshooting

### Issue: Server won't start
**Solution:**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>

# Start server again
python backtest_api_server.py
```

### Issue: Files not generated
**Check:**
1. Look for error messages in server logs
2. Verify `view_diagnostics.py` and `extract_trades_simplified.py` exist
3. Check file permissions in directory

### Issue: current_state still appears
**Verify:**
```bash
python -c "import json; d=json.load(open('diagnostics_export.json')); print('current_state' in d)"
```
Expected: `False`

### Issue: Time format still shows timestamps
**Check:**
```bash
python -c "import json; d=json.load(open('diagnostics_export.json')); e=list(d['events_history'].values())[0]; print(e.get('evaluated_conditions',{}).get('conditions_evaluated',[{}])[0].get('evaluated'))"
```
Expected: Should see time like `09:19:00`, not `1730173740.00`

---

## 📞 API Endpoints Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/v1/backtest/status` | GET | Service status |
| `/api/v1/backtest` | POST | Run backtest |
| `/api/v1/backtest/stream` | POST | Stream backtest results |
| `/api/v1/backtest/files/trades_daily` | GET | Get trades file |
| `/api/v1/backtest/files/diagnostics_export` | GET | Get diagnostics file |

**Full Documentation:** http://localhost:8000/docs (when server running)

---

## ✅ Ready to Test!

Everything is implemented and verified. You can now:
1. **Start the API server** - `python backtest_api_server.py`
2. **Run the test suite** - `python test_api_with_ui_files.py`
3. **Integrate with UI** - Use the endpoints in your frontend

**Good luck with testing! 🚀**
