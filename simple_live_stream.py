"""
Simple Live Streaming - Clone of Backtesting Pattern
Sends accumulated + delta data every second via SSE
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any


class SimpleLiveSession:
    """Maintains accumulated and delta data for a live session"""
    
    def __init__(self, session_id: str, user_id: str, strategy_id: str, speed_multiplier: float = 1.0):
        self.session_id = session_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.status = "initializing"
        self.speed_multiplier = speed_multiplier
        
        # Calculate SSE update interval based on speed
        # At 1x: 1 second, At 500x: 0.1 second (10 updates/sec)
        self.update_interval = max(0.05, min(1.0, 1.0 / max(1, speed_multiplier / 10)))
        
        # Accumulated data (grows over time)
        self.accumulated_trades: List[Dict] = []
        self.accumulated_events: Dict[str, Dict] = {}
        self.accumulated_summary = {
            "total_trades": 0,
            "total_pnl": "0.00",
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": "0.0"
        }
        
        # Delta data (resets every second)
        self.delta_trades: List[Dict] = []
        self.delta_events: Dict[str, Dict] = {}
        
        # Metadata
        self.current_tick = 0
        self.total_ticks = 0
        self.progress = 0.0
        self.current_time = None  # Current backtest data time
        self.last_update = datetime.now()
    
    def add_trade(self, trade: Dict):
        """Add or update a trade (upsert pattern to prevent duplicates)"""
        trade_id = trade.get('trade_id')
        
        # Find existing trade by trade_id
        existing_idx = None
        for idx, existing_trade in enumerate(self.accumulated_trades):
            if existing_trade.get('trade_id') == trade_id:
                existing_idx = idx
                break
        
        # Upsert: Update if exists, append if new
        if existing_idx is not None:
            self.accumulated_trades[existing_idx] = trade
        else:
            self.accumulated_trades.append(trade)
        
        # Always add to delta (for this second's update)
        self.delta_trades.append(trade)
        self._update_summary()
    
    def add_events(self, events: Dict[str, Dict]):
        """Add new events (goes to both accumulated and delta)"""
        self.accumulated_events.update(events)
        self.delta_events.update(events)
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get data for this second (accumulated + delta)"""
        from datetime import datetime as dt
        data = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "strategy_id": self.strategy_id,
            "status": self.status,
            "timestamp": dt.now().isoformat(),
            "current_time": self.current_time,  # Current backtest data time
            
            # Accumulated data (all trades/events so far)
            "accumulated": {
                "trades": self.accumulated_trades,
                "events_history": self.accumulated_events,
                "summary": self.accumulated_summary
            },
            
            # Delta data (only new trades/events this second)
            "delta": {
                "trades": self.delta_trades,
                "events": self.delta_events
            },
            
            # Progress
            "progress": {
                "current_tick": self.current_tick,
                "total_ticks": self.total_ticks,
                "percentage": self.progress
            }
        }
        
        # Clear delta for next second
        self.delta_trades = []
        self.delta_events = {}
        
        return data
    
    def _update_summary(self):
        """Update summary from accumulated trades"""
        if not self.accumulated_trades:
            return
        
        total_pnl = sum(float(t.get('pnl', 0)) for t in self.accumulated_trades)
        winning = sum(1 for t in self.accumulated_trades if float(t.get('pnl', 0)) > 0)
        losing = sum(1 for t in self.accumulated_trades if float(t.get('pnl', 0)) <= 0)
        
        self.accumulated_summary = {
            "total_trades": len(self.accumulated_trades),
            "total_pnl": f"{total_pnl:.2f}",
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate": f"{(winning / len(self.accumulated_trades) * 100):.1f}" if self.accumulated_trades else "0.0"
        }
    
    def update_progress(self, current_tick: int, total_ticks: int):
        """Update progress information"""
        self.current_tick = current_tick
        self.total_ticks = total_ticks
        self.progress = (current_tick / total_ticks * 100) if total_ticks > 0 else 0.0


class SimpleLiveStreamManager:
    """Manages all live sessions and their streaming"""
    
    def __init__(self):
        self.sessions: Dict[str, SimpleLiveSession] = {}
        self.session_timeouts: Dict[str, datetime] = {}  # Track last activity per session
        self.max_session_age_minutes = 60  # Auto-cleanup sessions older than 60 minutes
    
    def create_session(self, session_id: str, user_id: str, strategy_id: str, speed_multiplier: float = 1.0) -> SimpleLiveSession:
        """Create or replace live session (deterministic session IDs)"""
        # Check if session already exists
        if session_id in self.sessions:
            print(f"[SimpleStream] ♻️  Replacing existing session {session_id} (same strategy restarted)")
        
        session = SimpleLiveSession(session_id, user_id, strategy_id, speed_multiplier)
        self.sessions[session_id] = session
        self.session_timeouts[session_id] = datetime.now()
        print(f"[SimpleStream] Created session {session_id} for user {user_id} (speed: {speed_multiplier}x, update interval: {session.update_interval:.3f}s)")
        print(f"[SimpleStream] Total sessions: {len(self.sessions)}")
        return session
    
    def get_session(self, session_id: str) -> SimpleLiveSession:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_user_sessions(self, user_id: str) -> List[SimpleLiveSession]:
        """Get all sessions for a user"""
        return [s for s in self.sessions.values() if s.user_id == user_id]
    
    async def stream_session(self, session_id: str):
        """Stream accumulated + delta data every second for a session"""
        from datetime import datetime, date
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                return super().default(obj)
        
        session = self.get_session(session_id)
        if not session:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Session not found"})
            }
            return
        
        print(f"[SimpleStream] Starting stream for session {session_id}")
        
        try:
            while session.status in ["initializing", "running"]:
                # Get current data (accumulated + delta)
                data = session.get_current_data()
                
                # Send as SSE event with custom encoder
                yield {
                    "event": "data",
                    "data": json.dumps(data, cls=DateTimeEncoder)
                }
                
                # Wait based on speed multiplier (faster at higher speeds)
                await asyncio.sleep(session.update_interval)
            
            # When completed, keep connection alive and send final data periodically
            if session.status == "completed":
                print(f"[SimpleStream] Session {session_id} completed - keeping connection alive")
                
                while True:  # Keep connection alive for UI
                    final_data = session.get_current_data()
                    final_data["status"] = "completed"
                    yield {
                        "event": "completed",
                        "data": json.dumps(final_data, cls=DateTimeEncoder)
                    }
                    # Send final data every 5 seconds to keep connection alive
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            print(f"[SimpleStream] Client disconnected from {session_id}")
            raise
        except Exception as e:
            print(f"[SimpleStream] Error streaming {session_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    async def stream_user(self, user_id: str):
        """Stream all sessions for a user (aggregated)"""
        print(f"[SimpleStream] Starting user stream for {user_id}")
        
        try:
            while True:
                user_sessions = self.get_user_sessions(user_id)
                
                if not user_sessions:
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "No active sessions for user"})
                    }
                    await asyncio.sleep(5)
                    continue
                
                # Aggregate data from all user sessions
                for session in user_sessions:
                    data = session.get_current_data()
                    yield {
                        "event": "data",
                        "data": json.dumps(data)
                    }
                
                # Wait 1 second
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            print(f"[SimpleStream] User {user_id} disconnected")
            raise
        except Exception as e:
            print(f"[SimpleStream] Error streaming user {user_id}: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    def remove_session(self, session_id: str):
        """Remove a completed session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if session_id in self.session_timeouts:
                del self.session_timeouts[session_id]
            print(f"[SimpleStream] Removed session {session_id}")
            print(f"[SimpleStream] Remaining sessions: {len(self.sessions)}")
    
    def cleanup_stale_sessions(self, max_age_minutes: int = None) -> int:
        """Remove sessions older than max_age_minutes. Returns count of removed sessions."""
        if max_age_minutes is None:
            max_age_minutes = self.max_session_age_minutes
        
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        stale_sessions = []
        
        for session_id, last_activity in self.session_timeouts.items():
            if last_activity < cutoff_time:
                stale_sessions.append(session_id)
        
        for session_id in stale_sessions:
            self.remove_session(session_id)
        
        if stale_sessions:
            print(f"[SimpleStream] ⚠️  Cleaned up {len(stale_sessions)} stale sessions (older than {max_age_minutes} min)")
        
        return len(stale_sessions)
    
    def cleanup_all_sessions(self) -> int:
        """Remove ALL sessions (use on startup). Returns count of removed sessions."""
        count = len(self.sessions)
        self.sessions.clear()
        self.session_timeouts.clear()
        if count > 0:
            print(f"[SimpleStream] 🧹 Cleaned up ALL {count} sessions")
        return count
    
    def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session"""
        if session_id in self.session_timeouts:
            self.session_timeouts[session_id] = datetime.now()


# Global instance
simple_stream_manager = SimpleLiveStreamManager()
