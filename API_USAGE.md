# TradeLayout Backtest API - Usage Guide

## Overview
FastAPI-based REST API for running backtests and retrieving comprehensive diagnostic data for UI dashboard.

## Features
- ✅ Single day and multi-day backtests
- ✅ Comprehensive JSON with diagnostic text per transaction
- ✅ GZip compression (reduces payload by 70-80%)
- ✅ CORS enabled for cross-origin requests
- ✅ Automatic API documentation (Swagger/OpenAPI)

## Installation

### Requirements
```bash
pip install fastapi uvicorn pydantic
```

### Start the API Server
```bash
python backtest_api_server.py
```

Server will be available at:
- **API Endpoint:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## API Endpoints

### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Backtest API",
  "version": "1.0.0",
  "timestamp": "2024-10-29T10:30:00"
}
```

### 2. Run Backtest (Standard)
```http
POST /api/v1/backtest
Content-Type: application/json
```

**Request Body:**
```json
{
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-10-29",
  "end_date": "2024-10-31",
  "mode": "backtesting",
  "include_diagnostics": true
}
```

**Parameters:**
- `strategy_id` (required): Strategy UUID
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (optional): End date (defaults to start_date if not provided)
- `mode` (optional): "backtesting" (default)
- `include_diagnostics` (optional): Include formatted diagnostic text (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "date_range": {
      "start": "2024-10-29",
      "end": "2024-10-31"
    },
    "mode": "backtesting",
    "daily_results": [
      {
        "date": "2024-10-29",
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "positions": [
          {
            "position_id": "entry-2-pos1",
            "position_number": 1,
            "transaction_number": 1,
            "entry_node_id": "entry-2",
            "exit_node_id": "exit-3",
            "entry_time": "2024-10-29T09:19:00",
            "entry_timestamp": "09:19:00",
            "exit_time": "2024-10-29T10:48:00",
            "exit_timestamp": "10:48:00",
            "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
            "strike": "24250",
            "option_type": "PE",
            "entry_price": 181.60,
            "exit_price": 260.05,
            "quantity": 50,
            "pnl": -78.45,
            "pnl_percentage": -43.20,
            "duration_minutes": 89.0,
            "status": "CLOSED",
            "exit_reason": "exit_condition_met",
            "nifty_spot_at_entry": 24272.20,
            "nifty_spot_at_exit": 24145.00,
            "re_entry_num": 0,
            
            "diagnostic_text": "────────────────────────────────────────────────────────────────────────────────\nPosition #1 | Transaction #1\n...[Full formatted diagnostic text]...",
            
            "diagnostic_data": {
              "conditions_evaluated": [
                {
                  "lhs_value": 1730173740.00,
                  "lhs_expression": {"type": "current_time"},
                  "rhs_value": 1730173620.00,
                  "rhs_expression": {"type": "constant", "value": "09:17"},
                  "operator": ">=",
                  "result": true,
                  "condition_type": "non_live"
                }
              ],
              "candle_data": {
                "NIFTY": {
                  "previous": {"open": 24271.70, "high": 24272.00, "low": 24252.60, "close": 24270.70},
                  "current": {"open": 24270.20, "high": 24272.20, "low": 24270.20, "close": 24272.20}
                }
              }
            },
            
            "condition_preview": "Current Time >= 09:17 AND Previous[TI.1m.rsi(14,close)] < 30 AND TI.underlying_ltp > Previous[TI.1m.High]",
            
            "exit_diagnostic_data": {...},
            "exit_condition_preview": "...",
            
            "node_variables": {
              "entry_condition_1.SignalLow": 24252.60
            }
          }
        ],
        "summary": {
          "total_positions": 9,
          "closed_positions": 9,
          "open_positions": 0,
          "total_pnl": -167.85,
          "winning_trades": 1,
          "losing_trades": 8,
          "win_rate": 11.11,
          "largest_win": 5.10,
          "largest_loss": -78.45,
          "re_entries": 7
        }
      }
    ],
    "overall_summary": {
      "total_positions": 27,
      "total_pnl": -450.30,
      "total_winning_trades": 3,
      "total_losing_trades": 24,
      "overall_win_rate": 11.11,
      "largest_win": 12.05,
      "largest_loss": -78.45,
      "days_tested": 3
    },
    "metadata": {
      "total_days": 3,
      "diagnostics_included": true,
      "generated_at": "2024-10-29T11:00:00"
    }
  }
}
```

### 3. Run Backtest (Streaming) ⭐ RECOMMENDED for Large Date Ranges
```http
POST /api/v1/backtest/stream
Content-Type: application/json
```

**Perfect for:**
- 1 year backtests (250 days × 100 transactions = 25,000 transactions)
- Real-time progress updates
- No timeouts or memory issues
- Progressive UI updates

**Request Body:** Same as standard backtest
```json
{
  "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "mode": "backtesting",
  "include_diagnostics": true
}
```

**Response Format:** Newline-Delimited JSON (NDJSON)
Each line is a complete JSON object. Events are streamed in real-time:

```json
{"type": "metadata", "data": {"strategy_id": "...", "total_days": 250, "started_at": "..."}}
{"type": "day_start", "date": "2024-01-01", "day_number": 1, "total_days": 250}
{"type": "transaction", "date": "2024-01-01", "data": {...}}
{"type": "transaction", "date": "2024-01-01", "data": {...}}
{"type": "day_summary", "date": "2024-01-01", "summary": {...}}
{"type": "day_start", "date": "2024-01-02", "day_number": 2, "total_days": 250}
...
{"type": "complete", "overall_summary": {...}, "completed_at": "..."}
```

**Event Types:**

1. **metadata** - Sent first, contains backtest info
```json
{
  "type": "metadata",
  "data": {
    "strategy_id": "...",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_days": 250,
    "include_diagnostics": true,
    "started_at": "2024-10-29T10:00:00"
  }
}
```

2. **day_start** - New trading day begins
```json
{
  "type": "day_start",
  "date": "2024-01-01",
  "day_number": 1,
  "total_days": 250
}
```

3. **transaction** - Individual transaction (streamed as generated)
```json
{
  "type": "transaction",
  "date": "2024-01-01",
  "data": {
    "position_number": 1,
    "transaction_number": 1,
    "entry_timestamp": "09:19:00",
    "exit_timestamp": "10:48:00",
    "pnl": -78.45,
    "diagnostic_text": "...",  // Full formatted text (if include_diagnostics: true)
    // ... all other transaction fields
  }
}
```

4. **day_summary** - Day completed
```json
{
  "type": "day_summary",
  "date": "2024-01-01",
  "summary": {
    "total_positions": 10,
    "total_pnl": -150.30,
    "win_rate": 40.0,
    "winning_trades": 4,
    "losing_trades": 6
  }
}
```

5. **day_error** - Error on specific day (continues to next day)
```json
{
  "type": "day_error",
  "date": "2024-01-15",
  "error": "Error message"
}
```

6. **complete** - Backtest finished
```json
{
  "type": "complete",
  "overall_summary": {
    "total_positions": 2500,
    "total_pnl": 15000.50,
    "overall_win_rate": 55.2,
    "days_completed": 250
  },
  "completed_at": "2024-10-29T11:30:00"
}
```

7. **error** / **fatal_error** - Critical error
```json
{
  "type": "fatal_error",
  "message": "Error message",
  "traceback": "..."
}
```

## Usage Examples

### Streaming API - Python
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/api/v1/backtest/stream",
    json={
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "include_diagnostics": True
    },
    stream=True  # Enable streaming!
)

# Process events as they arrive
for line in response.iter_lines():
    if not line:
        continue
    
    event = json.loads(line)
    event_type = event.get('type')
    
    if event_type == 'transaction':
        # Update UI with new transaction
        txn = event['data']
        print(f"New transaction: {txn['strike']} {txn['option_type']} | P&L: ₹{txn['pnl']:.2f}")
    
    elif event_type == 'day_summary':
        # Update daily chart
        print(f"Day {event['date']} complete: P&L ₹{event['summary']['total_pnl']:.2f}")
    
    elif event_type == 'complete':
        # Show final results
        print(f"Backtest complete! Total P&L: ₹{event['overall_summary']['total_pnl']:.2f}")
```

### Streaming API - JavaScript (fetch with async iteration)
```javascript
const response = await fetch('http://localhost:8000/api/v1/backtest/stream', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    strategy_id: '5708424d-5962-4629-978c-05b3a174e104',
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    include_diagnostics: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  
  for (const line of lines) {
    if (!line.trim()) continue;
    
    const event = JSON.parse(line);
    
    if (event.type === 'transaction') {
      // Add transaction to UI table
      updateTransactionTable(event.data);
    } else if (event.type === 'day_summary') {
      // Update chart
      updateDailyChart(event.date, event.summary);
    } else if (event.type === 'complete') {
      // Show completion message
      showFinalSummary(event.overall_summary);
    }
  }
}
```

### Streaming API - React Hook
```javascript
import { useState, useEffect } from 'react';

function useStreamingBacktest(strategyId, startDate, endDate) {
  const [transactions, setTransactions] = useState([]);
  const [dailySummaries, setDailySummaries] = useState({});
  const [overallSummary, setOverallSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const runBacktest = async () => {
      const response = await fetch('http://localhost:8000/api/v1/backtest/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          strategy_id: strategyId,
          start_date: startDate,
          end_date: endDate,
          include_diagnostics: true
        })
      });
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        
        const text = decoder.decode(value);
        const lines = text.split('\n');
        
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          
          if (event.type === 'transaction') {
            setTransactions(prev => [...prev, event.data]);
          } else if (event.type === 'day_summary') {
            setDailySummaries(prev => ({...prev, [event.date]: event.summary}));
          } else if (event.type === 'complete') {
            setOverallSummary(event.overall_summary);
            setIsLoading(false);
          }
        }
      }
    };
    
    runBacktest();
  }, [strategyId, startDate, endDate]);
  
  return { transactions, dailySummaries, overallSummary, isLoading };
}
```

## Usage Examples (Standard API)

### Python (requests)
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/backtest",
    json={
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "include_diagnostics": True
    }
)

data = response.json()
if data['success']:
    for day in data['data']['daily_results']:
        print(f"Date: {day['date']}, P&L: ₹{day['summary']['total_pnl']:.2f}")
```

### JavaScript (fetch)
```javascript
fetch('http://localhost:8000/api/v1/backtest', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    strategy_id: '5708424d-5962-4629-978c-05b3a174e104',
    start_date: '2024-10-29',
    include_diagnostics: true
  })
})
.then(res => res.json())
.then(data => {
  if (data.success) {
    console.log('Backtest Results:', data.data);
  }
});
```

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "include_diagnostics": true
  }'
```

## Response Size & Performance

### Standard API (`/api/v1/backtest`)

**With Diagnostics:**
| Duration | Transactions | Uncompressed | Compressed | Recommended |
|----------|--------------|--------------|------------|-------------|
| Single Day | ~10-100 | 100-300 KB | 20-60 KB | ✅ Yes |
| 1 Week | ~50-500 | 500 KB - 1.5 MB | 100-300 KB | ✅ Yes |
| 1 Month | ~200-2000 | 2-6 MB | 400 KB - 1.2 MB | ⚠️ OK |
| 1 Year | ~25,000 | **75 MB** | **15-22 MB** | ❌ Too Large |

**Without Diagnostics:**
| Duration | Transactions | Uncompressed | Compressed | Recommended |
|----------|--------------|--------------|------------|-------------|
| Single Day | ~10-100 | 20-50 KB | 5-10 KB | ✅ Yes |
| 1 Month | ~200-2000 | 400 KB - 1 MB | 80-200 KB | ✅ Yes |
| 1 Year | ~25,000 | **15 MB** | **3-5 MB** | ⚠️ OK (slow) |

### Streaming API (`/api/v1/backtest/stream`) ⭐ RECOMMENDED

**Benefits:**
- ✅ **No size limit** - Can handle unlimited date ranges
- ✅ **Progressive loading** - UI updates in real-time
- ✅ **No timeouts** - Streams continuously
- ✅ **Memory efficient** - Only processes one event at a time
- ✅ **Better UX** - User sees results immediately

**Performance:**
| Duration | Transactions | Time to First Result | Total Time | Memory |
|----------|--------------|---------------------|------------|--------|
| Single Day | ~100 | ~1-2 seconds | ~5-10 seconds | Minimal |
| 1 Month | ~2,000 | ~1-2 seconds | ~2-4 minutes | Minimal |
| 1 Year | ~25,000 | ~1-2 seconds | ~30-60 minutes | Minimal |

**Comparison:**

| Metric | Standard API | Streaming API |
|--------|--------------|---------------|
| **Max Date Range** | ~30 days | Unlimited ✅ |
| **Memory Usage** | High (loads all in RAM) | Low (streams) ✅ |
| **Time to First Result** | Waits for completion | ~1-2 seconds ✅ |
| **UI Responsiveness** | Blocks until done | Updates in real-time ✅ |
| **Timeout Risk** | High for large ranges | None ✅ |
| **Best For** | Small date ranges | Large date ranges ✅ |

**Recommendation:**
- **< 1 week:** Either API works fine
- **1 week - 1 month:** Streaming API preferred
- **> 1 month:** Streaming API required ⭐

**Note:** GZip compression is automatically applied by the server, reducing payload size by 70-80%.

## UI Integration Guide

### 1. Fetch Backtest Results
```javascript
// In your UI component
const runBacktest = async (strategyId, startDate, endDate) => {
  const response = await fetch('http://localhost:8000/api/v1/backtest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      strategy_id: strategyId,
      start_date: startDate,
      end_date: endDate,
      include_diagnostics: true
    })
  });
  
  const result = await response.json();
  return result.data;
};
```

### 2. Display Transactions Table
```javascript
// daily_results[0].positions contains all transactions
const positions = backtestData.daily_results[0].positions;

positions.forEach(pos => {
  console.log(`Pos #${pos.position_number} | Txn #${pos.transaction_number}`);
  console.log(`Entry: ${pos.entry_timestamp} @ ₹${pos.entry_price}`);
  console.log(`Exit: ${pos.exit_timestamp} @ ₹${pos.exit_price}`);
  console.log(`P&L: ₹${pos.pnl}`);
});
```

### 3. Display Diagnostic Text (Multi-level)
```javascript
// Show diagnostic text in expandable section
const DiagnosticView = ({ transaction }) => {
  return (
    <div>
      <h3>Position #{transaction.position_number} | Transaction #{transaction.transaction_number}</h3>
      <pre>{transaction.diagnostic_text}</pre>
    </div>
  );
};
```

### 4. Render Structured Diagnostic Data
```javascript
// Use structured JSON for programmatic display
const ConditionsView = ({ diagnosticData }) => {
  return (
    <div>
      {diagnosticData.conditions_evaluated.map((cond, idx) => (
        <div key={idx}>
          {cond.result ? '✅' : '❌'} {cond.lhs_value} {cond.operator} {cond.rhs_value}
        </div>
      ))}
    </div>
  );
};
```

## Error Handling

### Example Error Response
```json
{
  "success": false,
  "error": "Invalid start_date format. Use YYYY-MM-DD"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `500` - Internal Server Error

## Testing

Run the test client:
```bash
python test_api_client.py
```

This will:
1. Test health check
2. Run single day backtest
3. Run multi-day backtest
4. Save sample response to `api_response_sample.json`

## Production Deployment

### Update CORS Origins
Edit `backtest_api_server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-ui-domain.com"],  # Update this!
    ...
)
```

### Run with Gunicorn (Production)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backtest_api_server:app
```

### Environment Variables
Set these before running:
```bash
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
```

## Questions?
See `test_api_client.py` for complete working examples!
