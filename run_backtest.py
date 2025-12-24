#!/usr/bin/env python3
"""
Production Backtest Runner
==========================

Uses the centralized tick processor (same as live trading engine).

Features:
- Full node framework with start_node.execute()
- Multi-timeframe, multi-symbol candle building
- Complete context with node_states and node_variables
- Matches live trading engine behavior exactly

Usage:
    python run_backtest.py
"""

import os
import sys
from datetime import datetime

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(SCRIPT_DIR)
paths_to_remove = [p for p in sys.path if parent_dir in p and SCRIPT_DIR not in p]
for path in paths_to_remove:
    sys.path.remove(path)

sys.path.insert(0, os.path.join(SCRIPT_DIR, 'src'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'strategy'))
sys.path.insert(0, SCRIPT_DIR)

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine


async def main():
    """
    Run backtest with production-ready centralized processor.
    """
    print("="*70)
    print("🚀 PRODUCTION BACKTEST")
    print("="*70)
    print("Using: CentralizedBacktestEngine (matches live trading)")
    print()
    
    # Configuration - Test 2 strategies together
    config = BacktestConfig(
        strategy_ids=[
            '5708424d-5962-4629-978c-05b3a174e104',
            'd70ec04a-1025-46c5-94c4-3e6bff499644'
        ],
        backtest_date=datetime(2024, 10, 29),
        debug_mode=None
    )
    
    print(f"📅 Date: {config.backtest_date.date()}")
    print(f"🎯 Strategy: {config.strategy_ids[0]}")
    print()
    
    # Run backtest
    engine = CentralizedBacktestEngine(config)
    results = await engine.run()
    
    # Print results
    print()
    print("="*70)
    print("📊 RESULTS")
    print("="*70)
    results.print()
    
    print()
    print("="*70)
    print("✅ BACKTEST COMPLETE!")
    print("="*70)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
