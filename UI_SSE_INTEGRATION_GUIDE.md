# SSE Events - UI Integration Guide

Complete guide for consuming live trading SSE events in your React/TypeScript UI.

---

## Table of Contents
1. [Event Overview](#event-overview)
2. [TypeScript Interfaces](#typescript-interfaces)
3. [Event Structures](#event-structures)
4. [React Integration](#react-integration)
5. [UI Component Examples](#ui-component-examples)
6. [Edge Cases & Error Handling](#edge-cases--error-handling)
7. [Performance Optimization](#performance-optimization)

---

## Event Overview

### 5 Event Types

| Event | When | Frequency | Compressed | Size | Purpose |
|-------|------|-----------|------------|------|---------|
| `initial_state` | Connect | 1× | ✅ Yes | ~15 KB | Full snapshot on session start |
| `tick_update` | Every second | ~22K× | ❌ No | 3-5 KB | Real-time tick data |
| `node_event` | Node completes | ~38× | ❌ No | 1 KB | Significant node milestones |
| `trade_update` | Trade closes | ~7× | ❌ No | 1 KB | Individual trade details |
| `backtest_complete` | End | 1× | ✅ Yes | ~15 KB | Final snapshot |

### Event Flow

```
Client Connects
    ↓
initial_state (compressed diagnostics + trades)
    ↓
tick_update (every second)
    ├─ positions updated
    ├─ P&L changes
    └─ node executions
    ↓
node_event (when signal emitted)
    ↓
trade_update (when position closes)
    ↓
backtest_complete (final state)
```

---

## TypeScript Interfaces

```typescript
// ============================================
// Event Wrapper (All Events)
// ============================================
interface SSEEvent {
  event: 'initial_state' | 'tick_update' | 'node_event' | 'trade_update' | 'backtest_complete';
  data: InitialStateData | TickUpdateData | NodeEventData | TradeUpdateData | BacktestCompleteData;
}

// ============================================
// 1. initial_state (Compressed)
// ============================================
interface InitialStateData {
  event_id: number;
  session_id: string;
  diagnostics: string;  // gzip + base64 encoded
  trades: string;       // gzip + base64 encoded
  uncompressed_sizes: {
    diagnostics: number;
    trades: number;
  };
  strategy_id: string;
  start_date: string;  // YYYY-MM-DD
  end_date: string;    // YYYY-MM-DD
}

// After decompression:
interface DiagnosticsSnapshot {
  events_history: Record<string, NodeExecutionEvent>;
  current_state: Record<string, any>;
}

interface TradesSnapshot {
  date: string;
  summary: TradeSummary;
  trades: Trade[];
}

// ============================================
// 2. tick_update (Every Second)
// ============================================
interface TickUpdateData {
  event_id: number;
  session_id: string;
  tick: number;
  timestamp: string;  // "2024-10-29 09:19:00+05:30"
  execution_count: number;
  
  // Node executions this tick
  node_executions: Record<string, NodeExecution>;
  
  // Positions with individual P&L
  open_positions: Position[];
  
  // Aggregated P&L metrics
  pnl_summary: PnLSummary;
  
  // Market data
  ltp: Record<string, LTPData>;
  indicators?: Record<string, any>;
  
  // Active nodes list
  active_nodes: string[];
}

interface NodeExecution {
  execution_id: string;
  node_id: string;
  node_name: string;
  node_type: string;
  timestamp: string;
  event_type: 'node_executing' | 'logic_completed';
  signal_emitted?: boolean;
  evaluated_conditions?: ConditionEvaluation[];
  node_variables?: Record<string, any>;
  children_nodes?: string[];
}

interface Position {
  position_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  entry_price: string;      // "215.00"
  current_price: string;    // "220.50"
  unrealized_pnl: string;   // "-275.00"
  entry_time?: string;
  status: 'open';
}

interface PnLSummary {
  realized_pnl: string;      // "29.25"
  unrealized_pnl: string;    // "-275.00"
  total_pnl: string;         // "-245.75"
  closed_trades: number;
  open_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;          // "100.00"
}

interface LTPData {
  ltp: number;
  timestamp: string;
}

// ============================================
// 3. node_event (On Completion)
// ============================================
interface NodeEventData {
  event_id: number;
  session_id: string;
  execution_id: string;
  node_id: string;
  node_name: string;
  node_type: string;
  timestamp: string;
  event_type: 'logic_completed';
  signal_emitted?: boolean;
  conditions_preview?: string;
}

// ============================================
// 4. trade_update (On Close)
// ============================================
interface TradeUpdateData {
  event_id: number;
  session_id: string;
  trade: Trade;
  summary: TradeSummary;
}

interface Trade {
  trade_id: string;
  position_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  entry_price: string;
  entry_time: string;
  exit_price: string;
  exit_time: string;
  pnl: string;
  status: 'CLOSED';
}

interface TradeSummary {
  total_trades: number;
  total_pnl: string;
  winning_trades: number;
  losing_trades: number;
  win_rate: string;
}

// ============================================
// 5. backtest_complete (Final)
// ============================================
interface BacktestCompleteData {
  event_id: number;
  session_id: string;
  diagnostics: string;  // gzip + base64 encoded
  trades: string;       // gzip + base64 encoded
  uncompressed_sizes: {
    diagnostics: number;
    trades: number;
  };
  total_ticks: number;
}
```

---

## Event Structures

### Event 1: `initial_state` (Compressed)

**Raw SSE:**
```
event: initial_state
data: {"event_id":0,"session_id":"...","diagnostics":"H4sIAAAAAAAA...","trades":"H4sIAAAAAAAA..."}
id: 0
```

**After Decompression:**
```typescript
const diagnostics: DiagnosticsSnapshot = {
  events_history: {},  // Empty at start
  current_state: {}
};

const trades: TradesSnapshot = {
  date: "2024-10-29",
  summary: {
    total_trades: 0,
    total_pnl: "0.00",
    winning_trades: 0,
    losing_trades: 0,
    win_rate: "0.00"
  },
  trades: []
};
```

---

### Event 2: `tick_update` (Uncompressed, Most Frequent)

**Raw SSE:**
```
event: tick_update
data: {"event_id":241,"tick":241,"timestamp":"2024-10-29 09:19:00+05:30",...}
id: 241
```

**Complete Example:**
```json
{
  "event_id": 241,
  "session_id": "sse-strategy-2024-10-29",
  "tick": 241,
  "timestamp": "2024-10-29 09:19:00+05:30",
  "execution_count": 3,
  
  "node_executions": {
    "exec_entry-condition-1_20241029_091900_0153a0": {
      "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
      "node_id": "entry-condition-1",
      "node_name": "Entry Bullish",
      "node_type": "EntrySignalNode",
      "timestamp": "2024-10-29 09:19:00+05:30",
      "event_type": "logic_completed",
      "signal_emitted": true,
      "evaluated_conditions": [
        {
          "condition_id": "cond_1",
          "expression": "Current Time >= 09:17",
          "result": true,
          "left_value": "09:19:00",
          "operator": ">=",
          "right_value": "09:17:00"
        }
      ],
      "node_variables": {
        "strike_price": 24000
      }
    }
  },
  
  "open_positions": [
    {
      "position_id": "entry-2-pos1",
      "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
      "side": "sell",
      "quantity": 50,
      "entry_price": "215.00",
      "current_price": "220.50",
      "unrealized_pnl": "-275.00",
      "entry_time": "2024-10-29 09:19:05+05:30",
      "status": "open"
    }
  ],
  
  "pnl_summary": {
    "realized_pnl": "0.00",
    "unrealized_pnl": "-275.00",
    "total_pnl": "-275.00",
    "closed_trades": 0,
    "open_trades": 1,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": "0.00"
  },
  
  "ltp": {
    "NIFTY": {
      "ltp": 24350.5,
      "timestamp": "2024-10-29 09:19:00.000000"
    }
  },
  
  "active_nodes": ["entry-condition-1", "entry-condition-2", "square-off-1"]
}
```

---

### Event 3: `node_event` (Incremental)

**Raw SSE:**
```
event: node_event
data: {"event_id":242,"node_id":"entry-condition-1","signal_emitted":true}
id: 242
```

**Complete Example:**
```json
{
  "event_id": 242,
  "session_id": "sse-strategy-2024-10-29",
  "execution_id": "exec_entry-condition-1_20241029_091900_0153a0",
  "node_id": "entry-condition-1",
  "node_name": "Entry Bullish",
  "node_type": "EntrySignalNode",
  "timestamp": "2024-10-29 09:19:00+05:30",
  "event_type": "logic_completed",
  "signal_emitted": true,
  "conditions_preview": "Current Time >= 09:17 AND NIFTY > 24000"
}
```

**Use Case:** Log to activity feed, show notifications for significant events.

---

### Event 4: `trade_update` (Incremental)

**Raw SSE:**
```
event: trade_update
data: {"event_id":243,"trade":{...},"summary":{...}}
id: 243
```

**Complete Example:**
```json
{
  "event_id": 243,
  "session_id": "sse-strategy-2024-10-29",
  "trade": {
    "trade_id": "entry-2-pos1",
    "position_id": "entry-2-pos1",
    "symbol": "NIFTY:2024-11-07:OPT:24000:PE",
    "side": "sell",
    "quantity": 50,
    "entry_price": "215.00",
    "entry_time": "2024-10-29 09:19:05+05:30",
    "exit_price": "185.75",
    "exit_time": "2024-10-29 10:48:00+05:30",
    "pnl": "29.25",
    "status": "CLOSED"
  },
  "summary": {
    "total_trades": 1,
    "total_pnl": "29.25",
    "winning_trades": 1,
    "losing_trades": 0,
    "win_rate": "100.00"
  }
}
```

**Use Case:** Add to trades list, show toast notification, update summary metrics.

---

### Event 5: `backtest_complete` (Compressed, Final)

**Raw SSE:**
```
event: backtest_complete
data: {"event_id":22351,"diagnostics":"H4sIAAAAAAAA...","total_ticks":22351}
id: 22351
```

**Use Case:** Save final state, show completion message, enable report download.

---

## React Integration

### Decompression Utility (Required for Compressed Events)

```typescript
// Install: npm install pako
import pako from 'pako';

function decompressGzipBase64(compressed: string): any {
  try {
    // Base64 decode
    const binaryString = atob(compressed);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Gunzip
    const decompressed = pako.ungzip(bytes, { to: 'string' });
    
    // Parse JSON
    return JSON.parse(decompressed);
  } catch (error) {
    console.error('Decompression failed:', error);
    return null;
  }
}
```

---

### React Hook: `useBacktestSSE`

```typescript
import { useEffect, useState, useRef } from 'react';
import pako from 'pako';

interface BacktestState {
  sessionId: string | null;
  status: 'idle' | 'connected' | 'running' | 'completed' | 'error';
  lastEventId: number;
  
  // Full state
  diagnostics: DiagnosticsSnapshot | null;
  trades: TradesSnapshot | null;
  
  // Current tick
  currentTick: TickUpdateData | null;
  
  // Connection
  isConnected: boolean;
  error: string | null;
}

export function useBacktestSSE(sessionId: string | null) {
  const [state, setState] = useState<BacktestState>({
    sessionId: null,
    status: 'idle',
    lastEventId: 0,
    diagnostics: null,
    trades: null,
    currentTick: null,
    isConnected: false,
    error: null
  });
  
  const eventSourceRef = useRef<EventSource | null>(null);
  
  useEffect(() => {
    if (!sessionId) return;
    
    // Create EventSource with Last-Event-ID for reconnection
    const eventSource = new EventSource(
      `/api/backtest/${sessionId}/stream`,
      {
        withCredentials: false
      }
    );
    
    // Set Last-Event-ID header manually (if supported)
    // Note: EventSource doesn't support custom headers directly
    // For production, use polyfill or Server-Sent-Events library
    
    eventSourceRef.current = eventSource;
    
    // ==========================================
    // Event 1: initial_state (Compressed)
    // ==========================================
    eventSource.addEventListener('initial_state', (e: MessageEvent) => {
      const data: InitialStateData = JSON.parse(e.data);
      
      // Decompress diagnostics
      const diagnostics = decompressGzipBase64(data.diagnostics);
      
      // Decompress trades
      const trades = decompressGzipBase64(data.trades);
      
      setState(prev => ({
        ...prev,
        sessionId: data.session_id,
        status: 'connected',
        lastEventId: data.event_id,
        diagnostics,
        trades,
        isConnected: true
      }));
      
      console.log('[SSE] Initial state received', {
        diagnostics_size: data.uncompressed_sizes.diagnostics,
        trades_size: data.uncompressed_sizes.trades
      });
    });
    
    // ==========================================
    // Event 2: tick_update (Most Frequent)
    // ==========================================
    eventSource.addEventListener('tick_update', (e: MessageEvent) => {
      const data: TickUpdateData = JSON.parse(e.data);
      
      setState(prev => ({
        ...prev,
        status: 'running',
        lastEventId: data.event_id,
        currentTick: data
      }));
      
      // Optional: Log every 100 ticks
      if (data.tick % 100 === 0) {
        console.log(`[SSE] Tick ${data.tick}:`, {
          positions: data.open_positions.length,
          pnl: data.pnl_summary.total_pnl
        });
      }
    });
    
    // ==========================================
    // Event 3: node_event (Incremental)
    // ==========================================
    eventSource.addEventListener('node_event', (e: MessageEvent) => {
      const data: NodeEventData = JSON.parse(e.data);
      
      // Append to diagnostics history
      setState(prev => {
        if (!prev.diagnostics) return prev;
        
        return {
          ...prev,
          lastEventId: data.event_id,
          diagnostics: {
            ...prev.diagnostics,
            events_history: {
              ...prev.diagnostics.events_history,
              [data.execution_id]: data
            }
          }
        };
      });
      
      console.log('[SSE] Node event:', data.node_id, 'signal:', data.signal_emitted);
    });
    
    // ==========================================
    // Event 4: trade_update (Incremental)
    // ==========================================
    eventSource.addEventListener('trade_update', (e: MessageEvent) => {
      const data: TradeUpdateData = JSON.parse(e.data);
      
      // Append trade and update summary
      setState(prev => {
        if (!prev.trades) return prev;
        
        return {
          ...prev,
          lastEventId: data.event_id,
          trades: {
            ...prev.trades,
            trades: [...prev.trades.trades, data.trade],
            summary: data.summary
          }
        };
      });
      
      console.log('[SSE] Trade closed:', data.trade.symbol, 'P&L:', data.trade.pnl);
    });
    
    // ==========================================
    // Event 5: backtest_complete (Final)
    // ==========================================
    eventSource.addEventListener('backtest_complete', (e: MessageEvent) => {
      const data: BacktestCompleteData = JSON.parse(e.data);
      
      // Decompress final diagnostics and trades
      const finalDiagnostics = decompressGzipBase64(data.diagnostics);
      const finalTrades = decompressGzipBase64(data.trades);
      
      setState(prev => ({
        ...prev,
        status: 'completed',
        lastEventId: data.event_id,
        diagnostics: finalDiagnostics,
        trades: finalTrades,
        isConnected: false
      }));
      
      console.log('[SSE] Backtest complete:', {
        total_ticks: data.total_ticks,
        final_pnl: finalTrades.summary.total_pnl
      });
      
      eventSource.close();
    });
    
    // ==========================================
    // Error Handling
    // ==========================================
    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error:', error);
      
      setState(prev => ({
        ...prev,
        status: 'error',
        isConnected: false,
        error: 'Connection lost'
      }));
      
      // EventSource will auto-reconnect, but we track state
    };
    
    // ==========================================
    // Cleanup
    // ==========================================
    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [sessionId]);
  
  return state;
}

// Helper function
function decompressGzipBase64(compressed: string): any {
  const binaryString = atob(compressed);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  const decompressed = pako.ungzip(bytes, { to: 'string' });
  return JSON.parse(decompressed);
}
```

---

## UI Component Examples

### 1. P&L Dashboard

```typescript
function PnLDashboard({ pnlSummary }: { pnlSummary: PnLSummary | null }) {
  if (!pnlSummary) return <div>No data</div>;
  
  const totalPnl = parseFloat(pnlSummary.total_pnl);
  const realizedPnl = parseFloat(pnlSummary.realized_pnl);
  const unrealizedPnl = parseFloat(pnlSummary.unrealized_pnl);
  
  return (
    <div className="pnl-dashboard">
      <div className={`total-pnl ${totalPnl >= 0 ? 'profit' : 'loss'}`}>
        <h2>Total P&L</h2>
        <div className="amount">₹{totalPnl.toFixed(2)}</div>
      </div>
      
      <div className="pnl-breakdown">
        <div className="metric">
          <span>Realized</span>
          <span className={realizedPnl >= 0 ? 'profit' : 'loss'}>
            ₹{realizedPnl.toFixed(2)}
          </span>
        </div>
        
        <div className="metric">
          <span>Unrealized</span>
          <span className={unrealizedPnl >= 0 ? 'profit' : 'loss'}>
            ₹{unrealizedPnl.toFixed(2)}
          </span>
        </div>
      </div>
      
      <div className="trade-stats">
        <div>Closed: {pnlSummary.closed_trades}</div>
        <div>Open: {pnlSummary.open_trades}</div>
        <div>Win Rate: {pnlSummary.win_rate}%</div>
        <div>W/L: {pnlSummary.winning_trades}/{pnlSummary.losing_trades}</div>
      </div>
    </div>
  );
}
```

---

### 2. Positions Table

```typescript
function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <table className="positions-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Side</th>
          <th>Qty</th>
          <th>Entry</th>
          <th>Current</th>
          <th>P&L</th>
          <th>%</th>
        </tr>
      </thead>
      <tbody>
        {positions.map(pos => {
          const entryPrice = parseFloat(pos.entry_price);
          const currentPrice = parseFloat(pos.current_price);
          const pnl = parseFloat(pos.unrealized_pnl);
          const pnlPercent = ((currentPrice - entryPrice) / entryPrice * 100).toFixed(2);
          
          return (
            <tr key={pos.position_id}>
              <td>{pos.symbol.split(':').pop()}</td>
              <td className={pos.side === 'buy' ? 'buy' : 'sell'}>
                {pos.side.toUpperCase()}
              </td>
              <td>{pos.quantity}</td>
              <td>₹{entryPrice.toFixed(2)}</td>
              <td>₹{currentPrice.toFixed(2)}</td>
              <td className={pnl >= 0 ? 'profit' : 'loss'}>
                ₹{pnl.toFixed(2)}
              </td>
              <td className={parseFloat(pnlPercent) >= 0 ? 'profit' : 'loss'}>
                {pnlPercent}%
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
```

---

### 3. Node Activity Feed

```typescript
function NodeActivityFeed({ nodeExecutions }: { nodeExecutions: Record<string, NodeExecution> }) {
  const executions = Object.values(nodeExecutions)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, 10); // Show last 10
  
  return (
    <div className="activity-feed">
      <h3>Node Activity</h3>
      {executions.map(exec => (
        <div key={exec.execution_id} className="activity-item">
          <div className="node-name">{exec.node_name}</div>
          <div className="node-status">
            {exec.signal_emitted && <span className="signal-badge">Signal Emitted</span>}
          </div>
          <div className="timestamp">{exec.timestamp}</div>
          
          {exec.evaluated_conditions && (
            <div className="conditions">
              {exec.evaluated_conditions.map((cond, i) => (
                <div key={i} className={`condition ${cond.result ? 'pass' : 'fail'}`}>
                  {cond.expression}: {cond.result ? '✓' : '✗'}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

### 4. Complete Backtest Component

```typescript
function LiveBacktest({ strategyId, date }: { strategyId: string; date: string }) {
  const sessionId = `sse-${strategyId}-${date}`;
  const backtestState = useBacktestSSE(sessionId);
  
  return (
    <div className="live-backtest">
      {/* Status Bar */}
      <div className="status-bar">
        <div className={`status ${backtestState.status}`}>
          {backtestState.status.toUpperCase()}
        </div>
        {backtestState.currentTick && (
          <>
            <div>Tick: {backtestState.currentTick.tick}</div>
            <div>Time: {backtestState.currentTick.timestamp}</div>
          </>
        )}
      </div>
      
      {/* P&L Dashboard */}
      {backtestState.currentTick && (
        <PnLDashboard pnlSummary={backtestState.currentTick.pnl_summary} />
      )}
      
      {/* Positions */}
      {backtestState.currentTick && backtestState.currentTick.open_positions.length > 0 && (
        <div className="section">
          <h3>Open Positions</h3>
          <PositionsTable positions={backtestState.currentTick.open_positions} />
        </div>
      )}
      
      {/* Node Activity */}
      {backtestState.currentTick && (
        <div className="section">
          <h3>Node Activity</h3>
          <NodeActivityFeed nodeExecutions={backtestState.currentTick.node_executions} />
        </div>
      )}
      
      {/* Trades History */}
      {backtestState.trades && backtestState.trades.trades.length > 0 && (
        <div className="section">
          <h3>Closed Trades ({backtestState.trades.trades.length})</h3>
          <TradesTable trades={backtestState.trades.trades} />
        </div>
      )}
      
      {/* Error Display */}
      {backtestState.error && (
        <div className="error-message">
          {backtestState.error}
        </div>
      )}
    </div>
  );
}
```

---

## Edge Cases & Error Handling

### 1. Connection Loss (Auto-Reconnect)

```typescript
function useBacktestSSE(sessionId: string | null) {
  const [reconnectCount, setReconnectCount] = useState(0);
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/backtest/${sessionId}/stream`);
    
    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error, reconnecting...', error);
      setReconnectCount(prev => prev + 1);
      
      // EventSource auto-reconnects, but track attempts
      if (reconnectCount > 5) {
        console.error('[SSE] Max reconnect attempts reached');
        eventSource.close();
        // Show UI error message
      }
    };
    
    // Reset count on successful connection
    eventSource.onopen = () => {
      setReconnectCount(0);
    };
    
    return () => eventSource.close();
  }, [sessionId, reconnectCount]);
}
```

---

### 2. Decompression Failure

```typescript
function decompressGzipBase64(compressed: string): any {
  try {
    const binaryString = atob(compressed);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const decompressed = pako.ungzip(bytes, { to: 'string' });
    return JSON.parse(decompressed);
  } catch (error) {
    console.error('[Decompression] Failed:', error);
    
    // Fallback: Try parsing as uncompressed JSON
    try {
      return JSON.parse(compressed);
    } catch {
      // Show error to user
      throw new Error('Failed to decompress data');
    }
  }
}
```

---

### 3. Stale Data Detection

```typescript
function useStaleDataCheck(currentTick: TickUpdateData | null) {
  const [isStale, setIsStale] = useState(false);
  const lastUpdateRef = useRef<number>(Date.now());
  
  useEffect(() => {
    if (currentTick) {
      lastUpdateRef.current = Date.now();
      setIsStale(false);
    }
    
    // Check every 5 seconds
    const interval = setInterval(() => {
      const timeSinceUpdate = Date.now() - lastUpdateRef.current;
      if (timeSinceUpdate > 10000) { // 10 seconds
        setIsStale(true);
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [currentTick]);
  
  return isStale;
}

// Usage in component:
function LiveBacktest() {
  const backtestState = useBacktestSSE(sessionId);
  const isStale = useStaleDataCheck(backtestState.currentTick);
  
  return (
    <div>
      {isStale && (
        <div className="warning">
          ⚠️ No updates received for 10+ seconds. Connection may be lost.
        </div>
      )}
    </div>
  );
}
```

---

### 4. Invalid Event Data

```typescript
eventSource.addEventListener('tick_update', (e: MessageEvent) => {
  try {
    const data: TickUpdateData = JSON.parse(e.data);
    
    // Validate required fields
    if (!data.tick || !data.timestamp || !data.pnl_summary) {
      console.warn('[SSE] Invalid tick_update data:', data);
      return; // Skip this update
    }
    
    // Validate P&L numbers
    if (isNaN(parseFloat(data.pnl_summary.total_pnl))) {
      console.warn('[SSE] Invalid P&L data:', data.pnl_summary);
      return;
    }
    
    // Update state
    setState(prev => ({ ...prev, currentTick: data }));
    
  } catch (error) {
    console.error('[SSE] Failed to parse tick_update:', error);
    // Continue processing other events
  }
});
```

---

## Performance Optimization

### 1. Memoize Expensive Calculations

```typescript
function PositionsTable({ positions }: { positions: Position[] }) {
  // Memoize calculations
  const enrichedPositions = useMemo(() => {
    return positions.map(pos => ({
      ...pos,
      entryPrice: parseFloat(pos.entry_price),
      currentPrice: parseFloat(pos.current_price),
      pnl: parseFloat(pos.unrealized_pnl),
      pnlPercent: ((parseFloat(pos.current_price) - parseFloat(pos.entry_price)) / parseFloat(pos.entry_price) * 100)
    }));
  }, [positions]);
  
  return (
    <table>
      {enrichedPositions.map(pos => (
        <tr key={pos.position_id}>
          <td>₹{pos.pnl.toFixed(2)}</td>
          <td>{pos.pnlPercent.toFixed(2)}%</td>
        </tr>
      ))}
    </table>
  );
}
```

---

### 2. Throttle Rapid Updates

```typescript
import { useRef, useEffect } from 'react';
import { throttle } from 'lodash';

function useThrottledSSE(sessionId: string | null) {
  const [state, setState] = useState<BacktestState>({...});
  
  // Throttle tick_update to max 10/second (100ms)
  const throttledSetTick = useRef(
    throttle((data: TickUpdateData) => {
      setState(prev => ({ ...prev, currentTick: data }));
    }, 100)
  ).current;
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/backtest/${sessionId}/stream`);
    
    eventSource.addEventListener('tick_update', (e: MessageEvent) => {
      const data: TickUpdateData = JSON.parse(e.data);
      throttledSetTick(data); // Throttled
    });
    
    return () => eventSource.close();
  }, [sessionId, throttledSetTick]);
  
  return state;
}
```

---

### 3. Virtual Scrolling for Large Lists

```typescript
// For 1000+ trades, use react-window for virtual scrolling
import { FixedSizeList } from 'react-window';

function TradesTable({ trades }: { trades: Trade[] }) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const trade = trades[index];
    return (
      <div style={style} className="trade-row">
        <span>{trade.symbol}</span>
        <span>{trade.pnl}</span>
      </div>
    );
  };
  
  return (
    <FixedSizeList
      height={400}
      itemCount={trades.length}
      itemSize={50}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}
```

---

## Summary

✅ **5 event types** with complete TypeScript interfaces  
✅ **Decompression utility** for gzip + base64  
✅ **React hook** for SSE consumption  
✅ **Component examples** for P&L, positions, activity feed  
✅ **Edge case handling** for connection loss, invalid data, staleness  
✅ **Performance optimization** with memoization, throttling, virtual scrolling  

**Next Steps for UI Team:**
1. Install `pako` for decompression: `npm install pako @types/pako`
2. Copy `useBacktestSSE` hook into your codebase
3. Implement UI components using provided examples
4. Test with live SSE endpoint from backend
5. Add custom styling and animations

**Backend SSE Endpoint:**
```
GET /api/backtest/{session_id}/stream
Content-Type: text/event-stream
```

The UI is now ready to consume all SSE events with full type safety and error handling.
