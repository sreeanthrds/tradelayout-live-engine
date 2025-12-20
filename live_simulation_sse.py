"""
Live Simulation SSE Module
Maintains in-memory diagnostics_export and trades_daily structures
Emits three event types: node_events, trade_update, tick_update
"""

import json
import gzip
import base64
import asyncio
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from collections import defaultdict


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts datetime objects to ISO format strings."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


class LiveSimulationState:
    """
    Maintains live simulation state matching backtesting JSON structures exactly.
    """
    
    def __init__(self, session_id: str, strategy_id: str, user_id: str, start_date: str):
        self.session_id = session_id
        self.strategy_id = strategy_id
        self.user_id = user_id
        self.start_date = start_date
        
        # Diagnostics (matches diagnostics_export.json exactly)
        self.diagnostics = {
            "events_history": {},  # { execution_id: event_payload }
            "current_state": {}    # { node_id: latest_state_payload }
        }
        
        # Trades (matches trades_daily.json exactly)
        self.trades = {
            "date": start_date,
            "summary": {
                "total_trades": 0,
                "total_pnl": "0.00",
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.00"
            },
            "trades": []
        }
        
        # Tick-level state
        self.tick_state = {
            "timestamp": "",
            "current_time": "",
            "progress": {
                "ticks_processed": 0,
                "total_ticks": 0,
                "progress_percentage": 0.0
            },
            "active_nodes": [],
            "pending_nodes": [],
            "completed_nodes_this_tick": [],
            "open_positions": [],
            "pnl_summary": {
                "realized_pnl": "0.00",
                "unrealized_pnl": "0.00",
                "total_pnl": "0.00",
                "closed_trades": 0,
                "open_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": "0.00"
            },
            "ltp_store": {},
            "candle_data": {}
        }
        
        # Event queues
        self.event_queue = asyncio.Queue()
        self.status = "initialized"
        self.error = None
        
        print(f"[LiveSimulationState] Initialized for session {session_id}")
        
    def add_node_event(self, execution_id: str, event_payload: Dict[str, Any]):
        """
        Add node execution event to history.
        Event payload must match exact structure from diagnostics_export.json
        Emits ONLY the single new event (not entire history).
        """
        # Add to events_history (immutable append)
        self.diagnostics["events_history"][execution_id] = event_payload
        
        # Update current_state (mutable snapshot per node_id)
        node_id = event_payload.get("node_id")
        if node_id:
            # Copy event payload and add status
            current_state_payload = event_payload.copy()
            # Status should come from the event or default to a computed value
            if "status" not in current_state_payload:
                current_state_payload["status"] = self._compute_node_status(event_payload)
            
            self.diagnostics["current_state"][node_id] = current_state_payload
            
        # Queue SINGLE event emission (not entire diagnostics)
        try:
            self.event_queue.put_nowait({
                "type": "node_events",
                "data": {execution_id: event_payload}  # Only the new event
            })
        except asyncio.QueueFull:
            pass  # Skip if queue is full
    
    def add_trade(self, trade_payload: Dict[str, Any]):
        """
        Add completed trade.
        Trade payload must match exact structure from trades_daily.json
        """
        self.trades["trades"].append(trade_payload)
        
        # Update summary
        self._update_trade_summary()
        
        # Queue trade_update emission (will be gzipped)
        asyncio.create_task(self.event_queue.put({
            "type": "trade_update",
            "data": self.trades.copy()
        }))
    
    def emit_trade_update(self, trade_payload: Dict[str, Any]):
        """
        Emit single trade update event (when position closes).
        This is called for each individual trade closure.
        
        Trade includes entry_flow_ids and exit_flow_ids.
        UI looks up events from its cached node_events (sent separately).
        """
        # Add to trades list
        self.trades["trades"].append(trade_payload)
        
        # Update summary
        self._update_trade_summary()
        
        # Emit trade with flow IDs only (UI resolves from cached events)
        try:
            self.event_queue.put_nowait({
                "type": "trade_update",
                "data": {
                    "trade": trade_payload,
                    "summary": self.trades["summary"]
                }
            })
        except asyncio.QueueFull:
            pass  # Skip if queue is full
    
    def update_tick_state(self, tick_data: Dict[str, Any]):
        """
        Update tick-level state.
        Tick data includes active_nodes, pending_nodes, positions, pnl, etc.
        
        NOTE: tick_data should already be JSON-serialized (all datetime objects converted to strings)
        by the caller (LiveBacktestEngineWithSSE._serialize_for_json)
        """
        # Update internal state for tracking
        self.tick_state.update(tick_data)
        
        # Queue tick_update emission using the INCOMING serialized data (not internal state copy)
        # This avoids any datetime serialization issues
        try:
            self.event_queue.put_nowait({
                "type": "tick_update",
                "data": tick_data  # Use incoming serialized data directly
            })
            # Debug: Log first few events
            if self.event_queue.qsize() <= 5:
                print(f"[SSE Queue] Added tick_update event (queue size: {self.event_queue.qsize()})")
        except Exception as e:
            print(f"[SSE Queue Error] Failed to queue tick_update: {e}")
            import traceback
            traceback.print_exc()
    
    def _compute_node_status(self, event_payload: Dict[str, Any]) -> str:
        """
        Compute node status from event payload.
        Returns: "active", "pending", "completed", "failed"
        """
        event_type = event_payload.get("event_type")
        node_type = event_payload.get("node_type")
        
        # Logic based on event characteristics
        if event_type == "logic_completed":
            # Check if node has ongoing work
            if node_type in ["EntrySignalNode", "ExitSignalNode"]:
                return "active"  # Signal nodes stay active
            elif node_type in ["EntryNode", "ExitNode", "SquareOffNode"]:
                return "completed"  # Action nodes complete after execution
            elif node_type == "ReEntrySignalNode":
                return "completed"  # Re-entry signals complete after emitting
            else:
                return "completed"
        
        return "active"  # Default
    
    def _update_trade_summary(self):
        """Update trades summary based on current trades list"""
        trades = self.trades["trades"]
        total_trades = len(trades)
        
        if total_trades == 0:
            return
        
        total_pnl = sum(float(t.get("pnl", "0")) for t in trades)
        winning_trades = sum(1 for t in trades if float(t.get("pnl", "0")) > 0)
        losing_trades = sum(1 for t in trades if float(t.get("pnl", "0")) < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        self.trades["summary"] = {
            "total_trades": total_trades,
            "total_pnl": f"{total_pnl:.2f}",
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": f"{win_rate:.2f}"
        }
    
    def emit_diagnostics_snapshot(self, snapshot_data: Dict[str, Any]):
        """
        Emit full diagnostics snapshot (same format as backtest output).
        
        Triggered when:
        1. Any node completes logic in current tick
        2. Client requests full diagnostics (refresh/on-demand)
        
        Args:
            snapshot_data: {
                'diagnostics': {'events_history': {...}},
                'trades': {'summary': {...}, 'trades': [...]}
            }
        """
        try:
            # Update internal state
            if 'diagnostics' in snapshot_data:
                self.diagnostics.update(snapshot_data['diagnostics'])
            
            if 'trades' in snapshot_data:
                self.trades.update(snapshot_data['trades'])
            
            # Queue diagnostics_snapshot emission (with gzip compression)
            self.event_queue.put_nowait({
                "type": "diagnostics_snapshot",
                "data": {
                    "diagnostics": self.diagnostics.copy(),
                    "trades": self.trades.copy()
                }
            })
            
            print(f"[LiveSimulation] Emitted diagnostics snapshot: {len(self.diagnostics['events_history'])} events, {len(self.trades['trades'])} trades")
        except asyncio.QueueFull:
            print(f"[LiveSimulation] Queue full, skipped diagnostics snapshot")
        except Exception as e:
            print(f"[LiveSimulation] Error emitting diagnostics snapshot: {e}")


class LiveSimulationSSEManager:
    """
    Manages active SSE sessions and event streaming.
    """
    
    def __init__(self):
        self.sessions: Dict[str, LiveSimulationState] = {}
        
    def create_session(self, session_id: str, strategy_id: str, user_id: str, start_date: str) -> LiveSimulationState:
        """Create new simulation session"""
        session = LiveSimulationState(session_id, strategy_id, user_id, start_date)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[LiveSimulationState]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    async def stream_events(self, session_id: str):
        """
        SSE event generator.
        Yields events in SSE format with proper compression.
        """
        session = self.get_session(session_id)
        if not session:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Session not found"}, cls=DateTimeEncoder)
            }
            return
        
        # Send initial state (diagnostics + trades)
        yield {
            "event": "initial_state",
            "data": json.dumps({
                "diagnostics": session.diagnostics,
                "trades": session.trades
            }, cls=DateTimeEncoder)
        }
        
        # Stream events
        try:
            while session.status in ["initialized", "running"]:
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(
                        session.event_queue.get(),
                        timeout=1.0
                    )
                    
                    event_type = event["type"]
                    event_data = event["data"]
                    
                    # Send all events as plain JSON (no compression)
                    # With incremental design, payloads are small (1-5 KB)
                    # Compression overhead not worth it
                    yield {
                        "event": event_type,
                        "data": json.dumps(event_data, cls=DateTimeEncoder)
                    }
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.now().isoformat()}, cls=DateTimeEncoder)
                    }
                    continue
            
            # Session completed - send final snapshot and close
            if session.status == "completed":
                yield {
                    "event": "session_complete",
                    "data": json.dumps({
                        "session_id": session_id,
                        "status": "completed",
                        "final_summary": {
                            "total_trades": session.trades["summary"]["total_trades"],
                            "total_pnl": session.trades["summary"]["total_pnl"],
                            "win_rate": session.trades["summary"]["win_rate"]
                        },
                        "events_count": len(session.diagnostics["events_history"]),
                        "timestamp": datetime.now().isoformat()
                    }, cls=DateTimeEncoder)
                }
                print(f"[SSE] Session {session_id} completed - closing SSE connection")
                    
        except asyncio.CancelledError:
            # Client disconnected
            print(f"[SSE] Client disconnected from session {session_id}")
            raise
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, cls=DateTimeEncoder)
            }
        finally:
            # Keep completed sessions in memory for testing/debugging
            # Sessions will be manually cleaned up or expire after 30 minutes
            if session.status == "completed":
                print(f"[SSE] Session {session_id} completed - keeping in memory for reconnection")
                # Don't remove - allow clients to connect and view completed data
                pass
    
    def _compress_json(self, data: Dict[str, Any]) -> str:
        """
        Compress JSON data with gzip and base64 encode.
        Returns base64-encoded gzip-compressed JSON string.
        """
        # Use custom encoder to handle datetime objects
        from datetime import datetime
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return super().default(obj)
        
        json_str = json.dumps(data, ensure_ascii=False, cls=DateTimeEncoder)
        json_bytes = json_str.encode('utf-8')
        compressed = gzip.compress(json_bytes, compresslevel=6)
        base64_encoded = base64.b64encode(compressed).decode('ascii')
        return base64_encoded


# Global manager instance
sse_manager = LiveSimulationSSEManager()
