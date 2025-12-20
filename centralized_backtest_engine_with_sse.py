"""
Centralized Backtest Engine with SSE Event Streaming
====================================================

Extends CentralizedBacktestEngine to emit SSE events during backtesting.
Uses hybrid model: compressed initial state, incremental updates, event ID tracking.

Event Types:
1. initial_state    - Full compressed snapshot on session start
2. tick_update      - Incremental tick data (uncompressed)
3. node_event       - Single node event when logic completes
4. trade_update     - Single trade when position closes
5. backtest_complete - Final compressed snapshot

DO NOT modify the original CentralizedBacktestEngine - this is a separate implementation.
"""

import os
import sys
import json
import gzip
import base64
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

# Add engine path
engine_path = os.path.join(os.path.dirname(__file__), '..', 'tradelayout-engine')
sys.path.insert(0, engine_path)

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from src.backtesting.results_manager import BacktestResults

logger = logging.getLogger(__name__)


class SSEEventEmitter:
    """
    Fire-and-forget SSE event emitter.
    Broadcasts events without tracking client state.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.event_id = 0
        self.callbacks: List[Callable] = []
    
    def register_callback(self, callback: Callable):
        """Register a callback to receive events"""
        self.callbacks.append(callback)
    
    def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Emit event to all registered callbacks.
        Fire-and-forget - doesn't care about client state.
        """
        self.event_id += 1
        
        event_payload = {
            "event": event_type,
            "data": {
                **data,
                "event_id": self.event_id,
                "session_id": self.session_id
            }
        }
        
        # Broadcast to all callbacks
        for callback in self.callbacks:
            try:
                callback(event_payload)
            except Exception as e:
                # Log but don't stop on callback errors
                logger.error(f"SSE callback error: {e}")
    
    def compress_json(self, data: Dict[str, Any]) -> str:
        """Gzip + base64 encode JSON data"""
        json_str = json.dumps(data, default=str)
        compressed = gzip.compress(json_str.encode('utf-8'))
        return base64.b64encode(compressed).decode('utf-8')
    
    def get_current_event_id(self) -> int:
        """Get current event ID for client tracking"""
        return self.event_id


class CentralizedBacktestEngineWithSSE(CentralizedBacktestEngine):
    """
    Extended backtest engine that emits SSE events during backtesting.
    
    Uses hybrid model:
    - Initial: Compressed full snapshot
    - Updates: Incremental uncompressed deltas
    - Reconnect: Event ID tracking for gap detection
    """
    
    def __init__(
        self, 
        config: BacktestConfig, 
        session_id: str,
        output_dir: str = "sse_backtest_output"
    ):
        """
        Initialize engine with SSE event streaming.
        
        Args:
            config: Backtest configuration
            session_id: Unique session identifier
            output_dir: Directory for fallback file output
        """
        super().__init__(config)
        
        # SSE configuration
        self.session_id = session_id
        self.emitter = SSEEventEmitter(session_id)
        
        # Output configuration (fallback)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Track state for incremental updates
        self.last_diagnostics_event_count = 0
        self.last_trades_count = 0
        self.initial_state_sent = False
    
    def register_sse_callback(self, callback: Callable):
        """
        Register callback to receive SSE events.
        Callback receives: {"event": "...", "data": {...}}
        """
        self.emitter.register_callback(callback)
    
    def _emit_initial_state(self):
        """
        Emit initial_state event with compressed diagnostics and trades.
        Called once at session start.
        """
        if self.initial_state_sent:
            return
        
        # Get initial diagnostics (empty at start)
        diagnostics = {
            "events_history": {},
            "current_state": {}
        }
        
        # Get initial trades (empty at start)
        trades = {
            "date": self.config.start_date.strftime("%Y-%m-%d"),
            "summary": {
                "total_trades": 0,
                "total_pnl": "0.00",
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.00"
            },
            "trades": []
        }
        
        # Compress
        diagnostics_compressed = self.emitter.compress_json(diagnostics)
        trades_compressed = self.emitter.compress_json(trades)
        
        # Calculate sizes
        diagnostics_size = len(json.dumps(diagnostics, default=str))
        trades_size = len(json.dumps(trades, default=str))
        
        # Emit
        self.emitter.emit("initial_state", {
            "diagnostics": diagnostics_compressed,
            "trades": trades_compressed,
            "uncompressed_sizes": {
                "diagnostics": diagnostics_size,
                "trades": trades_size
            },
            "strategy_id": self.config.strategy_id,
            "start_date": self.config.start_date.strftime("%Y-%m-%d"),
            "end_date": self.config.end_date.strftime("%Y-%m-%d")
        })
        
        self.initial_state_sent = True
        logger.info(f"[SSE] Emitted initial_state (diagnostics: {diagnostics_size}B, trades: {trades_size}B)")
    
    def _emit_tick_update(self, tick_num: int, tick_data: Dict[str, Any]):
        """
        Emit tick_update event with current tick state.
        Uncompressed, incremental data only.
        """
        self.emitter.emit("tick_update", {
            "tick": tick_num,
            "timestamp": tick_data.get("timestamp"),
            "node_executions": tick_data.get("node_executions", {}),
            "open_positions": tick_data.get("open_positions", []),
            "pnl_summary": self._get_pnl_summary(),
            "ltp": tick_data.get("ltp", {}),
            "indicators": tick_data.get("indicators", {}),
            "active_nodes": tick_data.get("active_nodes", []),
            "execution_count": tick_data.get("execution_count", 0)
        })
    
    def _emit_node_event(self, event: Dict[str, Any]):
        """
        Emit node_event for single completed node.
        Incremental - only the new event, not full history.
        """
        self.emitter.emit("node_event", {
            "execution_id": event.get("execution_id"),
            "node_id": event.get("node_id"),
            "node_name": event.get("node_name"),
            "node_type": event.get("node_type"),
            "timestamp": event.get("timestamp"),
            "event_type": event.get("event_type"),
            "signal_emitted": event.get("evaluation_data", {}).get("signal_emitted"),
            "conditions_preview": event.get("evaluation_data", {}).get("conditions_preview")
        })
    
    def _emit_trade_update(self, trade: Dict[str, Any], summary: Dict[str, Any]):
        """
        Emit trade_update for single closed trade.
        Incremental - only the new trade and updated summary.
        """
        self.emitter.emit("trade_update", {
            "trade": trade,
            "summary": summary
        })
    
    def _emit_backtest_complete(self):
        """
        Emit backtest_complete event with final compressed state.
        """
        # Get final diagnostics
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if active_strategies:
            strategy_state = list(active_strategies.values())[0]
            context = strategy_state.get('context', {})
            diagnostics = context.get('diagnostics')
            
            if diagnostics:
                diagnostics_data = diagnostics.get_all_events()
            else:
                diagnostics_data = {"events_history": {}, "current_state": {}}
        else:
            diagnostics_data = {"events_history": {}, "current_state": {}}
        
        # Get final trades
        trades_data = self._get_trades_data()
        
        # Compress
        diagnostics_compressed = self.emitter.compress_json(diagnostics_data)
        trades_compressed = self.emitter.compress_json(trades_data)
        
        # Calculate sizes
        diagnostics_size = len(json.dumps(diagnostics_data, default=str))
        trades_size = len(json.dumps(trades_data, default=str))
        
        # Emit
        self.emitter.emit("backtest_complete", {
            "diagnostics": diagnostics_compressed,
            "trades": trades_compressed,
            "uncompressed_sizes": {
                "diagnostics": diagnostics_size,
                "trades": trades_size
            },
            "total_ticks": getattr(self, 'total_ticks_processed', 0)
        })
        
        logger.info(f"[SSE] Emitted backtest_complete (diagnostics: {diagnostics_size}B, trades: {trades_size}B)")
    
    def _get_pnl_summary(self) -> Dict[str, Any]:
        """Get current P&L summary"""
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return {
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0
            }
        
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        gps = context.get('gps')
        
        if not gps:
            return {
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0
            }
        
        realized_pnl = gps.get_total_realized_pnl()
        unrealized_pnl = gps.get_total_unrealized_pnl()
        
        closed_positions = context.get('closed_positions', [])
        open_positions = gps.get_all_open_positions()
        
        # Calculate win rate
        winning_trades = sum(1 for p in closed_positions if p.get('pnl', 0) > 0)
        losing_trades = sum(1 for p in closed_positions if p.get('pnl', 0) < 0)
        win_rate = (winning_trades / len(closed_positions) * 100) if closed_positions else 0
        
        return {
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(realized_pnl + unrealized_pnl, 2),
            "closed_trades": len(closed_positions),
            "open_trades": len(open_positions),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2)
        }
    
    def _get_trades_data(self) -> Dict[str, Any]:
        """Get trades data in standard format"""
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return {
                "date": self.config.start_date.strftime("%Y-%m-%d"),
                "summary": {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0
                },
                "trades": []
            }
        
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        closed_positions = context.get('closed_positions', [])
        
        trades = []
        for pos in closed_positions:
            trade = {
                "trade_id": pos.get('position_id'),
                "position_id": pos.get('position_id'),
                "symbol": pos.get('symbol'),
                "side": pos.get('side'),
                "quantity": pos.get('quantity'),
                "entry_price": round(pos.get('entry_price', 0), 2),
                "entry_time": pos.get('entry_time'),
                "exit_price": round(pos.get('exit_price', 0), 2),
                "exit_time": pos.get('exit_time'),
                "pnl": round(pos.get('pnl', 0), 2),
                "status": "CLOSED"
            }
            trades.append(trade)
        
        # Calculate summary
        total_pnl = sum(t["pnl"] for t in trades)
        winning_trades = sum(1 for t in trades if t["pnl"] > 0)
        losing_trades = sum(1 for t in trades if t["pnl"] < 0)
        win_rate = (winning_trades / len(trades) * 100) if trades else 0
        
        return {
            "date": self.config.start_date.strftime("%Y-%m-%d"),
            "summary": {
                "total_trades": len(trades),
                "total_pnl": round(total_pnl, 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2)
            },
            "trades": trades
        }
    
    def _process_ticks_centralized(self, ticks: List[Dict]) -> None:
        """
        Override to emit SSE events during tick processing.
        Emits tick_update for each second, node_event and trade_update on changes.
        """
        # Emit initial state before first tick
        if not self.initial_state_sent:
            self._emit_initial_state()
        
        # Group ticks by second
        ticks_by_second = {}
        for tick in ticks:
            timestamp = tick['timestamp']
            second_key = timestamp.replace(microsecond=0)
            
            if second_key not in ticks_by_second:
                ticks_by_second[second_key] = []
            ticks_by_second[second_key].append(tick)
        
        total_seconds = len(ticks_by_second)
        
        # Process each second's batch of ticks
        second_count = 0
        for second_key in sorted(ticks_by_second.keys()):
            second_count += 1
            second_ticks = ticks_by_second[second_key]
            
            # Process all ticks for this second
            for tick in second_ticks:
                self.data_manager.process_tick(tick)
                self.tick_counter += 1
            
            # Initialize current_tick_events before strategy execution
            active_strategies = self.centralized_processor.strategy_manager.active_strategies
            if active_strategies:
                strategy_state = list(active_strategies.values())[0]
                context = strategy_state.get('context', {})
                context['current_tick_events'] = {}
            
            # Execute strategy once per second
            self.centralized_processor.on_tick(tick_data=second_ticks[-1])
            
            # EMIT TICK UPDATE
            self._emit_tick_update_from_context(second_key, second_count)
            
            # Check for new node events and emit incrementally
            self._check_and_emit_node_events()
            
            # Check for new trades and emit incrementally
            self._check_and_emit_trade_updates()
        
        self.total_ticks_processed = total_seconds
    
    def _emit_tick_update_from_context(self, timestamp: datetime, tick_num: int):
        """
        Emit tick_update event with data from current context.
        """
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return
        
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        
        # Get current_tick_events populated during execution
        current_tick_events = context.get('current_tick_events', {})
        
        # Get LTP data
        ltp_store = context.get('ltp_store', {})
        
        # Get open positions
        gps = context.get('gps')
        open_positions = []
        if gps:
            positions = gps.get_all_open_positions()
            open_positions = [
                {
                    "position_id": pos.get('position_id'),
                    "symbol": pos.get('symbol'),
                    "side": pos.get('side'),
                    "quantity": pos.get('quantity'),
                    "entry_price": round(pos.get('entry_price', 0), 2),
                    "current_price": round(pos.get('current_price', 0), 2),
                    "unrealized_pnl": round(pos.get('unrealized_pnl', 0), 2),
                    "entry_time": pos.get('entry_time'),
                    "status": "OPEN"
                }
                for pos in positions
            ]
        
        # Get closed positions (full trade details)
        closed_positions_raw = context.get('closed_positions', [])
        closed_positions = [
            {
                "trade_id": pos.get('position_id'),
                "position_id": pos.get('position_id'),
                "re_entry_num": pos.get('re_entry_num', 0),
                "symbol": pos.get('symbol'),
                "side": pos.get('side'),
                "quantity": pos.get('quantity'),
                "entry_price": round(pos.get('entry_price', 0), 2),
                "entry_time": pos.get('entry_time'),
                "exit_price": round(pos.get('exit_price', 0), 2),
                "exit_time": pos.get('exit_time'),
                "pnl": round(pos.get('pnl', 0), 2),
                "pnl_percent": round(pos.get('pnl_percent', 0), 2) if pos.get('pnl_percent') else 0.0,
                "duration_minutes": pos.get('duration_minutes', 0),
                "status": "CLOSED",
                "entry_flow_ids": pos.get('entry_flow_ids', []),
                "exit_flow_ids": pos.get('exit_flow_ids', []),
                "entry_trigger": pos.get('entry_trigger'),
                "exit_reason": pos.get('exit_reason')
            }
            for pos in closed_positions_raw
        ]
        
        # Get active node IDs
        active_nodes = []
        if current_tick_events:
            active_nodes = list(set(event.get('node_id') for event in current_tick_events.values()))
        
        # Option: Simplify node_executions if needed (set SIMPLIFY_NODE_EXECUTIONS=True)
        # By default, send full details for tracing/logging purposes
        SIMPLIFY_NODE_EXECUTIONS = False  # Set to True to reduce payload
        
        if SIMPLIFY_NODE_EXECUTIONS:
            # Simplified version - only essential fields
            node_executions_data = {}
            for exec_id, event in current_tick_events.items():
                node_executions_data[exec_id] = {
                    "execution_id": event.get('execution_id'),
                    "node_id": event.get('node_id'),
                    "node_name": event.get('node_name'),
                    "node_type": event.get('node_type'),
                    "timestamp": event.get('timestamp'),
                    "signal_emitted": event.get('signal_emitted', False),
                    "logic_completed": event.get('logic_completed', False)
                }
        else:
            # Full details - includes evaluated_conditions, candle_data, etc.
            node_executions_data = current_tick_events
        
        # Build tick data
        tick_data = {
            "tick": tick_num,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S+05:30"),
            "node_executions": node_executions_data,
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "pnl_summary": self._get_pnl_summary(),
            "ltp": ltp_store,
            "active_nodes": active_nodes,
            "execution_count": len(current_tick_events)
        }
        
        self._emit_tick_update(tick_num, tick_data)
    
    def _check_and_emit_node_events(self):
        """
        Check for new node events in diagnostics and emit incrementally.
        Only emits events that haven't been sent yet.
        """
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return
        
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        diagnostics = context.get('diagnostics')
        
        if not diagnostics:
            return
        
        # Get all events from diagnostics
        all_events = diagnostics.get_all_events()
        events_history = all_events.get('events_history', {})
        
        # Count current events
        current_event_count = len(events_history)
        
        # If new events, emit them
        if current_event_count > self.last_diagnostics_event_count:
            # Get only new events
            all_event_ids = sorted(events_history.keys())
            new_event_ids = all_event_ids[self.last_diagnostics_event_count:]
            
            for event_id in new_event_ids:
                event = events_history[event_id]
                # Only emit logic_completed events (significant milestones)
                if event.get('event_type') == 'logic_completed':
                    self._emit_node_event(event)
            
            self.last_diagnostics_event_count = current_event_count
    
    def _check_and_emit_trade_updates(self):
        """
        Check for new closed trades and emit incrementally.
        Only emits trades that haven't been sent yet.
        """
        active_strategies = self.centralized_processor.strategy_manager.active_strategies
        if not active_strategies:
            return
        
        strategy_state = list(active_strategies.values())[0]
        context = strategy_state.get('context', {})
        closed_positions = context.get('closed_positions', [])
        
        current_trade_count = len(closed_positions)
        
        # If new trades, emit them
        if current_trade_count > self.last_trades_count:
            # Get only new trades
            new_trades = closed_positions[self.last_trades_count:]
            
            for pos in new_trades:
                trade = {
                    "trade_id": pos.get('position_id'),
                    "position_id": pos.get('position_id'),
                    "symbol": pos.get('symbol'),
                    "side": pos.get('side'),
                    "quantity": pos.get('quantity'),
                    "entry_price": f"{pos.get('entry_price', 0):.2f}",
                    "entry_time": pos.get('entry_time'),
                    "exit_price": f"{pos.get('exit_price', 0):.2f}",
                    "exit_time": pos.get('exit_time'),
                    "pnl": f"{pos.get('pnl', 0):.2f}",
                    "status": "CLOSED"
                }
                
                # Calculate updated summary
                total_pnl = sum(float(p.get('pnl', 0)) for p in closed_positions)
                winning = sum(1 for p in closed_positions if float(p.get('pnl', 0)) > 0)
                losing = sum(1 for p in closed_positions if float(p.get('pnl', 0)) < 0)
                win_rate = (winning / len(closed_positions) * 100) if closed_positions else 0
                
                summary = {
                    "total_trades": len(closed_positions),
                    "total_pnl": f"{total_pnl:.2f}",
                    "winning_trades": winning,
                    "losing_trades": losing,
                    "win_rate": f"{win_rate:.2f}"
                }
                
                self._emit_trade_update(trade, summary)
            
            self.last_trades_count = current_trade_count
    
    def run(self) -> BacktestResults:
        """
        Override run to emit backtest_complete event at end.
        """
        logger.info(f"\n[SSE] Starting backtest with session_id: {self.session_id}")
        
        # Emit initial state
        self._emit_initial_state()
        
        # Run parent backtest
        result = super().run()
        
        # Emit final state
        self._emit_backtest_complete()
        
        logger.info(f"[SSE] Backtest complete, emitted {self.emitter.get_current_event_id()} events")
        
        return result


if __name__ == "__main__":
    print("This is a library module. Use run_backtest_with_sse.py to run backtests with SSE.")
