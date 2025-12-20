#!/usr/bin/env python3
"""
Run Real Backtest with SSE-Style Output

Runs actual backtest with real strategy and writes events to files
exactly as UI would receive them via SSE.

Usage:
    python run_backtest_with_sse_output.py
"""

import os
import sys
import json
import gzip
import base64
from datetime import datetime
from pathlib import Path

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


class SSEOutputWriter:
    """Writes backtest events in SSE format to files"""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tick_count = 0
        self.event_count = 0
        
    def compress_json(self, data):
        """Gzip + base64 encode (like SSE does)"""
        json_str = json.dumps(data, default=str)
        compressed = gzip.compress(json_str.encode('utf-8'))
        return base64.b64encode(compressed).decode('utf-8')
    
    def write_diagnostics(self, diagnostics):
        """Write diagnostics_export.json"""
        filepath = self.output_dir / "diagnostics_export.json"
        with open(filepath, 'w') as f:
            json.dump(diagnostics, f, indent=2, default=str)
        self.event_count = len(diagnostics.get('events_history', {}))
    
    def write_trades(self, trades):
        """Write trades_daily.json"""
        filepath = self.output_dir / "trades_daily.json"
        with open(filepath, 'w') as f:
            json.dump(trades, f, indent=2, default=str)
    
    def append_tick(self, tick_data):
        """Append tick update to stream file"""
        filepath = self.output_dir / "tick_updates_stream.jsonl"
        with open(filepath, 'a') as f:
            f.write(json.dumps(tick_data, default=str) + '\n')
        self.tick_count += 1


def main():
    print("="*80)
    print("🧪 REAL BACKTEST WITH SSE OUTPUT")
    print("="*80)
    print("Running actual strategy with real data")
    print("Writing events as UI would receive them")
    print("="*80)
    print()
    
    # Configuration - YOUR ACTUAL STRATEGY
    config = BacktestConfig(
        strategy_ids=['5708424d-5962-4629-978c-05b3a174e104'],
        backtest_date=datetime(2024, 10, 29),
        debug_mode=None
    )
    
    print(f"📅 Date: {config.backtest_date.date()}")
    print(f"🎯 Strategy: {config.strategy_ids[0]}")
    print(f"📁 Output: real_backtest_output/")
    print()
    
    # Initialize output writer
    writer = SSEOutputWriter("real_backtest_output")
    
    # Run backtest
    print("🔄 Running backtest...")
    engine = CentralizedBacktestEngine(config)
    
    # Hook into engine to capture events as they happen
    original_save = engine.save_results
    
    def save_with_sse_output(results):
        """Intercept save and write SSE-style output"""
        print(f"\n📊 Backtest complete - writing SSE output...")
        
        # Write diagnostics (like node_events)
        diagnostics_file = engine.output_paths['diagnostics']
        if os.path.exists(diagnostics_file):
            with open(diagnostics_file, 'r') as f:
                diagnostics = json.load(f)
            writer.write_diagnostics(diagnostics)
            print(f"✅ diagnostics_export.json: {len(diagnostics.get('events_history', {}))} events")
        
        # Write trades (like trade_update)
        trades_file = engine.output_paths['trades']
        if os.path.exists(trades_file):
            with open(trades_file, 'r') as f:
                trades = json.load(f)
            writer.write_trades(trades)
            num_trades = len(trades.get('trades', []))
            total_pnl = trades.get('summary', {}).get('total_pnl', '0.00')
            print(f"✅ trades_daily.json: {num_trades} trades, P&L: ₹{total_pnl}")
        
        # Write tick stream
        print(f"✅ tick_updates_stream.jsonl: {writer.tick_count} ticks")
        
        # Call original save
        return original_save(results)
    
    # Replace save method
    engine.save_results = save_with_sse_output
    
    # Capture tick-level updates
    original_process_tick = engine.tick_processor.process_tick
    
    def process_tick_with_sse(*args, **kwargs):
        """Capture each tick update"""
        result = original_process_tick(*args, **kwargs)
        
        # After tick is processed, write tick update
        context = engine.tick_processor.context
        if context:
            tick_data = {
                "timestamp": context.get("current_timestamp", ""),
                "current_time": context.get("current_time", ""),
                "progress": {
                    "ticks_processed": context.get("tick_count", 0),
                    "total_ticks": engine.tick_processor.total_ticks,
                    "progress_percentage": (context.get("tick_count", 0) / engine.tick_processor.total_ticks * 100) if engine.tick_processor.total_ticks > 0 else 0
                },
                "open_positions": context.get("open_positions", []),
                "pnl_summary": context.get("pnl_summary", {}),
                "ltp_store": dict(list(context.get("ltp_store", {}).items())[:10]),  # First 10 symbols
                "candle_data": {}  # Too large to include every tick
            }
            writer.append_tick(tick_data)
            
            # Print progress every 1000 ticks
            if writer.tick_count % 1000 == 0:
                positions = len(tick_data["open_positions"])
                pnl = tick_data["pnl_summary"].get("total_pnl", "0.00")
                print(f"  Tick {writer.tick_count} | Positions: {positions} | P&L: ₹{pnl}")
        
        return result
    
    engine.tick_processor.process_tick = process_tick_with_sse
    
    # Run the backtest
    results = engine.run()
    
    # Print final results
    print()
    print("="*80)
    print("📊 FINAL RESULTS")
    print("="*80)
    results.print()
    
    print()
    print("="*80)
    print("📂 OUTPUT FILES (SSE Format)")
    print("="*80)
    
    # Show file details
    diag_file = writer.output_dir / "diagnostics_export.json"
    if diag_file.exists():
        with open(diag_file) as f:
            diag = json.load(f)
        size = diag_file.stat().st_size
        events = len(diag.get('events_history', {}))
        print(f"  • diagnostics_export.json: {events} events ({size:,} bytes)")
    
    trades_file = writer.output_dir / "trades_daily.json"
    if trades_file.exists():
        with open(trades_file) as f:
            trades = json.load(f)
        size = trades_file.stat().st_size
        num_trades = len(trades.get('trades', []))
        total_pnl = trades['summary']['total_pnl']
        win_rate = trades['summary']['win_rate']
        print(f"  • trades_daily.json: {num_trades} trades, P&L: ₹{total_pnl}, Win Rate: {win_rate}% ({size:,} bytes)")
    
    tick_file = writer.output_dir / "tick_updates_stream.jsonl"
    if tick_file.exists():
        size = tick_file.stat().st_size
        lines = sum(1 for _ in open(tick_file))
        print(f"  • tick_updates_stream.jsonl: {lines} ticks ({size:,} bytes)")
    
    print()
    print("✅ Files match backtesting format exactly!")
    print("✅ This is how UI will receive data via SSE!")
    print("="*80)


if __name__ == '__main__':
    main()
