"""
Live Trading API Server
Multi-strategy live trading system with broker connection management
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from supabase import create_client, Client
from sse_starlette.sse import EventSourceResponse

# Initialize FastAPI
app = FastAPI(title="Live Trading API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client - set credentials
if 'SUPABASE_URL' not in os.environ:
    os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
if 'SUPABASE_SERVICE_ROLE_KEY' not in os.environ:
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_ROLE_KEY']
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Global session registry (in-memory, shared across all users)
live_sessions: Dict[str, Dict[str, Any]] = {}

# Import SSE components
from src.live_trading.live_session_manager import live_session_manager
from live_simulation_sse import sse_manager

# Base directory for live results
LIVE_RESULTS_DIR = Path("live_results")
LIVE_RESULTS_DIR.mkdir(exist_ok=True)


# =====================================================================
# Pydantic Models
# =====================================================================

class BrokerConnection(BaseModel):
    id: str
    user_id: str
    broker_name: str
    meta_data: Dict[str, Any]


class SessionRequest(BaseModel):
    user_id: str
    strategy_id: str
    broker_connection_id: str
    enabled: bool = True


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    strategy_id: str
    broker_connection_id: str
    enabled: bool
    strategy_name: Optional[str] = None
    broker_name: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class LiveTradingStartRequest(BaseModel):
    trigger_user_id: str  # User who triggered the start


class AddToExecutionRequest(BaseModel):
    """Request to add session to execution dictionary (toggle ON)"""
    user_id: str = Field(..., description="User ID")
    strategy_id: str = Field(..., description="Strategy ID")
    broker_connection_id: str = Field(..., description="Broker connection ID")
    scale: float = Field(1.0, description="Position scale multiplier")


class RemoveFromExecutionRequest(BaseModel):
    """Request to remove session from execution dictionary (toggle OFF)"""
    session_id: str = Field(..., description="Session ID to remove")


# =====================================================================
# Helper Functions
# =====================================================================

def get_session_id(user_id: str, strategy_id: str, broker_connection_id: str) -> str:
    """Generate session ID from user, strategy and broker connection"""
    return f"{user_id}_{strategy_id}_{broker_connection_id}"


def get_session_dir(user_id: str, session_id: str) -> Path:
    """Get directory path for session results"""
    session_dir = LIVE_RESULTS_DIR / user_id / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def load_broker_connection(broker_connection_id: str) -> Optional[Dict[str, Any]]:
    """Load broker connection from Supabase"""
    try:
        result = supabase.table("broker_connections").select("*").eq("id", broker_connection_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error loading broker connection: {e}")
        return None


def load_strategy(strategy_id: str) -> Optional[Dict[str, Any]]:
    """Load strategy from Supabase"""
    try:
        result = supabase.table("strategies").select("*").eq("id", strategy_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error loading strategy: {e}")
        return None


# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "live_trading_api",
        "active_sessions": len([s for s in live_sessions.values() if s.get("enabled")])
    }


@app.get("/api/v1/live/broker-connections")
async def get_broker_connections(user_id: Optional[str] = None):
    """Get all broker connections (optionally filtered by user)"""
    try:
        query = supabase.table("broker_connections").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        
        result = query.execute()
        return {"broker_connections": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching broker connections: {str(e)}")


@app.post("/api/v1/live/session/register")
async def register_session(request: SessionRequest):
    """
    Register a new session (strategy + broker connection)
    Validates uniqueness and stores in global registry
    """
    session_id = get_session_id(request.user_id, request.strategy_id, request.broker_connection_id)
    
    # Check if session already exists
    if session_id in live_sessions:
        existing = live_sessions[session_id]
        if existing.get("enabled"):
            raise HTTPException(
                status_code=409,
                detail=f"Session already exists and is enabled. Strategy '{request.strategy_id}' with broker connection '{request.broker_connection_id}' is already in use."
            )
    
    # Load strategy and broker connection metadata
    strategy = load_strategy(request.strategy_id)
    broker_conn = load_broker_connection(request.broker_connection_id)
    
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy '{request.strategy_id}' not found")
    if not broker_conn:
        raise HTTPException(status_code=404, detail=f"Broker connection '{request.broker_connection_id}' not found")
    
    # Create session
    session_data = {
        "session_id": session_id,
        "user_id": request.user_id,
        "strategy_id": request.strategy_id,
        "broker_connection_id": request.broker_connection_id,
        "enabled": request.enabled,
        "strategy_name": strategy.get("name", "Unknown"),
        "broker_name": broker_conn.get("broker_name", "Unknown"),
        "meta_data": broker_conn.get("meta_data", {}),
        "created_at": datetime.now().isoformat()
    }
    
    live_sessions[session_id] = session_data
    
    # Create session directory
    get_session_dir(request.user_id, session_id)
    
    return {
        "success": True,
        "session": session_data
    }


@app.post("/api/v1/live/session/{session_id}/toggle")
async def toggle_session(session_id: str, enabled: bool = Body(..., embed=True)):
    """Enable or disable a session"""
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    live_sessions[session_id]["enabled"] = enabled
    
    return {
        "success": True,
        "session_id": session_id,
        "enabled": enabled
    }


@app.delete("/api/v1/live/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session from registry"""
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    # Check if session is enabled
    if live_sessions[session_id].get("enabled"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an enabled session. Disable it first."
        )
    
    del live_sessions[session_id]
    
    return {
        "success": True,
        "message": f"Session '{session_id}' deleted"
    }


@app.get("/api/v1/live/sessions")
async def get_all_sessions(user_id: Optional[str] = None, enabled_only: bool = False):
    """Get all sessions (optionally filtered by user or enabled status) - PER USER"""
    # Use LiveSessionManager for SSE-enabled sessions
    sse_sessions = live_session_manager.list_sessions(user_id)
    
    # Also include legacy sessions from in-memory dict
    legacy_sessions = list(live_sessions.values())
    
    if user_id:
        legacy_sessions = [s for s in legacy_sessions if s.get("user_id") == user_id]
    
    if enabled_only:
        legacy_sessions = [s for s in legacy_sessions if s.get("enabled")]
        sse_sessions = [s for s in sse_sessions if s.get("status") == "running"]
    
    # Combine both
    all_sessions = sse_sessions + legacy_sessions
    
    return {
        "sessions": all_sessions,
        "total": len(all_sessions)
    }


@app.post("/api/v1/live/start")
async def start_live_trading(request: LiveTradingStartRequest):
    """
    Start live trading for all enabled sessions across all users
    This will spawn the multi-strategy executor
    """
    # Get all enabled sessions
    enabled_sessions = [s for s in live_sessions.values() if s.get("enabled")]
    
    if not enabled_sessions:
        raise HTTPException(status_code=400, detail="No enabled sessions found")
    
    # Import executor (will create this file next)
    try:
        from live_strategy_executor import start_multi_strategy_execution
        
        # Start execution in background
        import asyncio
        asyncio.create_task(start_multi_strategy_execution(enabled_sessions))
        
        return {
            "success": True,
            "message": f"Live trading started for {len(enabled_sessions)} sessions",
            "sessions": [s["session_id"] for s in enabled_sessions],
            "triggered_by": request.trigger_user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting live trading: {str(e)}")


@app.get("/api/v1/live/session/{session_id}/events")
async def get_session_events(session_id: str, limit: int = 100):
    """Get recent events for a session from JSONL log"""
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    session = live_sessions[session_id]
    session_dir = get_session_dir(session["user_id"], session_id)
    events_file = session_dir / "events.jsonl"
    
    if not events_file.exists():
        return {"events": []}
    
    # Read last N events
    events = []
    with open(events_file, 'r') as f:
        lines = f.readlines()
        for line in lines[-limit:]:
            try:
                events.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    return {"events": events, "total": len(events)}


@app.get("/api/v1/live/session/{session_id}/trades")
async def get_session_trades(session_id: str):
    """Get trades for a session"""
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    session = live_sessions[session_id]
    session_dir = get_session_dir(session["user_id"], session_id)
    trades_file = session_dir / "trades_daily.json.gz"
    
    if not trades_file.exists():
        return {"trades": [], "summary": {}}
    
    import gzip
    with gzip.open(trades_file, 'rt') as f:
        data = json.load(f)
    
    return data


@app.get("/api/v1/live/session/{session_id}/diagnostics")
async def get_session_diagnostics(session_id: str):
    """Get diagnostics for a session"""
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    session = live_sessions[session_id]
    session_dir = get_session_dir(session["user_id"], session_id)
    diagnostics_file = session_dir / "diagnostics_export.json.gz"
    
    if not diagnostics_file.exists():
        return {"events_history": {}}
    
    import gzip
    with open(diagnostics_file, 'rb') as f:
        data = json.loads(gzip.decompress(f.read()).decode('utf-8'))
    
    return data


@app.post("/api/v1/live/session/add-to-execution")
async def add_session_to_execution(request: AddToExecutionRequest):
    """
    Add a session to the execution dictionary (toggle ON - Submit to Queue).
    This marks the session as ready for execution.
    
    Session ID format: {user_id}_{strategy_id}_{broker_connection_id}
    
    Request body:
    {
        "user_id": "user_123",
        "strategy_id": "d70ec04a-1025-46c5-94c4-3e6bff499644",
        "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4",
        "scale": 2.0
    }
    """
    # Generate session ID
    session_id = get_session_id(
        request.user_id,
        request.strategy_id,
        request.broker_connection_id
    )
    
    # Validate broker connection exists
    try:
        broker_conn = load_broker_connection(request.broker_connection_id)
        if not broker_conn:
            raise HTTPException(
                status_code=404,
                detail=f"Broker connection not found: {request.broker_connection_id}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading broker connection: {str(e)}"
        )
    
    # Validate strategy exists
    try:
        strategy = load_strategy(request.strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=404,
                detail=f"Strategy not found: {request.strategy_id}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading strategy: {str(e)}"
        )
    
    # Check if session already in execution
    if session_id in live_sessions:
        existing = live_sessions[session_id]
        if existing.get("in_execution"):
            return {
                "success": False,
                "message": "Session already in execution queue",
                "session_id": session_id,
                "status": existing.get("status", "unknown")
            }
    
    # Prepare broker metadata with scale
    broker_metadata = broker_conn.get("broker_metadata", {}).copy()
    broker_metadata["scale"] = request.scale
    
    # Create/update session configuration
    session_config = {
        "session_id": session_id,
        "user_id": request.user_id,
        "strategy_id": request.strategy_id,
        "broker_connection_id": request.broker_connection_id,
        "scale": request.scale,
        "strategy_name": strategy.get("name", "Unknown"),
        "broker_name": broker_conn.get("broker_name", "Unknown"),
        "broker_metadata": broker_metadata,
        "in_execution": True,
        "status": "queued",
        "added_to_execution_at": datetime.now().isoformat(),
        "created_at": live_sessions.get(session_id, {}).get("created_at", datetime.now().isoformat())
    }
    
    # Store in live_sessions dict
    live_sessions[session_id] = session_config
    
    return {
        "success": True,
        "message": "Session added to execution queue",
        "session_id": session_id,
        "status": "queued",
        "configuration": {
            "user_id": request.user_id,
            "strategy_id": request.strategy_id,
            "strategy_name": session_config["strategy_name"],
            "broker_connection_id": request.broker_connection_id,
            "broker_name": session_config["broker_name"],
            "scale": request.scale
        }
    }


@app.post("/api/v1/live/session/remove-from-execution")
async def remove_session_from_execution(request: RemoveFromExecutionRequest):
    """
    Remove a session from the execution dictionary (toggle OFF).
    This stops the session from being executed.
    
    Request body:
    {
        "session_id": "user_123_strategy_456_broker_789"
    }
    """
    session_id = request.session_id
    
    # Check if session exists
    if session_id not in live_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    session = live_sessions[session_id]
    
    # Check if session is currently running
    if session.get("status") == "running":
        return {
            "success": False,
            "message": "Cannot remove running session. Stop the session first.",
            "session_id": session_id,
            "status": "running"
        }
    
    # Mark as removed from execution
    session["in_execution"] = False
    session["status"] = "removed"
    session["removed_from_execution_at"] = datetime.now().isoformat()
    
    # Update in dict (keep for history, but mark as removed)
    live_sessions[session_id] = session
    
    return {
        "success": True,
        "message": "Session removed from execution queue",
        "session_id": session_id,
        "status": "removed"
    }


@app.get("/api/v1/live/session/{session_id}/execution-status")
async def get_execution_status(session_id: str):
    """
    Get the execution status of a session.
    
    Returns:
        - in_execution: bool (is it in the execution queue?)
        - status: queued | running | completed | removed | error
        - configuration: session config if exists
    """
    if session_id not in live_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    
    session = live_sessions[session_id]
    
    return {
        "session_id": session_id,
        "in_execution": session.get("in_execution", False),
        "status": session.get("status", "unknown"),
        "configuration": {
            "user_id": session.get("user_id"),
            "strategy_id": session.get("strategy_id"),
            "strategy_name": session.get("strategy_name"),
            "broker_connection_id": session.get("broker_connection_id"),
            "broker_name": session.get("broker_name"),
            "scale": session.get("scale", 1.0)
        },
        "timestamps": {
            "created_at": session.get("created_at"),
            "added_to_execution_at": session.get("added_to_execution_at"),
            "removed_from_execution_at": session.get("removed_from_execution_at"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at")
        }
    }


@app.post("/api/v1/live/session/configure")
async def configure_session(
    session_id: str = Body(...),
    strategy_id: str = Body(...),
    broker_connection_id: str = Body(...),
    scale: float = Body(1.0)
):
    """
    Configure or update a session with strategy, broker connection, and scale.
    This stores the configuration that will be used when starting SSE sessions.
    
    Request body:
    {
        "session_id": "my_session_1",
        "strategy_id": "d70ec04a-1025-46c5-94c4-3e6bff499644",
        "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4",
        "scale": 2.0
    }
    """
    # Validate broker connection exists
    broker_conn = load_broker_connection(broker_connection_id)
    if not broker_conn:
        raise HTTPException(status_code=404, detail=f"Broker connection not found: {broker_connection_id}")
    
    # Store configuration (will be used when starting session)
    session_config = {
        "session_id": session_id,
        "strategy_id": strategy_id,
        "broker_connection_id": broker_connection_id,
        "scale": scale,
        "configured_at": datetime.now().isoformat()
    }
    
    # Store in live_sessions dict for reference
    if session_id not in live_sessions:
        live_sessions[session_id] = {}
    
    live_sessions[session_id].update(session_config)
    
    return {
        "success": True,
        "session_id": session_id,
        "configuration": session_config
    }


@app.get("/api/v1/live/session/{session_id}/configuration")
async def get_session_configuration(session_id: str):
    """
    Get the configuration for a specific session.
    
    Returns the session configuration including strategy_id, broker_connection_id, and scale.
    """
    if session_id not in live_sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    session = live_sessions[session_id]
    
    return {
        "session_id": session_id,
        "configuration": {
            "strategy_id": session.get("strategy_id"),
            "broker_connection_id": session.get("broker_connection_id"),
            "scale": session.get("scale", 1.0),
            "configured_at": session.get("configured_at"),
            "status": session.get("status", "not_started")
        }
    }


@app.get("/api/v1/live/sessions/configurations")
async def get_all_configurations(user_id: Optional[str] = Query(None)):
    """
    Get all session configurations, optionally filtered by user_id.
    
    Returns:
        List of all session configurations with their scale settings.
    """
    all_configs = []
    
    for session_id, session_data in live_sessions.items():
        # Filter by user_id if provided
        if user_id and session_data.get("user_id") != user_id:
            continue
        
        all_configs.append({
            "session_id": session_id,
            "user_id": session_data.get("user_id"),
            "strategy_id": session_data.get("strategy_id"),
            "broker_connection_id": session_data.get("broker_connection_id"),
            "scale": session_data.get("scale", 1.0),
            "status": session_data.get("status", "not_started"),
            "configured_at": session_data.get("configured_at"),
            "created_at": session_data.get("created_at")
        })
    
    return {
        "configurations": all_configs,
        "total": len(all_configs)
    }


@app.post("/api/v1/live/session/start-all")
async def start_all_queued_sessions(user_id: Optional[str] = Body(None)):
    """
    Start ALL sessions marked for execution (in_execution=True).
    This is the "Start All" button that executes all queued sessions.
    
    Optionally filter by user_id.
    
    Request body:
    {
        "user_id": "user_123"  // Optional - if provided, only start this user's sessions
    }
    """
    import threading
    from src.live_trading.session_executor import execute_session_async
    
    started_sessions = []
    errors = []
    
    # Get all sessions marked for execution
    for session_id, session_data in live_sessions.items():
        # Skip if not marked for execution
        if not session_data.get("in_execution"):
            continue
        
        # Skip if status is already running or completed
        if session_data.get("status") in ["running", "completed"]:
            continue
        
        # Filter by user_id if provided
        if user_id and session_data.get("user_id") != user_id:
            continue
        
        try:
            # Get configuration from execution dict
            strategy_id = session_data.get("strategy_id")
            broker_connection_id = session_data.get("broker_connection_id")
            broker_metadata = session_data.get("broker_metadata", {})
            
            # Create live session with scale from execution dict
            session_metadata = live_session_manager.create_session(
                user_id=session_data.get("user_id"),
                strategy_id=strategy_id,
                broker_connection_id=broker_connection_id,
                broker_metadata=broker_metadata,
                session_id=session_id
            )
            
            # Update status to running
            session_data["status"] = "running"
            session_data["started_at"] = datetime.now().isoformat()
            
            # Start execution in background thread
            thread = threading.Thread(
                target=execute_session_async,
                args=(session_id,),
                daemon=True
            )
            thread.start()
            
            # Store thread reference
            session_data["thread"] = thread
            
            started_sessions.append({
                "session_id": session_id,
                "user_id": session_data.get("user_id"),
                "strategy_id": strategy_id,
                "strategy_name": session_data.get("strategy_name"),
                "broker_name": session_data.get("broker_name"),
                "scale": broker_metadata.get("scale", 1.0),
                "status": "running"
            })
            
        except Exception as e:
            errors.append({
                "session_id": session_id,
                "error": str(e)
            })
    
    return {
        "success": len(started_sessions) > 0,
        "message": f"Started {len(started_sessions)} sessions",
        "started_sessions": started_sessions,
        "errors": errors,
        "total_started": len(started_sessions)
    }


@app.post("/api/v1/live/session/start-sse")
async def start_sse_session(
    user_id: str = Body(...),
    sessions: Dict[str, Dict[str, Any]] = Body(...)
):
    """
    DEPRECATED: Use add-to-execution + start-all instead.
    
    Legacy endpoint for backward compatibility.
    Directly starts sessions without execution dictionary.
    """
    created_sessions = []
    errors = []
    
    for session_id, session_config in sessions.items():
        try:
            # Load broker connection to get metadata
            broker_conn = load_broker_connection(session_config["broker_connection_id"])
            if not broker_conn:
                errors.append({
                    "session_id": session_id,
                    "error": f"Broker connection not found: {session_config['broker_connection_id']}"
                })
                continue
            
            # Get broker metadata and merge with scale from request
            broker_metadata = broker_conn.get("broker_metadata", {}).copy()
            
            # Override scale with value from request if provided
            if "scale" in session_config:
                broker_metadata["scale"] = float(session_config["scale"])
            elif "scale" not in broker_metadata:
                broker_metadata["scale"] = 1.0  # Default scale
            
            # Create session
            session_metadata = live_session_manager.create_session(
                user_id=user_id,
                strategy_id=session_config["strategy_id"],
                broker_connection_id=session_config["broker_connection_id"],
                broker_metadata=broker_metadata,
                session_id=session_id
            )
            
            created_sessions.append(session_metadata)
            
            # Start execution in background thread
            import threading
            from src.live_trading.session_executor import execute_session_async
            
            thread = threading.Thread(
                target=execute_session_async,
                args=(session_id,),
                daemon=True
            )
            thread.start()
            
            # Store thread reference
            session_data = live_session_manager.get_session(session_id)
            if session_data:
                session_data['thread'] = thread
            
        except Exception as e:
            errors.append({
                "session_id": session_id,
                "error": str(e)
            })
    
    return {
        "success": len(created_sessions) > 0,
        "created_sessions": created_sessions,
        "errors": errors,
        "total_created": len(created_sessions)
    }


@app.get("/api/v1/live/session/{session_id}/stream")
async def stream_session_events(session_id: str):
    """
    SSE endpoint - streams real-time events for a session with accumulated state.
    Compatible with existing Live Trade UI and backtest report format.
    
    Sends 'data' events with:
    - session_id: Session identifier
    - catchup_id: Unique event ID for catchup/reconnection
    - timestamp: Server timestamp
    - current_time: Current backtest/simulation time
    - status: running | completed | error
    - accumulated: Full state (trades, events_history, summary)
    - ltp_updates: Latest LTP changes (optional)
    - position_updates: Latest position changes (optional)
    """
    import asyncio
    
    sse_session = sse_manager.get_session(session_id)
    if not sse_session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    async def event_generator():
        """Generate SSE events with accumulated state"""
        last_global_seq = 0
        
        try:
            while True:
                # Get accumulated state
                accumulated_state = sse_session.get_accumulated_state()
                
                # Get latest events since last check
                new_events = sse_session.get_events('all', since_seq=last_global_seq)
                
                # Extract LTP and position updates from recent events
                ltp_updates = {}
                position_updates = []
                
                for event in new_events:
                    if event.get('event_type') == 'ltp_snapshot':
                        ltp_updates = event.get('data', {})
                    elif event.get('event_type') == 'position_update':
                        position_updates.append(event.get('data', {}))
                    
                    # Update last global sequence
                    if 'catchup_id' in event:
                        last_global_seq = sse_session.global_seq
                
                # Build consolidated SSE event (backtest-compatible format)
                event_data = {
                    'session_id': session_id,
                    'catchup_id': f"evt_{sse_session.global_seq:06d}",
                    'timestamp': datetime.now().isoformat(),
                    'current_time': accumulated_state.get('current_time'),
                    'status': sse_session.status,
                    
                    # Full accumulated state (for UI backtest report)
                    'accumulated': {
                        'trades': accumulated_state.get('trades', []),
                        'events_history': accumulated_state.get('events_history', {}),
                        'summary': accumulated_state.get('summary', {})
                    },
                    
                    # Latest updates (for real-time dashboard)
                    'ltp_updates': ltp_updates if ltp_updates else None,
                    'position_updates': position_updates if position_updates else None
                }
                
                # Send as SSE 'data' event
                yield {
                    "event": "data",
                    "data": json.dumps(event_data, default=str)
                }
                
                # Check if session completed
                if sse_session.status == 'completed':
                    # Send final completed event
                    yield {
                        "event": "completed",
                        "data": json.dumps({
                            'session_id': session_id,
                            'accumulated': event_data['accumulated'],
                            'timestamp': datetime.now().isoformat()
                        }, default=str)
                    }
                    break
                
                # Sleep briefly to avoid busy loop (10 updates/second)
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
    
    return EventSourceResponse(event_generator())


@app.post("/api/v1/live/session/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop a running SSE session"""
    session_data = live_session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    # Update status to stopped
    live_session_manager.update_session_status(session_id, "stopped")
    
    # Note: Thread cleanup handled by session manager
    
    return {
        "success": True,
        "session_id": session_id,
        "status": "stopped"
    }


@app.get("/api/v1/live/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current status of a session"""
    session_data = live_session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return session_data['metadata']


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
