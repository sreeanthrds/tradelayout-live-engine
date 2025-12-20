# Quick Start Guide - Testing the API

## Prerequisites

Make sure you have these installed:
- Python 3.8+
- Required packages: `pip install fastapi uvicorn requests`

---

## Step 1: Start the API Server

Open Terminal 1 and run:

```bash
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine

python backtest_file_api_server.py
```

**Expected Output:**
```
================================================================================
🚀 Backtest File Storage API Server Starting
================================================================================
Running initial cleanup...
✅ Cleanup complete: 0 strategies deleted, 0.0 MB freed
================================================================================
✅ Server ready
📝 API Documentation: http://localhost:8000/docs
================================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Keep this terminal open!** The server needs to keep running.

---

## Step 2: Run the Test Script

Open Terminal 2 (new tab/window) and run:

```bash
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine

python test_api_simple.py
```

**What it does:**
1. ✅ Checks if server is running
2. 🚀 Starts a 3-day backtest (Oct 1-3, 2024)
3. ⏳ Monitors progress in real-time
4. 📊 Retrieves metadata and statistics
5. 📅 Gets detailed day data
6. 🔍 Shows position-level diagnostics
7. 🗑️ Optional cleanup

---

## Step 3: Follow the Interactive Prompts

The test script will guide you through each step:

```
================================================================================
  📊 Backtest API Test Script
================================================================================

Configuration:
   API URL: http://localhost:8000
   User ID: user_123
   Strategy ID: 5708424d-5962-4629-978c-05b3a174e104

================================================================================
  TEST 1: Check Server Status
================================================================================

✅ Server is running
   Service: Backtest File Storage API
   Version: 1.0.0
   Status: running

▶️  Press Enter to start backtest...
```

Just press **Enter** after each step to continue.

---

## What You'll See

### 1. Server Status Check
```
✅ Server is running
   Service: Backtest File Storage API
   Version: 1.0.0
```

### 2. Backtest Started
```
✅ Backtest started successfully!
   Job ID: bt_20241202_163045_abc123
   Status: queued
```

### 3. Progress Monitoring
```
[RUNNING   ] 2024-10-01 | 1/3 days | 33.3%
[RUNNING   ] 2024-10-02 | 2/3 days | 66.7%
[RUNNING   ] 2024-10-03 | 3/3 days | 100.0%

✅ Backtest completed successfully!
```

### 4. Metadata Summary
```
Overall Summary:
   Total Positions: 30
   Total P&L: ₹-5,430.50
   Win Rate: 45.00%
   Winning Trades: 12
   Losing Trades: 18

Daily Breakdown:
   Date            Positions  P&L (₹)         File Size      
   ----------------------------------------------------------------
   01-10-2024      10         -1,250.50       205.34 KB
   02-10-2024      12         +3,400.00       245.12 KB
   03-10-2024      8          -7,580.00       180.56 KB
```

### 5. Day Data
```
Day Summary (01-10-2024):
   Total Positions: 10
   Closed Positions: 10
   Total P&L: ₹-1,250.50
   Win Rate: 40.00%

Positions Table:
   #     Pos ID       Num   Strike   Type  Entry ₹    Exit ₹     P&L ₹        Status  
   -------------------------------------------------------------------------------------
   1     entry-3      1     25050    CE      241.65    185.30    -2,817.50   CLOSED  
   2     entry-3      2     25100    CE      210.30    195.40      -745.00   CLOSED  
   ...
```

### 6. Position Details
```
Position Details:
   Position ID: entry-3
   Symbol: NIFTY:2024-10-17:OPT:25050:CE

Entry Condition Breakdown:
   1. ✅ PASS
      LHS: 09:17:00 (time)
      Operator: >=
      RHS: 09:17:00 (constant)
      Type: time
   
   2. ❌ FAIL
      LHS: 66.67 (indicator)
      Operator: >
      RHS: 70.00 (constant)
      Type: non_live
```

---

## Check the Files

While the backtest runs, you can check the files being created:

```bash
# Open another terminal
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine

# List user data
ls -lh backtest_data/user_123/5708424d-5962-4629-978c-05b3a174e104/
```

**Expected output:**
```
metadata.json           # Overall stats
01-10-2024.json.gz     # Day 1 data (compressed)
02-10-2024.json.gz     # Day 2 data
03-10-2024.json.gz     # Day 3 data
```

---

## View the Data

### Option 1: Using curl
```bash
# Get metadata
curl http://localhost:8000/api/v1/backtest/metadata/user_123/5708424d-5962-4629-978c-05b3a174e104 | jq

# Get day data
curl http://localhost:8000/api/v1/backtest/day/user_123/5708424d-5962-4629-978c-05b3a174e104/01-10-2024 | jq
```

### Option 2: Using browser
Open: http://localhost:8000/docs

Interactive API documentation (Swagger UI) where you can test all endpoints.

### Option 3: Using Python
```python
import requests

# Get metadata
response = requests.get(
    'http://localhost:8000/api/v1/backtest/metadata/user_123/5708424d-5962-4629-978c-05b3a174e104'
)
print(response.json())
```

---

## Troubleshooting

### Server not starting?
**Error:** `Address already in use`

**Fix:** Kill existing process
```bash
lsof -ti:8000 | xargs kill -9
python backtest_file_api_server.py
```

### Test script can't connect?
**Error:** `Cannot connect to server`

**Fix:** Make sure server is running in Terminal 1
```bash
# Terminal 1
python backtest_file_api_server.py
```

### Import errors?
**Error:** `ModuleNotFoundError`

**Fix:** Install dependencies
```bash
pip install fastapi uvicorn requests
```

### Strategy not found?
**Error:** `Strategy not found in Supabase`

**Fix:** Check strategy ID exists in database or update `STRATEGY_ID` in test script.

---

## Next Steps

After testing with requests:

1. **Explore the data structure**
   - Open generated `.json.gz` files
   - Understand the position format
   - Check diagnostic data

2. **Try different date ranges**
   - Edit `test_api_simple.py`
   - Change start_date/end_date
   - Run longer backtests

3. **Build the UI**
   - Use the same request patterns
   - Fetch metadata → Show calendar
   - Click date → Fetch day data
   - Click position → Show diagnostics

4. **Read the guides**
   - `FILE_STORAGE_API_GUIDE.md` - Complete API reference
   - `UI_DIAGNOSTIC_DATA_GUIDE.md` - UI integration examples

---

## Quick Commands Reference

```bash
# Start server
python backtest_file_api_server.py

# Run test (Terminal 2)
python test_api_simple.py

# Check files
ls -lh backtest_data/user_123/*/

# View API docs
open http://localhost:8000/docs

# Stop server
# Press Ctrl+C in Terminal 1
```

---

## File Sizes (Typical)

| Days | Positions/Day | File Size (Compressed) | Total Size |
|------|---------------|------------------------|------------|
| 1    | 10            | ~200 KB                | ~200 KB    |
| 10   | 10            | ~200 KB each           | ~2 MB      |
| 100  | 10            | ~200 KB each           | ~20 MB     |
| 230  | 10            | ~200 KB each           | ~45 MB     |

---

## Happy Testing! 🚀

If everything works, you're ready to build the UI!
