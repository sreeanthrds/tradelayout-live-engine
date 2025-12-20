# UI API Endpoints Specification

## Overview

This document specifies the REST API endpoints needed for the backtesting UI, based on the generated JSON files:
- `diagnostics_export.json` (75KB) - Raw execution events
- `trades_summary.json` (30KB) - Position-centric trades with multi-exit support

---

## 1. Backtest Run List

### GET `/api/backtests`

**Purpose:** Get list of all backtest runs with summary stats

**Response:**
```json
{
  "backtests": [
    {
      "id": "bt_20241029_091500",
      "strategy_name": "Iron Condor Strategy",
      "backtest_date": "2024-10-29",
      "timeframe": "1m",
      "symbol": "NIFTY",
      "total_trades": 2,
      "total_pnl": "-104.20",
      "win_rate": 0.0,
      "status": "completed",
      "created_at": "2024-12-09T13:30:00Z"
    }
  ]
}
```

---

## 2. Backtest Summary

### GET `/api/backtests/:backtest_id/summary`

**Purpose:** Get high-level summary for a specific backtest

**Response:**
```json
{
  "backtest_id": "bt_20241029_091500",
  "summary": {
    "total_trades": 2,
    "closed_trades": 2,
    "open_trades": 0
  },
  "daily_summary": {
    "2024-10-29": {
      "date": "2024-10-29",
      "total_trades": 2,
      "closed_trades": 2,
      "total_pnl": "-104.20",
      "winning_trades": 0,
      "losing_trades": 2,
      "win_rate": 0.0,
      "avg_pnl_per_trade": "-52.10"
    }
  }
}
```

**UI Usage:**
- Dashboard header stats
- Daily P&L chart
- Win rate gauge

---

## 3. Trade List (Main View)

### GET `/api/backtests/:backtest_id/trades`

**Purpose:** Get all trades for a backtest with filtering/sorting

**Query Parameters:**
- `status` (optional): `open` | `closed` | `all` (default: `all`)
- `sort_by` (optional): `timestamp` | `pnl` | `duration` (default: `timestamp`)
- `order` (optional): `asc` | `desc` (default: `asc`)
- `date` (optional): Filter by specific date (YYYY-MM-DD)

**Response:**
```json
{
  "trades": [
    {
      "position_id": "entry-2-pos1",
      "re_entry_num": 0,
      "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
      "entry_flow": {
        "execution_id": "exec_entry-2_20241029_091900_051886",
        "node_id": "entry-2",
        "node_name": "Entry 2 -Bullish",
        "timestamp": "2024-10-29 09:19:00+05:30",
        "side": "SELL",
        "quantity": 1,
        "price": "181.60",
        "signal_chain": [
          {
            "node_name": "Entry condition - Bullish",
            "timestamp": "2024-10-29 09:19:00+05:30"
          },
          {
            "node_name": "Start",
            "timestamp": "2024-10-29 09:15:00+05:30"
          }
        ]
      },
      "exit_flows": [
        {
          "execution_id": "exec_exit-3_20241029_104800_ff701c",
          "node_id": "exit-3",
          "node_name": "Exit 3 - SL",
          "timestamp": "2024-10-29 10:48:00+05:30",
          "requested_qty": 1,
          "closed_qty": 1,
          "remaining_after": 0,
          "effective": true,
          "exit_price": "260.05",
          "pnl": "-78.45",
          "reason": "SL",
          "signal_chain": [...]
        }
      ],
      "position_summary": {
        "entry_qty": 1,
        "net_closed_qty": 1,
        "remaining_qty": 0,
        "total_pnl": "-78.45",
        "status": "closed",
        "duration_minutes": 89.0
      }
    }
  ],
  "total_count": 2,
  "filtered_count": 2
}
```

**UI Usage:**
- Main trade list table
- Trade cards
- Filtering/sorting controls

**Data Source:** `trades_summary.json` → `trades` array

---

## 4. Trade Detail View

### GET `/api/backtests/:backtest_id/trades/:position_id/:re_entry_num`

**Purpose:** Get complete details for a specific trade including all flows

**Path Parameters:**
- `position_id`: Position identifier (e.g., `entry-2-pos1`)
- `re_entry_num`: Re-entry number (e.g., `0`)

**Response:**
```json
{
  "position_id": "entry-2-pos1",
  "re_entry_num": 0,
  "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
  
  "entry_flow": {
    "execution_id": "exec_entry-2_20241029_091900_051886",
    "node_id": "entry-2",
    "node_name": "Entry 2 -Bullish",
    "timestamp": "2024-10-29 09:19:00+05:30",
    "side": "SELL",
    "quantity": 1,
    "price": "181.60",
    "order_id": "ENTRY_entry-2_20251209_071323",
    "signal_chain": [
      {
        "execution_id": "exec_entry-condition-1_...",
        "node_id": "entry-condition-1",
        "node_name": "Entry condition - Bullish",
        "node_type": "EntrySignalNode",
        "timestamp": "2024-10-29 09:19:00+05:30"
      },
      {
        "execution_id": "exec_strategy-controller_...",
        "node_id": "strategy-controller",
        "node_name": "Start",
        "node_type": "StartNode",
        "timestamp": "2024-10-29 09:15:00+05:30"
      }
    ]
  },
  
  "exit_flows": [
    {
      "execution_id": "exec_exit-3_20241029_104800_ff701c",
      "node_id": "exit-3",
      "node_name": "Exit 3 - SL",
      "timestamp": "2024-10-29 10:48:00+05:30",
      "requested_qty": 1,
      "closed_qty": 1,
      "remaining_after": 0,
      "effective": true,
      "exit_price": "260.05",
      "pnl": "-78.45",
      "reason": "SL",
      "note": null,
      "signal_chain": [
        {
          "execution_id": "exec_exit-condition-2_...",
          "node_id": "exit-condition-2",
          "node_name": "Exit condition - SL",
          "node_type": "ExitSignalNode",
          "timestamp": "2024-10-29 10:48:00+05:30"
        }
      ]
    },
    {
      "execution_id": "exec_exit-2_20241029_114000_c96974",
      "node_id": "exit-2",
      "node_name": "Exit 2 -Target",
      "timestamp": "2024-10-29 11:40:00+05:30",
      "requested_qty": 0,
      "closed_qty": 0,
      "remaining_after": 0,
      "effective": false,
      "exit_price": null,
      "pnl": "0.00",
      "reason": "position_already_closed_by_other_exit",
      "signal_chain": [...]
    }
  ],
  
  "position_summary": {
    "entry_qty": 1,
    "net_closed_qty": 1,
    "remaining_qty": 0,
    "total_pnl": "-78.45",
    "status": "closed",
    "duration_minutes": 89.0
  }
}
```

**UI Usage:**
- Trade detail modal/page
- Timeline visualization
- Entry/Exit flow diagrams
- Signal chain display

**Data Source:** `trades_summary.json` → Find trade where `position_id` and `re_entry_num` match

---

## 5. Execution Chain (Debug View)

### GET `/api/backtests/:backtest_id/execution/:execution_id`

**Purpose:** Get raw execution event and its chain for deep debugging

**Path Parameters:**
- `execution_id`: Execution event identifier

**Response:**
```json
{
  "event": {
    "execution_id": "exec_exit-3_20241029_104800_ff701c",
    "parent_execution_id": "exec_exit-condition-2_20241029_104800_db",
    "timestamp": "2024-10-29 10:48:00+05:30",
    "node_id": "exit-3",
    "node_name": "Exit 3 - SL",
    "node_type": "ExitNode",
    "position": {
      "position_id": "entry-2-pos1",
      "re_entry_num": 0
    },
    "action": {
      "type": "exit_order",
      "target_position_id": "entry-2-pos1",
      "exit_type": "market"
    },
    "exit_result": {
      "positions_closed": 1,
      "exit_price": "260.05",
      "pnl": "-78.45",
      "exit_time": "2024-10-29 10:48:00+05:30"
    },
    "children_nodes": [
      {"id": "re-entry-signal-2"}
    ]
  },
  "parent_chain": [
    {
      "execution_id": "exec_exit-condition-2_...",
      "node_id": "exit-condition-2",
      "node_name": "Exit condition - SL",
      "timestamp": "2024-10-29 10:48:00+05:30"
    },
    {
      "execution_id": "exec_entry-2_...",
      "node_id": "entry-2",
      "node_name": "Entry 2 -Bullish",
      "timestamp": "2024-10-29 09:19:00+05:30"
    }
  ],
  "children_events": [
    {
      "execution_id": "exec_re-entry-signal-2_...",
      "node_id": "re-entry-signal-2",
      "timestamp": "2024-10-29 10:48:00+05:30"
    }
  ]
}
```

**UI Usage:**
- Advanced debugging panel
- Execution graph visualization
- Node relationships explorer

**Data Source:** `diagnostics_export.json` → `events_history[execution_id]`

---

## 6. Daily P&L Chart Data

### GET `/api/backtests/:backtest_id/pnl-chart`

**Purpose:** Get data for daily P&L chart

**Query Parameters:**
- `start_date` (optional): Start date for range
- `end_date` (optional): End date for range

**Response:**
```json
{
  "chart_data": [
    {
      "date": "2024-10-29",
      "total_pnl": "-104.20",
      "winning_trades": 0,
      "losing_trades": 2,
      "total_trades": 2,
      "cumulative_pnl": "-104.20"
    }
  ]
}
```

**UI Usage:**
- Daily P&L line/bar chart
- Cumulative P&L curve
- Trade count overlay

**Data Source:** `trades_summary.json` → `daily_summary`

---

## 7. Trade Statistics

### GET `/api/backtests/:backtest_id/statistics`

**Purpose:** Get detailed statistics across all trades

**Response:**
```json
{
  "overall": {
    "total_trades": 2,
    "closed_trades": 2,
    "open_trades": 0,
    "total_pnl": "-104.20",
    "win_rate": 0.0,
    "avg_pnl_per_trade": "-52.10",
    "avg_duration_minutes": 55.71
  },
  "by_exit_reason": {
    "SL": {
      "count": 2,
      "total_pnl": "-104.20",
      "avg_pnl": "-52.10"
    },
    "Target": {
      "count": 0,
      "total_pnl": "0.00",
      "avg_pnl": "0.00"
    }
  },
  "by_entry_node": {
    "entry-2": {
      "count": 1,
      "total_pnl": "-78.45"
    },
    "entry-3": {
      "count": 1,
      "total_pnl": "-25.75"
    }
  }
}
```

**UI Usage:**
- Statistics dashboard
- Performance breakdown
- Strategy analysis

**Data Source:** Calculated from `trades_summary.json` → `trades` array

---

## Implementation Guide

### Backend (Python Flask/FastAPI)

```python
from flask import Flask, jsonify
import json

app = Flask(__name__)

# Load JSON files (in production, store in database)
with open('diagnostics_export.json') as f:
    diagnostics = json.load(f)

with open('trades_summary.json') as f:
    trades_summary = json.load(f)

@app.route('/api/backtests/<backtest_id>/summary')
def get_backtest_summary(backtest_id):
    return jsonify({
        'backtest_id': backtest_id,
        'summary': trades_summary['summary'],
        'daily_summary': trades_summary['daily_summary']
    })

@app.route('/api/backtests/<backtest_id>/trades')
def get_trades(backtest_id):
    # Filter/sort logic here
    status = request.args.get('status', 'all')
    trades = trades_summary['trades']
    
    if status != 'all':
        trades = [t for t in trades if t['position_summary']['status'] == status]
    
    return jsonify({
        'trades': trades,
        'total_count': len(trades_summary['trades']),
        'filtered_count': len(trades)
    })

@app.route('/api/backtests/<backtest_id>/trades/<position_id>/<int:re_entry_num>')
def get_trade_detail(backtest_id, position_id, re_entry_num):
    trade = next(
        (t for t in trades_summary['trades'] 
         if t['position_id'] == position_id and t['re_entry_num'] == re_entry_num),
        None
    )
    
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404
    
    return jsonify(trade)

@app.route('/api/backtests/<backtest_id>/execution/<execution_id>')
def get_execution_detail(backtest_id, execution_id):
    event = diagnostics['events_history'].get(execution_id)
    
    if not event:
        return jsonify({'error': 'Execution not found'}), 404
    
    # Build parent chain
    parent_chain = []
    current_id = event.get('parent_execution_id')
    while current_id and current_id in diagnostics['events_history']:
        parent = diagnostics['events_history'][current_id]
        parent_chain.append({
            'execution_id': parent['execution_id'],
            'node_id': parent['node_id'],
            'node_name': parent['node_name'],
            'timestamp': parent['timestamp']
        })
        current_id = parent.get('parent_execution_id')
    
    return jsonify({
        'event': event,
        'parent_chain': parent_chain
    })
```

### Frontend (React Example)

```typescript
// API client
import axios from 'axios';

const api = axios.create({
  baseURL: '/api'
});

// Fetch trades
export const fetchTrades = async (backtestId: string, filters?: TradeFilters) => {
  const response = await api.get(`/backtests/${backtestId}/trades`, { params: filters });
  return response.data;
};

// Fetch trade detail
export const fetchTradeDetail = async (
  backtestId: string, 
  positionId: string, 
  reEntryNum: number
) => {
  const response = await api.get(
    `/backtests/${backtestId}/trades/${positionId}/${reEntryNum}`
  );
  return response.data;
};

// Usage in component
const TradeList = ({ backtestId }) => {
  const [trades, setTrades] = useState([]);
  
  useEffect(() => {
    fetchTrades(backtestId, { status: 'closed', sort_by: 'timestamp' })
      .then(data => setTrades(data.trades));
  }, [backtestId]);
  
  return (
    <div>
      {trades.map(trade => (
        <TradeCard key={`${trade.position_id}-${trade.re_entry_num}`} trade={trade} />
      ))}
    </div>
  );
};
```

---

## UI Component Mapping

### 1. Dashboard Page
- **Data:** `/api/backtests/:id/summary`
- **Components:**
  - Stats cards (total trades, P&L, win rate)
  - Daily P&L chart (`/api/backtests/:id/pnl-chart`)
  - Recent trades list (`/api/backtests/:id/trades?limit=10`)

### 2. Trade List Page
- **Data:** `/api/backtests/:id/trades`
- **Components:**
  - Filter controls (status, date range)
  - Sort controls (timestamp, P&L, duration)
  - Trade table/cards
  - Pagination

### 3. Trade Detail Modal/Page
- **Data:** `/api/backtests/:id/trades/:position_id/:re_entry_num`
- **Components:**
  - Entry flow timeline
  - Multiple exit flows (accordion/tabs)
  - Signal chain visualization
  - Position summary stats
  - Badges for effective/ineffective exits

### 4. Debug Panel (Advanced)
- **Data:** `/api/backtests/:id/execution/:execution_id`
- **Components:**
  - Execution event details
  - Parent chain tree
  - Children nodes list
  - Raw JSON viewer

---

## Key UI Features to Implement

### 1. Multi-Exit Display
Since positions can have multiple exits:
```jsx
<ExitFlowsList>
  {trade.exit_flows.map((exit, index) => (
    <ExitFlowCard 
      key={exit.execution_id}
      exit={exit}
      index={index + 1}
      effective={exit.effective}
    >
      {!exit.effective && (
        <Badge variant="warning">
          {exit.reason}
        </Badge>
      )}
    </ExitFlowCard>
  ))}
</ExitFlowsList>
```

### 2. Qty Tracking Visualization
```jsx
<QtyProgressBar>
  <div style={{width: `${(exit.closed_qty / entry_qty) * 100}%`}}>
    Closed: {exit.closed_qty}
  </div>
  <div style={{width: `${(exit.remaining_after / entry_qty) * 100}%`}}>
    Remaining: {exit.remaining_after}
  </div>
</QtyProgressBar>
```

### 3. Signal Chain Display
```jsx
<SignalChain>
  {trade.entry_flow.signal_chain.map((signal, i) => (
    <SignalNode key={i}>
      <Icon type={signal.node_type} />
      <span>{signal.node_name}</span>
      <time>{signal.timestamp}</time>
      {i < chain.length - 1 && <Arrow />}
    </SignalNode>
  ))}
</SignalChain>
```

### 4. Re-Entry Indicator
```jsx
{trade.re_entry_num > 0 && (
  <Badge color="blue">
    Re-entry #{trade.re_entry_num}
  </Badge>
)}
```

---

## Performance Considerations

### Backend
- Cache JSON files in memory (reload on backtest completion)
- For large backtests (>1000 trades):
  - Implement pagination (limit/offset)
  - Add database storage (PostgreSQL/MongoDB)
  - Index by position_id, re_entry_num, timestamp

### Frontend
- Virtualized lists for large trade counts (react-window)
- Lazy load trade details (don't fetch all upfront)
- Debounce filter/sort inputs
- Cache API responses (react-query / SWR)

---

## Testing Checklist

✅ **API Endpoints:**
- [ ] All endpoints return correct data
- [ ] Filtering works correctly
- [ ] Sorting works correctly
- [ ] Error handling (404, 500)

✅ **UI Components:**
- [ ] Trade list displays all trades
- [ ] Multi-exit trades show all exits
- [ ] Ineffective exits have warning badges
- [ ] Re-entries are clearly labeled
- [ ] Signal chains are clickable/expandable
- [ ] P&L values formatted to 2 decimals
- [ ] Timestamps in correct timezone

✅ **Edge Cases:**
- [ ] Open positions display correctly
- [ ] Partial exits show qty breakdown
- [ ] Over-qty attempts show notes
- [ ] Already-closed exits show reason
- [ ] Empty states (no trades)

---

## Next Steps

1. **Backend:** Implement REST API endpoints
2. **Frontend:** Create UI components based on spec
3. **Integration:** Connect frontend to backend APIs
4. **Testing:** Verify with generated JSON files
5. **Deployment:** Deploy to staging for user testing
