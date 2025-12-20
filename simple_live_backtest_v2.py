"""
Simple Live-like Backtest with File Output
Captures node events and trades from completed backtest (same as regular backtest).
No SSE, no speed multiplier - just normal backtest + file extraction.
"""

import os
import sys
import json
from datetime import datetime

# Set environment variables FIRST
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig


def extract_data_from_backtest(engine, output_dir):
    """
    Extract node events and trades from completed backtest.
    Same data as diagnostics_export.json and trades_daily.json
    """
    print(f"\n{'='*80}")
    print(f"📊 Extracting Data from Backtest")
    print(f"{'='*80}\n")
    
    # Get strategy state
    active_strategies = engine.centralized_processor.strategy_manager.active_strategies
    if not active_strategies:
        print("❌ No strategy state found")
        return
    
    strategy_state = list(active_strategies.values())[0]
    context = strategy_state.get('context', {})
    
    # 1. Extract node events history (complete)
    node_events_history = context.get('node_events_history', {})
    print(f"✅ Found {len(node_events_history)} node events")
    
    # Save full diagnostics (same format as diagnostics_export.json)
    diagnostics_file = os.path.join(output_dir, "diagnostics_export.json")
    diagnostics_data = {
        'events_history': node_events_history
    }
    with open(diagnostics_file, 'w') as f:
        json.dump(diagnostics_data, f, indent=2, default=str)
    print(f"📝 Saved: {diagnostics_file}")
    
    # 2. Extract trades from GPS
    gps = context.get('gps')
    trades = []
    
    if gps:
        closed_positions = context.get('closed_positions', [])
        print(f"✅ Found {len(closed_positions)} closed positions")
        
        for pos in closed_positions:
            # Extract trade info (same format as trades_daily.json)
            trade = {
                'trade_id': pos.get('position_id', 'N/A'),
                'position_id': pos.get('position_id', 'N/A'),
                'symbol': pos.get('symbol', 'N/A'),
                'side': pos.get('side', 'BUY'),
                'quantity': pos.get('quantity', 0),
                'entry_price': f"{float(pos.get('entry_price', 0)):.2f}",
                'entry_time': str(pos.get('entry_time', '')),
                'exit_price': f"{float(pos.get('exit_price', 0)):.2f}",
                'exit_time': str(pos.get('exit_time', '')),
                'pnl': f"{float(pos.get('pnl', 0)):.2f}",
                'status': 'closed',
                're_entry_num': pos.get('re_entry_num', 0)
            }
            trades.append(trade)
        
        # Calculate summary
        total_pnl = sum(float(t['pnl']) for t in trades)
        winning_trades = [t for t in trades if float(t['pnl']) > 0]
        losing_trades = [t for t in trades if float(t['pnl']) < 0]
        
        summary = {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'total_pnl': f"{total_pnl:.2f}",
            'win_rate': f"{(len(winning_trades) / len(trades) * 100):.2f}" if trades else "0.00"
        }
        
        # Save trades (same format as trades_daily.json)
        trades_file = os.path.join(output_dir, "trades_daily.json")
        trades_data = {
            'summary': summary,
            'trades': trades
        }
        with open(trades_file, 'w') as f:
            json.dump(trades_data, f, indent=2, default=str)
        print(f"📝 Saved: {trades_file}")
    else:
        print("⚠️  No GPS found in context")
    
    # 3. Extract tick-level node events (if current_tick_events exists)
    # This would require the modification to be active, but we can still extract
    # events by timestamp
    tick_events_file = os.path.join(output_dir, "node_events_by_tick.jsonl")
    
    # Group events by timestamp for tick-level view
    events_by_timestamp = {}
    for exec_id, event in node_events_history.items():
        timestamp = event.get('timestamp', '')
        if timestamp not in events_by_timestamp:
            events_by_timestamp[timestamp] = []
        events_by_timestamp[timestamp].append({
            'execution_id': exec_id,
            'event': event
        })
    
    # Write events grouped by timestamp (one line per tick)
    with open(tick_events_file, 'w') as f:
        for timestamp in sorted(events_by_timestamp.keys()):
            tick_data = {
                'timestamp': timestamp,
                'events': events_by_timestamp[timestamp]
            }
            f.write(json.dumps(tick_data, default=str) + '\n')
    
    print(f"📝 Saved: {tick_events_file}")
    print(f"   ({len(events_by_timestamp)} unique timestamps)")
    
    print(f"\n{'='*80}")
    print(f"✅ Data Extraction Complete")
    print(f"{'='*80}\n")
    
    # Print summary
    print("📊 Summary:")
    print(f"   Node events: {len(node_events_history)}")
    print(f"   Trades: {len(trades)}")
    print(f"   Unique timestamps: {len(events_by_timestamp)}")
    if trades:
        print(f"   Total P&L: {total_pnl:.2f}")


def run_simple_live_backtest(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = "simple_live_output"
):
    """
    Run backtest and extract data to files.
    Output matches regular backtest format exactly.
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting Simple Live-like Backtest")
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
    
    # Create and run engine
    engine = CentralizedBacktestEngine(config)
    
    print("Running backtest...")
    engine.run()
    
    # Extract data from completed backtest
    extract_data_from_backtest(engine, output_dir)
    
    return output_dir


if __name__ == "__main__":
    # Configuration
    STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
    BACKTEST_DATE = "2024-10-29"
    
    # Run simple live backtest
    output_dir = run_simple_live_backtest(
        strategy_id=STRATEGY_ID,
        backtest_date=BACKTEST_DATE
    )
    
    print(f"✅ All data saved to: {output_dir}")
