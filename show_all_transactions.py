#!/usr/bin/env python3
"""
Show ALL transactions from Oct 29, 2024 backtest
"""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime
from src.backtesting.backtest_runner import run_backtest

print(f"\n{'='*100}")
print(f"ALL TRANSACTIONS: Strategy 5708424d on Oct 29, 2024")
print(f"{'='*100}\n")

results = run_backtest(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date='2024-10-29'
)

print(f"\n{'='*100}")
print(f"DETAILED TRANSACTION REPORT")
print(f"{'='*100}\n")

print(f"Total Positions: {len(results.positions)}\n")

# Track all transactions
all_transactions = []

for idx, (position_id, pos) in enumerate(results.positions.items(), 1):
    print(f"{'='*100}")
    print(f"POSITION {idx}: {position_id}")
    
    # NEW: Read from transactions array instead of position-level data
    transactions = pos.get('transactions', [])
    print(f"Total Transactions: {len(transactions)}")
    
    if not transactions:
        # Fallback to old logic if no transactions array
        print(f"Entry Time: {pos.get('entry_time')}")
        print(f"Exit Time: {pos.get('exit_time')}")
        print(f"Symbol: {pos.get('symbol')}")
        print(f"Entry Price: {pos.get('entry_price')}")
        print(f"Exit Price: {pos.get('exit_price')}")
        print(f"PNL: {pos.get('pnl')}")
        
        # Entry transaction
        entry_txn = {
            'position_id': position_id,
            'position_num': idx,
            'type': 'ENTRY',
            'time': pos.get('entry_time'),
            'price': pos.get('entry_price'),
            'quantity': pos.get('quantity'),
            'symbol': pos.get('symbol'),
            'node_id': pos.get('node_id'),
            'order_id': pos.get('order_id')
        }
        all_transactions.append(entry_txn)
        
        # Exit transaction
        if pos.get('status') == 'closed':
            exit_txn = {
                'position_id': position_id,
                'position_num': idx,
                'type': 'EXIT',
                'time': pos.get('exit_time'),
                'price': pos.get('exit_price'),
                'quantity': pos.get('quantity'),
                'symbol': pos.get('symbol'),
                'pnl': pos.get('pnl'),
                'exit_node_id': pos.get('exit_node_id')
            }
            all_transactions.append(exit_txn)
    else:
        # NEW: Extract all transactions from transactions array
        for txn_idx, txn in enumerate(transactions, 1):
            print(f"\n   Transaction {txn_idx}:")
            print(f"      Position Num: {txn.get('position_num', 'N/A')}")
            print(f"      Status: {txn.get('status', 'N/A')}")
            print(f"      Entry Time: {txn.get('entry_time')}")
            print(f"      Entry Price: {txn.get('entry_price')}")
            if txn.get('status') == 'closed':
                print(f"      Exit Time: {txn.get('exit_time')}")
                print(f"      Exit Price: {txn.get('exit', {}).get('price', 'N/A')}")
                print(f"      PNL: {txn.get('pnl')}")
            
            # Add entry to all_transactions
            entry_txn = {
                'position_id': position_id,
                'position_num': txn.get('position_num', txn_idx),
                'type': 'ENTRY',
                'time': txn.get('entry_time'),
                'price': txn.get('entry_price'),
                'quantity': txn.get('quantity'),
                'symbol': txn.get('symbol'),
                'node_id': txn.get('node_id'),
                'order_id': txn.get('order_id')
            }
            all_transactions.append(entry_txn)
            
            # Add exit if closed
            if txn.get('status') == 'closed':
                exit_data = txn.get('exit', {})
                exit_txn = {
                    'position_id': position_id,
                    'position_num': txn.get('position_num', txn_idx),
                    'type': 'EXIT',
                    'time': txn.get('exit_time'),
                    'price': exit_data.get('price', txn.get('exit_price')),
                    'quantity': txn.get('quantity'),
                    'symbol': txn.get('symbol'),
                    'pnl': txn.get('pnl'),
                    'exit_node_id': exit_data.get('node_id')
                }
                all_transactions.append(exit_txn)
    
    if transactions:
        print(f"\n   {'─'*96}")
        print(f"   Transaction Details from Array:")
        print(f"   {'─'*96}")
        for txn_idx, txn in enumerate(transactions, 1):
            print(f"\n   Transaction {txn_idx}:")
            print(f"      Keys: {list(txn.keys())}")
            print(json.dumps(txn, indent=10, default=str))
    
    # Show entry conditions with NEW TEXT FORMATTING
    diagnostic_data = pos.get('diagnostic_data', {})
    conditions = diagnostic_data.get('conditions_evaluated', [])
    if conditions:
        print(f"\n   📋 Entry Conditions Evaluated ({len(conditions)} conditions):")
        for cond_idx, cond in enumerate(conditions, 1):
            cond_text = cond.get('condition_text', 'No text available')
            print(f"      {cond_idx}. {cond_text}")
    
    print()

print(f"\n{'='*100}")
print(f"TRANSACTION SUMMARY")
print(f"{'='*100}\n")

print(f"Total Transactions: {len(all_transactions)}\n")

for idx, txn in enumerate(all_transactions, 1):
    # Display as: position_id (position_num=X) to distinguish re-entries
    position_id = txn['position_id']
    position_num = txn.get('position_num', 1)
    display_id = f"{position_id} (position_num={position_num})"
    
    print(f"{idx}. [{txn['type']}] {display_id}")
    print(f"   Time: {txn['time']}")
    print(f"   Symbol: {txn['symbol']}")
    print(f"   Price: {txn['price']:.2f}")
    print(f"   Quantity: {txn['quantity']}")
    if txn['type'] == 'EXIT':
        print(f"   PNL: {txn.get('pnl', 0):.2f}")
    
    # Show diagnostic data if available
    if txn.get('diagnostic_data'):
        print(f"   💡 Diagnostic: Available (use --verbose to see details)")
    
    print()

print(f"{'='*100}\n")
