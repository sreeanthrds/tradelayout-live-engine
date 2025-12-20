#!/usr/bin/env python3
"""
Show detailed diagnostic information for each transaction
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_runner import run_backtest

# Strategy to test
strategy_ids = ['5708424d-5962-4629-978c-05b3a174e104']
backtest_date = '2024-10-29'

print(f"\n{'='*100}")
print(f"DETAILED TRANSACTION DIAGNOSTICS")
print(f"{'='*100}\n")

# Run backtest
results = run_backtest(
    strategy_ids=strategy_ids,
    backtest_date=backtest_date
)

print(f"Total Positions: {len(results.positions)}\n")

# Process each position
for pos_idx, (position_id, pos) in enumerate(results.positions.items(), 1):
    print(f"\n{'='*100}")
    print(f"POSITION {pos_idx}: {position_id}")
    print(f"{'='*100}\n")
    
    transactions = pos.get('transactions', [])
    
    if not transactions:
        print("No transactions found.\n")
        continue
    
    # Show each transaction with full diagnostic data
    for txn_idx, txn in enumerate(transactions, 1):
        position_num = txn.get('position_num', txn_idx)
        entry_data = txn.get('entry', {})
        exit_data = txn.get('exit', {})
        
        print(f"\n{'─'*100}")
        print(f"Transaction {txn_idx}: {position_id} (position_num={position_num})")
        print(f"{'─'*100}\n")
        
        # Entry info with enhanced snapshot
        entry_snapshot = entry_data.get('entry_snapshot', {})
        spot_at_entry = entry_data.get('nifty_spot') or entry_data.get('underlying_price_on_entry', 'N/A')
        
        # Get option contract LTP at entry
        symbol = txn.get('symbol')
        ltp_store_entry = entry_snapshot.get('ltp_store_snapshot', {})
        contract_ltp_entry = 'N/A'
        if symbol and symbol in ltp_store_entry:
            contract_data = ltp_store_entry[symbol]
            if isinstance(contract_data, dict):
                contract_ltp_entry = contract_data.get('ltp') or contract_data.get('price', 'N/A')
            else:
                contract_ltp_entry = contract_data
        
        print(f"📥 ENTRY:")
        print(f"   Time: {txn.get('entry_time')}")
        print(f"   Entry Price: {txn.get('entry_price')}")
        print(f"   Symbol: {txn.get('symbol')}")
        print(f"   Quantity: {txn.get('quantity')}")
        print(f"   Order ID: {txn.get('order_id')}")
        print(f"   Entry Node: {txn.get('node_id')}")
        print(f"   Re-entry Num: {txn.get('reEntryNum', 0)}")
        print(f"   💹 Spot at Entry: {spot_at_entry}")
        print(f"   📜 Contract LTP at Entry: {contract_ltp_entry}")
        
        # Exit info (if closed)
        if txn.get('status') == 'closed':
            exit_snapshot = exit_data.get('exit_snapshot', {})
            spot_at_exit = exit_data.get('nifty_spot') or exit_data.get('underlying_price_on_exit', 'N/A')
            
            # Get option contract LTP at exit
            ltp_store_exit = exit_snapshot.get('ltp_store_snapshot', {})
            contract_ltp_exit = 'N/A'
            if symbol and symbol in ltp_store_exit:
                contract_data = ltp_store_exit[symbol]
                if isinstance(contract_data, dict):
                    contract_ltp_exit = contract_data.get('ltp') or contract_data.get('price', 'N/A')
                else:
                    contract_ltp_exit = contract_data
            
            print(f"\n📤 EXIT:")
            print(f"   Time: {txn.get('exit_time')}")
            print(f"   Exit Price: {exit_data.get('price', 'N/A')}")
            print(f"   PNL: {txn.get('pnl', 0):.2f}")
            print(f"   Exit Node: {exit_data.get('node_id', 'N/A')}")
            print(f"   Trigger Node: {exit_data.get('trigger_node_id', 'N/A')}")
            print(f"   Close Reason: {exit_data.get('close_reason', 'N/A')}")
            print(f"   💹 Spot at Exit: {spot_at_exit}")
            print(f"   📜 Contract LTP at Exit: {contract_ltp_exit}")
            
            # Show spot movement
            if spot_at_entry != 'N/A' and spot_at_exit != 'N/A':
                try:
                    spot_change = float(spot_at_exit) - float(spot_at_entry)
                    spot_change_pct = (spot_change / float(spot_at_entry)) * 100
                    direction = "📈" if spot_change > 0 else "📉"
                    print(f"   {direction} Spot Movement: {spot_change:+.2f} ({spot_change_pct:+.2f}%)")
                except:
                    pass
            
            # Show contract price movement
            if contract_ltp_entry != 'N/A' and contract_ltp_exit != 'N/A':
                try:
                    contract_change = float(contract_ltp_exit) - float(contract_ltp_entry)
                    contract_change_pct = (contract_change / float(contract_ltp_entry)) * 100
                    direction = "📈" if contract_change > 0 else "📉"
                    print(f"   {direction} Contract Movement: {contract_change:+.2f} ({contract_change_pct:+.2f}%)")
                except:
                    pass
        
        # Diagnostic data from entry
        diagnostic_data = entry_data.get('diagnostic_data', {})
        conditions = diagnostic_data.get('conditions_evaluated', [])
        
        if conditions:
            print(f"\n🔍 ENTRY CONDITIONS EVALUATED ({len(conditions)} total):")
            print(f"   Showing conditions at entry trigger time:\n")
            
            # Group conditions by timestamp
            from collections import defaultdict
            conditions_by_time = defaultdict(list)
            for cond in conditions:
                ts = cond.get('timestamp', 'Unknown')
                conditions_by_time[ts].append(cond)
            
            # Show only the timestamp that matches the entry time
            entry_time_str = txn.get('entry_time', '')
            entry_time_key = entry_time_str.split('.')[0] if '.' in entry_time_str else entry_time_str.split('+')[0]
            
            matching_conditions = []
            for ts, conds in conditions_by_time.items():
                if entry_time_key in str(ts):
                    matching_conditions = conds
                    break
            
            if not matching_conditions:
                # Show last few conditions
                matching_conditions = conditions[-10:]
            
            for cond_idx, cond in enumerate(matching_conditions, 1):
                cond_text = cond.get('condition_text', 'N/A')
                timestamp = cond.get('timestamp', 'N/A')
                result = cond.get('result', False)
                result_icon = '✓' if result else '✗'
                
                print(f"   {cond_idx}. [{timestamp}] {cond_text}")
        else:
            print(f"\n🔍 ENTRY CONDITIONS: No diagnostic data available")
        
        # Exit conditions (if closed)
        if txn.get('status') == 'closed':
            exit_diagnostic = exit_data.get('diagnostic_data', {})
            exit_conditions = exit_diagnostic.get('conditions_evaluated', [])
            
            if exit_conditions:
                print(f"\n🔍 EXIT CONDITIONS EVALUATED ({len(exit_conditions)} total):")
                
                # Group by timestamp for exit
                exit_time_str = txn.get('exit_time', '')
                exit_time_key = exit_time_str.split('.')[0] if '.' in exit_time_str else exit_time_str.split('+')[0]
                
                exit_conditions_by_time = defaultdict(list)
                for cond in exit_conditions:
                    ts = cond.get('timestamp', 'Unknown')
                    exit_conditions_by_time[ts].append(cond)
                
                matching_exit_conditions = []
                for ts, conds in exit_conditions_by_time.items():
                    if exit_time_key in str(ts):
                        matching_exit_conditions = conds
                        break
                
                if not matching_exit_conditions:
                    matching_exit_conditions = exit_conditions[-10:]
                
                for cond_idx, cond in enumerate(matching_exit_conditions, 1):
                    cond_text = cond.get('condition_text', 'N/A')
                    lhs_value = cond.get('lhs_value')
                    rhs_value = cond.get('rhs_value')
                    operator = cond.get('operator', '?')
                    result = cond.get('result', False)
                    
                    print(f"   {cond_idx}. {cond_text}")
                    if lhs_value is not None and rhs_value is not None:
                        print(f"      Substitution: {lhs_value} {operator} {rhs_value} = {result}")
        
        # Node variables snapshots
        entry_node_vars = entry_data.get('node_variables', {})
        if entry_node_vars:
            print(f"\n📊 NODE VARIABLES AT ENTRY:")
            for var_name, var_value in entry_node_vars.items():
                print(f"   {var_name}: {var_value}")
        
        if txn.get('status') == 'closed':
            exit_node_vars = exit_data.get('node_variables', {})
            if exit_node_vars:
                print(f"\n📊 NODE VARIABLES AT EXIT:")
                for var_name, var_value in exit_node_vars.items():
                    print(f"   {var_name}: {var_value}")
        
        # Full snapshot summary
        if entry_snapshot:
            print(f"\n📸 ENTRY SNAPSHOT SUMMARY:")
            print(f"   Timestamp: {entry_snapshot.get('timestamp')}")
            print(f"   Spot Price: {entry_snapshot.get('spot_price')}")
            ltp_snapshot = entry_snapshot.get('ltp_store_snapshot', {})
            if ltp_snapshot:
                print(f"   LTP Store Keys: {list(ltp_snapshot.keys())}")
        
        if txn.get('status') == 'closed' and exit_snapshot:
            print(f"\n📸 EXIT SNAPSHOT SUMMARY:")
            print(f"   Timestamp: {exit_snapshot.get('timestamp')}")
            print(f"   Spot Price: {exit_snapshot.get('spot_price')}")
            print(f"   Trigger Node: {exit_snapshot.get('trigger_node_id')}")
            print(f"   Close Reason: {exit_snapshot.get('close_reason')}")
        
        print()

print(f"\n{'='*100}\n")
