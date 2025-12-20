# Quick Reference: UI Data Structures

## Trade Structure (trades_summary.json)

```typescript
interface Trade {
  position_id: string;           // "entry-2-pos1"
  re_entry_num: number;          // 0, 1, 2, ...
  symbol: string;                // "NIFTY:2024-11-07:OPT:24250:PE"
  
  entry_flow: EntryFlow;
  exit_flows: ExitFlow[];        // Multiple exits possible!
  position_summary: PositionSummary;
}

interface EntryFlow {
  execution_id: string;
  node_id: string;
  node_name: string;
  timestamp: string;             // ISO 8601
  side: "BUY" | "SELL";
  quantity: number;
  price: string;                 // "181.60" (2 decimals)
  order_id: string;
  signal_chain: SignalNode[];    // Parent chain
}

interface ExitFlow {
  execution_id: string;
  node_id: string;
  node_name: string;
  timestamp: string;
  requested_qty: number;         // Qty node tried to close
  closed_qty: number;            // Actual qty closed
  remaining_after: number;       // Qty left after this exit
  effective: boolean;            // true if closed_qty > 0
  exit_price: string | null;     // "260.05" or null
  pnl: string;                   // "-78.45" or "0.00"
  reason: string;                // "SL" | "Target" | "TSL" | "position_already_closed_by_other_exit"
  note?: string;                 // Optional note for partial/over-qty
  signal_chain: SignalNode[];
}

interface PositionSummary {
  entry_qty: number;             // Initial position size
  net_closed_qty: number;        // Total closed across all exits
  remaining_qty: number;         // Still open (0 = closed)
  total_pnl: string;             // "-78.45" (sum of effective exits)
  status: "open" | "closed";
  duration_minutes: number | null;
}

interface SignalNode {
  execution_id: string;
  node_id: string;
  node_name: string;
  node_type: string;             // "EntrySignalNode", "StartNode", etc.
  timestamp: string;
}
```

## Daily Summary Structure

```typescript
interface DailySummary {
  date: string;                  // "2024-10-29"
  total_trades: number;
  closed_trades: number;
  open_trades: number;
  total_pnl: string;             // "-104.20"
  winning_trades: number;
  losing_trades: number;
  win_rate: number;              // 0.0 to 100.0
  avg_pnl_per_trade: string;     // "-52.10"
  trades: Trade[];               // All trades for this day
}
```

## Execution Event Structure (diagnostics_export.json)

```typescript
interface ExecutionEvent {
  execution_id: string;
  parent_execution_id: string | null;
  timestamp: string;
  node_id: string;
  node_name: string;
  node_type: "StartNode" | "EntrySignalNode" | "EntryNode" | "ExitSignalNode" | "ExitNode" | ...;
  children_nodes: Array<{id: string}>;
  
  // Type-specific fields
  position?: PositionInfo;       // For Entry/Exit nodes
  action?: ActionInfo;           // For Entry/Exit nodes
  exit_result?: ExitResult;      // For Exit nodes
  strategy_config?: object;      // For Start node
}

interface PositionInfo {
  position_id: string;
  re_entry_num: number;
  symbol?: string;
  side?: "buy" | "sell";
  quantity?: number;
  entry_price?: string;
  entry_time?: string;
  node_id?: string;
}

interface ActionInfo {
  type: "place_order" | "exit_order";
  symbol?: string;
  side?: string;
  quantity?: number;
  price?: string;
  target_position_id?: string;   // For exits
  position_details?: object;
}

interface ExitResult {
  positions_closed: number;
  exit_price: string;            // "260.05"
  pnl: string;                   // "-78.45"
  exit_time: string;
}
```

## Key Points for UI Implementation

### 1. Trade Identification
```typescript
// Unique trade key
const tradeKey = `${trade.position_id}_${trade.re_entry_num}`;
```

### 2. Multiple Exits Handling
```typescript
// Filter effective exits
const effectiveExits = trade.exit_flows.filter(e => e.effective);
const ineffectiveExits = trade.exit_flows.filter(e => !e.effective);

// Total P&L (from position_summary, not sum of exits)
const totalPnl = parseFloat(trade.position_summary.total_pnl);
```

### 3. Status Badges
```typescript
// Re-entry badge
{trade.re_entry_num > 0 && <Badge>Re-entry #{trade.re_entry_num}</Badge>}

// Exit effectiveness
{exit.effective ? (
  <Badge color="green">Effective</Badge>
) : (
  <Badge color="yellow">Already Closed</Badge>
)}

// Trade status
<Badge color={trade.position_summary.status === 'closed' ? 'blue' : 'orange'}>
  {trade.position_summary.status.toUpperCase()}
</Badge>
```

### 4. Qty Display
```typescript
// Progress visualization
const qtyPercentage = (trade.position_summary.net_closed_qty / trade.position_summary.entry_qty) * 100;

<ProgressBar>
  <Fill width={`${qtyPercentage}%`} />
  <Label>
    {trade.position_summary.net_closed_qty} / {trade.position_summary.entry_qty} closed
  </Label>
</ProgressBar>
```

### 5. Signal Chain Display
```typescript
<Timeline>
  {trade.entry_flow.signal_chain.map((signal, i) => (
    <TimelineItem key={i}>
      <NodeIcon type={signal.node_type} />
      <NodeInfo>
        <Name>{signal.node_name}</Name>
        <Time>{formatTime(signal.timestamp)}</Time>
      </NodeInfo>
      {i < chain.length - 1 && <Arrow />}
    </TimelineItem>
  ))}
</Timeline>
```

## API Query Examples

```typescript
// Get all trades
const trades = await api.get(`/backtests/${id}/trades`);

// Get closed trades only
const closedTrades = await api.get(`/backtests/${id}/trades?status=closed`);

// Get trades sorted by P&L
const topTrades = await api.get(`/backtests/${id}/trades?sort_by=pnl&order=desc`);

// Get specific trade
const trade = await api.get(`/backtests/${id}/trades/entry-2-pos1/0`);
//                                                     ↑position_id  ↑re_entry_num

// Get execution event (debug)
const event = await api.get(`/backtests/${id}/execution/${execution_id}`);
```

## Price Formatting

All monetary values are **strings** formatted to exactly 2 decimals:
- `"181.60"` - with cents
- `"260.05"` - with cents  
- `"100.00"` - whole numbers still have .00

Display as-is or parse to number for calculations:
```typescript
const pnl = parseFloat(trade.position_summary.total_pnl); // -78.45
```

## Trade Status Rules

| remaining_qty | status   | Can re-enter? |
|---------------|----------|---------------|
| 0             | closed   | ✅ Yes        |
| > 0           | open     | ❌ No         |

Re-entry only allowed when `remaining_qty === 0`.
