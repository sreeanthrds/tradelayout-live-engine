"""
Simple Live-like Backtest with File Appending
Same as regular backtest but appends tick events, node events, and trades to files.
No SSE, no speed multiplier - just normal for loop.
"""

import os
import sys
import json
from datetime import datetime

# Set environment variables FIRST (before imports)
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig


def run_simple_live_backtest(
    strategy_id: str,
    backtest_date: str,
    output_dir: str = "simple_live_output"
):
    """
    Run backtest with file appending for tick events, node events, and trades.
    
    Output files:
    - tick_events.jsonl: One line per tick with current_tick_events
    - node_events.jsonl: One line per completed node with full event data
    - trades.jsonl: One line per closed trade with full trade data
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Clear previous output files
    tick_events_file = os.path.join(output_dir, "tick_events.jsonl")
    node_events_file = os.path.join(output_dir, "node_events.jsonl")
    trades_file = os.path.join(output_dir, "trades.jsonl")
    
    for file_path in [tick_events_file, node_events_file, trades_file]:
        if os.path.exists(file_path):
            os.remove(file_path)
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting Simple Live-like Backtest")
    print(f"{'='*80}")
    print(f"Strategy: {strategy_id}")
    print(f"Date: {backtest_date}")
    print(f"Output: {output_dir}")
    print(f"{'='*80}\n")
    
    # Create backtest config (using correct format)
    config = BacktestConfig(
        strategy_ids=[strategy_id],  # List of strategy IDs
        backtest_date=datetime.strptime(backtest_date, '%Y-%m-%d')  # datetime object
    )
    
    # Create custom engine class with file appending
    class SimpleBacktestEngine(CentralizedBacktestEngine):
        def __init__(self, config):
            super().__init__(config)
            self.tick_counter = 0
            self.previous_open_position_ids = set()
            self.tick_events_file = tick_events_file
            self.node_events_file = node_events_file
            self.trades_file = trades_file
        
        def _process_ticks_centralized(self, ticks):
            """Override to capture data after each tick"""
            # Call parent's implementation but hook into each tick
            from collections import defaultdict
            
            print(f"\n⚡ Processing {len(ticks):,} ticks through centralized processor...")
            print(f"📦 Batching ticks by second for efficient processing...")
            
            # Group ticks by second (same as parent)
            ticks_by_second = defaultdict(list)
            for tick in ticks:
                tick_timestamp = tick['timestamp']
                second_key = tick_timestamp.replace(microsecond=0)
                ticks_by_second[second_key].append(tick)
            
            sorted_seconds = sorted(ticks_by_second.keys())
            total_seconds = len(sorted_seconds)
            
            print(f"📊 Batched {len(ticks):,} ticks into {total_seconds:,} seconds")
            
            if total_seconds == 0:
                print(f"⚠️  No ticks to process")
                return
            
            print(f"   Average: {len(ticks)/total_seconds:.1f} ticks/second")
            print(f"   Time range: {sorted_seconds[0].strftime('%H:%M:%S')} → {sorted_seconds[-1].strftime('%H:%M:%S')}")
            
            processed_tick_count = 0
            
            for second_idx, second_timestamp in enumerate(sorted_seconds):
                tick_batch = ticks_by_second[second_timestamp]
                
                # Process all ticks in this second's batch
                last_processed_tick = None
                for tick in tick_batch:
                    try:
                        last_processed_tick = self.data_manager.process_tick(tick)
                        processed_tick_count += 1
                    except Exception as e:
                        if processed_tick_count < 10:
                            print(f"DataManager error at tick {processed_tick_count}: {e}")
                        continue
                
                # Process option ticks for this timestamp
                option_ticks = self.data_manager.get_option_ticks_for_timestamp(second_timestamp)
                for option_tick in option_ticks:
                    try:
                        self.data_manager.process_tick(option_tick)
                        processed_tick_count += 1
                    except Exception as e:
                        if processed_tick_count < 10:
                            print(f"Option tick processing error: {e}")
                        continue
                
                # Execute strategy once per second with the final state
                if last_processed_tick:
                    try:
                        tick_data = {
                            'symbol': last_processed_tick.get('symbol'),
                            'ltp': last_processed_tick.get('ltp'),
                            'timestamp': second_timestamp,
                            'volume': last_processed_tick.get('volume', 0),
                            'batch_size': len(tick_batch)
                        }
                        
                        # Execute strategy
                        self.centralized_processor.on_tick(tick_data)
                        
                        # CAPTURE DATA AFTER TICK
                        self._capture_tick_data(tick_data)
                        
                    except Exception as e:
                        print(f"Strategy execution error: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Progress reporting
                if second_idx % 100 == 0:
                    progress = (second_idx / total_seconds) * 100
                    print(f"   Progress: {progress:.1f}% ({second_idx}/{total_seconds} seconds)")
            
            print(f"\n✅ Processed {processed_tick_count:,} total ticks")
        
        def _capture_tick_data(self, tick_data):
            """Capture data after each tick"""
            self.tick_counter += 1
            tick_num = self.tick_counter
            
            # Get strategy state
            active_strategies = self.centralized_processor.strategy_manager.active_strategies
            if not active_strategies:
                print(f"[DEBUG] Tick {tick_num}: No active strategies")
                return
            
            strategy_state = list(active_strategies.values())[0]
            context = strategy_state.get('context', {})
            
            # 1. APPEND TICK EVENTS
            current_tick_events = context.get('current_tick_events', {})
            
            # Debug: Print first few ticks
            if tick_num <= 5:
                print(f"[DEBUG] Tick {tick_num}: current_tick_events has {len(current_tick_events)} events")
                print(f"[DEBUG]   'current_tick_events' exists in context: {'current_tick_events' in context}")
                print(f"[DEBUG]   Node states: {list(context.get('node_states', {}).keys())[:3]}")
                print(f"[DEBUG]   node_events_history count: {len(context.get('node_events_history', {}))}")
                if current_tick_events:
                    print(f"[DEBUG]   Event keys: {list(current_tick_events.keys())}")
            
            if current_tick_events:
                tick_event_data = {
                    'tick': tick_num,
                    'timestamp': str(tick_data.get('timestamp', '')),
                    'current_tick_events': current_tick_events
                }
                with open(self.tick_events_file, 'a') as f:
                    f.write(json.dumps(tick_event_data, default=str) + '\n')
                
                if tick_num <= 5:
                    print(f"[DEBUG]   ✅ Wrote tick event to file")
            
            # 2. APPEND NODE EVENTS
            for exec_id, event in current_tick_events.items():
                if event.get('logic_completed', False):
                    node_event_data = {
                        'tick': tick_num,
                        'timestamp': str(tick_data.get('timestamp', '')),
                        'execution_id': exec_id,
                        'event': event
                    }
                    with open(self.node_events_file, 'a') as f:
                        f.write(json.dumps(node_event_data, default=str) + '\n')
            
            # 3. APPEND TRADES
            gps = context.get('gps')
            if gps:
                current_open_position_ids = {pos_id for pos_id, pos in gps.positions.items() if pos.get('status') == 'open'}
                newly_closed_ids = self.previous_open_position_ids - current_open_position_ids
                
                if newly_closed_ids:
                    closed_positions = context.get('closed_positions', [])
                    for closed_id in newly_closed_ids:
                        for closed_pos in closed_positions:
                            if closed_pos.get('position_id') == closed_id:
                                trade_data = {
                                    'tick': tick_num,
                                    'timestamp': str(tick_data.get('timestamp', '')),
                                    'position_id': closed_id,
                                    'trade': closed_pos
                                }
                                with open(self.trades_file, 'a') as f:
                                    f.write(json.dumps(trade_data, default=str) + '\n')
                                break
                
                self.previous_open_position_ids = current_open_position_ids
    
    # Create engine
    engine = SimpleBacktestEngine(config)
    
    # Run backtest
    print("Running backtest...")
    engine.run()
    
    tick_num = engine.tick_counter
    
    print(f"\n{'='*80}")
    print(f"✅ Backtest Complete")
    print(f"{'='*80}")
    print(f"Total ticks: {tick_num}")
    print(f"\nOutput files:")
    print(f"  📝 {tick_events_file}")
    print(f"  📝 {node_events_file}")
    print(f"  📝 {trades_file}")
    print(f"{'='*80}\n")
    
    # Count lines in each file
    for file_path, label in [
        (tick_events_file, "Tick events"),
        (node_events_file, "Node events"),
        (trades_file, "Trades")
    ]:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                line_count = sum(1 for _ in f)
            print(f"  {label}: {line_count} entries")
    
    print(f"\n{'='*80}\n")
    
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
