"""
Centralized Backtest Engine with Tick Event Capture
====================================================

Extends CentralizedBacktestEngine to capture tick-level events during backtesting.
Appends data to files without using SSE or speed multipliers.

Output Files:
- tick_events.jsonl: One line per tick with LTP, indicators, positions, node states
- node_events.jsonl: One line per node execution (from diagnostics)
- trades.jsonl: One line per closed trade

DO NOT modify the original CentralizedBacktestEngine - this is a separate implementation.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.results_manager import BacktestResults

logger = logging.getLogger(__name__)


class CentralizedBacktestEngineWithTickCapture(CentralizedBacktestEngine):
    """
    Extended backtest engine that captures tick-level events to files.
    
    Overrides _process_ticks_centralized to append data after each tick.
    """
    
    def __init__(self, config: BacktestConfig, output_dir: str = "tick_capture_output"):
        """
        Initialize engine with tick capture.
        
        Args:
            config: Backtest configuration
            output_dir: Directory for output files
        """
        super().__init__(config)
        
        # Output configuration
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Output files
        self.tick_events_file = os.path.join(output_dir, "tick_events.jsonl")
        self.node_events_file = os.path.join(output_dir, "node_events.jsonl")
        self.trades_file = os.path.join(output_dir, "trades.jsonl")
        
        # Clear previous files
        for file_path in [self.tick_events_file, self.node_events_file, self.trades_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Track previous state
        self.previous_open_position_ids = set()
        self.tick_counter = 0
        self.capture_context = {}  # Store context for capture after strategy execution
        
        logger.info(f"📁 Tick capture output directory: {output_dir}")
    
    def _process_ticks_centralized(self, ticks: List[Dict[str, Any]]) -> None:
        """
        Override to capture tick events after each tick is processed.
        
        Calls parent's _process_ticks_centralized, then appends data to files.
        """
        # First, get the parent to process ticks normally
        # But we need to intercept tick-by-tick, so we'll override the batching logic
        
        print(f"\n⚡ Processing {len(ticks):,} ticks with tick capture...")
        print(f"📦 Batching ticks by second for efficient processing...")
        
        # Group ticks by second (same as parent)
        ticks_by_second = {}
        for tick in ticks:
            tick_time = tick['timestamp']
            second_key = tick_time.replace(microsecond=0)
            
            if second_key not in ticks_by_second:
                ticks_by_second[second_key] = []
            ticks_by_second[second_key].append(tick)
        
        total_seconds = len(ticks_by_second)
        print(f"📊 Batched {len(ticks):,} ticks into {total_seconds:,} seconds")
        
        if total_seconds > 0:
            first_time = min(ticks_by_second.keys())
            last_time = max(ticks_by_second.keys())
            avg_ticks = len(ticks) / total_seconds
            print(f"   Average: {avg_ticks:.1f} ticks/second")
            print(f"   Time range: {first_time.strftime('%H:%M:%S')} → {last_time.strftime('%H:%M:%S')}")
        
        # Process each second's batch of ticks
        second_count = 0
        for second_key in sorted(ticks_by_second.keys()):
            second_count += 1
            second_ticks = ticks_by_second[second_key]
            
            # Process all ticks for this second (update data manager)
            for tick in second_ticks:
                self.data_manager.process_tick(tick)
                self.tick_counter += 1
            
            # CRITICAL: Initialize current_tick_events before strategy execution
            # This dict will be populated by nodes during execution via add_tick_event()
            active_strategies = self.centralized_processor.strategy_manager.active_strategies
            if active_strategies:
                strategy_state = list(active_strategies.values())[0]
                context = strategy_state.get('context', {})
                context['current_tick_events'] = {}  # Clear and initialize for this tick
            
            # Execute strategy once per second (centralized processor)
            # Nodes will populate current_tick_events during execution
            self.centralized_processor.on_tick(tick_data=second_ticks[-1])
            
            # CAPTURE TICK DATA immediately after strategy execution
            # Must be done here before current_tick_events gets cleared
            self._capture_tick_data(second_key, second_count, total_seconds)
        
        print(f"   ✅ Processed {len(ticks):,} ticks in {total_seconds:,} seconds")
        print(f"   ⚡ Strategy executed {total_seconds:,} times (once per second)")
    
    def _capture_tick_data(self, timestamp: datetime, tick_num: int, total_ticks: int) -> None:
        """
        Capture and append tick-level data to files.
        
        Args:
            timestamp: Current tick timestamp
            tick_num: Current tick number
            total_ticks: Total number of ticks
        """
        # Get strategy state from centralized processor
        if not hasattr(self.centralized_processor, 'strategy_manager'):
            return
        
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return
        
        # Get first (and currently only) strategy state
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        
        # 1. CAPTURE TICK EVENT DATA
        # Get LTP data from context (not cache_manager)
        ltp_store = context.get('ltp_store', {})
        ltp_data = {}
        for symbol, ltp in ltp_store.items():
            ltp_data[symbol] = ltp
        
        # Get indicator data from cache
        indicator_data = {}
        if hasattr(self, 'data_manager') and self.data_manager:
            # Get last candle for each symbol/timeframe
            for key in self.strategies_agg.get('cache_requirements', []):
                if ':' in key and not key.startswith('option:'):
                    parts = key.split(':')
                    if len(parts) == 2:
                        symbol, timeframe = parts
                        candles = self.data_manager.get_candles(symbol, timeframe)
                        if candles and len(candles) > 0:
                            last_candle = candles[-1]
                            indicators = last_candle.get('indicators', {})
                            if indicators:
                                indicator_data[key] = indicators
        
        # Get position data from GPS
        gps = context.get('gps')
        open_positions = []
        pnl_summary = {
            'realized_pnl': '0.00',
            'unrealized_pnl': '0.00',
            'total_pnl': '0.00',
            'closed_trades': 0,
            'open_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': '0.00'
        }
        
        if gps:
            # Get open positions with individual P&L
            positions = context.get('open_positions', [])
            for pos in positions:
                open_positions.append({
                    'position_id': pos.get('position_id'),
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side'),
                    'quantity': pos.get('quantity'),
                    'entry_price': pos.get('entry_price'),
                    'current_price': pos.get('current_price'),
                    'pnl': pos.get('pnl'),  # Individual unrealized P&L
                    'status': pos.get('status')
                })
            
            # Calculate P&L summary
            realized_pnl = gps.get_total_realized_pnl()
            unrealized_pnl = gps.get_total_unrealized_pnl()
            
            # Get closed positions for trade statistics
            closed_positions = context.get('closed_positions', [])
            winning_trades = sum(1 for p in closed_positions if p.get('pnl', 0) > 0)
            losing_trades = sum(1 for p in closed_positions if p.get('pnl', 0) < 0)
            win_rate = (winning_trades / len(closed_positions) * 100) if closed_positions else 0
            
            pnl_summary = {
                'realized_pnl': round(realized_pnl, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'total_pnl': round(realized_pnl + unrealized_pnl, 2),
                'closed_trades': len(closed_positions),
                'open_trades': len(open_positions),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2)
            }
        
        # Get node states
        node_states = strategy_state.get('node_states', {})
        active_nodes = [
            {'node_id': node_id, 'status': state.get('status')}
            for node_id, state in node_states.items()
            if state.get('status') == 'active'
        ]
        
        # CRITICAL: Capture current_tick_events populated during this tick's execution
        # This contains ALL nodes that executed (active nodes), not just completed ones
        # Nodes populate this via add_tick_event() in base_node.py line 235
        current_tick_events = context.get('current_tick_events', {})
        
        # Debug first few ticks
        if tick_num <= 3:
            print(f"\n[DEBUG Tick {tick_num}] current_tick_events keys: {list(current_tick_events.keys())}")
            if current_tick_events:
                for exec_id, event in list(current_tick_events.items())[:5]:
                    print(f"  - {exec_id}: node_id={event.get('node_id')}, event_type={event.get('event_type')}")
        
        # Copy the events (contains full diagnostics for all active nodes this tick)
        node_executions = {}
        for exec_id, event in current_tick_events.items():
            node_executions[exec_id] = event.copy()
        
        # Build tick event data
        tick_event_data = {
            'tick': tick_num,
            'timestamp': str(timestamp),
            'ltp': ltp_data,
            'indicators': indicator_data,
            'open_positions': open_positions,  # Individual position details with P&L
            'pnl_summary': pnl_summary,  # Aggregated P&L metrics
            'active_nodes': active_nodes,
            'position_count': len(open_positions),
            'node_executions': node_executions,  # Full node diagnostics for this tick
            'execution_count': len(node_executions)  # How many nodes executed
        }
        
        # Append to tick events file
        with open(self.tick_events_file, 'a') as f:
            f.write(json.dumps(tick_event_data, default=str) + '\n')
        
        # 2. CAPTURE NODE EVENTS (when nodes complete logic)
        node_events_history = context.get('node_events_history', {})
        
        # Find events at this timestamp
        for exec_id, event in node_events_history.items():
            event_time = event.get('timestamp', '')
            if event_time and str(timestamp) in event_time:
                if event.get('event_type') == 'logic_completed':
                    node_event_data = {
                        'tick': tick_num,
                        'timestamp': event_time,
                        'execution_id': exec_id,
                        'node_id': event.get('node_id'),
                        'node_name': event.get('node_name'),
                        'node_type': event.get('node_type'),
                        'signal_emitted': event.get('signal_emitted'),
                        'position_action': event.get('position_action'),
                        'conditions_preview': event.get('conditions_preview')
                    }
                    
                    # Append to node events file
                    with open(self.node_events_file, 'a') as f:
                        f.write(json.dumps(node_event_data, default=str) + '\n')
        
        # 3. CAPTURE TRADES (when positions are closed)
        if gps:
            closed_positions = context.get('closed_positions', [])
            current_closed_ids = {pos.get('position_id') for pos in closed_positions}
            
            # Find newly closed positions
            new_closed_ids = current_closed_ids - self.previous_open_position_ids
            
            for pos in closed_positions:
                if pos.get('position_id') in new_closed_ids:
                    trade_data = {
                        'tick': tick_num,
                        'timestamp': str(timestamp),
                        'position_id': pos.get('position_id'),
                        'symbol': pos.get('symbol'),
                        'side': pos.get('side'),
                        'quantity': pos.get('quantity'),
                        'entry_price': pos.get('entry_price'),
                        'entry_time': str(pos.get('entry_time')),
                        'exit_price': pos.get('exit_price'),
                        'exit_time': str(pos.get('exit_time')),
                        'pnl': pos.get('pnl'),
                        'status': 'closed'
                    }
                    
                    # Append to trades file
                    with open(self.trades_file, 'a') as f:
                        f.write(json.dumps(trade_data, default=str) + '\n')
            
            # Update tracking
            self.previous_open_position_ids = current_closed_ids
        
        # Print progress every 1000 ticks
        if tick_num % 1000 == 0:
            progress = (tick_num / total_ticks * 100) if total_ticks > 0 else 0
            print(f"   📊 Progress: {tick_num:,}/{total_ticks:,} ticks ({progress:.1f}%) | "
                  f"Positions: {len(open_positions)} | Active Nodes: {len(active_nodes)}")
    
    def run(self) -> BacktestResults:
        """
        Run backtest with tick capture.
        
        Calls parent's run() which will use our overridden _process_ticks_centralized.
        """
        print(f"\n{'='*80}")
        print(f"🎬 BACKTEST WITH TICK EVENT CAPTURE")
        print(f"{'='*80}")
        print(f"Output Directory: {self.output_dir}")
        print(f"{'='*80}\n")
        
        # Run parent's backtest (will use our overridden tick processing)
        result = super().run()
        
        # Note: No enrichment needed - tick events already contain full diagnostics
        # captured directly from current_tick_events during execution
        print(f"\n📊 Tick events already contain full node diagnostics from current_tick_events")
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"✅ TICK CAPTURE COMPLETE")
        print(f"{'='*80}")
        print(f"Output files:")
        print(f"  📝 {self.tick_events_file}")
        print(f"  📝 {self.node_events_file}")
        print(f"  📝 {self.trades_file}")
        
        # Count lines in each file
        for file_path, label in [
            (self.tick_events_file, "Tick events"),
            (self.node_events_file, "Node events"),
            (self.trades_file, "Trades")
        ]:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                print(f"  {label}: {line_count:,} lines")
        
        print(f"{'='*80}\n")
        
        return result
    
    def _export_node_diagnostics(self):
        """Export complete node_events_history after backtest completes."""
        # Get the strategy state
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            print("  ⚠️  No active strategies found")
            return
        
        strategy_state = list(active_strategies.values())[0]
        
        # Debug: Print what's available
        print(f"  [DEBUG] Strategy state keys: {list(strategy_state.keys())}")
        print(f"  [DEBUG] Context keys: {list(strategy_state.get('context', {}).keys())}")
        
        # Try both locations - context level and strategy_state level
        # Strategy subscription manager stores at both levels (lines 434 and 439)
        node_events_history = strategy_state.get('node_events_history', {})
        print(f"  [DEBUG] node_events_history from strategy_state: {len(node_events_history)} events")
        
        if not node_events_history:
            context = strategy_state.get('context', {})
            node_events_history = context.get('node_events_history', {})
            print(f"  [DEBUG] node_events_history from context: {len(node_events_history)} events")
        
        # Check if diagnostics object has the data
        diagnostics = strategy_state.get('diagnostics')
        if diagnostics:
            print(f"  [DEBUG] Diagnostics object found: {type(diagnostics)}")
            print(f"  [DEBUG] Diagnostics attributes: {dir(diagnostics)[:10]}")
        
        # Save to diagnostics_export.json (same format as original)
        diagnostics_file = os.path.join(self.output_dir, "diagnostics_export.json")
        diagnostics_data = {
            'events_history': node_events_history
        }
        
        with open(diagnostics_file, 'w') as f:
            json.dump(diagnostics_data, f, indent=2, default=str)
        
        print(f"  ✅ Exported {len(node_events_history)} node events to diagnostics_export.json")
    
    def _enrich_tick_events(self):
        """Post-process tick events to add node diagnostics by timestamp."""
        # Load diagnostics
        diagnostics_file = os.path.join(self.output_dir, "diagnostics_export.json")
        if not os.path.exists(diagnostics_file):
            print("  ⚠️  No diagnostics file found")
            return
        
        with open(diagnostics_file, 'r') as f:
            diagnostics_data = json.load(f)
        
        events_history = diagnostics_data.get('events_history', {})
        
        # Group events by timestamp
        events_by_timestamp = {}
        for exec_id, event in events_history.items():
            timestamp = event.get('timestamp', '')
            if timestamp:
                # Extract just the date-time part (YYYY-MM-DD HH:MM:SS)
                timestamp_key = timestamp[:19] if len(timestamp) >= 19 else timestamp
                if timestamp_key not in events_by_timestamp:
                    events_by_timestamp[timestamp_key] = {}
                events_by_timestamp[timestamp_key][exec_id] = event
        
        # Read and update tick events
        temp_file = self.tick_events_file + ".tmp"
        updated_count = 0
        
        with open(self.tick_events_file, 'r') as infile, open(temp_file, 'w') as outfile:
            for line in infile:
                tick_event = json.loads(line)
                timestamp = tick_event.get('timestamp', '')
                
                # Extract date-time part
                timestamp_key = timestamp[:19] if len(timestamp) >= 19 else timestamp
                
                # Add node executions for this timestamp
                if timestamp_key in events_by_timestamp:
                    tick_event['node_executions'] = events_by_timestamp[timestamp_key]
                    tick_event['execution_count'] = len(events_by_timestamp[timestamp_key])
                    updated_count += 1
                
                outfile.write(json.dumps(tick_event, default=str) + '\n')
        
        # Replace original with enriched version
        os.replace(temp_file, self.tick_events_file)
        
        print(f"  ✅ Enriched {updated_count} ticks with node diagnostics")
