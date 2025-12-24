"""
EventEmitter Module
Engine: Emits events to separate JSONL files per event type per session

Input: Events from StrategyExecutor
Output: Separate JSONL files (nodes.jsonl, trades.jsonl, ticks.jsonl, positions.jsonl)
"""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import json

from src.utils.logger import log_info, log_error, log_debug


class EventEmitter:
    """
    Emits events to separate JSONL files per event type for each session
    
    Event Types:
    - initialization: Strategy initialization (events.jsonl)
    - node_completion: Node execution completed (nodes.jsonl)
    - trade: Position opened/closed (trades.jsonl)
    - tick: Per-tick snapshot of active nodes (ticks.jsonl)
    - position: GPS snapshot per tick (positions.jsonl)
    - finalization: Strategy execution completed (events.jsonl)
    
    Snapshot IDs:
    - Each event type has independent snapshot_id counter
    - Used for client synchronization
    
    Engine Contract:
    - Input: session_id (str), event_type (str), event (Dict)
    - Output: None
    - Side Effects: Appends to event-type-specific JSONL file
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        
        # Track session directories
        self.session_dirs: Dict[str, Path] = {}
        
        # Track snapshot IDs per session per event type
        # Structure: {session_id: {event_type: snapshot_id}}
        self.snapshot_counters: Dict[str, Dict[str, int]] = {}
        
        # Event type to file mapping
        self.event_files = {
            "initialization": "events.jsonl",
            "finalization": "events.jsonl",
            "node_completion": "nodes.jsonl",
            "node_diagnostics": "node_diagnostics.jsonl",
            "trade": "trades.jsonl",
            "tick": "ticks.jsonl",
            "position": "positions.jsonl",
            "candle_completion": "candles.jsonl",
            "ltp_update": "ltp.jsonl"
        }
        
        # Statistics
        self.events_emitted = 0
    
    def register_session(self, session_id: str, user_id: str):
        """
        Register a session and create its directory
        
        Input: session_id, user_id
        Output: None (creates directory)
        """
        session_dir = self.base_dir / user_id / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_dirs[session_id] = session_dir
        
        # Initialize snapshot counters for all event types
        self.snapshot_counters[session_id] = {
            "node_completion": 0,
            "node_diagnostics": 0,
            "trade": 0,
            "tick": 0,
            "position": 0,
            "candle_completion": 0,
            "ltp_update": 0
        }
        
        log_info(f"[EventEmitter] Registered session: {session_id}")
    
    def _get_next_snapshot_id(self, session_id: str, event_type: str) -> int:
        """Get next snapshot ID for event type"""
        if session_id not in self.snapshot_counters:
            return 0
        
        if event_type not in self.snapshot_counters[session_id]:
            self.snapshot_counters[session_id][event_type] = 0
        
        self.snapshot_counters[session_id][event_type] += 1
        return self.snapshot_counters[session_id][event_type]
    
    def _get_latest_snapshot_ids(self, session_id: str) -> Dict[str, int]:
        """Get latest snapshot IDs for all event types"""
        if session_id not in self.snapshot_counters:
            return {
                "node": 0,
                "node_diagnostics": 0,
                "trade": 0,
                "position": 0,
                "candle": 0,
                "ltp": 0
            }
        
        return {
            "node": self.snapshot_counters[session_id].get("node_completion", 0),
            "node_diagnostics": self.snapshot_counters[session_id].get("node_diagnostics", 0),
            "trade": self.snapshot_counters[session_id].get("trade", 0),
            "position": self.snapshot_counters[session_id].get("position", 0),
            "candle": self.snapshot_counters[session_id].get("candle_completion", 0),
            "ltp": self.snapshot_counters[session_id].get("ltp_update", 0)
        }
    
    def emit_event(self, session_id: str, event_type: str, event_data: Dict[str, Any]):
        """
        Emit an event to appropriate JSONL file with snapshot ID
        
        Input: session_id, event_type, event_data
        Output: None
        
        Engine Contract:
        - Input: session_id (str), event_type (str), event_data (Dict)
        - Output: None
        - Side Effects: Appends to event-type-specific JSONL file with snapshot_id
        """
        if session_id not in self.session_dirs:
            log_error(f"[EventEmitter] Session {session_id} not registered")
            return
        
        try:
            # Get snapshot ID if applicable
            snapshot_id = None
            if event_type in ["node_completion", "node_diagnostics", "trade", "tick", "position", "candle_completion", "ltp_update"]:
                snapshot_id = self._get_next_snapshot_id(session_id, event_type)
            
            # Build event
            event = {
                "event_type": event_type,
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
                **event_data
            }
            
            # Add snapshot_id if applicable
            if snapshot_id is not None:
                event["snapshot_id"] = snapshot_id
            
            # For tick events, add latest snapshot IDs for synchronization
            if event_type == "tick":
                event["latest_snapshot_ids"] = self._get_latest_snapshot_ids(session_id)
            
            # Get file path
            filename = self.event_files.get(event_type, "events.jsonl")
            file_path = self.session_dirs[session_id] / filename
            
            # Write to JSONL
            with open(file_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            self.events_emitted += 1
            
        except Exception as e:
            log_error(f"[EventEmitter] Error emitting event: {e}")
    
    def emit_initialization(self, session_id: str, strategy_config: Dict[str, Any]):
        """Emit initialization event"""
        event_data = {
            "session_id": session_id,
            "strategy_id": strategy_config.get("id"),
            "strategy_name": strategy_config.get("name"),
            "symbol": strategy_config.get("symbol"),
            "timeframe": strategy_config.get("timeframe")
        }
        self.emit_event(session_id, "initialization", event_data)
    
    def emit_node_completion(self, session_id: str, node_data: Dict[str, Any]):
        """Emit node completion event to nodes.jsonl"""
        self.emit_event(session_id, "node_completion", node_data)
    
    def emit_node_diagnostics(self, session_id: str, diagnostics_data: Dict[str, Any]):
        """Emit node diagnostics event to node_diagnostics.jsonl"""
        self.emit_event(session_id, "node_diagnostics", diagnostics_data)
    
    def emit_trade_event(self, session_id: str, trade_data: Dict[str, Any]):
        """Emit trade event to trades.jsonl"""
        self.emit_event(session_id, "trade", trade_data)
    
    def emit_tick_event(self, session_id: str, tick_data: Dict[str, Any]):
        """Emit tick event to ticks.jsonl with latest snapshot IDs"""
        self.emit_event(session_id, "tick", tick_data)
    
    def emit_position_event(self, session_id: str, position_data: Dict[str, Any]):
        """Emit position snapshot event to positions.jsonl"""
        self.emit_event(session_id, "position", position_data)
    
    def emit_candle_completion(self, session_id: str, candle_data: Dict[str, Any]):
        """Emit candle completion snapshot to candles.jsonl"""
        self.emit_event(session_id, "candle_completion", candle_data)
    
    def emit_ltp_update(self, session_id: str, ltp_data: Dict[str, Any]):
        """Emit LTP update snapshot to ltp.jsonl"""
        self.emit_event(session_id, "ltp_update", ltp_data)
    
    def emit_finalization(self, session_id: str, summary: Dict[str, Any]):
        """Emit finalization event"""
        event_data = {
            "session_id": session_id,
            "summary": summary
        }
        self.emit_event(session_id, "finalization", event_data)
    
    def get_statistics(self) -> Dict[str, int]:
        """Get emission statistics"""
        return {
            "events_emitted": self.events_emitted,
            "sessions_registered": len(self.session_dirs)
        }
