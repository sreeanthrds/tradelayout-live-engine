#!/usr/bin/env python3
"""
Show detailed positions from Oct 29, 2024 backtest
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime
from src.backtesting.backtest_runner import run_backtest

print(f"\n{'='*100}")
print(f"DETAILED POSITIONS: Strategy 5708424d on Oct 29, 2024")
print(f"{'='*100}\n")

results = run_backtest(
    strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
    backtest_date='2024-10-29'
)

print(f"\n{'='*100}")
print(f"POSITION DETAILS")
print(f"{'='*100}\n")

print(f"Total Positions: {len(results.positions)}\n")

# results.positions is a dict: {position_id: position_data}
for idx, (position_id, pos) in enumerate(results.positions.items(), 1):
    print(f"{'='*100}")
    print(f"POSITION {idx}: {pos.get('position_id')}")
    print(f"{'='*100}")
    print(f"   Symbol: {pos.get('symbol')}")
    print(f"   Status: {pos.get('status').upper()}")
    print(f"   Quantity: {pos.get('quantity')}")
    print(f"   Overall PNL: {pos.get('pnl', 0):.2f}")
    print(f"   Position Number: {pos.get('position_num', 1)}")
    print(f"   Re-Entry Number: {pos.get('reEntryNum', 0)}")
    
    # Show transactions
    transactions = pos.get('transactions', [])
    print(f"\n   📊 TRANSACTIONS ({len(transactions)} total):")
    
    for txn_idx, txn in enumerate(transactions, 1):
        print(f"\n   {'─'*96}")
        print(f"   Transaction {txn_idx}:")
        print(f"   {'─'*96}")
        print(f"      Type: {txn.get('type', 'N/A').upper()}")
        print(f"      Time: {txn.get('entry_time') if txn.get('type') == 'entry' else txn.get('exit_time')}")
        print(f"      Price: {txn.get('entry_price') if txn.get('type') == 'entry' else txn.get('exit_price')}")
        print(f"      Quantity: {txn.get('quantity', 0)}")
        print(f"      Status: {txn.get('status', 'N/A')}")
        
        if txn.get('type') == 'exit':
            print(f"      PNL: {txn.get('pnl', 0):.2f}")
            print(f"      Exit Reason: {txn.get('exit_reason', 'N/A')}")
        
        # Show entry condition evaluations
        if txn.get('type') == 'entry':
            diagnostic_data = txn.get('diagnostic_data', {})
            conditions = diagnostic_data.get('conditions_evaluated', [])
            if conditions:
                print(f"\n      Entry Conditions Evaluated:")
                for cond in conditions:
                    cond_text = cond.get('condition_text', 'No text')
                    print(f"         {cond_text}")
        
        # Show exit condition evaluations
        if txn.get('type') == 'exit':
            diagnostic_data = txn.get('diagnostic_data', {})
            conditions = diagnostic_data.get('conditions_evaluated', [])
            if conditions:
                print(f"\n      Exit Conditions Evaluated:")
                for cond in conditions:
                    cond_text = cond.get('condition_text', 'No text')
                    print(f"         {cond_text}")
    
    print()

print(f"{'='*100}\n")
