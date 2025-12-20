# Trade Diagnostics API Documentation

## Overview
This API provides access to backtest results, trade data, and execution diagnostics for strategy analysis and visualization.

---

## Base URL
```
https://api.yourplatform.com/v1
```

---

## Authentication
```http
Authorization: Bearer {token}
```

---

## Endpoints

### 1. Get Daily Summary

Get high-level summary for a specific backtest date.

**Endpoint:**
```http
GET /backtest/{strategy_id}/summary/{date}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| strategy_id | string | Yes | UUID of the strategy |
| date | string | Yes | Date in YYYY-MM-DD format |

**Response:** `200 OK`
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30",
    "winning_trades": 1,
    "losing_trades": 8,
    "win_rate": "11.11"
  }
}
```

**Example:**
```bash
curl -X GET "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/summary/2024-10-29" \
  -H "Authorization: Bearer {token}"
```

---

### 2. Get Daily Trades

Get all trades for a specific date with flow IDs for visualization.

**Endpoint:**
```http
GET /backtest/{strategy_id}/trades/{date}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| strategy_id | string | Yes | UUID of the strategy |
| date | string | Yes | Date in YYYY-MM-DD format |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | integer | 1 | Page number for pagination |
| limit | integer | 50 | Number of trades per page |
| status | string | all | Filter: `all`, `open`, `closed` |
| sort | string | entry_time | Sort by: `entry_time`, `pnl`, `duration` |
| order | string | asc | Order: `asc`, `desc` |

**Response:** `200 OK`
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30",
    "winning_trades": 1,
    "losing_trades": 8,
    "win_rate": "11.11"
  },
  "trades": [
    {
      "trade_id": "entry-2-pos1-r0",
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "side": "SELL",
      "quantity": 1,
      "entry_price": "181.60",
      "entry_time": "2024-10-29 09:19:00+05:30",
      "exit_price": "260.05",
      "exit_time": "2024-10-29 10:48:00+05:30",
      "pnl": "-78.45",
      "pnl_percent": "-43.20",
      "duration_minutes": 89,
      "status": "closed",
      "entry_flow_ids": [
        "exec_strategy-controller_20241029_091500_42169b",
        "exec_entry-condition-1_20241029_091900_1e0dc0",
        "exec_entry-2_20241029_091900_d98850"
      ],
      "exit_flow_ids": [
        "exec_strategy-controller_20241029_091500_42169b",
        "exec_entry-condition-1_20241029_091900_1e0dc0",
        "exec_entry-2_20241029_091900_d98850",
        "exec_exit-condition-2_20241029_104800_df9923",
        "exec_exit-3_20241029_104800_b25e6c"
      ],
      "entry_trigger": "Entry condition - Bullish",
      "exit_reason": "Exit 3 - SL"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 9,
    "total_pages": 1
  }
}
```

**Example:**
```bash
curl -X GET "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/trades/2024-10-29?page=1&limit=50&status=closed" \
  -H "Authorization: Bearer {token}"
```

---

### 3. Get Single Trade Details

Get detailed information for a specific trade.

**Endpoint:**
```http
GET /backtest/{strategy_id}/trade/{trade_id}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| strategy_id | string | Yes | UUID of the strategy |
| trade_id | string | Yes | Trade ID (e.g., `entry-2-pos1-r0`) |

**Response:** `200 OK`
```json
{
  "trade_id": "entry-2-pos1-r0",
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  "side": "SELL",
  "quantity": 1,
  "entry_price": "181.60",
  "entry_time": "2024-10-29 09:19:00+05:30",
  "exit_price": "260.05",
  "exit_time": "2024-10-29 10:48:00+05:30",
  "pnl": "-78.45",
  "pnl_percent": "-43.20",
  "duration_minutes": 89,
  "status": "closed",
  "entry_flow_ids": ["..."],
  "exit_flow_ids": ["..."],
  "entry_trigger": "Entry condition - Bullish",
  "exit_reason": "Exit 3 - SL"
}
```

**Example:**
```bash
curl -X GET "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/trade/entry-2-pos1-r0" \
  -H "Authorization: Bearer {token}"
```

---

### 4. Get Execution Node Details

Get full diagnostic data for a specific execution node.

**Endpoint:**
```http
GET /backtest/{strategy_id}/node/{execution_id}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| strategy_id | string | Yes | UUID of the strategy |
| execution_id | string | Yes | Execution ID (e.g., `exec_entry-2_20241029_091900_d98850`) |

**Response:** `200 OK`
```json
{
  "execution_id": "exec_entry-2_20241029_091900_d98850",
  "parent_execution_id": "exec_entry-condition-1_20241029_091900_1e0dc0",
  "timestamp": "2024-10-29 09:19:00+05:30",
  "event_type": "logic_completed",
  "node_id": "entry-2",
  "node_name": "Entry 2",
  "node_type": "EntryNode",
  "children_nodes": [
    {
      "id": "exit-condition-2"
    }
  ],
  "position": {
    "position_id": "entry-2-pos1",
    "re_entry_num": 0
  },
  "action": {
    "type": "place_order",
    "action_type": "entry",
    "order_id": "ORD_001",
    "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
    "side": "sell",
    "quantity": 1,
    "order_type": "market",
    "price": "181.60",
    "status": "filled"
  },
  "entry_config": {
    "max_entries": 1,
    "position_num": 1,
    "re_entry_num": 0
  },
  "ltp_store": {
    "NIFTY": {
      "ltp": 24367.55,
      "timestamp": "2024-10-29 09:19:00.000000"
    },
    "NIFTY:2024-11-07:OPT:24250:PE": {
      "ltp": 181.6,
      "timestamp": "2024-10-29 09:19:00.000000"
    }
  }
}
```

**Example:**
```bash
curl -X GET "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/node/exec_entry-2_20241029_091900_d98850" \
  -H "Authorization: Bearer {token}"
```

---

### 5. Get Flow Details (Batch)

Get diagnostic data for multiple nodes at once (for flow visualization).

**Endpoint:**
```http
POST /backtest/{strategy_id}/flow
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| strategy_id | string | Yes | UUID of the strategy |

**Request Body:**
```json
{
  "execution_ids": [
    "exec_strategy-controller_20241029_091500_42169b",
    "exec_entry-condition-1_20241029_091900_1e0dc0",
    "exec_entry-2_20241029_091900_d98850"
  ]
}
```

**Response:** `200 OK`
```json
{
  "nodes": [
    {
      "execution_id": "exec_strategy-controller_20241029_091500_42169b",
      "node_name": "Strategy Controller",
      "node_type": "StartNode",
      "timestamp": "2024-10-29 09:15:00+05:30"
    },
    {
      "execution_id": "exec_entry-condition-1_20241029_091900_1e0dc0",
      "node_name": "Entry condition - Bullish",
      "node_type": "EntrySignalNode",
      "timestamp": "2024-10-29 09:19:00+05:30"
    },
    {
      "execution_id": "exec_entry-2_20241029_091900_d98850",
      "node_name": "Entry 2",
      "node_type": "EntryNode",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "action": {
        "type": "place_order",
        "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
        "price": "181.60"
      }
    }
  ]
}
```

**Example:**
```bash
curl -X POST "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/flow" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_ids": [
      "exec_strategy-controller_20241029_091500_42169b",
      "exec_entry-condition-1_20241029_091900_1e0dc0",
      "exec_entry-2_20241029_091900_d98850"
    ]
  }'
```

---

### 6. Get Date Range Summary

Get summary across multiple dates.

**Endpoint:**
```http
GET /backtest/{strategy_id}/summary/range
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |

**Response:** `200 OK`
```json
{
  "start_date": "2024-10-01",
  "end_date": "2024-10-31",
  "summary": {
    "total_trading_days": 21,
    "total_trades": 189,
    "total_pnl": "-10,250.75",
    "winning_days": 8,
    "losing_days": 13,
    "best_day": {
      "date": "2024-10-15",
      "pnl": "2,450.30"
    },
    "worst_day": {
      "date": "2024-10-22",
      "pnl": "-3,120.50"
    }
  },
  "daily_breakdown": [
    {
      "date": "2024-10-29",
      "trades": 9,
      "pnl": "-483.30",
      "win_rate": "11.11"
    }
  ]
}
```

**Example:**
```bash
curl -X GET "https://api.yourplatform.com/v1/backtest/5708424d-5962-4629-978c-05b3a174e104/summary/range?start_date=2024-10-01&end_date=2024-10-31" \
  -H "Authorization: Bearer {token}"
```

---

## Data Models

### Trade Object
```typescript
interface Trade {
  trade_id: string;              // Unique identifier: "{position_id}-r{re_entry_num}"
  position_id: string;           // Position identifier
  re_entry_num: number;          // Re-entry sequence number (0-based)
  symbol: string;                // Trading instrument
  side: "BUY" | "SELL";         // Trade direction
  quantity: number;              // Quantity traded
  entry_price: string;           // Entry price (formatted to 2 decimals)
  entry_time: string;            // Entry timestamp (ISO 8601)
  exit_price: string | null;     // Exit price (null if open)
  exit_time: string | null;      // Exit timestamp (null if open)
  pnl: string;                   // Profit/Loss (formatted to 2 decimals)
  pnl_percent: string;           // P&L percentage
  duration_minutes: number;      // Trade duration in minutes
  status: "open" | "closed";     // Trade status
  entry_flow_ids: string[];      // Execution IDs for entry flow
  exit_flow_ids: string[];       // Execution IDs for exit flow
  entry_trigger: string;         // Entry trigger node name
  exit_reason: string | null;    // Exit reason node name
}
```

### Execution Node Object
```typescript
interface ExecutionNode {
  execution_id: string;          // Unique execution identifier
  parent_execution_id: string;   // Parent node execution ID
  timestamp: string;             // Execution timestamp (ISO 8601)
  event_type: string;            // Event type: logic_completed, etc.
  node_id: string;               // Node identifier from strategy
  node_name: string;             // Human-readable node name
  node_type: string;             // Node type: EntryNode, ExitNode, etc.
  children_nodes: Array<{id: string}>;  // Child nodes
  
  // Optional fields based on node type
  position?: {
    position_id: string;
    re_entry_num: number;
  };
  action?: {
    type: string;
    symbol: string;
    side: string;
    quantity: number;
    price: string;
    status: string;
  };
  exit_result?: {
    positions_closed: number;
    exit_price: string;
    pnl: string;
  };
  entry_config?: {
    max_entries: number;
    position_num: number;
    re_entry_num: number;
  };
  ltp_store?: Record<string, {
    ltp: number;
    timestamp: string;
  }>;
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "bad_request",
  "message": "Invalid date format. Expected YYYY-MM-DD",
  "details": {
    "field": "date",
    "provided": "2024/10/29"
  }
}
```

### 401 Unauthorized
```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}
```

### 404 Not Found
```json
{
  "error": "not_found",
  "message": "No backtest data found for the specified date",
  "details": {
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "date": "2024-10-29"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again later",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "internal_error",
  "message": "An internal error occurred while processing your request",
  "request_id": "req_abc123"
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Summary endpoints | 60 requests | per minute |
| Trade list | 30 requests | per minute |
| Node details | 120 requests | per minute |
| Flow batch | 30 requests | per minute |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
```

---

## Caching

The API supports standard HTTP caching headers:

```http
Cache-Control: public, max-age=3600
ETag: "abc123def456"
Last-Modified: Mon, 29 Oct 2024 15:25:00 GMT
```

**Recommendations:**
- Cache trade data for at least 1 hour (historical data doesn't change)
- Use ETags for conditional requests
- Implement client-side caching for diagnostics data

---

## Implementation Example

### Frontend Implementation (React)

```typescript
// 1. Fetch daily trades
const fetchDailyTrades = async (strategyId: string, date: string) => {
  const response = await fetch(
    `https://api.yourplatform.com/v1/backtest/${strategyId}/trades/${date}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return await response.json();
};

// 2. Display trades in table
const TradesTable = ({ trades }) => {
  return (
    <table>
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Entry</th>
          <th>Exit</th>
          <th>P&L</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {trades.map(trade => (
          <tr key={trade.trade_id} onClick={() => showTradeFlow(trade)}>
            <td>{trade.symbol}</td>
            <td>{trade.entry_price}</td>
            <td>{trade.exit_price || '-'}</td>
            <td className={trade.pnl > 0 ? 'profit' : 'loss'}>
              {trade.pnl}
            </td>
            <td>{trade.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

// 3. Show flow diagram when trade clicked
const showTradeFlow = async (trade: Trade) => {
  // Fetch diagnostics (cached after first load)
  const diagnostics = await fetchDiagnostics(strategyId);
  
  // Get flow nodes
  const entryNodes = trade.entry_flow_ids.map(id => 
    diagnostics.events_history[id]
  );
  
  const exitNodes = trade.exit_flow_ids.map(id => 
    diagnostics.events_history[id]
  );
  
  // Render flow
  renderFlowDiagram({
    entry: entryNodes,
    exit: exitNodes
  });
};

// 4. Load diagnostics once and cache
let diagnosticsCache: any = null;

const fetchDiagnostics = async (strategyId: string) => {
  if (diagnosticsCache) {
    return diagnosticsCache;
  }
  
  const response = await fetch(
    `https://api.yourplatform.com/v1/backtest/${strategyId}/diagnostics`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  diagnosticsCache = await response.json();
  return diagnosticsCache;
};
```

---

## Best Practices

### 1. Progressive Loading
```
1. Load summary first (fast, <1KB)
2. Load trade list on page load (medium, ~50KB)
3. Load diagnostics when user clicks trade (heavy, ~1MB, cached)
4. Load individual nodes on demand
```

### 2. Pagination
For large datasets (>100 trades), use pagination:
```
GET /backtest/{id}/trades/{date}?page=1&limit=50
```

### 3. Caching Strategy
```javascript
// Cache diagnostics in browser
const CACHE_KEY = `diagnostics_${strategyId}`;
const cached = localStorage.getItem(CACHE_KEY);

if (cached) {
  return JSON.parse(cached);
} else {
  const data = await fetchDiagnostics(strategyId);
  localStorage.setItem(CACHE_KEY, JSON.stringify(data));
  return data;
}
```

### 4. Error Handling
```javascript
try {
  const trades = await fetchDailyTrades(strategyId, date);
  renderTrades(trades);
} catch (error) {
  if (error.status === 404) {
    showMessage('No data found for this date');
  } else if (error.status === 429) {
    showMessage('Too many requests. Please wait.');
  } else {
    showMessage('An error occurred. Please try again.');
  }
}
```

---

## Real-Time Backtesting Updates

For live backtesting progress, use **polling** (client requests every second).

### Get Backtest Status

**Endpoint:**
```http
GET /backtest/{strategy_id}/status/{date}
```

**Response:** `200 OK`
```json
{
  "status": "running" | "completed" | "failed",
  "progress": {
    "current_time": "2024-10-29 12:30:00+05:30",
    "total_trades": 5,
    "completed_trades": 5,
    "open_positions": 2,
    "current_pnl": "-125.50"
  },
  "last_update": "2024-10-29 12:30:00+05:30"
}
```

### Polling Implementation

```javascript
// Poll every 1 second during backtest
let pollingInterval;

const startPolling = (strategyId, date) => {
  pollingInterval = setInterval(async () => {
    try {
      const status = await fetch(
        `https://api.yourplatform.com/v1/backtest/${strategyId}/status/${date}`
      ).then(r => r.json());
      
      // Update UI with current status
      updateBacktestProgress(status.progress);
      
      // If completed, stop polling and load final results
      if (status.status === 'completed') {
        clearInterval(pollingInterval);
        loadFinalResults(strategyId, date);
      }
      
      // If failed, stop polling and show error
      if (status.status === 'failed') {
        clearInterval(pollingInterval);
        showError('Backtest failed');
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  }, 1000); // Poll every 1 second
};

const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval);
  }
};

// Usage
startPolling('5708424d-5962-4629-978c-05b3a174e104', '2024-10-29');
```

### Get Incremental Updates

Get only new trades since last fetch:

**Endpoint:**
```http
GET /backtest/{strategy_id}/trades/{date}/since/{timestamp}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| timestamp | string | Yes | ISO 8601 timestamp of last fetch |

**Response:** `200 OK`
```json
{
  "new_trades": [
    {
      "trade_id": "entry-3-pos1-r5",
      "symbol": "NIFTY:...",
      "entry_price": "254.70",
      "status": "open",
      "entry_time": "2024-10-29 13:05:49+05:30"
    }
  ],
  "updated_trades": [
    {
      "trade_id": "entry-3-pos1-r4",
      "status": "closed",
      "exit_price": "262.90",
      "pnl": "-94.50"
    }
  ],
  "summary": {
    "total_trades": 6,
    "total_pnl": "-315.75"
  }
}
```

**Example with incremental updates:**
```javascript
let lastFetchTime = null;

const pollBacktest = async (strategyId, date) => {
  const endpoint = lastFetchTime
    ? `/backtest/${strategyId}/trades/${date}/since/${lastFetchTime}`
    : `/backtest/${strategyId}/trades/${date}`;
  
  const data = await fetch(endpoint).then(r => r.json());
  
  // Add new trades to table
  if (data.new_trades) {
    data.new_trades.forEach(trade => addTradeToTable(trade));
  }
  
  // Update existing trades
  if (data.updated_trades) {
    data.updated_trades.forEach(trade => updateTradeInTable(trade));
  }
  
  // Update summary
  updateSummary(data.summary);
  
  // Save timestamp for next poll
  lastFetchTime = new Date().toISOString();
};

// Poll every second
setInterval(() => pollBacktest(strategyId, date), 1000);
```

### Best Practices for Polling

1. **Use incremental updates** - Only fetch new/changed data
2. **Stop polling when backtest completes** - Check status first
3. **Handle errors gracefully** - Don't stop polling on single failure
4. **Throttle if needed** - Reduce frequency if server load is high
5. **Use timestamps** - Track last fetch to get only new data

---

## Support

For API support or questions:
- Documentation: https://docs.yourplatform.com
- Support: support@yourplatform.com
- Status: https://status.yourplatform.com
