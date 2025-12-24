"""
Live Simulation SSE Manager

Provides real-time event streaming for live simulation sessions.
Handles node events, trades, positions, LTP updates, and candle updates.
"""

from typing import Dict, Any, Optional, List
from collections import deque
import threading
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class SSESession:
    """
    Manages SSE event queues for a single live simulation session.
    Thread-safe for concurrent access.
    """
    
    def __init__(self, session_id: str, max_queue_size: int = 1000):
        """
        Initialize SSE session.
        
        Args:
            session_id: Unique session identifier
            max_queue_size: Maximum events to buffer per queue
        """
        self.session_id = session_id
        self.max_queue_size = max_queue_size
        
        # Event queues (separate for different event types)
        self.node_events = deque(maxlen=max_queue_size)  # Node execution events
        self.trade_events = deque(maxlen=max_queue_size)  # Trade open/close events
        self.position_updates = deque(maxlen=max_queue_size)  # Position P&L updates
        self.ltp_snapshots = deque(maxlen=max_queue_size)  # LTP store snapshots
        self.candle_updates = deque(maxlen=max_queue_size)  # Candle completions
        
        # Sequence counters (for client-side ordering)
        self.node_seq = 0
        self.trade_seq = 0
        self.position_seq = 0
        self.ltp_seq = 0
        self.candle_seq = 0
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Session metadata
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_node_event(self, execution_id: str, event_data: Dict[str, Any]):
        """
        Add node execution event (from NodeDiagnostics.record_event).
        
        Args:
            execution_id: Unique execution ID
            event_data: Event data from NodeDiagnostics
        """
        with self._lock:
            self.node_seq += 1
            self.node_events.append({
                'seq': self.node_seq,
                'event_type': 'node_event',
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat(),
                'data': event_data
            })
            self.last_activity = datetime.now()
            logger.debug(f"📡 SSE [{self.session_id}]: Node event #{self.node_seq} ({execution_id})")
    
    def add_trade_event(self, trade_data: Dict[str, Any]):
        """
        Add trade event (position opened/closed).
        
        Args:
            trade_data: Trade details (entry/exit)
        """
        with self._lock:
            self.trade_seq += 1
            self.trade_events.append({
                'seq': self.trade_seq,
                'event_type': 'trade_event',
                'timestamp': datetime.now().isoformat(),
                'data': trade_data
            })
            self.last_activity = datetime.now()
            logger.debug(f"📡 SSE [{self.session_id}]: Trade event #{self.trade_seq}")
    
    def add_position_update(self, position_data: Dict[str, Any]):
        """
        Add position P&L update (per-tick).
        
        Args:
            position_data: Position snapshot with current P&L
        """
        with self._lock:
            self.position_seq += 1
            self.position_updates.append({
                'seq': self.position_seq,
                'event_type': 'position_update',
                'timestamp': datetime.now().isoformat(),
                'data': position_data
            })
            self.last_activity = datetime.now()
    
    def add_ltp_snapshot(self, ltp_store: Dict[str, Any], timestamp: Any):
        """
        Add LTP store snapshot (configurable frequency).
        
        Args:
            ltp_store: Current LTP store dict
            timestamp: Tick timestamp
        """
        with self._lock:
            self.ltp_seq += 1
            self.ltp_snapshots.append({
                'seq': self.ltp_seq,
                'event_type': 'ltp_snapshot',
                'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                'data': ltp_store
            })
            self.last_activity = datetime.now()
    
    def add_candle_update(self, candle_data: Dict[str, Any]):
        """
        Add candle completion event.
        
        Args:
            candle_data: Completed candle data
        """
        with self._lock:
            self.candle_seq += 1
            self.candle_updates.append({
                'seq': self.candle_seq,
                'event_type': 'candle_update',
                'timestamp': datetime.now().isoformat(),
                'data': candle_data
            })
            self.last_activity = datetime.now()
    
    def get_events(self, event_type: str = 'all', since_seq: int = 0) -> List[Dict[str, Any]]:
        """
        Get events for SSE streaming.
        
        Args:
            event_type: Event type to fetch ('all', 'node', 'trade', 'position', 'ltp', 'candle')
            since_seq: Return events with seq > since_seq
            
        Returns:
            List of events
        """
        with self._lock:
            if event_type == 'all':
                # Combine all events, sorted by timestamp
                all_events = (
                    list(self.node_events) +
                    list(self.trade_events) +
                    list(self.position_updates) +
                    list(self.ltp_snapshots) +
                    list(self.candle_updates)
                )
                return sorted(all_events, key=lambda e: e.get('timestamp', ''))
            
            elif event_type == 'node':
                return [e for e in self.node_events if e['seq'] > since_seq]
            
            elif event_type == 'trade':
                return [e for e in self.trade_events if e['seq'] > since_seq]
            
            elif event_type == 'position':
                return [e for e in self.position_updates if e['seq'] > since_seq]
            
            elif event_type == 'ltp':
                return [e for e in self.ltp_snapshots if e['seq'] > since_seq]
            
            elif event_type == 'candle':
                return [e for e in self.candle_updates if e['seq'] > since_seq]
            
            return []
    
    def emit_trade_update(self, trade_payload: Dict[str, Any]):
        """
        Emit trade update (alias for add_trade_event for GPS compatibility).
        
        Args:
            trade_payload: Trade data
        """
        self.add_trade_event(trade_payload)


class SSEManager:
    """
    Global SSE session manager.
    Singleton pattern for managing all active SSE sessions.
    """
    
    def __init__(self):
        """Initialize SSE manager."""
        self.sessions: Dict[str, SSESession] = {}
        self._lock = threading.Lock()
        logger.info("📡 SSE Manager initialized")
    
    def create_session(self, session_id: str, max_queue_size: int = 1000) -> SSESession:
        """
        Create new SSE session.
        
        Args:
            session_id: Unique session identifier
            max_queue_size: Maximum events per queue
            
        Returns:
            SSESession instance
        """
        with self._lock:
            if session_id in self.sessions:
                logger.warning(f"SSE session {session_id} already exists, returning existing")
                return self.sessions[session_id]
            
            session = SSESession(session_id, max_queue_size)
            self.sessions[session_id] = session
            logger.info(f"✅ SSE session created: {session_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[SSESession]:
        """
        Get existing SSE session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SSESession or None if not found
        """
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """
        Remove SSE session.
        
        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"🗑️  SSE session removed: {session_id}")
    
    def list_sessions(self) -> List[str]:
        """
        List all active session IDs.
        
        Returns:
            List of session IDs
        """
        with self._lock:
            return list(self.sessions.keys())


# Global singleton instance
sse_manager = SSEManager()
