#!/usr/bin/env python3
"""
Backtest Strategy for Complete October 2024
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime, timedelta
from src.backtesting.backtest_runner import run_backtest

# Strategy to test
strategy_ids = ['5708424d-5962-4629-978c-05b3a174e104']

# October 2024 date range
start_date = datetime(2024, 10, 1)
end_date = datetime(2024, 10, 31)

print(f"\n{'='*100}")
print(f"BACKTESTING STRATEGY FOR OCTOBER 2024")
print(f"{'='*100}")
print(f"Strategy ID: {strategy_ids[0]}")
print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"{'='*100}\n")

# Track overall statistics
total_days = 0
trading_days = 0
total_transactions = 0
total_pnl = 0
daily_results = []

# Generate all dates in October 2024
current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime('%Y-%m-%d')
    
    # Skip weekends (Saturday=5, Sunday=6)
    if current_date.weekday() >= 5:
        print(f"⏭️  Skipping {date_str} (Weekend)")
        current_date += timedelta(days=1)
        continue
    
    total_days += 1
    
    print(f"\n{'─'*100}")
    print(f"📅 Testing: {date_str} ({current_date.strftime('%A')})")
    print(f"{'─'*100}")
    
    try:
        # Run backtest for this date
        results = run_backtest(
            strategy_ids=strategy_ids,
            backtest_date=date_str
        )
        
        # Count transactions for this day
        day_transactions = 0
        day_pnl = 0
        
        for position_id, pos in results.positions.items():
            transactions = pos.get('transactions', [])
            for txn in transactions:
                if txn.get('status') == 'closed':
                    day_transactions += 1
                    pnl = txn.get('pnl', 0)
                    day_pnl += pnl
        
        total_transactions += day_transactions
        total_pnl += day_pnl
        
        if day_transactions > 0:
            trading_days += 1
            print(f"\n✅ {date_str}: {day_transactions} transactions, PNL: {day_pnl:.2f}")
            daily_results.append({
                'date': date_str,
                'transactions': day_transactions,
                'pnl': day_pnl
            })
        else:
            print(f"\n⚪ {date_str}: No transactions")
        
    except Exception as e:
        print(f"\n❌ Error on {date_str}: {e}")
        import traceback
        traceback.print_exc()
    
    current_date += timedelta(days=1)

# Print summary
print(f"\n\n{'='*100}")
print(f"OCTOBER 2024 SUMMARY")
print(f"{'='*100}\n")

print(f"Total Days Tested: {total_days}")
print(f"Trading Days (with transactions): {trading_days}")
print(f"Total Transactions: {total_transactions}")
print(f"Total PNL: {total_pnl:.2f}")

if trading_days > 0:
    avg_pnl_per_trading_day = total_pnl / trading_days
    print(f"Average PNL per Trading Day: {avg_pnl_per_trading_day:.2f}")

if total_transactions > 0:
    avg_pnl_per_transaction = total_pnl / total_transactions
    print(f"Average PNL per Transaction: {avg_pnl_per_transaction:.2f}")

# Show daily breakdown
if daily_results:
    print(f"\n{'─'*100}")
    print(f"DAILY BREAKDOWN")
    print(f"{'─'*100}\n")
    print(f"{'Date':<12} {'Transactions':<15} {'PNL':<15}")
    print(f"{'─'*42}")
    
    for day in daily_results:
        pnl_str = f"{day['pnl']:>10.2f}"
        pnl_emoji = "📈" if day['pnl'] > 0 else "📉" if day['pnl'] < 0 else "➖"
        print(f"{day['date']:<12} {day['transactions']:<15} {pnl_emoji} {pnl_str}")

print(f"\n{'='*100}\n")
