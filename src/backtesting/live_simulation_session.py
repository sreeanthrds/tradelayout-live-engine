"""
Live Simulation Session Manager

Manages live simulation sessions with per-second state updates.
Stores formatted state from context for UI polling.
"""

from typing import Dict, Optional, Any
from datetime import datetime
import threading
import uuid


class LiveSimulationSession:
    """
    Manages a live simulation session.
    
    Stores:
    - Session metadata (user_id, strategy_id, etc.)
    - Latest state (updated every second by executor)
    - Session status and control
    
    Thread-safe for concurrent access by executor and API.
    """
    
    # Class-level registry of active sessions
    _sessions: Dict[str, 'LiveSimulationSession'] = {}
    _lock = threading.Lock()
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        strategy_id: str,
        backtest_date: str,
        speed_multiplier: float = 1.0
    ):
        """
        Initialize simulation session.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            strategy_id: Strategy identifier
            backtest_date: Date to simulate (YYYY-MM-DD)
            speed_multiplier: Speed factor (1.0 = real-time, 10.0 = 10x faster)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.backtest_date = backtest_date
        self.speed_multiplier = speed_multiplier
        
        # Session state
        self.status = 'initializing'  # initializing, running, paused, completed, stopped, error
        self.started_at = None
        self.completed_at = None
        
        # Latest state (updated every second)
        self.latest_state = {}
        self._state_lock = threading.Lock()
        
        # Control flags
        self.should_stop = False
        self.should_pause = False
        
        # Executor reference (set when simulation starts)
        self.executor = None
        self.simulator = None
        self.execution_thread = None
    
    @classmethod
    def create_session(
        cls,
        user_id: str,
        strategy_id: str,
        backtest_date: str,
        speed_multiplier: float = 1.0
    ) -> str:
        """
        Create new simulation session and return session_id.
        
        Args:
            user_id: User identifier
            strategy_id: Strategy identifier
            backtest_date: Date to simulate
            speed_multiplier: Speed factor
            
        Returns:
            Session ID string
        """
        session_id = f"sim-{uuid.uuid4().hex[:12]}"
        
        session = cls(
            session_id=session_id,
            user_id=user_id,
            strategy_id=strategy_id,
            backtest_date=backtest_date,
            speed_multiplier=speed_multiplier
        )
        
        with cls._lock:
            cls._sessions[session_id] = session
        
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional['LiveSimulationSession']:
        """Get session by ID."""
        return cls._sessions.get(session_id)
    
    @classmethod
    def remove_session(cls, session_id: str):
        """Remove session from registry."""
        with cls._lock:
            if session_id in cls._sessions:
                del cls._sessions[session_id]
    
    @classmethod
    def list_sessions(cls) -> list:
        """List all active sessions."""
        with cls._lock:
            return list(cls._sessions.values())
    
    def update_state(self, formatted_state: Dict[str, Any]):
        """
        Update latest state (called every second by executor).
        Thread-safe.
        
        Args:
            formatted_state: State dictionary from live_state_formatter
        """
        with self._state_lock:
            self.latest_state = formatted_state
    
    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current state for API response.
        Thread-safe.
        
        Returns:
            Dictionary with session info and latest state
        """
        with self._state_lock:
            return {
                'session_id': self.session_id,
                'user_id': self.user_id,
                'strategy_id': self.strategy_id,
                'backtest_date': self.backtest_date,
                'speed_multiplier': self.speed_multiplier,
                'status': self.status,
                'started_at': self.started_at.isoformat() if self.started_at else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
                **self.latest_state  # Merge latest state
            }
    
    def start_simulation(self):
        """
        Start simulation in background thread.
        """
        self.status = 'running'
        self.started_at = datetime.now()
        
        # Start execution thread
        self.execution_thread = threading.Thread(
            target=self._run_simulation_thread,
            daemon=True
        )
        self.execution_thread.start()
    
    def _run_simulation_thread(self):
        """
        Run simulation (called in background thread).
        Uses centralized backtest engine with live state capture.
        """
        try:
            # Import here to avoid circular dependency
            from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
            from src.backtesting.backtest_config import BacktestConfig
            from datetime import datetime
            
            # Create config
            config = BacktestConfig(
                strategy_ids=[self.strategy_id],
                backtest_date=datetime.strptime(self.backtest_date, '%Y-%m-%d'),
                debug_mode=None
            )
            
            # Create engine with this session for state updates
            engine = CentralizedBacktestEngine(
                config=config,
                live_simulation_session=self  # Pass self for state updates
            )
            
            # Store engine reference
            self.simulator = engine
            
            # Run backtest (will update state every second via our hook)
            results = engine.run()
            
            # Mark complete
            self.status = 'completed'
            self.completed_at = datetime.now()
            
            # Store final results in state
            with self._state_lock:
                self.latest_state['final_results'] = {
                    'completed': True,
                    'results_available': results is not None
                }
            
        except Exception as e:
            self.status = 'error'
            self.completed_at = datetime.now()
            with self._state_lock:
                self.latest_state['error'] = str(e)
            import traceback
            print(f"Simulation error: {e}")
            print(traceback.format_exc())
    
    def pause(self):
        """Pause simulation."""
        self.should_pause = True
        self.status = 'paused'
    
    def resume(self):
        """Resume paused simulation."""
        self.should_pause = False
        self.status = 'running'
    
    def stop(self):
        """Stop simulation."""
        self.should_stop = True
        self.status = 'stopped'
        
        # Wait for thread to finish
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=5)
    
    def is_complete(self) -> bool:
        """Check if simulation should stop."""
        if self.should_stop:
            return True
        
        # Check if all nodes inactive and no open positions
        with self._state_lock:
            active_nodes = self.latest_state.get('active_nodes', [])
            open_positions = self.latest_state.get('open_positions', [])
            
            # If no active nodes and no open positions, strategy is complete
            if len(active_nodes) == 0 and len(open_positions) == 0:
                return True
        
        return False
    
    def cleanup(self):
        """Cleanup session resources."""
        self.stop()
        self.remove_session(self.session_id)
