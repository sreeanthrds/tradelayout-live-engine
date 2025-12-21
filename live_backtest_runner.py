"""
Live Backtest Runner
====================

Runs CentralizedBacktestEngine and feeds events to SSE manager in real-time.
Used by API endpoint to execute actual backtests as background tasks.
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'src'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'strategy'))
sys.path.insert(0, SCRIPT_DIR)

from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from live_simulation_sse import sse_manager
from simple_live_stream import simple_stream_manager


class LiveBacktestRunner:
    """
    Runs backtest and feeds events to SSE manager.
    """
    
    def __init__(self, session_id: str, strategy_id: str, user_id: str, start_date: str, speed_multiplier: float = 1.0):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.user_id = user_id
        self.start_date = start_date
        self.speed_multiplier = speed_multiplier
        self.session = sse_manager.get_session(user_id)
        self.tick_count = 0
        
        # Track previous positions to detect closures (by position_id + re_entry_num)
        self.previous_closed_trades = set()  # Set of (position_id, re_entry_num) tuples for CLOSED trades
        self.last_node_events_count = 0
        
        # Initialize centralized processor
        self.centralized_processor = None
        
    async def run(self):
        """
        Execute backtest and feed events to sse_manager.
        """
        session = sse_manager.get_session(self.session_id)
        if not session:
            print(f"[LiveBacktest] Session {self.session_id} not found")
            return
        
        try:
            # Update status
            session.status = "initializing"
            print(f"[LiveBacktest] Starting backtest for session {self.session_id}")
            print(f"[LiveBacktest] Strategy: {self.strategy_id}")
            print(f"[LiveBacktest] Date: {self.start_date}")
            
            # Parse date
            backtest_date = datetime.strptime(self.start_date, '%Y-%m-%d')
            
            # Configure backtest
            config = BacktestConfig(
                strategy_ids=[self.strategy_id],
                backtest_date=backtest_date,
                debug_mode=None
            )
            
            # Create custom engine that feeds events to SSE
            engine = LiveBacktestEngineWithSSE(
                config, 
                session, 
                self.speed_multiplier, 
                self.session_id,
                user_id=self.user_id,
                strategy_id=self.strategy_id,
                backtest_date=self.start_date
            )
            
            # Update status to running
            session.status = "running"
            
            # CRITICAL FIX: Run CPU-heavy backtest in thread pool to avoid blocking event loop
            # This allows API endpoints to return immediately while backtest runs in background
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, engine.run)
            
            # Mark BOTH sessions as completed
            session.status = "completed"
            
            # Also mark simple_session as completed (prevents infinite SSE stream)
            simple_session = simple_stream_manager.get_session(self.session_id)
            if simple_session:
                simple_session.status = "completed"
            
            print(f"[LiveBacktest] Backtest completed for session {self.session_id}")
            
        except Exception as e:
            print(f"[LiveBacktest] Error in session {self.session_id}: {e}")
            import traceback
            traceback.print_exc()
            session.status = "error"
            session.error = str(e)


class LiveBacktestEngineWithSSE(CentralizedBacktestEngine):
    """
    Extended backtest engine that feeds events to SSE manager.
    """
    
    def __init__(self, config: BacktestConfig, session, speed_multiplier: float, session_id: str, 
                 user_id: str = None, strategy_id: str = None, backtest_date: str = None):
        super().__init__(config)
        self.session = session
        self.session_id = session_id
        self.speed_multiplier = speed_multiplier
        self.tick_count = 0
        
        # Track previous positions to detect closures (by position_id + re_entry_num)
        self.previous_closed_trades = set()  # Set of (position_id, re_entry_num) tuples for CLOSED trades
        self.previous_open_trades = {}  # Dict of {(position_id, re_entry_num): trade} for state comparison
        self.last_node_events_count = 0
        
        # Phase 2: State persistence setup
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.backtest_date = backtest_date
        self.state_file_path = None
        
        # Setup state persistence folder if metadata provided
        if user_id and strategy_id and backtest_date:
            self._setup_state_persistence(user_id, strategy_id, backtest_date)
    
    def _setup_state_persistence(self, user_id: str, strategy_id: str, backtest_date: str):
        """
        Setup folder structure for state persistence:
        {date}/{userid}/{strategyid}/node_events.jsonl
        """
        # Create base state directory
        state_base_dir = Path(SCRIPT_DIR) / 'live_state_cache'
        
        # Parse date to create folder
        try:
            date_obj = datetime.strptime(backtest_date, '%Y-%m-%d')
            date_folder = date_obj.strftime('%Y-%m-%d')
        except:
            date_folder = backtest_date
        
        # Create folder path: date/userid/strategyid
        state_folder = state_base_dir / date_folder / user_id / strategy_id
        state_folder.mkdir(parents=True, exist_ok=True)
        
        # State file paths
        self.state_file_path = state_folder / 'node_events.jsonl'
        self.trades_file_path = state_folder / 'trades.jsonl'
        
        # Clear old state files for fresh run
        if self.state_file_path.exists():
            self.state_file_path.unlink()
        if self.trades_file_path.exists():
            self.trades_file_path.unlink()
    
    def _persist_node_events(self, new_events: Dict[str, Any]):
        """
        Append new node events to state file incrementally (JSONL format).
        Each line is a separate event for efficient delta loading.
        """
        if not self.state_file_path:
            return
        
        try:
            with open(self.state_file_path, 'a') as f:
                for exec_id, event in new_events.items():
                    # Write each event as a JSON line
                    event_line = {
                        'exec_id': exec_id,
                        'event': event,
                        'timestamp': event.get('timestamp')
                    }
                    f.write(json.dumps(event_line) + '\n')
        except Exception as e:
            pass  # Silent fail for event persistence
    
    def _persist_trade(self, trade: Dict[str, Any]):
        """
        Append or update trade in trades file (JSONL format).
        Uses upsert pattern: overwrites existing trade with same trade_id.
        """
        if not self.trades_file_path:
            return
        
        try:
            trade_id = trade.get('trade_id')
            if not trade_id:
                return
            
            # Read all existing trades
            existing_trades = {}
            if self.trades_file_path.exists():
                with open(self.trades_file_path, 'r') as f:
                    for line in f:
                        trade_data = json.loads(line.strip())
                        existing_trades[trade_data['trade_id']] = trade_data
            
            # Update/add this trade
            existing_trades[trade_id] = trade
            
            # Write all trades back (upsert pattern)
            with open(self.trades_file_path, 'w') as f:
                for tid, tdata in existing_trades.items():
                    f.write(json.dumps(tdata) + '\n')
        
        except Exception as e:
            pass  # Silent fail for trade persistence
    
    def load_initial_state(self, last_event_id: str = None, last_trade_id: str = None) -> Dict[str, Any]:
        """
        Load initial state for reconnection/refresh.
        
        Args:
            last_event_id: If provided, return only events after this ID (delta).
            last_trade_id: If provided, return only trades after this ID (delta).
                          If None, return full state.
        
        Returns:
            Dict with 'events', 'trades', and 'is_delta' flag
        """
        result = {
            'events': {},
            'trades': [],
            'is_delta': False
        }
        
        # Load node events
        if self.state_file_path and self.state_file_path.exists():
            try:
                all_events = {}
                event_order = []
                
                with open(self.state_file_path, 'r') as f:
                    for line in f:
                        event_line = json.loads(line.strip())
                        exec_id = event_line['exec_id']
                        event = event_line['event']
                        all_events[exec_id] = event
                        event_order.append(exec_id)
                
                # Delta or full events
                if last_event_id and last_event_id in event_order:
                    last_idx = event_order.index(last_event_id)
                    delta_exec_ids = event_order[last_idx + 1:]
                    result['events'] = {eid: all_events[eid] for eid in delta_exec_ids}
                    result['is_delta'] = True
                else:
                    result['events'] = all_events
                
                pass  # Events loaded
            except Exception as e:
                pass  # Silent fail for event loading
        
        # Load trades
        if self.trades_file_path and self.trades_file_path.exists():
            try:
                all_trades = []
                
                with open(self.trades_file_path, 'r') as f:
                    for line in f:
                        trade = json.loads(line.strip())
                        all_trades.append(trade)
                
                # Delta or full trades
                if last_trade_id:
                    # Find index of last_trade_id
                    trade_ids = [t['trade_id'] for t in all_trades]
                    if last_trade_id in trade_ids:
                        last_idx = trade_ids.index(last_trade_id)
                        result['trades'] = all_trades[last_idx + 1:]
                        result['is_delta'] = True
                    else:
                        result['trades'] = all_trades
                else:
                    result['trades'] = all_trades
                
                pass  # Trades loaded
            except Exception as e:
                pass  # Silent fail for trade loading
        
        return result
        
    async def _process_ticks_centralized(self, ticks: list):
        """
        Override to feed events to SSE as ticks are processed.
        """
        from collections import defaultdict
        
        # Group ticks by second
        ticks_by_second = defaultdict(list)
        for tick in ticks:
            tick_timestamp = tick['timestamp']
            second_key = tick_timestamp.replace(microsecond=0)
            ticks_by_second[second_key].append(tick)
        
        sorted_seconds = sorted(ticks_by_second.keys())
        total_seconds = len(sorted_seconds)
        
        if total_seconds == 0:
            print(f"⚠️  No ticks to process")
            return
        
        print(f"⚡ Processing {len(ticks):,} ticks | Speed: {self.speed_multiplier}x")
        
        # Process each second
        for second_idx, second_timestamp in enumerate(sorted_seconds):
            tick_batch = ticks_by_second[second_timestamp]
            
            # Process ticks through data manager
            last_processed_tick = None
            for tick in tick_batch:
                try:
                    last_processed_tick = self.data_manager.process_tick(tick)
                    self.tick_count += 1
                except Exception as e:
                    continue
            
            # Process option ticks
            option_ticks = self.data_manager.get_option_ticks_for_timestamp(second_timestamp)
            for option_tick in option_ticks:
                try:
                    self.data_manager.process_tick(option_tick)
                    self.tick_count += 1
                except Exception as e:
                    continue
            
            # Execute strategy
            if last_processed_tick:
                try:
                    self.centralized_processor.on_tick(last_processed_tick)
                    
                    # Feed tick update to SSE
                    self._feed_tick_update_to_sse(second_timestamp, total_seconds)
                    
                except Exception as e:
                    print(f"⚠️  Processor error at {second_timestamp}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Throttle based on speed multiplier
            if self.speed_multiplier < 1000:  # Don't throttle for high speed
                import time
                time.sleep(1.0 / self.speed_multiplier if self.speed_multiplier > 0 else 0)
        
        print(f"✅ Processed {self.tick_count:,} total ticks")
    
    def _feed_tick_update_to_sse(self, timestamp, total_seconds):
        """
        Feed tick update event to SSE manager using diagnostics node events.
        Uses backtesting extraction logic to identify trades correctly.
        """
        try:
            # Get current strategy state
            active_strategies = self.centralized_processor.strategy_manager.active_strategies
            
            strategy_state = None
            for instance_id, state in active_strategies.items():
                strategy_state = state
                break
            
            if not strategy_state:
                return
            
            context = strategy_state.get('context', {})
            node_states = strategy_state.get('node_states', {})
            node_events_history = strategy_state.get('node_events_history', {})
            current_tick_events = context.get('current_tick_events', {})
            
            # Extract active/pending nodes
            active_nodes = []
            pending_nodes = []
            for node_id, state in node_states.items():
                status = state.get('status', 'Inactive')
                if status == 'Active':
                    active_nodes.append(node_id)
                elif status == 'Pending':
                    pending_nodes.append(node_id)
            
            # Build complete LTP store for ALL subscribed symbols (spot + options)
            ltp_store = {}
            
            # Get spot + option LTPs from context (where DataManager stores them)
            context_ltp_store = context.get('ltp_store', {})
            for symbol, ltp_data in context_ltp_store.items():
                if isinstance(ltp_data, dict):
                    ltp_store[symbol] = {
                        'ltp': float(ltp_data.get('ltp', 0)),
                        'timestamp': str(ltp_data.get('timestamp', '')),
                        'volume': ltp_data.get('volume', 0),
                        'oi': ltp_data.get('oi', 0)
                    }
                else:
                    # Legacy format: just a number
                    ltp_store[symbol] = {
                        'ltp': float(ltp_data),
                        'timestamp': timestamp.isoformat(),
                        'volume': 0,
                        'oi': 0
                    }
            
            # ========================================================================
            # USE GPS DIRECTLY - Same as regular backtesting!
            # ========================================================================
            # Get GPS (Global Position Store) from context
            context_manager = context.get('context_manager')
            if not context_manager:
                return
            
            gps = context_manager.gps
            
            # Get positions directly from GPS (authoritative source)
            gps_open_positions = gps.get_open_positions()
            gps_closed_positions = gps.get_closed_positions()
            
            # Build unified positions list with both open and closed positions
            # This allows UI to see the same position transition from open to closed
            all_positions = []
            
            # Add open positions (status = 'OPEN', no exit data)
            for position_id, gps_pos in gps_open_positions.items():
                transactions = gps_pos.get('transactions', [])
                if not transactions:
                    continue
                
                # Get latest transaction (current open position)
                latest_txn = transactions[-1]
                
                symbol = gps_pos.get('symbol', '')
                entry_price = float(latest_txn.get('entry_price', 0))
                quantity = float(latest_txn.get('quantity', 0))
                side = latest_txn.get('side', 'BUY').upper()
                entry_time = latest_txn.get('entry_time', '')
                
                # Get current price from LTP store
                symbol_ltp_data = ltp_store.get(symbol, {})
                current_price = symbol_ltp_data.get('ltp', entry_price) if isinstance(symbol_ltp_data, dict) else entry_price
                
                # Calculate unrealized P&L
                if side.lower() == 'buy':
                    unrealized_pnl = (current_price - entry_price) * quantity
                else:
                    unrealized_pnl = (entry_price - current_price) * quantity
                
                # Format entry time (space format)
                if 'T' in str(entry_time):
                    entry_time = str(entry_time).replace('T', ' ')
                
                all_positions.append({
                    'position_id': position_id,
                    're_entry_num': gps_pos.get('reEntryNum', 0),
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'entry_price': f"{entry_price:.2f}",
                    'current_price': current_price,
                    'unrealized_pnl': round(unrealized_pnl, 2),
                    'entry_time': entry_time,
                    'exit_price': None,  # No exit yet
                    'exit_time': None,
                    'pnl': None,
                    'status': 'OPEN',
                    'node_id': gps_pos.get('node_id', ''),
                    'entry_execution_id': gps_pos.get('entry_execution_id', ''),
                    'entry_flow_ids': gps_pos.get('entry_flow_ids', []),
                    'entry_trigger': gps_pos.get('entry_trigger', '')
                })
            
            # Add closed positions (status = 'CLOSED', with exit data)
            for position_id, gps_pos in gps_closed_positions.items():
                transactions = gps_pos.get('transactions', [])
                if not transactions:
                    continue
                
                # Iterate through ALL transactions (each re-entry is a separate transaction)
                for txn in transactions:
                    # Only include closed transactions
                    if txn.get('status') != 'closed':
                        continue
                    
                    # Get entry and exit data from the transaction
                    entry_data = txn.get('entry', {})
                    exit_data = txn.get('exit', {})
                    
                    entry_price = float(entry_data.get('price', 0))
                    exit_price = float(exit_data.get('price', 0))
                    pnl = float(txn.get('pnl', 0))
                    
                    all_positions.append({
                        'position_id': position_id,
                        're_entry_num': txn.get('reEntryNum', 0),
                        'symbol': txn.get('symbol', ''),
                        'side': entry_data.get('side', '').upper(),
                        'quantity': entry_data.get('quantity', 0),
                        'entry_price': f"{entry_price:.2f}",
                        'current_price': exit_price,  # Final price is exit price
                        'unrealized_pnl': 0,  # No unrealized P&L for closed positions
                        'entry_time': txn.get('entry_time', ''),
                        'exit_price': f"{exit_price:.2f}",
                        'exit_time': txn.get('exit_time', ''),
                        'pnl': round(pnl, 2),
                        'status': 'CLOSED',
                        'node_id': gps_pos.get('node_id', ''),
                        'entry_execution_id': gps_pos.get('entry_execution_id', ''),
                        'entry_flow_ids': gps_pos.get('entry_flow_ids', []),
                        'entry_trigger': gps_pos.get('entry_trigger', ''),
                        'exit_reason': exit_data.get('reason', '')
                    })
            
            # Separate for backward compatibility with existing UI code
            open_positions = [p for p in all_positions if p['status'] == 'OPEN']
            closed_positions = [p for p in all_positions if p['status'] == 'CLOSED']
            
            # OLD CODE REMOVED - No more event scanning!
            # Now using GPS as single source of truth
            
            # Dummy loop to maintain structure (will remove in next section)
            for exec_id, event in []:
                
                # Extract positions from EntryNode events
                if event.get('node_type') == 'EntryNode' and 'position' in event:
                    pos = event['position']
                    position_id = pos.get('position_id')
                    
                    # Check if position is still open (no exit event for this position + re_entry_num)
                    # NOTE: re_entry_num is in entry_config, NOT in position field for EntryNode
                    is_open = True
                    pos_re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
                    for check_exec_id, check_event in node_events_history.items():
                        node_type = check_event.get('node_type')
                        
                        # Check ExitNode events
                        if node_type == 'ExitNode':
                            exit_pos = check_event.get('position', {})
                            target_pos = exit_pos.get('position_id')
                            target_re_entry = exit_pos.get('re_entry_num', 0)
                            if target_pos == position_id and target_re_entry == pos_re_entry_num:
                                is_open = False
                                # Extract exit data
                                exit_result = check_event.get('exit_result', {})
                                closed_positions.append({
                                    'position_id': position_id,
                                    're_entry_num': pos_re_entry_num,
                                    'symbol': pos.get('symbol', ''),
                                    'side': pos.get('side', ''),
                                    'quantity': pos.get('quantity', 0),
                                    'entry_price': float(pos.get('entry_price', 0)),
                                    'exit_price': float(exit_result.get('exit_price', 0)),
                                    'pnl': float(exit_result.get('pnl', 0)),
                                    'entry_time': pos.get('entry_time', ''),
                                    'exit_time': exit_result.get('exit_time', '')
                                })
                                break
                        
                        # Check SquareOffNode events
                        elif node_type == 'SquareOffNode':
                            square_off_closed = check_event.get('closed_positions', [])
                            for sq_pos in square_off_closed:
                                if sq_pos.get('position_id') == position_id and sq_pos.get('re_entry_num', 0) == pos_re_entry_num:
                                    is_open = False
                                    # SquareOffNode has exit data directly in closed_positions
                                    # Calculate PnL for square-off
                                    entry_price = float(pos.get('entry_price', 0))
                                    exit_price = float(sq_pos.get('exit_price', 0))
                                    quantity = float(pos.get('quantity', 0))
                                    side = pos.get('side', 'buy').lower()
                                    if side == 'sell':
                                        pnl = (entry_price - exit_price) * quantity
                                    else:
                                        pnl = (exit_price - entry_price) * quantity
                                    
                                    closed_positions.append({
                                        'position_id': position_id,
                                        're_entry_num': pos_re_entry_num,
                                        'symbol': pos.get('symbol', ''),
                                        'side': pos.get('side', ''),
                                        'quantity': pos.get('quantity', 0),
                                        'entry_price': entry_price,
                                        'exit_price': exit_price,
                                        'pnl': pnl,
                                        'entry_time': pos.get('entry_time', ''),
                                        'exit_time': check_event.get('timestamp', '')
                                    })
                                    break
                            if not is_open:
                                break
                    
                    if is_open:
                        symbol = pos.get('symbol', '')
                        entry_price = float(pos.get('entry_price', 0))
                        # Get current LTP from ltp_store
                        symbol_ltp_data = ltp_store.get(symbol, {})
                        current_price = symbol_ltp_data.get('ltp', entry_price) if isinstance(symbol_ltp_data, dict) else entry_price
                        side_raw = pos.get('side', 'buy')
                        side = side_raw.upper()  # Match backtest format: uppercase
                        quantity = pos.get('quantity', 0)
                        
                        # Calculate unrealized P&L
                        if side_raw.lower() == 'buy':
                            unrealized_pnl = (current_price - entry_price) * quantity
                        else:  # sell
                            unrealized_pnl = (entry_price - current_price) * quantity
                        
                        # Get entry timestamp and format like backtest (space format)
                        entry_time_raw = pos.get('entry_time', '')
                        if 'T' in entry_time_raw:
                            # Convert ISO to space format: "2024-10-29T09:19:00+05:30" -> "2024-10-29 09:19:00+05:30"
                            entry_time = entry_time_raw.replace('T', ' ')
                        else:
                            entry_time = entry_time_raw
                        
                        # Get entry flow IDs by traversing parent chain
                        entry_flow_ids = []
                        current_exec_id = event.get('execution_id', '')
                        visited = set()
                        while current_exec_id and current_exec_id not in visited:
                            entry_flow_ids.insert(0, current_exec_id)  # Prepend to maintain order
                            visited.add(current_exec_id)
                            current_event = node_events_history.get(current_exec_id, {})
                            current_exec_id = current_event.get('parent_execution_id')
                        
                        # Get entry trigger (node_name, not node_id)
                        entry_node_event = node_events_history.get(event.get('execution_id'), {})
                        entry_trigger = entry_node_event.get('node_name', pos.get('node_id', ''))
                        
                        open_positions.append({
                            'position_id': position_id,
                            'symbol': symbol,
                            'side': side,  # Uppercase
                            'quantity': quantity,
                            'entry_price': f"{entry_price:.2f}",  # String format
                            'current_price': current_price,
                            'unrealized_pnl': round(unrealized_pnl, 2),
                            'entry_time': entry_time,  # Space format
                            'node_id': pos.get('node_id', ''),
                            'entry_execution_id': event.get('execution_id', ''),
                            're_entry_num': pos.get('re_entry_num', 0),
                            'entry_flow_ids': entry_flow_ids,
                            'entry_trigger': entry_trigger
                        })
            
            # Calculate P&L summary
            realized_pnl = sum(p['pnl'] for p in closed_positions)
            unrealized_pnl = sum(p['unrealized_pnl'] for p in open_positions)
            winning_trades = sum(1 for p in closed_positions if p['pnl'] > 0)
            losing_trades = sum(1 for p in closed_positions if p['pnl'] < 0)
            closed_count = len(closed_positions)
            
            pnl_summary = {
                'realized_pnl': f"{realized_pnl:.2f}",
                'unrealized_pnl': f"{unrealized_pnl:.2f}",
                'total_pnl': f"{realized_pnl + unrealized_pnl:.2f}",
                'closed_trades': closed_count,
                'open_trades': len(open_positions),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': f"{(winning_trades / closed_count * 100):.2f}" if closed_count > 0 else '0.00'
            }
            
            # Get candle data from context (ltp_store already populated from node events above)
            candle_data = {}
            
            # Get candle data from context (where it's actually stored)
            candle_df_dict = context.get('candle_df_dict', {})
            for symbol_tf, candles in candle_df_dict.items():
                if ':' in symbol_tf and candles is not None:
                    symbol, tf = symbol_tf.rsplit(':', 1)
                    last_candle = None
                    
                    # candles might be a list or DataFrame
                    if isinstance(candles, list) and len(candles) > 0:
                        last_candle = candles[-1]
                    elif hasattr(candles, 'iloc') and len(candles) > 0:  # DataFrame
                        last_candle = candles.iloc[-1].to_dict()
                    
                    # Convert to JSON-safe format (use _serialize_for_json for recursive handling)
                    if last_candle:
                        serializable_candle = self._serialize_for_json(last_candle)
                        
                        if symbol not in candle_data:
                            candle_data[symbol] = {}
                        candle_data[symbol][tf] = serializable_candle
            
            # ========================================================================
            # EXTRACT TRADES FROM EVENTS - EXACT BACKTESTING LOGIC
            # ========================================================================
            # Use the same extraction logic as backtesting (extract_trades_simplified.py)
            # This ensures consistent trade identification using (position_id, re_entry_num) tuples
            trades_data = self._extract_trades_from_events(node_events_history)
            all_closed_trades = trades_data.get('trades', [])
            
            # OLD EMISSION LOGIC REMOVED - Phase 1 comprehensive logic below handles all trades
            
            # ========================================================================
            # PHASE 1: EMIT TRADE_UPDATE FOR ALL TRADES (OPEN + CLOSED)
            # ========================================================================
            # Use comprehensive trade extraction (includes OPEN positions with flow IDs)
            all_trades = all_closed_trades  # This now includes OPEN trades from _extract_trades_from_events
            
            # ========================================================================
            # PHASE 6: CALCULATE UNREALIZED P&L FOR OPEN/PARTIAL TRADES
            # ========================================================================
            ltp_store = context.get('ltp_store', {})
            
            for trade in all_trades:
                status = trade.get('status')
                
                # Only calculate unrealized P&L for OPEN or PARTIAL trades
                if status in ['OPEN', 'PARTIAL']:
                    symbol = trade.get('symbol')
                    symbol_ltp_data = ltp_store.get(symbol, {})
                    
                    # Extract LTP from dict (ltp_store contains dicts with 'ltp' key)
                    if isinstance(symbol_ltp_data, dict):
                        current_ltp = symbol_ltp_data.get('ltp')
                    else:
                        current_ltp = symbol_ltp_data  # Legacy: direct number
                    
                    if current_ltp is not None:
                        entry_price = float(trade.get('entry_price', 0))
                        quantity = int(trade.get('quantity', 0))
                        qty_closed = int(trade.get('qty_closed', 0))
                        qty_open = quantity - qty_closed  # Remaining open quantity
                        side = trade.get('side', 'BUY').upper()
                        
                        # Calculate unrealized P&L for remaining open quantity
                        if side == 'BUY':
                            unrealized_pnl = (current_ltp - entry_price) * qty_open
                        else:  # SELL
                            unrealized_pnl = (entry_price - current_ltp) * qty_open
                        
                        # Update trade object
                        trade['unrealized_pnl'] = f"{unrealized_pnl:.2f}"
                        
                        # Also update P&L percentage to include unrealized
                        if entry_price > 0:
                            realized_pnl = float(trade.get('pnl', 0))
                            total_pnl = realized_pnl + unrealized_pnl
                            total_pnl_percent = (total_pnl / (entry_price * quantity)) * 100
                            trade['pnl_percent'] = f"{total_pnl_percent:.2f}"
            
            # Track ALL trades by key (not just closed)
            current_all_trades = {(t['position_id'], t['re_entry_num']): t for t in all_trades}
            
            # Compare with previous state
            for trade_key, trade in current_all_trades.items():
                previous_trade = self.previous_open_trades.get(trade_key) if hasattr(self, 'previous_open_trades') and isinstance(self.previous_open_trades, dict) else None
                
                # Emit if: new trade OR status changed OR exit data updated OR unrealized P&L changed
                is_new = previous_trade is None
                status_changed = previous_trade and previous_trade.get('status') != trade.get('status')
                exit_updated = previous_trade and previous_trade.get('exit_time') != trade.get('exit_time')
                unrealized_changed = previous_trade and previous_trade.get('unrealized_pnl') != trade.get('unrealized_pnl')
                
                if is_new or status_changed or exit_updated or unrealized_changed:
                    # Emit trade_update event
                    self.session.emit_trade_update(trade)
                    
                    # Also add to simple stream manager
                    simple_session = simple_stream_manager.get_session(self.session_id)
                    if simple_session:
                        simple_session.add_trade(trade)
                    
                    # Persist trade to disk (upsert pattern)
                    self._persist_trade(trade)
                    
                    # Trade emitted to SSE
            
            # Update tracking (store as dict for next comparison)
            self.previous_open_trades = current_all_trades
            
            # Emit node_event for any new events since last tick
            current_events_count = len(node_events_history)
            if current_events_count > self.last_node_events_count:
                # Get new events
                all_exec_ids = list(node_events_history.keys())
                new_exec_ids = all_exec_ids[self.last_node_events_count:]
                
                # Build new events dict
                new_events = {exec_id: node_events_history[exec_id] for exec_id in new_exec_ids}
                
                # Phase 2: Persist new events to disk incrementally
                self._persist_node_events(new_events)
                
                for exec_id in new_exec_ids:
                    event_payload = node_events_history[exec_id]
                    # Emit as node_event (existing SSE)
                    self.session.add_node_event(exec_id, event_payload)
                
                # Also add to simple stream manager (new simple pattern)
                simple_session = simple_stream_manager.get_session(self.session_id)
                if simple_session:
                    simple_session.add_events(new_events)
                
                self.last_node_events_count = current_events_count
            
            # Capture active node diagnostics
            # Get node_name and node_type from node_events_history (most reliable source)
            active_node_states = []
            
            # Build a lookup map: node_id -> (node_name, node_type) from events history
            node_metadata = {}
            for exec_id, event in node_events_history.items():
                nid = event.get('node_id')
                if nid and nid not in node_metadata:
                    node_metadata[nid] = {
                        'node_name': event.get('node_name', nid),
                        'node_type': event.get('node_type', 'Unknown')
                    }
            
            for node_id in active_nodes:
                node_state = node_states.get(node_id, {})
                
                # Get metadata from events history (most reliable)
                metadata = node_metadata.get(node_id, {})
                node_name = metadata.get('node_name', node_state.get('name', node_id))
                node_type = metadata.get('node_type', node_state.get('type', 'Unknown'))
                
                # Build partial diagnostics for this active node at current tick
                active_node_states.append({
                    'node_id': node_id,
                    'node_name': node_name,
                    'node_type': node_type,
                    'status': 'Active',
                    'timestamp': timestamp.isoformat(),
                    # These would be populated if node stores current evaluation state
                    'current_evaluation': node_state.get('last_evaluation', {})
                })
            
            # Build tick state and serialize EVERYTHING for JSON compatibility
            tick_state = {
                'timestamp': timestamp.isoformat(),
                'current_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'progress': {
                    'ticks_processed': self.tick_count,
                    'total_ticks': total_seconds,
                    'progress_percentage': round((self.tick_count / total_seconds) * 100, 2) if total_seconds > 0 else 0
                },
                'active_nodes': active_nodes,
                'pending_nodes': pending_nodes,
                'active_node_states': active_node_states,
                'current_tick_events': current_tick_events,
                'positions': all_positions,  # Unified list with both open and closed
                'open_positions': open_positions,  # Backward compatibility
                'closed_positions': closed_positions,  # Backward compatibility
                'pnl_summary': pnl_summary,
                'ltp_store': ltp_store,
                'candle_data': candle_data
            }
            
            # Serialize the entire tick state (handles all datetime objects recursively)
            serialized_tick_state = self._serialize_for_json(tick_state)
            
            # Update session tick state with serialized data
            self.session.update_tick_state(serialized_tick_state)
            
            # Also update simple stream manager session
            simple_session = simple_stream_manager.get_session(self.session_id)
            if simple_session:
                simple_session.update_progress(self.tick_count, total_seconds)
                simple_session.current_time = serialized_tick_state.get('current_time')
            
            # Clear current tick events for next tick
            context['current_tick_events'] = {}
            
            # Check if any node completed in this tick
            # If so, send full diagnostics snapshot
            has_completed_nodes = any(
                event.get('logic_completed', False) 
                for event in current_tick_events.values()
            )
            
            if has_completed_nodes:
                # Build full diagnostics (same format as backtest)
                # IMPORTANT: Serialize to handle datetime objects
                full_diagnostics = {
                    'events_history': self._serialize_for_json(node_events_history)
                }
                
                # Build trades from events (same extraction as backtest)
                trades = self._extract_trades_from_events(node_events_history)
                
                # Serialize trades as well
                serialized_trades = self._serialize_for_json(trades)
                
                # Emit full diagnostics snapshot (all data is now JSON-safe)
                self.session.emit_diagnostics_snapshot({
                    'diagnostics': full_diagnostics,
                    'trades': serialized_trades
                })
            
        except Exception as e:
            print(f"[SSE Feed] Error feeding tick update: {e}")
    
    def _serialize_for_json(self, obj):
        """
        Recursively serialize objects for JSON compatibility.
        Converts datetime objects, pandas Timestamp, numpy types to JSON-safe types.
        """
        import pandas as pd
        import numpy as np
        
        # Handle None
        if obj is None:
            return None
        
        # Handle datetime-like objects (datetime, pandas Timestamp)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        
        # Handle numpy types
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        
        # Handle pandas types
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        
        # Handle dict recursively
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        
        # Handle list/tuple recursively
        if isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(item) for item in obj]
        
        # Handle primitives
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # Fallback: convert to string
        return str(obj)
    
    def _extract_trades_from_events(self, node_events_history):
        """
        Extract trades from node events history (EXACT same logic as backtest extract_trades_simplified.py).
        
        Key difference from old implementation:
        - Uses (position_id, re_entry_num) TUPLE as key instead of just position_id
        - Gets re_entry_num from entry_config.re_entry_num (NOT from position)
        - Handles both ExitNode and SquareOffNode exits
        
        Returns trades in same format as trades_daily.json:
        {
            'summary': {...},
            'trades': [...]
        }
        """
        from collections import defaultdict
        from datetime import datetime
        
        # Build position index using (position_id, re_entry_num) tuple as key
        position_index = defaultdict(lambda: {
            'entry_event': None,
            'entry_exec_id': None,
            'exit_events': []
        })
        
        # Index all entry and exit events
        for exec_id, event in node_events_history.items():
            node_type = event.get('node_type', '')
            
            if node_type == 'EntryNode':
                position = event.get('position', {})
                position_id = position.get('position_id')
                # CRITICAL: Get re_entry_num from entry_config, NOT from position!
                re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
                
                if position_id:
                    key = (position_id, re_entry_num)  # Tuple key!
                    position_index[key]['entry_event'] = event
                    position_index[key]['entry_exec_id'] = exec_id
            
            elif node_type == 'ExitNode':
                position = event.get('position', {})
                position_id = position.get('position_id')
                re_entry_num = position.get('re_entry_num', 0)
                
                if not position_id:
                    position_id = event.get('action', {}).get('target_position_id')
                
                if position_id:
                    key = (position_id, re_entry_num)
                    timestamp = event.get('timestamp')
                    position_index[key]['exit_events'].append((timestamp, exec_id, event))
            
            elif node_type == 'SquareOffNode':
                # Square-off closes multiple positions
                closed_positions = event.get('closed_positions', [])
                timestamp = event.get('timestamp')
                
                for pos_info in closed_positions:
                    position_id = pos_info.get('position_id')
                    re_entry_num = pos_info.get('re_entry_num', 0)
                    
                    if position_id:
                        key = (position_id, re_entry_num)
                        position_index[key]['exit_events'].append((timestamp, exec_id, event))
        
        # Build trades list
        trades_list = []
        
        for (position_id, re_entry_num), trade_data in sorted(position_index.items()):
            entry_event = trade_data['entry_event']
            entry_exec_id = trade_data['entry_exec_id']
            exit_events = sorted(trade_data['exit_events'], key=lambda x: x[0])
            
            if not entry_event:
                continue
            
            # Extract entry data
            position = entry_event.get('position', {})
            action = entry_event.get('action', {})
            
            entry_price = float(action.get('price', 0))
            entry_qty = int(action.get('quantity', 1))
            entry_time = entry_event.get('timestamp', '')
            symbol = action.get('symbol', position.get('symbol', ''))
            side = action.get('side', position.get('side', '')).upper()
            
            # Extract exit data (use first exit for primary exit, aggregate P&L and qty)
            exit_price = None
            exit_time = None
            exit_reason = None
            trade_pnl = 0.0
            total_qty_closed = 0  # Track total quantity closed across all exits
            
            for _, exit_exec_id, exit_event in exit_events:
                node_type = exit_event.get('node_type', '')
                
                # Handle ExitNode vs SquareOffNode differently
                if node_type == 'ExitNode':
                    exit_result = exit_event.get('exit_result', {})
                    positions_closed = exit_result.get('positions_closed', 0)
                    
                    if positions_closed > 0:
                        # Use first effective exit for display
                        if exit_price is None:
                            exit_price_str = exit_result.get('exit_price', '0')
                            if isinstance(exit_price_str, str):
                                exit_price = float(exit_price_str.replace(',', ''))
                            else:
                                exit_price = float(exit_price_str)
                            
                            exit_time = exit_event.get('timestamp', '')
                            exit_reason = exit_event.get('node_name', '')
                        
                        # Aggregate P&L and quantity
                        pnl_value = exit_result.get('pnl', 0)
                        if isinstance(pnl_value, str):
                            pnl_value = float(pnl_value.replace(',', ''))
                        trade_pnl += pnl_value
                        total_qty_closed += positions_closed  # Each exit closes 1 position
                
                elif node_type == 'SquareOffNode':
                    # Square-off has different structure - data is in closed_positions
                    closed_positions_list = exit_event.get('closed_positions', [])
                    
                    # Find this specific position in the closed_positions list
                    for pos_info in closed_positions_list:
                        if pos_info.get('position_id') == position_id and pos_info.get('re_entry_num') == re_entry_num:
                            # Use first effective exit for display
                            if exit_price is None:
                                exit_price = float(pos_info.get('exit_price', 0))
                                exit_time = exit_event.get('timestamp', '')
                                exit_reason = exit_event.get('node_name', '') or 'Square-Off'
                            
                            # Calculate P&L for square-off
                            entry_px = float(pos_info.get('entry_price', 0))
                            exit_px = float(pos_info.get('exit_price', 0))
                            qty = int(pos_info.get('quantity', 1))
                            pos_side = pos_info.get('side', 'buy').lower()
                            
                            if pos_side == 'buy':
                                pnl = (exit_px - entry_px) * qty
                            else:  # sell
                                pnl = (entry_px - exit_px) * qty
                            
                            trade_pnl += pnl
                            total_qty_closed += 1  # Square-off closes 1 position
                            break
            
            # Calculate duration
            duration_minutes = 0
            if entry_time and exit_time:
                try:
                    entry_dt = datetime.fromisoformat(str(entry_time).replace('+05:30', ''))
                    exit_dt = datetime.fromisoformat(str(exit_time).replace('+05:30', ''))
                    duration_minutes = int((exit_dt - entry_dt).total_seconds() / 60)
                except:
                    pass
            
            # Calculate P&L percentage
            pnl_percent = 0.0
            if entry_price > 0:
                pnl_percent = (trade_pnl / (entry_price * entry_qty)) * 100
            
            # Determine status based on qty closed vs qty entered
            if total_qty_closed == 0:
                status = 'OPEN'
            elif total_qty_closed < entry_qty:
                status = 'PARTIAL'
            else:
                status = 'CLOSED'
            
            # Format trade_id (match backtesting format)
            if re_entry_num == 0:
                trade_id = position_id  # No suffix for initial entry
            else:
                trade_id = f"{position_id}-r{re_entry_num}"
            
            # Build entry flow IDs by traversing parent chain
            entry_flow_ids = []
            current_exec_id = entry_exec_id
            visited = set()
            while current_exec_id and current_exec_id not in visited:
                entry_flow_ids.insert(0, current_exec_id)  # Prepend to maintain order
                visited.add(current_exec_id)
                current_event = node_events_history.get(current_exec_id, {})
                current_exec_id = current_event.get('parent_execution_id')
            
            # Build exit flow IDs - one array per exit event (for partial exits)
            exit_flow_ids = []  # Array of arrays
            for _, exit_exec_id, _ in exit_events:
                exit_flow = []
                current_exec_id = exit_exec_id
                visited_exit = set()
                while current_exec_id and current_exec_id not in visited_exit:
                    exit_flow.insert(0, current_exec_id)
                    visited_exit.add(current_exec_id)
                    current_event = node_events_history.get(current_exec_id, {})
                    current_exec_id = current_event.get('parent_execution_id')
                exit_flow_ids.append(exit_flow)
            
            # Build trade object
            trade = {
                'trade_id': trade_id,
                'position_id': position_id,
                're_entry_num': re_entry_num,
                'symbol': symbol,
                'side': side,
                'quantity': entry_qty,
                'qty_closed': total_qty_closed,  # Phase 6: Track closed quantity
                'entry_price': f"{entry_price:.2f}",
                'entry_time': entry_time,
                'exit_price': f"{exit_price:.2f}" if exit_price else None,
                'exit_time': exit_time,
                'pnl': f"{trade_pnl:.2f}",
                'pnl_percent': f"{pnl_percent:.2f}",
                'unrealized_pnl': None,  # Phase 6: Will be calculated on each tick for OPEN/PARTIAL
                'duration_minutes': duration_minutes,
                'status': status,
                'entry_flow_ids': entry_flow_ids,
                'exit_flow_ids': exit_flow_ids,  # Phase 6: Now array of arrays
                'entry_trigger': entry_event.get('node_name', ''),
                'exit_reason': exit_reason
            }
            
            trades_list.append(trade)
        
        # Calculate summary
        total_pnl = sum(float(t['pnl']) for t in trades_list)
        winning_trades = [t for t in trades_list if float(t['pnl']) > 0]
        losing_trades = [t for t in trades_list if float(t['pnl']) < 0]
        
        summary = {
            'total_trades': len(trades_list),
            'total_pnl': round(total_pnl, 2),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(trades_list) * 100, 2) if trades_list else 0
        }
        
        return {
            'summary': summary,
            'trades': trades_list
        }


async def run_live_backtest(session_id: str, strategy_id: str, user_id: str, 
                            start_date: str, speed_multiplier: float = 1.0):
    """
    Run backtest as async task.
    """
    runner = LiveBacktestRunner(session_id, strategy_id, user_id, start_date, speed_multiplier)
    await runner.run()
