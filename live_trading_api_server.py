"""
Live Trading API Server
Multi-strategy live trading system with broker connection management
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client, Client

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

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Global session registry (in-memory, shared across all users)
live_sessions: Dict[str, Dict[str, Any]] = {}

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


# =====================================================================
# Helper Functions
# =====================================================================

def get_session_id(strategy_id: str, broker_connection_id: str) -> str:
    """Generate session ID from strategy and broker connection"""
    return f"{strategy_id}_{broker_connection_id}"


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
    session_id = get_session_id(request.strategy_id, request.broker_connection_id)
    
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
    """Get all sessions (optionally filtered by user or enabled status)"""
    sessions = list(live_sessions.values())
    
    if user_id:
        sessions = [s for s in sessions if s.get("user_id") == user_id]
    
    if enabled_only:
        sessions = [s for s in sessions if s.get("enabled")]
    
    return {
        "sessions": sessions,
        "total": len(sessions)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
