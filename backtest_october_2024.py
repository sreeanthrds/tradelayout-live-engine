#!/usr/bin/env python3
"""
Backtest Strategy for Complete October 2024 with Progress Updates
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime, timedelta
from src.backtesting.backtest_runner import run_backtest
import json

# Strategy to test
strategy_ids = ['5708424d-5962-4629-978c-05b3a174e104']

# October 2024 date range
start_date = datetime(2024, 10, 1)
end_date = datetime(2024, 10, 31)

print(f"\n{'='*100}")
print(f"🚀 BACKTESTING STRATEGY FOR OCTOBER 2024")
print(f"{'='*100}")
print(f"Strategy ID: {strategy_ids[0]}")
print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"{'='*100}\n")
sys.stdout.flush()

# Track overall statistics
total_days = 0
trading_days = 0
total_transactions = 0
total_pnl = 0
daily_results = []
all_positions = {}

# Generate all dates in October 2024
current_date = start_date
date_count = 0

while current_date <= end_date:
    date_str = current_date.strftime('%Y-%m-%d')
    
    # Skip weekends (Saturday=5, Sunday=6)
    if current_date.weekday() >= 5:
        print(f"⏭️  Skipping {date_str} (Weekend)")
        sys.stdout.flush()
        current_date += timedelta(days=1)
        continue
    
    total_days += 1
    date_count += 1
    
    print(f"\n📅 [{date_count}/{22}] Processing: {date_str} ({current_date.strftime('%A')})...", end=' ')
    sys.stdout.flush()
    
    try:
        # Run backtest for this date (suppress verbose output)
        results = run_backtest(
            strategy_ids=strategy_ids,
            backtest_date=date_str
        )
        
        # Store positions
        all_positions[date_str] = results.positions
        
        # Count transactions for this day
        day_transactions = 0
        day_pnl = 0
        day_positions = []
        
        for position_id, pos in results.positions.items():
            transactions = pos.get('transactions', [])
            for txn in transactions:
                if txn.get('status') == 'closed':
                    day_transactions += 1
                    pnl = txn.get('pnl', 0)
                    day_pnl += pnl
                    day_positions.append({
                        'position_id': position_id,
                        'position_num': txn.get('position_num'),
                        'entry_time': txn.get('entry_time'),
                        'exit_time': txn.get('exit_time'),
                        'pnl': pnl
                    })
        
        total_transactions += day_transactions
        total_pnl += day_pnl
        
        if day_transactions > 0:
            trading_days += 1
            pnl_emoji = "📈" if day_pnl > 0 else "📉" if day_pnl < 0 else "➖"
            print(f"{pnl_emoji} {day_transactions} trades, PNL: {day_pnl:+.2f}")
            daily_results.append({
                'date': date_str,
                'transactions': day_transactions,
                'pnl': day_pnl,
                'positions': day_positions
            })
        else:
            print(f"⚪ No trades")
        sys.stdout.flush()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.stdout.flush()
    
    current_date += timedelta(days=1)

# Print summary
print(f"\n\n{'='*100}")
print(f"📊 OCTOBER 2024 SUMMARY")
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

# Profit/Loss days
profit_days = [d for d in daily_results if d['pnl'] > 0]
loss_days = [d for d in daily_results if d['pnl'] < 0]
breakeven_days = [d for d in daily_results if d['pnl'] == 0]

print(f"\nProfit Days: {len(profit_days)}")
print(f"Loss Days: {len(loss_days)}")
print(f"Breakeven Days: {len(breakeven_days)}")

if len(profit_days) > 0 and len(loss_days) > 0:
    win_rate = (len(profit_days) / trading_days) * 100
    print(f"Win Rate: {win_rate:.2f}%")

# Show daily breakdown
if daily_results:
    print(f"\n{'─'*100}")
    print(f"DAILY BREAKDOWN")
    print(f"{'─'*100}\n")
    print(f"{'Date':<12} {'Trades':<10} {'PNL':<15} {'Status':<10}")
    print(f"{'─'*47}")
    
    for day in daily_results:
        pnl_str = f"{day['pnl']:>10.2f}"
        status = "✅ Profit" if day['pnl'] > 0 else "❌ Loss" if day['pnl'] < 0 else "➖ Breakeven"
        print(f"{day['date']:<12} {day['transactions']:<10} {pnl_str:<15} {status}")

# Save detailed results to file
output_file = 'october_2024_backtest_results.json'
with open(output_file, 'w') as f:
    json.dump({
        'summary': {
            'total_days': total_days,
            'trading_days': trading_days,
            'total_transactions': total_transactions,
            'total_pnl': total_pnl,
            'profit_days': len(profit_days),
            'loss_days': len(loss_days),
            'breakeven_days': len(breakeven_days)
        },
        'daily_results': daily_results
    }, f, indent=2, default=str)

print(f"\n✅ Detailed results saved to: {output_file}")
print(f"\n{'='*100}\n")
