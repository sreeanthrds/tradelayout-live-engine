"""
Live Session Manager - Dictionary-based session storage for multi-strategy execution.

Manages concurrent live simulation sessions with SSE streaming.
No queue complexity - direct dictionary access for add/update/delete.
"""

import threading
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from live_simulation_sse import sse_manager, SSESession
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from src.utils.logger import log_info, log_error, log_warning


class LiveSessionManager:
    """
    Manages multiple concurrent live simulation sessions.
    Dictionary-based storage - no queue complexity.
    """
    
    def __init__(self):
        """Initialize session manager with thread-safe dict."""
        self.sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session_data
        self._lock = threading.Lock()
        log_info("📡 Live Session Manager initialized")
    
    def create_session(
        self,
        user_id: str,
        strategy_id: str,
        broker_connection_id: str,
        broker_metadata: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new live simulation session.
        
        Args:
            user_id: User ID (for filtering)
            strategy_id: Strategy to execute
            broker_connection_id: Broker connection ID
            broker_metadata: Broker-specific config (date, scale, etc.)
            session_id: Optional session ID (auto-generated if not provided)
        
        Returns:
            Session metadata dict
        """
        with self._lock:
            # Generate session ID if not provided
            if not session_id:
                session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Check if session already exists
            if session_id in self.sessions:
                log_warning(f"Session {session_id} already exists, returning existing")
                return self.sessions[session_id]['metadata']
            
            # Create SSE session
            sse_session = sse_manager.create_session(session_id)
            
            # Parse broker metadata
            backtest_date = broker_metadata.get('date')  # For ClickHouse backtesting
            scale = broker_metadata.get('scale', 1.0)
            
            # Create backtest config
            config = BacktestConfig(
                strategy_ids=[strategy_id],
                backtest_date=datetime.strptime(backtest_date, '%Y-%m-%d') if isinstance(backtest_date, str) else backtest_date,
                strategy_scale=scale
            )
            
            # Store session metadata (engine will be created in separate thread)
            session_data = {
                'metadata': {
                    'session_id': session_id,
                    'user_id': user_id,
                    'strategy_id': strategy_id,
                    'broker_connection_id': broker_connection_id,
                    'broker_metadata': broker_metadata,
                    'status': 'initializing',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                },
                'config': config,
                'sse_session': sse_session,
                'engine': None,  # Will be set by executor thread
                'thread': None,  # Will be set by executor thread
                'error': None
            }
            
            self.sessions[session_id] = session_data
            
            log_info(f"✅ Session created: {session_id} (user: {user_id}, strategy: {strategy_id})")
            return session_data['metadata']
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dict or None
        """
        return self.sessions.get(session_id)
    
    def update_session_status(self, session_id: str, status: str, error: Optional[str] = None):
        """
        Update session status.
        
        Args:
            session_id: Session identifier
            status: New status (initializing, running, paused, stopped, error)
            error: Optional error message
        """
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]['metadata']['status'] = status
                self.sessions[session_id]['metadata']['updated_at'] = datetime.now().isoformat()
                if error:
                    self.sessions[session_id]['error'] = error
                    self.sessions[session_id]['metadata']['error'] = error
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove session and cleanup resources.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if session_id not in self.sessions:
                log_warning(f"Session {session_id} not found for removal")
                return False
            
            session_data = self.sessions[session_id]
            
            # Stop engine if running
            if session_data.get('engine'):
                try:
                    # Engine cleanup handled by thread termination
                    pass
                except Exception as e:
                    log_error(f"Error stopping engine for {session_id}: {e}")
            
            # Remove SSE session
            sse_manager.remove_session(session_id)
            
            # Remove from storage
            del self.sessions[session_id]
            
            log_info(f"🗑️ Session removed: {session_id}")
            return True
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all sessions, optionally filtered by user.
        
        Args:
            user_id: Optional user ID filter
        
        Returns:
            List of session metadata dicts
        """
        with self._lock:
            sessions = []
            for session_id, session_data in self.sessions.items():
                metadata = session_data['metadata']
                
                # Filter by user if specified
                if user_id and metadata.get('user_id') != user_id:
                    continue
                
                sessions.append(metadata)
            
            return sessions
    
    def get_session_count(self, user_id: Optional[str] = None) -> int:
        """
        Get count of active sessions, optionally filtered by user.
        
        Args:
            user_id: Optional user ID filter
        
        Returns:
            Session count
        """
        return len(self.list_sessions(user_id))


# Global singleton instance
live_session_manager = LiveSessionManager()
