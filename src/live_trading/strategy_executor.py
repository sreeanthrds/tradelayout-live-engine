"""
StrategyExecutor Module
Engine: Executes strategy nodes and emits events

Input: Tick batch (unified format)
Output: Node events, Trade events, Tick events
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine, BacktestConfig
from src.utils.logger import log_info, log_error, log_debug


class StrategyExecutor:
    """
    Executes a single strategy's logic for each tick batch
    
    Responsibilities:
    - Process ticks through strategy nodes
    - Emit Node completion events
    - Emit Trade events
    - Emit Tick events
    
    Engine Contract:
    - Input: tick_batch (List[unified_tick])
    - Output: events (List[event_dict])
    - Side Effects: Updates strategy state, places orders
    """
    
    def __init__(self, session: Dict[str, Any], trade_date: datetime, candle_store, ltp_store, event_emitter):
        self.session = session
        self.session_id = session["session_id"]
        self.user_id = session["user_id"]
        self.strategy_id = session["strategy_id"]
        self.trade_date = trade_date
        
        # Data stores
        self.candle_store = candle_store
        self.ltp_store = ltp_store
        
        # Event emitter
        self.event_emitter = event_emitter
        
        # Backtest engine (will be initialized)
        self.engine: Optional[CentralizedBacktestEngine] = None
        self.config: Optional[BacktestConfig] = None
        
        # Strategy configuration
        self.strategy_config: Dict[str, Any] = {}
        
        # Statistics
        self.ticks_processed = 0
        self.nodes_executed = 0
        self.trades_completed = 0
        
        log_info(f"[StrategyExecutor:{self.session_id}] Initialized")
    
    def initialize(self, strategy_config: Dict[str, Any]):
        """
        Initialize strategy executor with configuration
        
        Input: strategy_config - Strategy configuration from metadata scanner
        Output: None
        
        Engine Contract:
        - Input: strategy_config (Dict)
        - Output: None
        - Side Effects: Initializes backtest engine
        """
        self.strategy_config = strategy_config
        
        # Create backtest config
        self.config = BacktestConfig(
            strategy_ids=[self.strategy_id],  # Must be a list
            backtest_date=self.trade_date,
            strategy_scale=1.0
        )
        
        # Create backtest engine
        # Note: We don't pass DataManager here since data comes from shared stores
        self.engine = self._create_engine()
        
        # Emit initialization event
        self.event_emitter.emit_initialization(self.session_id, self.strategy_config)
        
        log_info(f"[StrategyExecutor:{self.session_id}] Initialized with strategy {self.strategy_id}")
    
    def _create_engine(self) -> CentralizedBacktestEngine:
        """Create backtest engine instance"""
        # For now, we'll need to create a minimal data manager wrapper
        # that provides data from our shared stores
        from src.backtesting.data_manager import DataManager
        
        # Create a wrapper data manager that uses our stores
        data_manager = self._create_data_manager_wrapper()
        
        return CentralizedBacktestEngine(self.config, data_manager)
    
    def _create_data_manager_wrapper(self):
        """
        Create a DataManager wrapper that uses shared CandleStore and LTPStore
        
        This allows the existing CentralizedBacktestEngine to work with our modular stores
        """
        from src.backtesting.data_manager import DataManager
        from src.backtesting.dict_cache import DictCache
        
        # Create minimal data manager with proper signature
        data_manager = DataManager(
            cache=DictCache(),  # Dummy cache, we'll override stores
            broker_name="clickhouse",
            shared_cache=None
        )
        
        # Override its stores with our shared stores
        # This is a bridge between old architecture and new modular one
        data_manager.candle_store = self.candle_store
        data_manager.ltp_store = self.ltp_store
        
        return data_manager
    
    def process_tick_batch(self, tick_batch: List[Dict[str, Any]], completed_candles: List[Dict[str, Any]] = None, ltp_snapshot: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """
        Process tick batch through strategy
        
        Input: 
        - tick_batch - List of unified ticks
        - completed_candles - List of completed candles from CandleBuilder
        - ltp_snapshot - Current LTP snapshot for all symbols
        Output: events - List of emitted events
        
        Engine Contract:
        - Input: tick_batch (List[unified_tick]), completed_candles, ltp_snapshot
        - Output: events (List[event_dict])
        - Side Effects: Executes nodes, updates positions, emits events
        """
        events = []
        
        if not self.engine:
            log_error(f"[StrategyExecutor:{self.session_id}] Engine not initialized")
            return events
        
        try:
            # Emit completed candles for this strategy's symbols
            if completed_candles:
                self._emit_completed_candles(completed_candles)
            
            # Emit LTP snapshot for this strategy's symbols
            if ltp_snapshot:
                self._emit_ltp_snapshot(ltp_snapshot)
            
            for tick in tick_batch:
                # Process tick through engine
                tick_events = self._process_single_tick(tick)
                events.extend(tick_events)
                self.ticks_processed += 1
            
            log_debug(f"[StrategyExecutor:{self.session_id}] Processed batch: {len(tick_batch)} ticks, {len(events)} events")
        
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error processing tick batch: {e}")
        
        return events
    
    def _process_single_tick(self, tick: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a single tick through strategy
        
        Returns: List of events generated by this tick
        """
        events = []
        
        try:
            # Process tick through engine
            self.engine.process_tick(tick)
            
            # Extract events from engine diagnostics (nodes, trades)
            tick_events = self._extract_events_from_engine()
            
            # Emit node and trade events
            for event in tick_events:
                event_type = event.get("event_type")
                if event_type == "node_completion":
                    self.event_emitter.emit_node_completion(self.session_id, event)
                elif event_type == "trade":
                    self.event_emitter.emit_trade_event(self.session_id, event)
                events.append(event)
            
            # Emit node diagnostics for all active nodes (even if not completed)
            node_diagnostics = self._create_node_diagnostics(tick)
            self.event_emitter.emit_node_diagnostics(self.session_id, node_diagnostics)
            events.append(node_diagnostics)
            
            # Emit position snapshot (GPS snapshot)
            position_snapshot = self._create_position_snapshot(tick)
            self.event_emitter.emit_position_event(self.session_id, position_snapshot)
            events.append(position_snapshot)
            
            # Emit tick event (lean - only snapshot IDs and essential data)
            tick_event = self._create_tick_event(tick)
            self.event_emitter.emit_tick_event(self.session_id, tick_event)
            events.append(tick_event)
            
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error processing tick: {e}")
        
        return events
    
    def _extract_events_from_engine(self) -> List[Dict[str, Any]]:
        """
        Extract events from engine diagnostics
        
        Returns: List of events (Node events, Trade events)
        """
        events = []
        
        try:
            # Get latest execution nodes from engine diagnostics
            diagnostics = self.engine.get_diagnostics_export()
            events_history = diagnostics.get("events_history", {})
            
            # Find new events since last extraction
            # For now, return all events (in production, track processed events)
            for execution_id, execution_node in events_history.items():
                # Node completion event
                if execution_node.get("event_type") in ["node_completed", "action_taken"]:
                    node_event = self._create_node_event(execution_node)
                    events.append(node_event)
                    self.nodes_executed += 1
                
                # Trade event (position closed)
                if execution_node.get("event_type") == "position_closed":
                    trade_event = self._create_trade_event(execution_node)
                    events.append(trade_event)
                    self.trades_completed += 1
            
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error extracting events: {e}")
        
        return events
    
    def _create_node_event(self, execution_node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Node completion event
        
        Event structure:
        {
            "event_type": "node_completion",
            "node_id": "...",
            "node_type": "...",
            "timestamp": "...",
            "result": {...}
        }
        """
        return {
            "event_type": "node_completion",
            "node_id": execution_node.get("node_id"),
            "node_type": execution_node.get("node_type"),
            "node_name": execution_node.get("node_name"),
            "timestamp": execution_node.get("timestamp"),
            "result": {
                "action": execution_node.get("action"),
                "position": execution_node.get("position"),
                "exit_result": execution_node.get("exit_result")
            }
        }
    
    def _create_trade_event(self, execution_node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Trade event
        
        Event structure:
        {
            "event_type": "trade",
            "position_id": "...",
            "entry": {...},
            "exit": {...},
            "pnl": ...,
            "timestamp": "..."
        }
        """
        position = execution_node.get("position", {})
        exit_result = execution_node.get("exit_result", {})
        
        return {
            "event_type": "trade",
            "position_id": position.get("position_id"),
            "re_entry_num": position.get("re_entry_num", 0),
            "symbol": position.get("symbol"),
            "side": position.get("side"),
            "entry": {
                "price": position.get("entry_price"),
                "time": position.get("entry_time"),
                "quantity": position.get("actual_quantity")
            },
            "exit": {
                "price": exit_result.get("exit_price"),
                "time": exit_result.get("exit_time"),
                "reason": execution_node.get("exit_reason")
            },
            "pnl": exit_result.get("pnl"),
            "timestamp": execution_node.get("timestamp")
        }
    
    def _create_node_diagnostics(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Node diagnostics event for all active nodes
        
        Event structure:
        {
            "event_type": "node_diagnostics",
            "timestamp": "...",
            "nodes": [
                {
                    "node_id": "entry-1",
                    "node_type": "EntryNode",
                    "status": "ACTIVE",
                    "evaluation_data": {...}
                },
                ...
            ]
        }
        """
        try:
            nodes_data = []
            
            if self.engine and hasattr(self.engine, 'tick_processor'):
                context = self.engine.tick_processor.context
                node_states = context.get('node_states', {})
                
                # Get diagnostics for all active nodes
                for node_id, state in node_states.items():
                    status = state.get('status')
                    
                    # Include only ACTIVE nodes (or nodes that executed logic this tick)
                    if status == 'ACTIVE':
                        node_data = {
                            "node_id": node_id,
                            "node_type": state.get('node_type', 'Unknown'),
                            "status": status,
                            "evaluation_data": state.get('evaluation_data', {})
                        }
                        nodes_data.append(node_data)
            
            return {
                "event_type": "node_diagnostics",
                "timestamp": tick.get("timestamp"),
                "nodes": nodes_data,
                "active_count": len(nodes_data)
            }
            
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error creating node diagnostics: {e}")
            return {
                "event_type": "node_diagnostics",
                "timestamp": tick.get("timestamp"),
                "nodes": [],
                "active_count": 0
            }
    
    def _create_position_snapshot(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Position snapshot event (full GPS state)
        
        Event structure:
        {
            "event_type": "position",
            "timestamp": "...",
            "positions": {
                "open": [...],
                "closed": [...]
            },
            "summary": {
                "total_open": 5,
                "total_closed": 10,
                "unrealized_pnl": 1500.0,
                "realized_pnl": 3200.0
            }
        }
        """
        try:
            # Get all positions from GPS
            all_positions = self._get_current_positions()
            
            # Separate open and closed positions
            open_positions = []
            closed_positions = []
            
            unrealized_pnl = 0.0
            realized_pnl = 0.0
            
            for position in all_positions:
                status = position.get("status", "open")
                
                # Calculate P&L
                if status == "open":
                    # Unrealized P&L calculation
                    entry_price = position.get("entry_price", 0)
                    current_ltp = tick.get("ltp", entry_price)
                    quantity = position.get("actual_quantity", 0)
                    side = position.get("side", "BUY")
                    
                    if side == "BUY":
                        pnl = (current_ltp - entry_price) * quantity
                    else:
                        pnl = (entry_price - current_ltp) * quantity
                    
                    position["unrealized_pnl"] = pnl
                    unrealized_pnl += pnl
                    open_positions.append(position)
                else:
                    # Realized P&L
                    pnl = position.get("pnl", 0)
                    realized_pnl += pnl
                    closed_positions.append(position)
            
            return {
                "event_type": "position",
                "timestamp": tick.get("timestamp"),
                "positions": {
                    "open": open_positions,
                    "closed": closed_positions
                },
                "summary": {
                    "total_open": len(open_positions),
                    "total_closed": len(closed_positions),
                    "unrealized_pnl": unrealized_pnl,
                    "realized_pnl": realized_pnl,
                    "total_pnl": unrealized_pnl + realized_pnl
                }
            }
            
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error creating position snapshot: {e}")
            return {
                "event_type": "position",
                "timestamp": tick.get("timestamp"),
                "positions": {"open": [], "closed": []},
                "summary": {"total_open": 0, "total_closed": 0, "unrealized_pnl": 0.0, "realized_pnl": 0.0, "total_pnl": 0.0}
            }
    
    def _create_tick_event(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create Tick event (LEAN - only snapshot IDs and essential data)
        
        Event structure:
        {
            "event_type": "tick",
            "timestamp": "...",
            "latest_snapshot_ids": {
                "node": 15,
                "node_diagnostics": 4433,
                "trade": 10,
                "position": 4432,
                "candle": 42,
                "ltp": 4433
            }
        }
        
        Note: 
        - latest_snapshot_ids automatically added by EventEmitter
        - Full LTP store snapshot in ltp.jsonl (use ltp snapshot_id to fetch)
        - Node diagnostics in node_diagnostics.jsonl (use node_diagnostics snapshot_id to fetch)
        - Position details in positions.jsonl (use position snapshot_id to fetch)
        """
        # Lean tick event - only timestamp and snapshot IDs
        # All details available in respective event files
        return {
            "event_type": "tick",
            "timestamp": tick.get("timestamp")
        }
    
    def _get_active_nodes(self) -> List[str]:
        """Get list of currently active node IDs"""
        try:
            if self.engine and hasattr(self.engine, 'tick_processor'):
                context = self.engine.tick_processor.context
                
                # Get node states
                node_states = context.get('node_states', {})
                
                # Find active nodes
                active = [node_id for node_id, state in node_states.items() 
                         if state.get('status') == 'ACTIVE']
                
                return active
        except:
            pass
        
        return []
    
    def _get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from GPS"""
        try:
            if self.engine and hasattr(self.engine, 'tick_processor'):
                context_manager = self.engine.tick_processor.context.get('context_manager')
                if context_manager:
                    gps = context_manager.get_gps()
                    return list(gps.positions.values())
        except:
            pass
        
        return []
    
    def _emit_completed_candles(self, completed_candles: List[Dict[str, Any]]):
        """
        Emit completed candles for this session's symbols
        
        Input: completed_candles from CandleBuilder
        Output: None (emits candle_completion events for matching symbols)
        """
        try:
            # Get this strategy's symbol
            strategy_symbol = self.session.get("strategy_config", {}).get("symbol")
            
            if not strategy_symbol:
                return
            
            # Emit candles for this strategy's symbol
            for completed in completed_candles:
                candle_symbol = completed.get("symbol")
                
                # Check if this candle is for this strategy's symbol
                if candle_symbol == strategy_symbol:
                    candle_data = {
                        "symbol": completed.get("symbol"),
                        "timeframe": completed.get("timeframe"),
                        "candle": completed.get("candle")
                    }
                    
                    self.event_emitter.emit_candle_completion(self.session_id, candle_data)
                    
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error emitting completed candles: {e}")
    
    def _emit_ltp_snapshot(self, ltp_snapshot: Dict[str, float]):
        """
        Emit full LTP store snapshot (all symbols)
        
        Input: ltp_snapshot - Dict of {symbol: ltp} for ALL symbols
        Output: None (emits ltp_update event with full LTP store)
        """
        try:
            if ltp_snapshot:
                ltp_data = {
                    "symbols": ltp_snapshot
                }
                
                self.event_emitter.emit_ltp_update(self.session_id, ltp_data)
                    
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error emitting LTP snapshot: {e}")
    
    def finalize(self) -> Dict[str, Any]:
        """
        Finalize execution and return results
        
        Input: None
        Output: {success: bool, summary: Dict, diagnostics: Dict}
        
        Engine Contract:
        - Input: None
        - Output: results (Dict)
        - Side Effects: Emits finalization event
        """
        if not self.engine:
            return {"success": False, "error": "Engine not initialized"}
        
        try:
            # Get final results
            diagnostics = self.engine.get_diagnostics_export()
            dashboard_data = self.engine.get_dashboard_data()
            summary = dashboard_data.get("summary", {})
            
            # Emit finalization event
            self.event_emitter.emit_finalization(self.session_id, summary)
            
            log_info(f"[StrategyExecutor:{self.session_id}] Finalized: {summary.get('total_trades', 0)} trades")
            
            return {
                "success": True,
                "session_id": self.session_id,
                "summary": summary,
                "diagnostics": diagnostics,
                "dashboard_data": dashboard_data,
                "statistics": self.get_statistics()
            }
            
        except Exception as e:
            log_error(f"[StrategyExecutor:{self.session_id}] Error finalizing: {e}")
            return {
                "success": False,
                "session_id": self.session_id,
                "error": str(e)
            }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get execution statistics"""
        return {
            "ticks_processed": self.ticks_processed,
            "nodes_executed": self.nodes_executed,
            "trades_completed": self.trades_completed
        }
