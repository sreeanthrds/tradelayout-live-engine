# Transaction-Centric UI Design

## Problem
Current diagnostics is organized by **node_id**. Users need **transaction view** showing complete trade story.

## Complete Flow (5 Steps)

```
Entry Signal → Entry → Exit Signal → Exit → Re-Entry Signal
```

## Transaction Data Structure

```typescript
interface Transaction {
  transaction_id: number;
  position_id: string;
  re_entry_num: number;
  symbol: string;
  
  // 1. Entry Signal
  entry_signal: {
    timestamp: string;
    node_name: string;  // "Entry condition - Bullish"
  };
  
  // 2. Entry
  entry: {
    timestamp: string;
    node_name: string;  // "Entry 2 - Bullish"
    price: number;
    side: string;
  };
  
  // 3. Exit Signal (CRITICAL - shows why)
  exit_signal: {
    timestamp: string;
    node_name: string;  // "Exit condition - SL" / "Exit condition - Target"
    exit_reason: "SL" | "Target" | "TSL";
  };
  
  // 4. Exit
  exit: {
    timestamp: string;
    node_name: string;  // "Exit 3 - SL"
    exit_price: number;
    pnl: number;
  };
  
  // 5. Re-Entry Signal (optional)
  re_entry_signal?: {
    timestamp: string;
    will_re_enter: boolean;
  };
}
```

## Build Algorithm

```typescript
function buildTransactions(diagnostics): Transaction[] {
  const transactions = [];
  
  // Step 1: Find all entries
  const entries = findNodeEvents(diagnostics, 'EntryNode');
  
  entries.forEach(entry => {
    const positionId = entry.position.position_id;
    const reEntryNum = entry.entry_config.re_entry_num;
    
    // Step 2: Find entry signal (parent)
    const entrySignal = findParentEvent(diagnostics, entry.node_id, 'EntrySignalNode');
    
    // Step 3: Find exit signal (child)
    const exitSignal = findChildEvent(diagnostics, positionId, 'ExitSignalNode');
    
    // Step 4: Find exit (child of exit signal)
    const exit = findChildEvent(diagnostics, positionId, 'ExitNode');
    
    // Step 5: Find re-entry signal (child of exit)
    const reEntrySignal = exit?.children_nodes ? 
      findNodeById(diagnostics, exit.children_nodes[0].id) : null;
    
    transactions.push({
      transaction_id: transactions.length + 1,
      position_id: positionId,
      re_entry_num: reEntryNum,
      symbol: entry.action.symbol,
      entry_signal: entrySignal,
      entry: entry,
      exit_signal: exitSignal,
      exit: exit,
      re_entry_signal: reEntrySignal
    });
  });
  
  return transactions;
}
```

## UI Component

```tsx
<TransactionCard>
  <Timeline>
    {/* 1 */}
    <Step icon="🟢">Entry Signal: {tx.entry_signal.node_name}</Step>
    
    {/* 2 */}
    <Step icon="📥">Entry: {tx.entry.side} @ ₹{tx.entry.price}</Step>
    
    {/* 3 - CRITICAL */}
    <Step icon="🔔">Exit Signal: {tx.exit_signal.node_name} ({tx.exit_signal.exit_reason})</Step>
    
    {/* 4 */}
    <Step icon="📤">Exit: @ ₹{tx.exit.exit_price} | P&L: ₹{tx.exit.pnl}</Step>
    
    {/* 5 */}
    {tx.re_entry_signal && (
      <Step icon="🔄">Re-Entry: {tx.re_entry_signal.will_re_enter ? 'Yes' : 'No'}</Step>
    )}
  </Timeline>
</TransactionCard>
```

## Parent-Child Relationship

```
Entry Signal (EntrySignalNode)
    ↓ children_nodes
Entry (EntryNode) → creates position_id
    ↓ children_nodes
Exit Signal (ExitSignalNode) → monitors position_id
    ↓ children_nodes
Exit (ExitNode) → closes position_id
    ↓ children_nodes
Re-Entry Signal (ReEntrySignalNode)
```

## Key Points

1. **Link by position_id**: Track same position across nodes
2. **Link by re_entry_num**: Group re-entries together
3. **Exit Signal shows WHY**: SL/Target/TSL trigger reason
4. **Parent-child via children_nodes**: Follow the chain
5. **Timeline order**: entry_signal → entry → exit_signal → exit → re_entry

This transforms node-centric data into user-friendly transaction stories.
