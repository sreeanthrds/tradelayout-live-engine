# API Quick Reference

## 📋 Common Endpoints

### Get Daily Trades (Main Endpoint)
```bash
GET /backtest/{strategy_id}/trades/{date}
```
Returns: `trades_daily.json` structure

---

### Get Node Details (On-Demand)
```bash
GET /backtest/{strategy_id}/node/{execution_id}
```
Returns: Full diagnostic data for one node

---

### Batch Get Flow Nodes
```bash
POST /backtest/{strategy_id}/flow
Body: { "execution_ids": ["id1", "id2", "id3"] }
```
Returns: Array of node data for flow visualization

---

## 🎯 Typical Usage Flow

```
1. User opens page
   └─> GET /backtest/{id}/trades/2024-10-29
       Returns: Summary + All trades + Flow IDs
       Size: ~15KB
       
2. User clicks trade row
   └─> Render flow using cached trade.entry_flow_ids
   └─> Load diagnostics if not cached (77KB, one-time)
   
3. User clicks node in flow
   └─> Show modal with diagnostics[execution_id]
       Data already loaded, instant display
```

---

## 📦 Response Structures

### Trade List Response
```json
{
  "date": "2024-10-29",
  "summary": {
    "total_trades": 9,
    "total_pnl": "-483.30",
    "win_rate": "11.11"
  },
  "trades": [
    {
      "trade_id": "entry-2-pos1-r0",
      "symbol": "NIFTY:...",
      "entry_price": "181.60",
      "exit_price": "260.05",
      "pnl": "-78.45",
      "status": "closed",
      "entry_flow_ids": ["id1", "id2", "id3"],
      "exit_flow_ids": ["id4", "id5"]
    }
  ]
}
```

### Node Details Response
```json
{
  "execution_id": "exec_entry-2_...",
  "node_name": "Entry 2",
  "node_type": "EntryNode",
  "timestamp": "2024-10-29 09:19:00",
  "action": {
    "symbol": "NIFTY:...",
    "price": "181.60",
    "quantity": 1
  },
  "ltp_store": {...}
}
```

---

## 💡 Frontend Code Snippets

### Load & Display Trades
```typescript
// 1. Fetch trades
const data = await fetch(`/api/backtest/${id}/trades/${date}`).then(r => r.json());

// 2. Display as table
data.trades.forEach(trade => {
  addTableRow({
    symbol: trade.symbol,
    entry: trade.entry_price,
    exit: trade.exit_price,
    pnl: trade.pnl
  });
});
```

### Show Flow Diagram
```typescript
// When user clicks trade
const showFlow = async (trade) => {
  // Load diagnostics once
  if (!diagnosticsCache) {
    diagnosticsCache = await fetch(`/api/diagnostics.json`).then(r => r.json());
  }
  
  // Render entry flow
  trade.entry_flow_ids.forEach(execId => {
    const node = diagnosticsCache.events_history[execId];
    renderNode(node);
  });
  
  // Render exit flow
  trade.exit_flow_ids.forEach(execId => {
    const node = diagnosticsCache.events_history[execId];
    renderNode(node);
  });
};
```

### Show Node Details
```typescript
// When user clicks node
const showNodeDetails = (execId) => {
  const node = diagnosticsCache.events_history[execId];
  
  showModal({
    title: node.node_name,
    time: node.timestamp,
    type: node.node_type,
    details: node.action || node.exit_result || {}
  });
};
```

---

## 🚀 Performance Tips

1. **Cache diagnostics.json** - Load once per session
2. **Use pagination** - For >100 trades
3. **Lazy load flows** - Only when user clicks
4. **Virtual scrolling** - For large trade tables
5. **Compress JSON** - Enable gzip on server

---

## 📊 File Mapping

| Frontend Need | API Endpoint | File Source |
|---------------|--------------|-------------|
| Trade table | GET /trades/{date} | trades_daily.json |
| Flow visualization | (use cached IDs) | trades_daily.json |
| Node details | GET /node/{exec_id} | diagnostics_export.json |

---

## ⚡ Quick Start

```bash
# 1. Get trades for a date
curl https://api.yourplatform.com/v1/backtest/{id}/trades/2024-10-29

# 2. Get specific node details
curl https://api.yourplatform.com/v1/backtest/{id}/node/exec_entry-2_20241029_091900_d98850

# 3. Batch get flow nodes
curl -X POST https://api.yourplatform.com/v1/backtest/{id}/flow \
  -d '{"execution_ids": ["id1", "id2", "id3"]}'
```

---

## ⚡ Real-Time Backtesting (Polling)

For live backtest progress, poll every 1 second:

```javascript
// Poll backtest status
const pollStatus = setInterval(async () => {
  const status = await fetch(`/api/backtest/${id}/status/${date}`)
    .then(r => r.json());
  
  updateProgress(status.progress);
  
  if (status.status === 'completed') {
    clearInterval(pollStatus);
    loadFinalResults();
  }
}, 1000); // Every 1 second
```

**Endpoints:**
- `GET /backtest/{id}/status/{date}` - Current status & progress
- `GET /backtest/{id}/trades/{date}/since/{timestamp}` - Incremental updates

---

## 📁 Local File Serving (Development)

For development, you can serve the JSON files directly:

```bash
# Serve trades_daily.json
python -m http.server 8000

# Access from frontend
fetch('http://localhost:8000/trades_daily.json')
```

Or use them as static assets:

```javascript
// In React/Next.js
import tradesData from './data/trades_daily.json';
import diagnostics from './data/diagnostics_export.json';
```

---

## 🎨 UI Component Structure

```
App
├─ TradesList (loads trades_daily.json)
│  ├─ TradeRow (each trade)
│  │  └─ onClick → showFlowModal()
│  │
│  └─ FlowModal
│     ├─ EntryFlow (from entry_flow_ids)
│     ├─ ExitFlow (from exit_flow_ids)
│     └─ FlowNode (clickable)
│        └─ onClick → showNodeModal()
│
└─ NodeModal (shows diagnostics[exec_id])
   ├─ NodeHeader
   ├─ ActionDetails
   ├─ PositionInfo
   └─ LTPData
```

---

## ✅ Checklist

- [ ] Load trades_daily.json on page load
- [ ] Display trades in table
- [ ] Cache diagnostics_export.json
- [ ] Show flow diagram on trade click
- [ ] Show node details on node click
- [ ] Handle loading states
- [ ] Handle errors (404, 500)
- [ ] Add pagination for >100 trades
- [ ] Implement search/filter
- [ ] Add export functionality
