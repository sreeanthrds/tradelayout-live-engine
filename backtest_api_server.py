"""
Backtest API Server - FastAPI REST API for backtesting only
Clean version with all live trading code removed
"""

import os
import sys
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import json
import gzip
import zipfile
from io import BytesIO
from sse_starlette.sse import EventSourceResponse
from supabase import create_client, Client

# Store backtest metadata (in-memory)
backtest_metadata = {}

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts datetime objects to ISO format strings."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Initialize Supabase client
supabase: Client = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_ROLE_KEY']
)

from show_dashboard_data import run_dashboard_backtest, dashboard_data, format_value_for_display, substitute_condition_values
from backtest_modular_adapter import run_backtest_with_modular_executor

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_backtest_id(strategy_id: str, start_date: str, end_date: str) -> str:
    """Create backtest ID from strategy_id and date range"""
    return f"{strategy_id}_{start_date}_{end_date}"

def get_backtest_dir(strategy_id: str) -> str:
    """Get backtest results directory for strategy"""
    return os.path.join("backtest_results", strategy_id)

def save_daily_results(strategy_id: str, date_str: str, daily_data: Dict[str, Any]):
    """Save daily backtest results to gzipped JSON files"""
    dir_path = os.path.join(get_backtest_dir(strategy_id), date_str)
    os.makedirs(dir_path, exist_ok=True)
    
    # Transform to match frontend expectations
    trades_data = {
        "date": date_str,
        "summary": daily_data.get('summary', {}),
        "trades": daily_data.get('positions', [])  # Frontend expects 'trades' not 'positions'
    }
    
    # Save trades
    trades_path = os.path.join(dir_path, "trades_daily.json.gz")
    with gzip.open(trades_path, 'wt', encoding='utf-8') as f:
        json.dump(trades_data, f, cls=DateTimeEncoder, indent=2)
    
    # Save diagnostics
    diagnostics_path = os.path.join(dir_path, "diagnostics_export.json.gz")
    with gzip.open(diagnostics_path, 'wt', encoding='utf-8') as f:
        json.dump(daily_data.get('diagnostics', {}), f, cls=DateTimeEncoder, indent=2)
    
    print(f"[API] Saved files for {date_str} to {dir_path}")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Backtest API",
    description="Clean backtesting-only API",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class BacktestRequest(BaseModel):
    """Request model for backtest"""
    user_id: str = Field(..., description="User UUID")
    strategy_id: str = Field(..., description="Strategy UUID")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    broker_connection_id: str = Field(..., description="Broker connection UUID")
    initial_capital: Optional[float] = Field(100000.0, description="Initial capital")
    commission_percentage: Optional[float] = Field(0.01, description="Commission %")
    strategy_scale: Optional[float] = Field(1.0, description="Strategy scale multiplier")

class BacktestResponse(BaseModel):
    """Response model for backtest"""
    backtest_id: str
    strategy_id: str
    start_date: str
    end_date: str
    summary: Dict[str, Any]
    daily_results: List[Dict[str, Any]]

class BacktestStartRequest(BaseModel):
    """Request to start backtest with SSE streaming"""
    strategy_id: str = Field(..., description="Strategy UUID")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    initial_capital: Optional[float] = Field(100000.0, description="Initial capital")
    slippage_percentage: Optional[float] = Field(0.0, description="Slippage %")
    commission_percentage: Optional[float] = Field(0.01, description="Commission %")
    scale: Optional[float] = Field(1.0, description="Quantity scale multiplier")
    use_modular: Optional[bool] = Field(False, description="Use modular live_strategy_executor (with JSONL events)")

class ValidateReadyRequest(BaseModel):
    """Request model for validate-ready endpoint"""
    user_id: str
    strategy_id: str
    broker_connection_id: Optional[str] = None

class StrategyQueueItem(BaseModel):
    """Individual strategy in queue submission"""
    strategy_id: str
    broker_connection_id: str
    scale: Optional[float] = 1.0

class QueueSubmitRequest(BaseModel):
    """Request model for queue submission"""
    strategies: List[StrategyQueueItem]

# ============================================================================
# BASIC ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Backtest API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "backtest": "/api/v1/backtest",
            "stream": "/api/v1/backtest/start",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "backtest-api",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/live-trading/validate-ready")
async def validate_ready(request: ValidateReadyRequest):
    """
    Validate if a strategy is ready to start live trading.
    Checks if strategy exists and broker connection is valid.
    
    Returns:
        ready: bool - Whether the strategy is ready to start
        message: str - Status message
        missing: list - List of missing requirements
    """
    missing = []
    
    # Check if strategy exists in Supabase
    try:
        strategy_response = supabase.table('strategies').select('*').eq('id', request.strategy_id).execute()
        if not strategy_response.data or len(strategy_response.data) == 0:
            missing.append("strategy")
    except Exception as e:
        return {
            "ready": False,
            "message": f"Error validating strategy: {str(e)}",
            "missing": ["strategy"]
        }
    
    # Check if broker connection is provided and valid
    if request.broker_connection_id:
        try:
            broker_response = supabase.table('broker_connections').select('*').eq('id', request.broker_connection_id).execute()
            if not broker_response.data or len(broker_response.data) == 0:
                missing.append("broker_connection")
        except Exception as e:
            return {
                "ready": False,
                "message": f"Error validating broker connection: {str(e)}",
                "missing": ["broker_connection"]
            }
    else:
        missing.append("broker_connection")
    
    # Return validation result
    if missing:
        return {
            "ready": False,
            "message": f"Missing: {', '.join(missing)}",
            "missing": missing
        }
    
    return {
        "ready": True,
        "message": "Strategy is ready to start",
        "missing": []
    }

@app.get("/api/live-trading/session/check")
async def check_session_status(
    user_id: str,
    strategy_id: str,
    broker_connection_id: str
):
    """
    Check if a session exists for the given strategy and broker connection.
    Used by UI to determine if "View Trades" should show the modal or trades.
    
    Query params:
        user_id: User ID
        strategy_id: Strategy ID
        broker_connection_id: Broker connection ID
    
    Returns session details if found, otherwise returns not_found status.
    """
    # Generate session ID
    session_id = f"{user_id}_{strategy_id}_{broker_connection_id}"
    
    # Check execution queue
    if not hasattr(app.state, 'execution_queue'):
        return {
            "found": False,
            "message": "No sessions in queue"
        }
    
    queue = app.state.execution_queue
    
    # Look for session
    if session_id in queue:
        session_data = queue[session_id]
        
        # Get live status if running
        live_status = None
        if session_data.get('status') == 'running':
            try:
                import requests
                response = requests.get(
                    f'http://localhost:8001/api/v1/live/session/{session_id}/status',
                    timeout=2
                )
                if response.status_code == 200:
                    live_status = response.json()
            except:
                pass
        
        return {
            "found": True,
            "session_id": session_id,
            "status": session_data.get('status'),
            "strategy_id": session_data.get('strategy_id'),
            "strategy_name": session_data.get('strategy_name'),
            "broker_name": session_data.get('broker_name'),
            "scale": session_data.get('scale', 1.0),
            "submitted_at": session_data.get('submitted_at'),
            "started_at": session_data.get('started_at'),
            "queue_type": session_data.get('queue_type'),
            "live_status": live_status
        }
    
    return {
        "found": False,
        "message": f"No session found for strategy {strategy_id}"
    }

@app.get("/api/live-trading/session-status/{user_id}/{strategy_id}/{broker_connection_id}")
async def get_session_status_path(
    user_id: str,
    strategy_id: str,
    broker_connection_id: str
):
    """
    Alternative endpoint with path parameters (UI preference).
    Same as /api/live-trading/session/check but with path params instead of query params.
    """
    # Reuse the logic from check_session_status
    session_id = f"{user_id}_{strategy_id}_{broker_connection_id}"
    
    if not hasattr(app.state, 'execution_queue'):
        return {
            "found": False,
            "message": "No sessions in queue"
        }
    
    queue = app.state.execution_queue
    
    if session_id in queue:
        session_data = queue[session_id]
        
        live_status = None
        if session_data.get('status') == 'running':
            try:
                import requests
                response = requests.get(
                    f'http://localhost:8001/api/v1/live/session/{session_id}/status',
                    timeout=2
                )
                if response.status_code == 200:
                    live_status = response.json()
            except:
                pass
        
        return {
            "found": True,
            "session_id": session_id,
            "status": session_data.get('status'),
            "strategy_id": session_data.get('strategy_id'),
            "strategy_name": session_data.get('strategy_name'),
            "broker_name": session_data.get('broker_name'),
            "scale": session_data.get('scale', 1.0),
            "submitted_at": session_data.get('submitted_at'),
            "started_at": session_data.get('started_at'),
            "queue_type": session_data.get('queue_type'),
            "live_status": live_status
        }
    
    return {
        "found": False,
        "message": f"No session found for strategy {strategy_id}"
    }

@app.get("/api/queue/status/{queue_type}")
async def get_queue_status(queue_type: str):
    """
    Get status of all sessions in a specific queue.
    
    Path params:
        queue_type: Queue type (e.g., 'admin_tester')
    
    Returns list of sessions and counts.
    """
    if not hasattr(app.state, 'execution_queue'):
        return {
            "queue_type": queue_type,
            "sessions": [],
            "total": 0,
            "queued": 0,
            "running": 0
        }
    
    queue = app.state.execution_queue
    queue_sessions = [
        {
            "session_id": session_id,
            "user_id": data.get('user_id'),
            "strategy_id": data.get('strategy_id'),
            "strategy_name": data.get('strategy_name'),
            "broker_name": data.get('broker_name'),
            "status": data.get('status'),
            "scale": data.get('scale', 1.0),
            "submitted_at": data.get('submitted_at'),
            "started_at": data.get('started_at')
        }
        for session_id, data in queue.items()
        if data.get('queue_type') == queue_type
    ]
    
    queued_count = sum(1 for s in queue_sessions if s['status'] == 'queued')
    running_count = sum(1 for s in queue_sessions if s['status'] == 'running')
    
    return {
        "queue_type": queue_type,
        "sessions": queue_sessions,
        "total": len(queue_sessions),
        "queued": queued_count,
        "running": running_count
    }

@app.get("/api/live-trading/stream/{user_id}")
async def stream_user_sessions(user_id: str):
    """
    SSE stream for all of a user's live trading sessions.
    Aggregates data from all running sessions and streams updates.
    
    Path params:
        user_id: User ID
    """
    import asyncio
    import requests
    
    async def event_generator():
        """Generate SSE events for all user sessions"""
        try:
            while True:
                # Get all sessions for this user from execution queue
                if not hasattr(app.state, 'execution_queue'):
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "message": "No active sessions",
                            "user_id": user_id,
                            "sessions": []
                        })
                    }
                    await asyncio.sleep(2)
                    continue
                
                queue = app.state.execution_queue
                user_sessions = [
                    (session_id, session_data)
                    for session_id, session_data in queue.items()
                    if session_data.get('user_id') == user_id
                    and session_data.get('status') in ['queued', 'running']
                ]
                
                if not user_sessions:
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "message": "No active sessions",
                            "user_id": user_id,
                            "sessions": []
                        })
                    }
                    await asyncio.sleep(2)
                    continue
                
                # Aggregate session data
                aggregated_data = {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "sessions": [],
                    "total_sessions": len(user_sessions),
                    "running_count": 0,
                    "queued_count": 0
                }
                
                for session_id, session_data in user_sessions:
                    session_info = {
                        "session_id": session_id,
                        "strategy_id": session_data.get('strategy_id'),
                        "strategy_name": session_data.get('strategy_name'),
                        "broker_name": session_data.get('broker_name'),
                        "status": session_data.get('status'),
                        "scale": session_data.get('scale', 1.0),
                        "submitted_at": session_data.get('submitted_at'),
                        "started_at": session_data.get('started_at')
                    }
                    
                    # Try to get live data from live trading API if running
                    if session_data.get('status') == 'running':
                        try:
                            # Get session status from live trading API
                            response = requests.get(
                                f'http://localhost:8001/api/v1/live/session/{session_id}/status',
                                timeout=2
                            )
                            if response.status_code == 200:
                                live_status = response.json()
                                session_info['live_status'] = live_status
                        except:
                            pass
                        
                        aggregated_data['running_count'] += 1
                    else:
                        aggregated_data['queued_count'] += 1
                    
                    aggregated_data['sessions'].append(session_info)
                
                # Send aggregated update
                yield {
                    "event": "data",
                    "data": json.dumps(aggregated_data, default=str)
                }
                
                # Update every 2 seconds
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
    
    return EventSourceResponse(event_generator())

@app.post("/api/queue/execute")
async def execute_queue(queue_type: str, trigger_type: str):
    """
    Execute all strategies in the queue.
    Starts all queued strategies that match the queue_type.
    
    Query params:
        queue_type: Queue type (e.g., 'admin_tester')
        trigger_type: Trigger type (e.g., 'manual')
    
    Returns list of started sessions.
    """
    import requests
    
    started = []
    errors = []
    
    # Get execution queue
    if not hasattr(app.state, 'execution_queue'):
        return {
            "success": False,
            "message": "No strategies in queue",
            "started": [],
            "errors": [],
            "total_started": 0
        }
    
    queue = app.state.execution_queue
    
    # Filter by queue_type and status
    to_execute = [
        (session_id, session_data) 
        for session_id, session_data in queue.items()
        if session_data.get('queue_type') == queue_type 
        and session_data.get('status') == 'queued'
        and session_data.get('in_execution') == True
    ]
    
    if not to_execute:
        return {
            "success": False,
            "message": f"No queued strategies found for queue_type: {queue_type}",
            "started": [],
            "errors": [],
            "total_started": 0
        }
    
    # Start each session by calling live trading API
    for session_id, session_data in to_execute:
        try:
            # Prepare session config for live trading API
            session_config = {
                session_id: {
                    "strategy_id": session_data['strategy_id'],
                    "broker_connection_id": session_data['broker_connection_id'],
                    "scale": session_data.get('scale', 1.0)
                }
            }
            
            # Call live trading API to start session
            response = requests.post(
                'http://localhost:8001/api/v1/live/session/start-sse',
                json={
                    "user_id": session_data['user_id'],
                    "sessions": session_config
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Update queue status
                session_data['status'] = 'running'
                session_data['started_at'] = datetime.now().isoformat()
                
                started.append({
                    "session_id": session_id,
                    "strategy_id": session_data['strategy_id'],
                    "strategy_name": session_data.get('strategy_name'),
                    "broker_name": session_data.get('broker_name'),
                    "scale": session_data.get('scale', 1.0),
                    "status": "running"
                })
            else:
                errors.append({
                    "session_id": session_id,
                    "error": f"Failed to start: {response.status_code}"
                })
        
        except Exception as e:
            errors.append({
                "session_id": session_id,
                "error": str(e)
            })
    
    return {
        "success": len(started) > 0,
        "message": f"Started {len(started)} sessions",
        "started": started,
        "errors": errors,
        "total_started": len(started),
        "total_errors": len(errors),
        "trigger_type": trigger_type
    }

@app.post("/api/queue/submit")
async def submit_to_queue(request: QueueSubmitRequest, user_id: str, queue_type: str):
    """
    Submit strategies to execution queue.
    This endpoint adds strategies to the execution dictionary for later execution.
    
    Query params:
        user_id: User ID
        queue_type: Queue type (e.g., 'admin_tester')
    
    Request body:
    {
        "strategies": [
            {
                "strategy_id": "d70ec04a-...",
                "broker_connection_id": "acf98a95-...",
                "scale": 1.0
            }
        ]
    }
    """
    submitted = []
    errors = []
    
    for strategy_item in request.strategies:
        try:
            # Validate strategy exists
            strategy_response = supabase.table('strategies').select('*').eq('id', strategy_item.strategy_id).execute()
            if not strategy_response.data or len(strategy_response.data) == 0:
                errors.append({
                    "strategy_id": strategy_item.strategy_id,
                    "error": "Strategy not found"
                })
                continue
            
            strategy_data = strategy_response.data[0]
            
            # Validate broker connection exists
            broker_response = supabase.table('broker_connections').select('*').eq('id', strategy_item.broker_connection_id).execute()
            if not broker_response.data or len(broker_response.data) == 0:
                errors.append({
                    "strategy_id": strategy_item.strategy_id,
                    "error": "Broker connection not found"
                })
                continue
            
            broker_data = broker_response.data[0]
            
            # Generate session ID
            session_id = f"{user_id}_{strategy_item.strategy_id}_{strategy_item.broker_connection_id}"
            
            # Add to execution queue (in-memory dict for now)
            # In production, this would go to Redis or database
            queue_entry = {
                "session_id": session_id,
                "user_id": user_id,
                "strategy_id": strategy_item.strategy_id,
                "strategy_name": strategy_data.get('name', 'Unknown'),
                "broker_connection_id": strategy_item.broker_connection_id,
                "broker_name": broker_data.get('broker_name', 'Unknown'),
                "scale": strategy_item.scale or 1.0,
                "queue_type": queue_type,
                "status": "queued",
                "in_execution": True,
                "submitted_at": datetime.now().isoformat(),
                "broker_metadata": {
                    "scale": strategy_item.scale or 1.0
                }
            }
            
            # Store in in-memory dict (would be Redis in production)
            if not hasattr(app.state, 'execution_queue'):
                app.state.execution_queue = {}
            
            app.state.execution_queue[session_id] = queue_entry
            
            submitted.append({
                "session_id": session_id,
                "strategy_id": strategy_item.strategy_id,
                "strategy_name": strategy_data.get('name'),
                "broker_name": broker_data.get('broker_name'),
                "scale": strategy_item.scale or 1.0,
                "status": "queued"
            })
            
        except Exception as e:
            errors.append({
                "strategy_id": strategy_item.strategy_id,
                "error": str(e)
            })
    
    return {
        "success": len(submitted) > 0,
        "message": f"Submitted {len(submitted)} strategies to queue",
        "submitted": submitted,
        "errors": errors,
        "total_submitted": len(submitted),
        "total_errors": len(errors)
    }

# ============================================================================
# BACKTEST ENDPOINTS
# ============================================================================

@app.post("/api/v1/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run backtest and return complete results
    """
    try:
        backtest_id = create_backtest_id(
            request.strategy_id,
            request.start_date,
            request.end_date
        )
        
        # Run backtest (synchronous function)
        backtest_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        results = run_dashboard_backtest(
            strategy_id=request.strategy_id,
            backtest_date=backtest_date,
            strategy_scale=request.strategy_scale or 1.0
        )
        
        # Save results
        for daily_result in results.get('daily_results', []):
            save_daily_results(
                request.strategy_id,
                daily_result['date'],
                daily_result
            )
        
        return BacktestResponse(
            backtest_id=backtest_id,
            strategy_id=request.strategy_id,
            start_date=request.start_date,
            end_date=request.end_date,
            summary=results.get('summary', {}),
            daily_results=results.get('daily_results', [])
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {str(e)}"
        )

@app.post("/api/v1/backtest/start")
async def start_backtest(request: BacktestStartRequest):
    """
    Start backtest and return backtest_id for streaming
    """
    try:
        backtest_id = create_backtest_id(
            request.strategy_id,
            request.start_date,
            request.end_date
        )
        
        # Store execution config in metadata
        backtest_metadata[backtest_id] = {
            "scale": request.scale or 1.0,
            "use_modular": request.use_modular or False
        }
        
        # Create results directory
        os.makedirs(get_backtest_dir(request.strategy_id), exist_ok=True)
        
        # Calculate total days
        start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(request.end_date, "%Y-%m-%d").date()
        total_days = (end - start).days + 1
        
        return {
            "backtest_id": backtest_id,
            "total_days": total_days,
            "status": "starting",
            "stream_url": f"/api/v1/backtest/{backtest_id}/stream"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start: {str(e)}")

@app.get("/api/v1/backtest/{backtest_id}/stream")
async def stream_backtest_progress(backtest_id: str):
    """
    SSE stream for backtest progress - matches frontend expectations
    """
    async def event_generator():
        try:
            # Parse backtest_id
            parts = backtest_id.split('_')
            strategy_id = parts[0]
            start_date_str = parts[1]
            end_date_str = parts[2]
            
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            # Get execution config from metadata
            metadata = backtest_metadata.get(backtest_id, {})
            scale = metadata.get("scale", 1.0)
            use_modular = metadata.get("use_modular", False)
            
            # Calculate date range
            current_date = start_date
            all_dates = []
            while current_date <= end_date:
                all_dates.append(current_date)
                current_date += timedelta(days=1)
            
            total_days = len(all_dates)
            
            # Accumulators for overall summary
            overall_trades = 0
            overall_pnl = 0.0
            overall_winning = 0
            overall_losing = 0
            overall_largest_win = 0.0
            overall_largest_loss = 0.0
            
            # Process each day
            for day_number, backtest_date in enumerate(all_dates, start=1):
                date_str = backtest_date.strftime("%Y-%m-%d")
                
                # Emit day_started
                yield {
                    "event": "day_started",
                    "data": json.dumps({
                        "date": date_str,
                        "day_number": day_number,
                        "total_days": total_days
                    })
                }
                
                # Choose execution path
                if use_modular:
                    # Use modular live_strategy_executor (with JSONL events)
                    # Adapter handles: Supabase load, session prep, modular execution, JSONL conversion
                    result = await run_backtest_with_modular_executor(
                        strategy_id=strategy_id,
                        trade_date=date_str,
                        user_id="backtest_user",
                        scale=scale
                    )
                    
                    # Extract results
                    if result.get("success"):
                        results = {
                            "positions": result.get("dashboard_data", {}).get("positions", []),
                            "summary": result.get("summary", {})
                        }
                    else:
                        results = {"positions": [], "summary": {}}
                    
                    # JSONL files + JSON.gz files already saved by adapter
                else:
                    # Use legacy show_dashboard_data (no JSONL events)
                    results = run_dashboard_backtest(
                        strategy_id=strategy_id,
                        backtest_date=backtest_date,
                        strategy_scale=scale
                    )
                    
                    # Save daily results
                    save_daily_results(strategy_id, date_str, results)
                
                # Accumulate daily summary for overall summary
                daily_summary = results.get('summary', {})
                overall_trades += daily_summary.get('total_trades', 0)
                overall_pnl += daily_summary.get('total_pnl', 0)
                overall_winning += daily_summary.get('winning_trades', 0)
                overall_losing += daily_summary.get('losing_trades', 0)
                overall_largest_win = max(overall_largest_win, daily_summary.get('largest_win', 0))
                overall_largest_loss = min(overall_largest_loss, daily_summary.get('largest_loss', 0))
                
                # Emit day_completed
                yield {
                    "event": "day_completed",
                    "data": json.dumps({
                        "date": date_str,
                        "day_number": day_number,
                        "total_days": total_days,
                        "summary": daily_summary,
                        "has_detail_data": True
                    }, cls=DateTimeEncoder)
                }
                
                await asyncio.sleep(0.05)
            
            # Calculate overall summary from accumulated data
            overall_win_rate = (overall_winning / overall_trades * 100) if overall_trades > 0 else 0
            
            overall_summary = {
                "total_days": total_days,
                "total_trades": overall_trades,
                "total_pnl": round(overall_pnl, 2),
                "win_rate": round(overall_win_rate, 2),
                "winning_trades": overall_winning,
                "losing_trades": overall_losing,
                "largest_win": round(overall_largest_win, 2),
                "largest_loss": round(overall_largest_loss, 2)
            }
            
            # Emit backtest_completed
            yield {
                "event": "backtest_completed",
                "data": json.dumps({
                    "backtest_id": backtest_id,
                    "overall_summary": overall_summary
                }, cls=DateTimeEncoder)
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(event_generator())

@app.get("/api/v1/backtest/{backtest_id}/day/{date}")
async def download_day_details(backtest_id: str, date: str):
    """
    Download daily results as ZIP
    """
    try:
        strategy_id = backtest_id.split('_')[0]
        dir_path = os.path.join(get_backtest_dir(strategy_id), date)
        
        if not os.path.exists(dir_path):
            raise HTTPException(status_code=404, detail="Day not found")
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                zip_file.write(file_path, filename)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={date}_details.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/backtest/status")
async def get_backtest_status():
    """Get backtest service status"""
    return {
        "status": "ready",
        "service": "backtest",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
