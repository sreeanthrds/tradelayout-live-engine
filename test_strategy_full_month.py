#!/usr/bin/env python3
"""
Test Strategy for Full Month - October 2024
Runs backtest for all trading days and measures execution time
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import date, datetime, timedelta
from show_dashboard_data import run_dashboard_backtest
from src.utils.market_calendar import get_trading_days_in_month, validate_backtest_date, get_holiday_name
import time
import json

def test_full_month(strategy_id: str, year: int = 2024, month: int = 10):
    """
    Test strategy for all days in a month
    
    Args:
        strategy_id: Strategy UUID to test
        year: Year to test
        month: Month to test (1-12)
    """
    
    # Get only actual trading days (excludes weekends and holidays)
    trading_days = get_trading_days_in_month(year, month)
    
    # Also get all days for reference
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    all_days = []
    current_date = start_date
    while current_date < end_date:
        all_days.append(current_date)
        current_date += timedelta(days=1)
    
    print(f"\n{'='*100}")
    print(f"FULL MONTH BACKTEST - {start_date.strftime('%B %Y')}")
    print(f"Strategy: {strategy_id}")
    print(f"{'='*100}\n")
    
    print(f"📅 Trading Days to Test: {len(trading_days)}")
    print(f"   From: {trading_days[0]}")
    print(f"   To:   {trading_days[-1]}")
    print(f"\n{'='*100}\n")
    
    # Track results
    all_results = []
    total_positions = 0
    total_pnl = 0
    winning_days = 0
    losing_days = 0
    breakeven_days = 0
    failed_days = []
    
    # Start timing
    start_time = time.time()
    
    for idx, test_date in enumerate(trading_days, 1):
        print(f"\n{'='*100}")
        print(f"📅 Day {idx}/{len(trading_days)}: {test_date.strftime('%Y-%m-%d (%A)')}")
        print(f"{'='*100}")
        
        day_start_time = time.time()
        
        try:
            # Run backtest for this day
            result = run_dashboard_backtest(strategy_id, test_date)
            
            day_end_time = time.time()
            day_duration = day_end_time - day_start_time
            
            if result and 'summary' in result:
                summary = result['summary']
                day_pnl = summary.get('total_pnl', 0)
                day_positions = summary.get('total_positions', 0)
                
                total_positions += day_positions
                total_pnl += day_pnl
                
                if day_pnl > 0:
                    winning_days += 1
                    day_status = '🟢 WIN'
                elif day_pnl < 0:
                    losing_days += 1
                    day_status = '🔴 LOSS'
                else:
                    breakeven_days += 1
                    day_status = '⚪ BREAKEVEN'
                
                print(f"\n✅ Day Complete:")
                print(f"   Status: {day_status}")
                print(f"   Positions: {day_positions}")
                print(f"   P&L: ₹{day_pnl:.2f}")
                print(f"   Duration: {day_duration:.2f}s")
                
                all_results.append({
                    'date': test_date.strftime('%Y-%m-%d'),
                    'day_name': test_date.strftime('%A'),
                    'positions': day_positions,
                    'pnl': day_pnl,
                    'duration': round(day_duration, 2),
                    'summary': summary
                })
            else:
                failed_days.append(test_date.strftime('%Y-%m-%d'))
                print(f"\n❌ Day Failed: No results returned")
                
        except ValueError as e:
            # ValueError = validation errors (non-trading day, no data)
            day_end_time = time.time()
            day_duration = day_end_time - day_start_time
            error_str = str(e)
            
            if "Cannot backtest" in error_str or "No tick data" in error_str:
                # Expected error for non-trading days
                print(f"\n⚠️ Skipped: {error_str}")
            else:
                failed_days.append(test_date.strftime('%Y-%m-%d'))
                print(f"\n❌ Day Failed (Validation): {error_str}")
            print(f"   Duration: {day_duration:.2f}s")
                
        except Exception as e:
            # Other errors (network, ClickHouse, etc.)
            day_end_time = time.time()
            day_duration = day_end_time - day_start_time
            failed_days.append(test_date.strftime('%Y-%m-%d'))
            
            error_str = str(e)
            if "NameResolutionError" in error_str or "Max retries" in error_str:
                print(f"\n❌ Day Failed (Network): Connection error to ClickHouse")
            else:
                print(f"\n❌ Day Failed: {error_str[:100]}")
            print(f"   Duration: {day_duration:.2f}s")
    
    # End timing
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Calculate statistics
    successful_days = len(all_results)
    avg_pnl_per_day = total_pnl / successful_days if successful_days > 0 else 0
    avg_positions_per_day = total_positions / successful_days if successful_days > 0 else 0
    
    # Print final report
    print(f"\n\n{'='*100}")
    print(f"📊 FULL MONTH SUMMARY - {start_date.strftime('%B %Y')}")
    print(f"{'='*100}\n")
    
    print(f"⏱️  EXECUTION TIME:")
    print(f"   Total Time: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
    print(f"   Avg per Day: {total_duration/len(trading_days):.2f} seconds")
    
    print(f"\n📅 DAYS TESTED:")
    print(f"   Total Days: {len(trading_days)}")
    print(f"   Successful: {successful_days}")
    print(f"   Failed: {len(failed_days)}")
    
    print(f"\n📊 TRADING STATISTICS:")
    print(f"   Total Positions: {total_positions}")
    print(f"   Avg Positions/Day: {avg_positions_per_day:.1f}")
    
    print(f"\n💰 P&L SUMMARY:")
    pnl_emoji = '🟢' if total_pnl >= 0 else '🔴'
    print(f"   Total P&L: {pnl_emoji} ₹{total_pnl:.2f}")
    print(f"   Avg P&L/Day: ₹{avg_pnl_per_day:.2f}")
    
    if successful_days > 0:
        winning_pct = (winning_days / successful_days) * 100
        print(f"\n📈 DAY PERFORMANCE:")
        print(f"   Winning Days: {winning_days} ({winning_pct:.1f}%)")
        print(f"   Losing Days: {losing_days}")
        print(f"   Breakeven Days: {breakeven_days}")
    
    if failed_days:
        print(f"\n❌ FAILED DAYS:")
        for failed_date in failed_days:
            print(f"   - {failed_date}")
    
    # Show best and worst days
    if all_results:
        sorted_by_pnl = sorted(all_results, key=lambda x: x['pnl'], reverse=True)
        
        print(f"\n🏆 BEST DAYS (Top 5):")
        for i, day in enumerate(sorted_by_pnl[:5], 1):
            print(f"   {i}. {day['date']} ({day['day_name']}): ₹{day['pnl']:.2f} ({day['positions']} positions)")
        
        print(f"\n📉 WORST DAYS (Bottom 5):")
        for i, day in enumerate(sorted_by_pnl[-5:][::-1], 1):
            print(f"   {i}. {day['date']} ({day['day_name']}): ₹{day['pnl']:.2f} ({day['positions']} positions)")
    
    print(f"\n{'='*100}\n")
    
    # Save results to file
    output_file = f'backtest_full_month_{year}_{month:02d}.json'
    with open(output_file, 'w') as f:
        json.dump({
            'strategy_id': strategy_id,
            'month': f'{year}-{month:02d}',
            'execution_time_seconds': round(total_duration, 2),
            'total_days': len(trading_days),
            'successful_days': successful_days,
            'failed_days': failed_days,
            'total_positions': total_positions,
            'total_pnl': round(total_pnl, 2),
            'winning_days': winning_days,
            'losing_days': losing_days,
            'daily_results': all_results
        }, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}\n")
    
    return all_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test strategy for full month')
    parser.add_argument('strategy_id', help='Strategy UUID')
    parser.add_argument('--year', type=int, default=2024, help='Year (default: 2024)')
    parser.add_argument('--month', type=int, default=10, help='Month (default: 10 for October)')
    
    args = parser.parse_args()
    
    test_full_month(args.strategy_id, args.year, args.month)
