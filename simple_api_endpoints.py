"""
Simple API Endpoints for Live Trading - Clone of Backtesting Pattern
Add these to backtest_api_server.py
"""

# @app.post("/api/simple/live/start")
async def start_simple_live(
    user_id: str,
    strategy_id: str,
    start_date: str = "2024-10-29",
    speed_multiplier: float = 50.0
):
    """
    START endpoint - Clone of backtesting start
    No Supabase, no complexity. Just start and return session_id.
    """
    import os
    import asyncio
    from simple_live_stream import simple_stream_manager
    from live_backtest_runner import run_live_backtest
    
    # Generate session ID
    session_id = f"live-{os.urandom(6).hex()}"
    
    # Create session in simple manager
    session = simple_stream_manager.create_session(
        session_id=session_id,
        user_id=user_id,
        strategy_id=strategy_id
    )
    
    session.status = "running"
    
    # Launch backtest - it will push data to simple_stream_manager
    asyncio.create_task(
        run_live_backtest(
            session_id=session_id,
            strategy_id=strategy_id,
            user_id=user_id,
            start_date=start_date,
            speed_multiplier=speed_multiplier
        )
    )
    
    print(f"✅ [Simple API] Started session {session_id}")
    print(f"   User: {user_id}")
    print(f"   Strategy: {strategy_id}")
    print(f"   Stream: /api/simple/live/stream/{session_id}")
    
    return {
        "session_id": session_id,
        "stream_url": f"/api/simple/live/stream/{session_id}",
        "status": "running"
    }


# @app.get("/api/simple/live/stream/{session_id}")
async def stream_simple_live(session_id: str):
    """
    STREAM endpoint - Clone of backtesting stream
    Sends accumulated + delta data every second.
    """
    from sse_starlette.sse import EventSourceResponse
    from simple_live_stream import simple_stream_manager
    from fastapi import HTTPException
    
    session = simple_stream_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return EventSourceResponse(
        simple_stream_manager.stream_session(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# @app.get("/api/simple/live/user/{user_id}")
async def stream_simple_user(user_id: str):
    """
    USER STREAM endpoint - All sessions for a user
    Aggregates data from all user's sessions.
    """
    from sse_starlette.sse import EventSourceResponse
    from simple_live_stream import simple_stream_manager
    
    return EventSourceResponse(
        simple_stream_manager.stream_user(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
