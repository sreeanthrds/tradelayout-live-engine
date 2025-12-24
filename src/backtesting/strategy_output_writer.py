"""
Strategy Output Writer
======================

Handles per-strategy file output for unified execution engine.
Creates isolated output directories and manages incremental/batch writes.

Directory Structure:
    backtest_data/
        ├── {user_id}/
        │   ├── {strategy_id}_{broker_connection_id}/
        │   │   ├── positions.json
        │   │   ├── trades.json
        │   │   ├── metrics.json
        │   │   └── events.jsonl
"""

import json
import gzip
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategyOutputWriter:
    """
    Manages file output for a single strategy in unified execution engine.
    
    Supports two write modes:
    - Batch mode (backtesting): Write all results at end
    - Incremental mode (live simulation): Write updates as they happen
    """
    
    def __init__(
        self,
        user_id: str,
        strategy_id: str,
        broker_connection_id: str,
        mode: str = "backtest",
        base_dir: str = "backtest_data",
        session_id: Optional[str] = None
    ):
        """
        Initialize output writer for a strategy.
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            broker_connection_id: Broker connection ID
            mode: "backtest" (batch writes) or "live_simulation" (incremental writes)
            base_dir: Base directory for output files
            session_id: Optional session ID for SSE streaming (live simulation only)
        """
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.broker_connection_id = broker_connection_id
        self.mode = mode
        self.session_id = session_id
        
        # SSE session (initialized lazily if session_id provided)
        self.sse_session = None
        if session_id:
            try:
                from live_simulation_sse import sse_manager
                self.sse_session = sse_manager.get_session(session_id)
                if not self.sse_session:
                    self.sse_session = sse_manager.create_session(session_id)
                logger.info(f"📡 SSE streaming enabled for session: {session_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize SSE session: {e}")
        
        # Create folder name: {strategy_id}_{broker_connection_id}
        # Truncate IDs to 13 chars for reasonable folder names
        strategy_short = strategy_id[:13] if len(strategy_id) > 13 else strategy_id
        broker_short = broker_connection_id[:13] if len(broker_connection_id) > 13 else broker_connection_id
        folder_name = f"{strategy_short}_{broker_short}"
        
        # Create output directory structure
        self.output_dir = Path(base_dir) / user_id / folder_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.positions_file = self.output_dir / "positions.json"
        self.trades_file = self.output_dir / "trades.json"
        self.metrics_file = self.output_dir / "metrics.json"
        self.events_file = self.output_dir / "events.jsonl"
        
        # In-memory buffers for batch mode
        self.positions_buffer: Dict[str, Any] = {}
        self.trades_buffer: List[Dict[str, Any]] = []
        self.metrics_buffer: Dict[str, Any] = {}
        
        # Context storage for diagnostics export
        self.context: Optional[Dict[str, Any]] = None
        
        logger.info(f"📁 Output writer initialized: {self.output_dir}")
    
    def write_position_update(self, position_data: Dict[str, Any]):
        """
        Write or update a single position.
        Also pushes to SSE if session is active.
        
        In batch mode: Stores in buffer
        In incremental mode: Writes to file immediately
        
        Args:
            position_data: Position data dict
        """
        position_id = position_data.get('position_id')
        
        if self.mode == "live_simulation":
            # Incremental write: Read existing, update, write back
            try:
                existing = self._read_json(self.positions_file) if self.positions_file.exists() else {}
                existing[position_id] = position_data
                self._write_json(self.positions_file, existing)
            except Exception as e:
                logger.warning(f"Failed to write position update: {e}")
        else:
            # Batch mode: Store in buffer
            self.positions_buffer[position_id] = position_data
        
        # Push to SSE if enabled
        if self.sse_session:
            self._push_to_sse('position', position_data)
    
    def write_trade(self, trade_data: Dict[str, Any]):
        """
        Write a trade record.
        Also pushes to SSE if session is active.
        
        Args:
            trade_data: Trade data dict
        """
        if self.mode == "live_simulation":
            # Incremental: Append to trades file
            try:
                existing = self._read_json(self.trades_file) if self.trades_file.exists() else []
                existing.append(trade_data)
                self._write_json(self.trades_file, existing)
            except Exception as e:
                logger.warning(f"Failed to write trade: {e}")
        else:
            # Batch mode: Store in buffer
            self.trades_buffer.append(trade_data)
        
        # Push to SSE if enabled
        if self.sse_session:
            self._push_to_sse('trade', trade_data)
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """
        Update strategy metrics.
        
        Args:
            metrics: Metrics dict (P&L, positions count, etc.)
        """
        if self.mode == "live_simulation":
            # Incremental: Overwrite metrics file
            try:
                self._write_json(self.metrics_file, metrics)
            except Exception as e:
                logger.warning(f"Failed to write metrics: {e}")
        else:
            # Batch mode: Store in buffer
            self.metrics_buffer = metrics
    
    def write_event(self, event_data: Dict[str, Any]):
        """
        Write an event to the events log (JSONL format).
        Also pushes to SSE if session is active.
        
        Args:
            event_data: Event data dict
        """
        try:
            with open(self.events_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write event: {e}")
        
        # Push to SSE if enabled
        if self.sse_session:
            self._push_to_sse('node', event_data)
    
    def set_context(self, context: Dict[str, Any]):
        """
        Store context for diagnostics export.
        Should be called at end of backtest before flush_batch().
        
        Args:
            context: Strategy execution context with node_events_history
        """
        self.context = context
    
    def flush_batch(self):
        """
        Write all buffered data to files (batch mode).
        Called at end of backtest.
        """
        if self.mode == "backtest":
            try:
                # Write positions
                if self.positions_buffer:
                    self._write_json(self.positions_file, self.positions_buffer)
                    logger.info(f"✅ Wrote {len(self.positions_buffer)} positions to {self.positions_file}")
                
                # Write trades
                if self.trades_buffer:
                    self._write_json(self.trades_file, self.trades_buffer)
                    logger.info(f"✅ Wrote {len(self.trades_buffer)} trades to {self.trades_file}")
                
                # Write metrics
                if self.metrics_buffer:
                    self._write_json(self.metrics_file, self.metrics_buffer)
                    logger.info(f"✅ Wrote metrics to {self.metrics_file}")
                
                # Generate diagnostics_export.json.gz, trades_daily.json.gz, and tick_events.json.gz
                if self.context:
                    self._export_diagnostics()
                    self._export_trades_daily()
                    self._export_tick_events()
                
            except Exception as e:
                logger.error(f"Failed to flush batch: {e}")
    
    def get_positions(self) -> Dict[str, Any]:
        """Get all positions (from buffer or file)."""
        if self.mode == "backtest":
            return self.positions_buffer.copy()
        else:
            return self._read_json(self.positions_file) if self.positions_file.exists() else {}
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all trades (from buffer or file)."""
        if self.mode == "backtest":
            return self.trades_buffer.copy()
        else:
            return self._read_json(self.trades_file) if self.trades_file.exists() else []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics (from buffer or file)."""
        if self.mode == "backtest":
            return self.metrics_buffer.copy()
        else:
            return self._read_json(self.metrics_file) if self.metrics_file.exists() else {}
    
    def _read_json(self, file_path: Path) -> Any:
        """Read JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return {} if file_path.name == "positions.json" or file_path.name == "metrics.json" else []
    
    def _write_json(self, file_path: Path, data: Any):
        """Write JSON file with pretty formatting."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")
    
    # ==================== SSE Streaming Methods ====================
    
    def write_ltp_snapshot(self, ltp_store: Dict[str, Any], timestamp: Any):
        """
        Write LTP store snapshot (for debugging/replay).
        Pushes to SSE if session is active.
        
        Args:
            ltp_store: Current LTP store dictionary
            timestamp: Current timestamp
        """
        if self.sse_session:
            self.sse_session.add_ltp_snapshot(ltp_store, timestamp)
    
    def write_candle_update(self, candle_data: Dict[str, Any]):
        """
        Write candle completion event.
        Pushes to SSE if session is active.
        
        Args:
            candle_data: Completed candle data (symbol, timeframe, OHLCV)
        """
        if self.sse_session:
            self.sse_session.add_candle_update(candle_data)
    
    def write_node_diagnostic(self, execution_id: str, diagnostic_data: Dict[str, Any]):
        """
        Write per-tick node diagnostic (active nodes only).
        Uses same format as NodeDiagnostics but captures every tick.
        Pushes to SSE if session is active.
        
        Args:
            execution_id: Unique execution ID
            diagnostic_data: Node diagnostic snapshot
        """
        if self.sse_session:
            self.sse_session.add_node_event(execution_id, diagnostic_data)
    
    def _push_to_sse(self, event_type: str, data: Dict[str, Any]):
        """
        Internal helper to push events to SSE.
        
        Args:
            event_type: Type of event ('node', 'trade', 'position', 'ltp', 'candle')
            data: Event data
        """
        if not self.sse_session:
            return
        
        try:
            if event_type == 'node':
                # Extract execution_id if present, otherwise generate
                execution_id = data.get('execution_id', f"evt_{datetime.now().timestamp()}")
                self.sse_session.add_node_event(execution_id, data)
            
            elif event_type == 'trade':
                self.sse_session.add_trade_event(data)
            
            elif event_type == 'position':
                self.sse_session.add_position_update(data)
            
            logger.debug(f"📡 SSE push: {event_type} event")
            
        except Exception as e:
            logger.warning(f"Failed to push {event_type} event to SSE: {e}")
    
    # ==================== Diagnostics Export (UI Format) ====================
    
    def _export_diagnostics(self):
        """
        Export diagnostics in diagnostics_export.json.gz format.
        """
        try:
            node_events_history = self.context.get('node_events_history', {})
            
            diagnostics_data = {
                'events_history': node_events_history
            }
            
            diagnostics_file = self.output_dir / 'diagnostics_export.json.gz'
            with gzip.open(diagnostics_file, 'wt', encoding='utf-8') as f:
                json.dump(diagnostics_data, f, indent=2, default=str)
            
            logger.info(f"✅ Exported {len(node_events_history)} node events to {diagnostics_file}")
            
        except Exception as e:
            logger.error(f"Failed to export diagnostics: {e}")
    
    def _export_trades_daily(self):
        """
        Export trades in trades_daily.json.gz format.
        Uses same logic as extract_trades_simplified.py.
        """
        try:
            node_events_history = self.context.get('node_events_history', {})
            
            # Build position index
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
                    re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
                    
                    if position_id:
                        key = (position_id, re_entry_num)
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
                    closed_positions = event.get('closed_positions', [])
                    timestamp = event.get('timestamp')
                    
                    for pos_info in closed_positions:
                        position_id = pos_info.get('position_id')
                        re_entry_num = pos_info.get('re_entry_num', 0)
                        
                        if position_id:
                            key = (position_id, re_entry_num)
                            position_index[key]['exit_events'].append((timestamp, exec_id, event))
            
            # Build trades list
            trades = []
            total_pnl = 0.0
            winning_trades = 0
            losing_trades = 0
            
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
                
                # Build entry flow IDs
                entry_flow_ids = self._build_flow_chain(node_events_history, entry_exec_id)
                
                # Extract exit data
                exit_price = None
                exit_time = None
                exit_reason = None
                exit_flow_ids = []
                trade_pnl = 0.0
                
                for _, exit_exec_id, exit_event in exit_events:
                    node_type = exit_event.get('node_type', '')
                    
                    if node_type == 'ExitNode':
                        exit_result = exit_event.get('exit_result', {})
                        positions_closed = exit_result.get('positions_closed', 0)
                        
                        if positions_closed > 0:
                            if exit_price is None:
                                exit_price_str = exit_result.get('exit_price', '0')
                                if isinstance(exit_price_str, str):
                                    exit_price = float(exit_price_str.replace(',', ''))
                                else:
                                    exit_price = float(exit_price_str)
                                
                                exit_time = exit_event.get('timestamp', '')
                                exit_reason = exit_event.get('node_name', '')
                                exit_flow_ids = self._build_flow_chain(node_events_history, exit_exec_id)
                            
                            pnl_value = exit_result.get('pnl', 0)
                            if isinstance(pnl_value, str):
                                pnl_value = float(pnl_value.replace(',', ''))
                            trade_pnl += pnl_value
                    
                    elif node_type == 'SquareOffNode':
                        closed_positions_list = exit_event.get('closed_positions', [])
                        
                        for pos_info in closed_positions_list:
                            if pos_info.get('position_id') == position_id and pos_info.get('re_entry_num') == re_entry_num:
                                if exit_price is None:
                                    exit_price = float(pos_info.get('exit_price', 0))
                                    exit_time = exit_event.get('timestamp', '')
                                    exit_reason = exit_event.get('node_name', '') or 'Square-Off'
                                    exit_flow_ids = self._build_flow_chain(node_events_history, exit_exec_id)
                                
                                entry_px = float(pos_info.get('entry_price', 0))
                                exit_px = float(pos_info.get('exit_price', 0))
                                qty = int(pos_info.get('quantity', 1))
                                pos_side = pos_info.get('side', 'buy').lower()
                                
                                if pos_side == 'buy':
                                    pnl = (exit_px - entry_px) * qty
                                else:
                                    pnl = (entry_px - exit_px) * qty
                                
                                trade_pnl += pnl
                                break
                
                # Calculate duration
                duration_minutes = 0
                if entry_time and exit_time:
                    try:
                        from datetime import datetime
                        entry_dt = datetime.fromisoformat(entry_time.replace('+05:30', ''))
                        exit_dt = datetime.fromisoformat(exit_time.replace('+05:30', ''))
                        duration_minutes = int((exit_dt - entry_dt).total_seconds() / 60)
                    except:
                        pass
                
                # Calculate P&L percentage
                pnl_percent = 0.0
                if entry_price > 0:
                    pnl_percent = (trade_pnl / (entry_price * entry_qty)) * 100
                
                # Status
                status = 'closed' if exit_price else 'open'
                
                # Track stats
                total_pnl += trade_pnl
                if trade_pnl > 0:
                    winning_trades += 1
                elif trade_pnl < 0:
                    losing_trades += 1
                
                # Get entry trigger name
                entry_trigger = "Unknown"
                if entry_flow_ids:
                    for exec_id in entry_flow_ids:
                        node = node_events_history.get(exec_id, {})
                        node_type = node.get('node_type', '')
                        if 'Signal' in node_type or 'Condition' in node_type:
                            entry_trigger = node.get('node_name', 'Unknown')
                            break
                
                # Build trade object
                trade = {
                    "trade_id": f"{position_id}-r{re_entry_num}",
                    "position_id": position_id,
                    "re_entry_num": re_entry_num,
                    "symbol": symbol,
                    "side": side,
                    "quantity": entry_qty,
                    "entry_price": f"{entry_price:.2f}",
                    "entry_time": entry_time,
                    "exit_price": f"{exit_price:.2f}" if exit_price else None,
                    "exit_time": exit_time,
                    "pnl": f"{trade_pnl:.2f}",
                    "pnl_percent": f"{pnl_percent:.2f}",
                    "duration_minutes": duration_minutes,
                    "status": status,
                    "entry_flow_ids": entry_flow_ids,
                    "exit_flow_ids": exit_flow_ids,
                    "entry_trigger": entry_trigger,
                    "exit_reason": exit_reason
                }
                
                trades.append(trade)
            
            # Build summary
            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            # Extract date
            date = "unknown"
            if trades:
                first_time = trades[0].get('entry_time', '')
                if first_time:
                    try:
                        date = first_time.split()[0]
                    except:
                        pass
            
            result = {
                "date": date,
                "summary": {
                    "total_trades": total_trades,
                    "total_pnl": f"{total_pnl:.2f}",
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": f"{win_rate:.2f}"
                },
                "trades": trades
            }
            
            trades_file = self.output_dir / 'trades_daily.json.gz'
            with gzip.open(trades_file, 'wt', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            logger.info(f"✅ Exported {total_trades} trades to {trades_file} (P&L: ₹{total_pnl:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to export trades: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _build_flow_chain(self, events_history: Dict, exec_id: str, max_depth: int = 50) -> List[str]:
        """
        Build flow chain from current node back to start/trigger.
        Returns list of execution IDs in chronological order.
        """
        chain = [exec_id]
        current_id = exec_id
        depth = 0
        
        while current_id and current_id in events_history and depth < max_depth:
            event = events_history[current_id]
            parent_id = event.get('parent_execution_id')
            
            if parent_id and parent_id in events_history:
                parent_event = events_history[parent_id]
                node_type = parent_event.get('node_type', '')
                
                if any(keyword in node_type for keyword in ['Signal', 'Condition', 'Start', 'Entry', 'Exit']):
                    chain.append(parent_id)
                
                current_id = parent_id
                depth += 1
            else:
                break
        
        return list(reversed(chain))
    
    def _export_tick_events(self):
        """
        Export per-tick snapshots (LTP store, candle store) to tick_events.json.gz.
        Provides complete market data visibility at every tick.
        """
        try:
            tick_events = self.context.get('tick_events', {})
            
            if not tick_events:
                logger.warning("No tick events captured - skipping tick_events.json.gz export")
                return
            
            output_file = self.output_dir / 'tick_events.json.gz'
            
            # Sort by timestamp for chronological order
            sorted_events = dict(sorted(tick_events.items()))
            
            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                json.dump(sorted_events, f, indent=2, default=str)
            
            logger.info(f"✅ Exported {len(tick_events)} tick events to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export tick events: {e}")
            import traceback
            logger.error(traceback.format_exc())
