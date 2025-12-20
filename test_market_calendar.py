#!/usr/bin/env python3
"""
Test Market Calendar Validation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from src.utils.market_calendar import (
    is_trading_day,
    is_weekend,
    is_holiday,
    get_holiday_name,
    validate_backtest_date,
    get_trading_days_in_month
)

print("\n" + "="*80)
print("TESTING MARKET CALENDAR")
print("="*80 + "\n")

# Test known dates
test_dates = [
    date(2024, 10, 1),   # Tuesday - Trading day
    date(2024, 10, 2),   # Wednesday - Gandhi Jayanti
    date(2024, 10, 5),   # Saturday - Weekend
    date(2024, 10, 12),  # Saturday - Dussehra + Weekend
    date(2024, 10, 31),  # Thursday - Diwali
]

for test_date in test_dates:
    is_valid, reason = validate_backtest_date(test_date)
    status = "✅ Valid" if is_valid else "❌ Invalid"
    
    print(f"{test_date} ({test_date.strftime('%A')})")
    print(f"  Status: {status}")
    if not is_valid:
        print(f"  Reason: {reason}")
    print()

# Test October 2024 trading days
print("="*80)
print("OCTOBER 2024 TRADING DAYS")
print("="*80 + "\n")

trading_days = get_trading_days_in_month(2024, 10)
print(f"Total Trading Days: {len(trading_days)}\n")

for day in trading_days:
    print(f"  {day} ({day.strftime('%A')})")

print("\n" + "="*80 + "\n")
