#!/usr/bin/env python3
"""
Run Backtest with SSE Event Streaming
=====================================

Demonstrates hybrid SSE model:
- Compressed initial_state on connect
- Incremental tick_update events (uncompressed)
- Incremental node_event and trade_update events
- Event ID tracking for reconnection resilience
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from centralized_backtest_engine_with_sse import (
    CentralizedBacktestEngineWithSSE,
    SSEEventEmitter
)
from src.backtesting.backtest_config import BacktestConfig

# Configuration
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"
OUTPUT_DIR = "sse_backtest_output"
SESSION_ID = f"sse-{STRATEGY_ID}-{BACKTEST_DATE}"


class SSEEventLogger:
    """
    Simple callback to log SSE events to console and files.
    In production, this would be replaced with SSE endpoint.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Event counters
        self.event_counts = {
            'initial_state': 0,
            'tick_update': 0,
            'node_event': 0,
            'trade_update': 0,
            'backtest_complete': 0
        }
        
        # File handles
        self.tick_stream = open(output_dir / "tick_updates_stream.jsonl", 'w')
        self.node_stream = open(output_dir / "node_events_stream.jsonl", 'w')
        self.trade_stream = open(output_dir / "trade_updates_stream.jsonl", 'w')
        
        print(f"\n📡 SSE Event Logger initialized")
        print(f"   Output: {output_dir}")
    
    def __call__(self, event: dict):
        """
        Handle SSE event (fire-and-forget callback).
        """
        event_type = event.get('event')
        event_data = event.get('data', {})
        event_id = event_data.get('event_id', 0)
        
        # Count event
        if event_type in self.event_counts:
            self.event_counts[event_type] += 1
        
        # Handle different event types
        if event_type == 'initial_state':
            self._handle_initial_state(event_data, event_id)
        elif event_type == 'tick_update':
            self._handle_tick_update(event_data, event_id)
        elif event_type == 'node_event':
            self._handle_node_event(event_data, event_id)
        elif event_type == 'trade_update':
            self._handle_trade_update(event_data, event_id)
        elif event_type == 'backtest_complete':
            self._handle_backtest_complete(event_data, event_id)
    
    def _handle_initial_state(self, data: dict, event_id: int):
        """Handle initial_state event"""
        diagnostics_size = data.get('uncompressed_sizes', {}).get('diagnostics', 0)
        trades_size = data.get('uncompressed_sizes', {}).get('trades', 0)
        
        print(f"\n[Event {event_id}] initial_state")
        print(f"   Diagnostics: {diagnostics_size:,} bytes (compressed)")
        print(f"   Trades: {trades_size:,} bytes (compressed)")
        print(f"   Strategy: {data.get('strategy_id')}")
        print(f"   Date: {data.get('start_date')}")
        
        # Save to file
        with open(self.output_dir / "initial_state.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def _handle_tick_update(self, data: dict, event_id: int):
        """Handle tick_update event"""
        tick = data.get('tick', 0)
        execution_count = data.get('execution_count', 0)
        positions = len(data.get('open_positions', []))
        
        # Log every 100 ticks
        if tick % 100 == 0 or tick <= 5:
            print(f"[Event {event_id}] tick_update #{tick}: {execution_count} nodes, {positions} positions")
        
        # Write to stream file
        self.tick_stream.write(json.dumps({
            "event_id": event_id,
            "tick": tick,
            "timestamp": data.get('timestamp'),
            "execution_count": execution_count,
            "open_positions": positions,
            "pnl_summary": data.get('pnl_summary')
        }) + '\n')
        self.tick_stream.flush()
    
    def _handle_node_event(self, data: dict, event_id: int):
        """Handle node_event (incremental)"""
        node_id = data.get('node_id')
        signal = data.get('signal_emitted')
        
        print(f"[Event {event_id}] node_event: {node_id} (signal={signal})")
        
        # Write to stream file
        self.node_stream.write(json.dumps({
            "event_id": event_id,
            "execution_id": data.get('execution_id'),
            "node_id": node_id,
            "node_name": data.get('node_name'),
            "timestamp": data.get('timestamp'),
            "signal_emitted": signal
        }) + '\n')
        self.node_stream.flush()
    
    def _handle_trade_update(self, data: dict, event_id: int):
        """Handle trade_update (incremental)"""
        trade = data.get('trade', {})
        summary = data.get('summary', {})
        
        print(f"[Event {event_id}] trade_update: {trade.get('symbol')} P&L={trade.get('pnl')}")
        print(f"   Total: {summary.get('total_trades')} trades, P&L={summary.get('total_pnl')}")
        
        # Write to stream file
        self.trade_stream.write(json.dumps({
            "event_id": event_id,
            "trade": trade,
            "summary": summary
        }) + '\n')
        self.trade_stream.flush()
    
    def _handle_backtest_complete(self, data: dict, event_id: int):
        """Handle backtest_complete event"""
        diagnostics_size = data.get('uncompressed_sizes', {}).get('diagnostics', 0)
        trades_size = data.get('uncompressed_sizes', {}).get('trades', 0)
        total_ticks = data.get('total_ticks', 0)
        
        print(f"\n[Event {event_id}] backtest_complete")
        print(f"   Total ticks: {total_ticks:,}")
        print(f"   Final diagnostics: {diagnostics_size:,} bytes (compressed)")
        print(f"   Final trades: {trades_size:,} bytes (compressed)")
        
        # Save final state
        with open(self.output_dir / "final_state.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def close(self):
        """Close file handles"""
        self.tick_stream.close()
        self.node_stream.close()
        self.trade_stream.close()
        
        print(f"\n📊 Event Summary:")
        for event_type, count in self.event_counts.items():
            print(f"   {event_type}: {count:,} events")
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def run_backtest_with_sse(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = OUTPUT_DIR
) -> dict:
    """
    Run backtest with SSE event streaming.
    
    Args:
        strategy_id: Strategy UUID
        backtest_date: Date in YYYY-MM-DD format
        output_dir: Output directory for event logs
        
    Returns:
        Backtest results
    """
    print(f"\n{'='*80}")
    print(f"🚀 Starting Backtest with SSE Streaming")
    print(f"{'='*80}")
    print(f"Strategy ID: {strategy_id}")
    print(f"Date: {backtest_date}")
    print(f"Session: {SESSION_ID}")
    print(f"{'='*80}\n")
    
    # Parse date
    date_obj = datetime.strptime(backtest_date, "%Y-%m-%d")
    
    # Create configuration (BacktestConfig expects strategy_ids as list and backtest_date)
    config = BacktestConfig(
        strategy_ids=[strategy_id],  # Always a list
        backtest_date=date_obj
    )
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create engine with SSE
    engine = CentralizedBacktestEngineWithSSE(
        config=config,
        session_id=SESSION_ID,
        output_dir=str(output_path)
    )
    
    # Register callback to log events
    with SSEEventLogger(output_path) as logger:
        engine.register_sse_callback(logger)
        
        # Run backtest (will emit events to callback)
        result = engine.run()
    
    print(f"\n{'='*80}")
    print(f"✅ Backtest Complete")
    print(f"{'='*80}")
    print(f"Output directory: {output_path}")
    print(f"{'='*80}\n")
    
    return result


if __name__ == "__main__":
    try:
        result = run_backtest_with_sse(
            strategy_id=STRATEGY_ID,
            backtest_date=BACKTEST_DATE,
            output_dir=OUTPUT_DIR
        )
        
        print("\n✅ SUCCESS - SSE backtest completed")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
