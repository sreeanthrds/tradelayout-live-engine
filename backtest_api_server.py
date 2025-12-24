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
