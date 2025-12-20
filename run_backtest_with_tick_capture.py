"""
Run Backtest with Tick Event Capture
=====================================

Uses CentralizedBacktestEngineWithTickCapture to run backtests and capture:
- Tick events (LTP, indicators, positions, node states)
- Node events (when nodes execute)
- Trades (when positions close)

Output: JSONL files with one line per event
"""

import os
import sys
from datetime import datetime

# Set environment variables FIRST
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from centralized_backtest_engine_with_tick_capture import CentralizedBacktestEngineWithTickCapture
from src.backtesting.backtest_config import BacktestConfig


def run_backtest_with_tick_capture(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = "tick_capture_output"
):
    """
    Run backtest with tick event capture.
    
    Args:
        strategy_id: Strategy ID to backtest
        backtest_date: Date in YYYY-MM-DD format
        output_dir: Output directory for captured events
    """
    
    print(f"\n{'='*80}")
    print(f"🚀 Running Backtest with Tick Capture")
    print(f"{'='*80}")
    print(f"Strategy: {strategy_id}")
    print(f"Date: {backtest_date}")
    print(f"Output: {output_dir}")
    print(f"{'='*80}\n")
    
    # Create backtest config
    config = BacktestConfig(
        strategy_ids=[strategy_id],
        backtest_date=datetime.strptime(backtest_date, '%Y-%m-%d')
    )
    
    # Create engine with tick capture
    engine = CentralizedBacktestEngineWithTickCapture(
        config=config,
        output_dir=output_dir
    )
    
    # Run backtest (will capture tick events)
    result = engine.run()
    
    print(f"\n{'='*80}")
    print(f"✅ Backtest Complete")
    print(f"{'='*80}")
    print(f"All events saved to: {output_dir}")
    print(f"{'='*80}\n")
    
    return result


if __name__ == "__main__":
    # Configuration
    STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
    BACKTEST_DATE = "2024-10-29"
    OUTPUT_DIR = "tick_capture_output"
    
    # Run backtest with tick capture
    result = run_backtest_with_tick_capture(
        strategy_id=STRATEGY_ID,
        backtest_date=BACKTEST_DATE,
        output_dir=OUTPUT_DIR
    )
    
    # Note: No post-processing needed - tick events now contain full diagnostics
    # captured directly from current_tick_events during execution
