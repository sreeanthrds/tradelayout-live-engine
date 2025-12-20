"""
Simple Backtest with File Output
Extracts diagnostics and trades exactly like show_dashboard_data.py
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


def run_backtest_and_export(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = "simple_live_output"
):
    """
    Run backtest and extract diagnostics + trades (exactly like show_dashboard_data.py)
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"🚀 Running Backtest")
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
    print("Running backtest...")
    engine = CentralizedBacktestEngine(config)
    engine.run()
    print("✅ Backtest completed\n")
    
    # Extract diagnostics (same as show_dashboard_data.py lines 184-209)
    print("📊 Extracting diagnostics...")
    diagnostics_export = {}
    
    if hasattr(engine, 'centralized_processor'):
        # Get diagnostics from strategy_state (centralized processor)
        active_strategies = engine.centralized_processor.strategy_manager.active_strategies
        
        # For single-strategy backtests, get first strategy
        if active_strategies:
            strategy_state = list(active_strategies.values())[0]
            context = strategy_state.get('context', {})
            
            # Get node_events_history directly
            node_events_history = context.get('node_events_history', {})
            print(f"   Found {len(node_events_history)} events in node_events_history")
            
            # Also try diagnostics object
            diagnostics = strategy_state.get('diagnostics')
            if diagnostics:
                print(f"   Found diagnostics object")
                diagnostics_export = {
                    'events_history': diagnostics.get_all_events({
                        'node_events_history': node_events_history
                    })
                }
            else:
                # Fallback: use node_events_history directly
                print(f"   No diagnostics object, using node_events_history directly")
                diagnostics_export = {
                    'events_history': node_events_history
                }
            
            # Save diagnostics
            diagnostics_file = os.path.join(output_dir, "diagnostics_export.json")
            with open(diagnostics_file, 'w') as f:
                json.dump(diagnostics_export, f, indent=2, default=str)
            print(f"✅ Saved: {diagnostics_file}")
            print(f"   Events: {len(diagnostics_export.get('events_history', {}))}")
            
            # Extract trades from GPS (same as show_dashboard_data.py)
            print(f"\n📊 Extracting trades...")
            gps = context.get('gps')
            
            if gps:
                closed_positions = context.get('closed_positions', [])
                print(f"   Found {len(closed_positions)} closed positions")
                
                # Format trades
                trades = []
                for pos in closed_positions:
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
                    'win_rate': f"{(len(winning_trades) / len(trades) * 100):.2f}" if trades else "0.00",
                    'largest_win': f"{max((float(t['pnl']) for t in trades), default=0):.2f}",
                    'largest_loss': f"{min((float(t['pnl']) for t in trades), default=0):.2f}"
                }
                
                # Save trades
                trades_file = os.path.join(output_dir, "trades_daily.json")
                trades_data = {
                    'summary': summary,
                    'trades': trades
                }
                with open(trades_file, 'w') as f:
                    json.dump(trades_data, f, indent=2, default=str)
                print(f"✅ Saved: {trades_file}")
                print(f"   Trades: {len(trades)}")
                print(f"   Total P&L: {total_pnl:.2f}")
            else:
                print("⚠️  No GPS found in context")
        else:
            print("❌ No active strategies found")
    else:
        print("❌ No centralized_processor found")
    
    print(f"\n{'='*80}")
    print(f"✅ Export Complete")
    print(f"{'='*80}\n")
    
    return output_dir


if __name__ == "__main__":
    # Configuration
    STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
    BACKTEST_DATE = "2024-10-29"
    
    # Run backtest and export
    output_dir = run_backtest_and_export(
        strategy_id=STRATEGY_ID,
        backtest_date=BACKTEST_DATE
    )
    
    print(f"✅ All data saved to: {output_dir}")
