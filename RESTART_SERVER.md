# 🔄 CRITICAL: RESTART API SERVER

## ⚠️ Your server is still running with OLD code!

The ClickHouse Cloud URL is still being used because the server process hasn't been restarted.

---

## 🛑 Step 1: Stop the Current Server

### Find the running process:
```bash
# Find process using port 8000
lsof -i :8000
```

You'll see something like:
```
COMMAND   PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python  12345 user    7u  IPv4 0x1234567890      0t0  TCP *:8000 (LISTEN)
```

### Kill the process:
```bash
# Replace 12345 with your actual PID
kill -9 12345

# OR kill all Python processes on port 8000
lsof -ti:8000 | xargs kill -9
```

---

## 🚀 Step 2: Start the Server with New Code

```bash
cd /Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine
python backtest_api_server.py
```

### Expected Output (with warnings, not errors):
```
INFO:     Started server process [XXXXX]
⚠️  ClickHouse connection failed: Connection refused
⚠️  Running in backtest-only mode (no live ClickHouse queries)
⚠️  Skipping option loader (no ClickHouse connection)
⚠️  ExpiryDetector: Cannot connect to ClickHouse
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ These are **WARNINGS**, not errors! The server will work.

---

## ✅ Step 3: Test the API

### Test with curl:
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

### Or test with Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/backtest",
    json={
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "mode": "backtesting",
        "include_diagnostics": True
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ SUCCESS!")
    print(f"P&L: {response.json()['data']['overall_summary']['total_pnl']}")
else:
    print(f"❌ Error: {response.text}")
```

---

## 🔍 What Changed

| File | Change |
|------|--------|
| `src/config/clickhouse_config.py` | HOST changed to 'localhost' |
| `src/backtesting/data_manager.py` | Made ClickHouse optional (try-catch) |
| `src/backtesting/expiry_detector.py` | Made ClickHouse optional (try-catch) |

---

## 💡 Why This Happened

Python caches imported modules. When you:
1. Start the server → It loads `clickhouse_config.py` with OLD code
2. Edit the files → Server still uses cached version
3. Try to run backtest → Still uses ClickHouse Cloud URL

**Solution:** Restart the server process!

---

## 🎯 Alternative: Use Uvicorn with Auto-Reload

For development, start server with auto-reload:
```bash
uvicorn backtest_api_server:app --reload --host 0.0.0.0 --port 8000
```

This automatically restarts when files change!

---

**RESTART THE SERVER NOW!** 🔄
