#!/usr/bin/env python3
"""
Test Strategy - Simple wrapper to invoke show_dashboard_data.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import date
from show_dashboard_data import run_dashboard_backtest


def test_strategy(strategy_id: str, backtest_date: str = '2024-10-01'):
    """
    Test a strategy - just calls show_dashboard_data with parameters
    
    Args:
        strategy_id: Strategy UUID to test
        backtest_date: Date in 'YYYY-MM-DD' format
    
    Returns:
        dict: Dashboard data with positions and summary
    """
    # Parse date
    date_parts = backtest_date.split('-')
    backtest_date_obj = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
    
    # Just call the existing function
    return run_dashboard_backtest(strategy_id, backtest_date_obj)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test a strategy')
    parser.add_argument('strategy_id', help='Strategy UUID')
    parser.add_argument('--date', default='2024-10-01', help='Backtest date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    test_strategy(args.strategy_id, args.date)
