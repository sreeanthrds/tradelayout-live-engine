"""
Backtest API Server - FastAPI REST API for backtesting
Provides comprehensive JSON data with diagnostic text for UI dashboard
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta, time
import json
import asyncio
import subprocess
import gzip
import zipfile
from io import BytesIO
from threading import Lock
from sse_starlette.sse import EventSourceResponse
from supabase import create_client, Client


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that converts datetime objects to ISO format strings."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables FIRST
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Import live simulation SSE manager
from live_simulation_sse import sse_manager
from live_backtest_runner import run_live_backtest
from simple_live_stream import simple_stream_manager
from src.core.global_instances import get_instance_manager

# Initialize Supabase client AFTER environment variables are set
supabase: Client = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_ROLE_KEY']
)

# ============================================================================
# MULTI-STRATEGY QUEUE SYSTEM
# ============================================================================

# Global strategy queues (in-memory for now, Redis for distributed)
# Dict structure: {queue_type: {strategy_id: queue_entry}}
# Using strategy_id as key prevents duplicate submissions
strategy_queues = {
    'production': {},      # Live trading queue (scheduled at 09:13 AM)
    'admin_tester': {}     # Test queue (manual trigger by admin)
}

# Queue locks for thread safety
queue_locks = {
    'production': Lock(),
    'admin_tester': Lock()
}

# Active processing tracker
active_processing = {
    'production': False,
    'admin_tester': False
}

# Global instance manager
instance_manager = get_instance_manager()

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

from show_dashboard_data import run_dashboard_backtest, dashboard_data, format_value_for_display, substitute_condition_values

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_backtest_id(strategy_id: str, start_date: str, end_date: str) -> str:
    """Create backtest ID from strategy_id and date range"""
    return f"{strategy_id}_{start_date}_{end_date}"

def parse_backtest_id(backtest_id: str) -> tuple:
    """Parse backtest ID to extract strategy_id, start_date, end_date"""
    parts = backtest_id.rsplit('_', 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid backtest_id format: {backtest_id}")
    return parts[0], parts[1], parts[2]

def get_backtest_dir(strategy_id: str) -> str:
    """Get backtest results directory for a strategy"""
    return f"backtest_results/{strategy_id}"

def get_day_dir(strategy_id: str, date: str) -> str:
    """Get directory for a specific day's backtest results"""
    return f"backtest_results/{strategy_id}/{date}"

def has_historical_backtest_data(strategy_id: str) -> bool:
    """
    Check if strategy has any historical backtest data files.
    Returns True if any backtest result files exist for this strategy.
    """
    strategy_dir = get_strategy_dir(strategy_id)
    
    # Check if strategy directory exists
    if not os.path.exists(strategy_dir):
        return False
    
    # Check if any date subdirectories exist with trade files
    try:
        for date_dir in os.listdir(strategy_dir):
            day_path = os.path.join(strategy_dir, date_dir)
            if os.path.isdir(day_path):
                # Check for trades_daily.json.gz file
                trades_file = os.path.join(day_path, 'trades_daily.json.gz')
                if os.path.exists(trades_file):
                    return True
    except Exception as e:
        print(f"Error checking backtest data for {strategy_id}: {e}")
    
    return False

def build_flow_chain(events_history: dict, exec_id: str, max_depth: int = 50) -> list:
    """
    Build flow chain from current node back to start/trigger.
    Returns list of execution IDs in CHRONOLOGICAL order (oldest to newest).
    """
    chain = [exec_id]  # Include the current node
    current_id = exec_id
    depth = 0
    
    while current_id and current_id in events_history and depth < max_depth:
        event = events_history[current_id]
        parent_id = event.get('parent_execution_id')
        
        if parent_id and parent_id in events_history:
            parent_event = events_history[parent_id]
            node_type = parent_event.get('node_type', '')
            
            # Add ALL parent nodes (signals, conditions, start)
            if any(keyword in node_type for keyword in ['Signal', 'Condition', 'Start', 'Entry', 'Exit']):
                chain.append(parent_id)
            
            current_id = parent_id
            depth += 1
        else:
            break
    
    # Return in chronological order (oldest first)
    return list(reversed(chain))

def extract_flow_ids_from_diagnostics(diagnostics: dict, node_id: str, timestamp: str) -> list:
    """Extract execution_ids (flow_ids) for a specific node execution"""
    events = diagnostics.get('events_history', {})
    
    for exec_id, event in events.items():
        if event.get('node_id') == node_id:
            # Check if timestamp matches (compare HH:MM:SS)
            event_time = event.get('timestamp', '')
            if timestamp and event_time:
                # Extract time portion from diagnostic timestamp
                # Diagnostic format: "2024-10-28 09:18:00+05:30"
                # Position format: "09:18:00"
                # Extract HH:MM:SS from diagnostic (chars 11-19)
                if len(event_time) >= 19:
                    diagnostic_time = event_time[11:19]  # "09:18:00"
                    # Compare HH:MM:SS (first 8 chars)
                    if diagnostic_time == timestamp[:8]:
                        # Found the node execution - build full chain
                        return build_flow_chain(events, exec_id)
    
    return []

def map_position_to_trade(pos: dict, diagnostics: dict) -> dict:
    """
    Map position data to trade format expected by UI
    Adds entry_flow_ids and exit_flow_ids to link to diagnostic events
    """
    # Extract flow IDs
    entry_flow_ids = extract_flow_ids_from_diagnostics(
        diagnostics,
        pos.get('entry_node_id'),
        pos.get('entry_timestamp')
    )
    
    exit_flow_ids = []
    if pos.get('status') == 'CLOSED':
        exit_flow_ids = extract_flow_ids_from_diagnostics(
            diagnostics,
            pos.get('exit_node_id'),
            pos.get('exit_timestamp')
        )
    
    # Convert datetime objects to strings
    entry_time = pos.get('entry_time')
    if hasattr(entry_time, 'isoformat'):
        entry_time = entry_time.isoformat()
    elif entry_time:
        entry_time = str(entry_time)
    
    exit_time = pos.get('exit_time')
    if hasattr(exit_time, 'isoformat'):
        exit_time = exit_time.isoformat()
    elif exit_time:
        exit_time = str(exit_time)
    
    return {
        'trade_id': pos.get('position_id'),
        'position_id': pos.get('position_id'),
        're_entry_num': pos.get('re_entry_num', 0),
        'symbol': pos.get('symbol'),
        'side': pos.get('side'),
        'quantity': pos.get('actual_quantity'),  # Use actual_quantity (scaled shares) instead of quantity (lots)
        'entry_price': f"{pos.get('entry_price', 0):.2f}",
        'entry_time': entry_time,
        'exit_price': f"{pos.get('exit_price', 0):.2f}" if pos.get('exit_price') else None,
        'exit_time': exit_time,
        'pnl': f"{pos.get('pnl', 0):.2f}" if pos.get('pnl') is not None else None,
        'pnl_percent': f"{pos.get('pnl_percentage', 0):.2f}" if pos.get('pnl_percentage') is not None else None,
        'duration_minutes': pos.get('duration_minutes'),
        'status': pos.get('status'),
        'entry_flow_ids': entry_flow_ids,
        'exit_flow_ids': exit_flow_ids,
        'entry_trigger': pos.get('entry_node_id'),
        'exit_reason': pos.get('exit_reason')
    }

def save_daily_files(strategy_id: str, date_str: str, daily_data: dict):
    """
    Save trades_daily.json.gz and diagnostics_export.json.gz
    to backtest_results/{strategy_id}/{date}/
    """
    dir_path = get_day_dir(strategy_id, date_str)
    os.makedirs(dir_path, exist_ok=True)
    
    # trades_daily.json
    trades_data = {
        'date': date_str,
        'summary': {
            'total_trades': daily_data['summary']['total_positions'],
            'total_pnl': f"{daily_data['summary']['total_pnl']:.2f}",
            'winning_trades': daily_data['summary']['winning_trades'],
            'losing_trades': daily_data['summary']['losing_trades'],
            'win_rate': f"{daily_data['summary']['win_rate']:.2f}"
        },
        'trades': [
            map_position_to_trade(pos, daily_data.get('diagnostics', {}))
            for pos in daily_data['positions']
        ]
    }
    
    with gzip.open(f"{dir_path}/trades_daily.json.gz", 'wt', encoding='utf-8') as f:
        json.dump(trades_data, f, indent=2, cls=DateTimeEncoder)
    
    # diagnostics_export.json
    diagnostics_data = {
        'events_history': daily_data.get('diagnostics', {}).get('events_history', {})
    }
    
    with gzip.open(f"{dir_path}/diagnostics_export.json.gz", 'wt', encoding='utf-8') as f:
        json.dump(diagnostics_data, f, indent=2, cls=DateTimeEncoder)
    
    print(f"[API] Saved files for {date_str} to {dir_path}")

# ============================================================================
# UI FILES GENERATION (Legacy)
# ============================================================================

def generate_ui_files_from_diagnostics():
    """
    Generate trades_daily.json and diagnostics_export.json files.
    These files are useful for reference and can be served directly.
    """
    try:
        print("[API] Generating UI files...")
        
        # Step 1: Generate diagnostics_export.json
        result1 = subprocess.run(
            [sys.executable, 'view_diagnostics.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result1.returncode != 0:
            print(f"[API WARNING] Failed to generate diagnostics_export.json: {result1.stderr}")
            return False
        
        # Step 2: Extract trades
        result2 = subprocess.run(
            [sys.executable, 'extract_trades_simplified.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result2.returncode != 0:
            print(f"[API WARNING] Failed to generate trades_daily.json: {result2.stderr}")
            return False
        
        # Step 3: Format prices
        result3 = subprocess.run(
            [sys.executable, 'format_diagnostics_prices.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result3.returncode != 0:
            print(f"[API WARNING] Failed to format prices: {result3.stderr}")
            return False
        
        print("[API] ✅ UI files generated successfully")
        return True
        
    except Exception as e:
        print(f"[API ERROR] Failed to generate UI files: {e}")
        return False

# Initialize FastAPI app
app = FastAPI(
    title="TradeLayout Backtest API",
    description="REST API for running backtests and retrieving comprehensive diagnostic data",
    version="1.0.0"
)

# Initialize session storage for live simulations
active_sessions: Dict[str, Dict[str, Any]] = {}
active_sse_connections: Dict[str, Any] = {}

# Middleware to bypass ngrok browser warning
@app.middleware("http")
async def bypass_ngrok_warning(request, call_next):
    """Add header to bypass ngrok browser warning page"""
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (including lovable.app and ngrok)
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["*"],
    allow_headers=["*", "ngrok-skip-browser-warning"],  # Explicitly allow ngrok header
    expose_headers=["*"]
)

# Add GZip compression middleware (reduces JSON size by 70-80%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request/Response Models
class BacktestRequest(BaseModel):
    strategy_id: str = Field(..., description="Strategy UUID")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format (defaults to start_date)")
    mode: str = Field("backtesting", description="Execution mode (currently only 'backtesting' supported)")
    include_diagnostics: bool = Field(True, description="Include diagnostic text in response")

class BacktestResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

def generate_diagnostic_text(pos: Dict[str, Any], pos_num: int, txn_num: int) -> str:
    """
    Generate formatted diagnostic text for a transaction (same as console output)
    
    Args:
        pos: Position/transaction data
        pos_num: Position number
        txn_num: Transaction number
        
    Returns:
        Formatted diagnostic text string
    """
    lines = []
    
    # Header
    re_entry_label = f" (Re-entry #{pos['re_entry_num']})" if pos['re_entry_num'] > 0 else ""
    lines.append("─" * 80)
    lines.append(f"Position #{pos_num} | Transaction #{txn_num}{re_entry_label}")
    lines.append(f"Position ID: {pos['position_id']} | Contract: {pos['symbol']}")
    lines.append(f"Entry Node: {pos['entry_node_id']} | Entry: {pos['entry_timestamp']} @ ₹{pos['entry_price']:.2f} | NIFTY Spot: ₹{pos['nifty_spot_at_entry']:.2f}")
    lines.append("─" * 80)
    
    # Entry Diagnostic Data
    if 'diagnostic_data' in pos and pos['diagnostic_data']:
        diag = pos['diagnostic_data']
        
        if 'condition_preview' in pos and pos['condition_preview']:
            preview = pos['condition_preview']
            lines.append("")
            lines.append("   📋 Entry Condition Preview:")
            lines.append(f"      Original: {preview}")
            
            substituted = substitute_condition_values(preview, diag)
            if substituted != preview:
                lines.append(f"      With Values: {substituted}")
            
            # Condition evaluations
            if 'conditions_evaluated' in diag and diag['conditions_evaluated']:
                lines.append("")
                lines.append("   💡 Condition Evaluations:")
                for idx, cond in enumerate(diag['conditions_evaluated'], 1):
                    lhs_val = cond.get('lhs_value', 'N/A')
                    rhs_val = cond.get('rhs_value', 'N/A')
                    lhs_expr = cond.get('lhs_expression', '')
                    rhs_expr = cond.get('rhs_expression', '')
                    operator = cond.get('operator', '?')
                    result = cond.get('result', False)
                    result_icon = '✅' if result else '❌'
                    cond_type = cond.get('condition_type', 'unknown')
                    
                    lhs_str = format_value_for_display(lhs_val, str(lhs_expr))
                    rhs_str = format_value_for_display(rhs_val, str(rhs_expr))
                    
                    lines.append(f"      {idx}. {result_icon} {lhs_str} {operator} {rhs_str} [{cond_type}]")
            
            # Node variables
            if 'node_variables' in pos and pos['node_variables']:
                if preview and any(nv in preview for nv in pos['node_variables'].keys()):
                    lines.append("")
                    lines.append("   📌 Node Variables at Entry:")
                    for var_name, var_value in pos['node_variables'].items():
                        if var_name in preview:
                            formatted_val = format_value_for_display(var_value, var_name)
                            lines.append(f"      {var_name} = {formatted_val}")
        
        # Candle data
        if 'candle_data' in diag and diag['candle_data']:
            lines.append("")
            lines.append("   📊 Candle Data at Entry:")
            for symbol, candles in diag['candle_data'].items():
                if 'previous' in candles and candles['previous']:
                    prev = candles['previous']
                    lines.append(f"      {symbol} Previous: O={prev.get('open', 0):.2f} H={prev.get('high', 0):.2f} ⬆️  L={prev.get('low', 0):.2f} ⬇️  C={prev.get('close', 0):.2f}")
                if 'current' in candles and candles['current']:
                    curr = candles['current']
                    lines.append(f"      {symbol} Current:  O={curr.get('open', 0):.2f} H={curr.get('high', 0):.2f} ⬆️  L={curr.get('low', 0):.2f} ⬇️  C={curr.get('close', 0):.2f}")
    
    # Exit Information
    if pos['status'] == 'CLOSED':
        lines.append("")
        lines.append("─" * 80)
        pnl_icon = '🟢' if pos['pnl'] >= 0 else '🔴'
        exit_node = pos.get('exit_node_id', 'N/A')
        lines.append(f"Exit Node: {exit_node} | Exit: {pos['exit_timestamp']} @ ₹{pos['exit_price']:.2f} | Duration: {pos['duration_minutes']:.1f}m")
        nifty_exit = pos.get('nifty_spot_at_exit', 0)
        if nifty_exit:
            lines.append(f"NIFTY Spot @ Exit: ₹{nifty_exit:.2f} | P&L: {pnl_icon} ₹{pos['pnl']:.2f} ({pos['pnl_percentage']:.2f}%)")
        else:
            lines.append(f"P&L: {pnl_icon} ₹{pos['pnl']:.2f} ({pos['pnl_percentage']:.2f}%)")
        lines.append(f"Exit Reason: {pos['exit_reason']}")
        
        # Exit diagnostic data
        exit_diag = pos.get('exit_diagnostic_data', {})
        exit_preview = pos.get('exit_condition_preview')
        
        if exit_diag and exit_preview:
            lines.append("")
            lines.append("   📋 Exit Condition Preview:")
            lines.append(f"      Original: {exit_preview}")
            
            exit_substituted = substitute_condition_values(exit_preview, exit_diag)
            if exit_substituted != exit_preview:
                lines.append(f"      With Values: {exit_substituted}")
            
            if 'conditions_evaluated' in exit_diag and exit_diag['conditions_evaluated']:
                lines.append("")
                lines.append("   💡 Exit Condition Evaluations:")
                for idx, cond in enumerate(exit_diag['conditions_evaluated'], 1):
                    lhs_val = cond.get('lhs_value', 'N/A')
                    rhs_val = cond.get('rhs_value', 'N/A')
                    lhs_expr = cond.get('lhs_expression', '')
                    rhs_expr = cond.get('rhs_expression', '')
                    operator = cond.get('operator', '?')
                    result = cond.get('result', False)
                    result_icon = '✅' if result else '❌'
                    cond_type = cond.get('condition_type', 'unknown')
                    
                    lhs_str = format_value_for_display(lhs_val, str(lhs_expr))
                    rhs_str = format_value_for_display(rhs_val, str(rhs_expr))
                    
                    lines.append(f"      {idx}. {result_icon} {lhs_str} {operator} {rhs_str} [{cond_type}]")
        
        lines.append("─" * 80)
    
    return "\n".join(lines)

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "service": "TradeLayout Backtest API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/api/v1/backtest": "Run backtest (POST)",
            "/api/v1/backtest/status": "Get backtest status (GET)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with session stats"""
    return {
        "status": "healthy",
        "service": "Backtest API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(simple_stream_manager.sessions),
        "memory_sessions": len(active_sessions)
    }

@app.post("/api/admin/cleanup-sessions")
async def cleanup_sessions_endpoint(max_age_minutes: int = 60):
    """
    Manual cleanup endpoint - Remove stale sessions
    Use in emergencies when sessions accumulate
    """
    cleaned_simple = simple_stream_manager.cleanup_stale_sessions(max_age_minutes)
    cleaned_memory = 0
    
    # Also clean active_sessions if needed
    if max_age_minutes == 0:  # Force cleanup all
        cleaned_simple = simple_stream_manager.cleanup_all_sessions()
        cleaned_memory = len(active_sessions)
        active_sessions.clear()
    
    return {
        "status": "success",
        "cleaned_sessions": cleaned_simple,
        "cleaned_memory": cleaned_memory,
        "remaining_sessions": len(simple_stream_manager.sessions),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/backtest", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run backtest for a strategy and return comprehensive results
    
    Request Body:
    {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "end_date": "2024-10-31",  // Optional, defaults to start_date
        "mode": "backtesting",
        "include_diagnostics": true  // Optional, defaults to true
    }
    
    Response includes:
    - Daily results with positions/transactions
    - Each transaction has diagnostic_text (formatted string)
    - Each transaction has full JSON data for UI rendering
    - Summary statistics per day and overall
    """
    try:
        # Parse dates
        try:
            start_dt = datetime.strptime(request.start_date, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use YYYY-MM-DD"
            )
        
        if request.end_date:
            try:
                end_dt = datetime.strptime(request.end_date, '%Y-%m-%d').date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )
        else:
            end_dt = start_dt
        
        # Validate date range
        if end_dt < start_dt:
            raise HTTPException(
                status_code=400,
                detail="end_date must be >= start_date"
            )
        
        # Calculate date range
        date_range = []
        current_date = start_dt
        while current_date <= end_dt:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # Run backtests for each date
        results = []
        overall_summary = {
            'total_positions': 0,
            'total_pnl': 0,
            'total_winning_trades': 0,
            'total_losing_trades': 0,
            'total_breakeven_trades': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'days_tested': len(date_range)
        }
        
        for test_date in date_range:
            print(f"[API] Running backtest for {test_date}")
            
            # Run backtest using UNIFIED ENGINE
            from src.backtesting.backtest_runner import run_backtest as unified_run_backtest
            
            # Run unified engine (note: not async, returns BacktestResults directly)
            unified_results = unified_run_backtest(
                strategy_ids=request.strategy_id,  # Accepts string or list
                backtest_date=test_date
            )
            
            # Convert unified engine results to dashboard format
            daily_data = {
                'strategy_id': request.strategy_id,
                'positions': unified_results.positions,
                'summary': {
                    'total_pnl': sum(p.get('pnl', 0) for p in unified_results.positions),
                    'total_positions': len(unified_results.positions),
                    'winning_trades': len([p for p in unified_results.positions if p.get('pnl', 0) > 0]),
                    'losing_trades': len([p for p in unified_results.positions if p.get('pnl', 0) < 0]),
                    'breakeven_trades': len([p for p in unified_results.positions if p.get('pnl', 0) == 0])
                }
            }
            
            # Generate diagnostic text for each transaction
            position_numbers = {}
            next_pos_num = 1
            
            for pos in daily_data['positions']:
                pos_id = pos['position_id']
                if pos_id not in position_numbers:
                    position_numbers[pos_id] = next_pos_num
                    next_pos_num += 1
                
                pos_num = position_numbers[pos_id]
                txn_num = pos.get('re_entry_num', 0) + 1
                
                # Generate diagnostic text if requested
                if request.include_diagnostics:
                    pos['diagnostic_text'] = generate_diagnostic_text(pos, pos_num, txn_num)
                
                # Add position/transaction numbers for UI reference
                pos['position_number'] = pos_num
                pos['transaction_number'] = txn_num
            
            # Add daily result
            results.append({
                'date': test_date.strftime('%Y-%m-%d'),
                'strategy_id': daily_data['strategy_id'],
                'positions': daily_data['positions'],
                'summary': daily_data['summary']
            })
            
            # Update overall summary
            overall_summary['total_positions'] += daily_data['summary']['total_positions']
            overall_summary['total_pnl'] += daily_data['summary']['total_pnl']
            overall_summary['total_winning_trades'] += daily_data['summary']['winning_trades']
            overall_summary['total_losing_trades'] += daily_data['summary']['losing_trades']
            overall_summary['total_breakeven_trades'] += daily_data['summary']['breakeven_trades']
            overall_summary['largest_win'] = max(overall_summary['largest_win'], daily_data['summary']['largest_win'])
            overall_summary['largest_loss'] = min(overall_summary['largest_loss'], daily_data['summary']['largest_loss'])
        
        # Calculate overall averages
        if overall_summary['total_winning_trades'] > 0:
            overall_summary['overall_win_rate'] = (overall_summary['total_winning_trades'] / overall_summary['total_positions'] * 100) if overall_summary['total_positions'] > 0 else 0
        else:
            overall_summary['overall_win_rate'] = 0
        
        # Generate UI files (trades_daily.json and diagnostics_export.json) for reference
        print("[API] Backtest complete. Generating UI files...")
        ui_files_generated = generate_ui_files_from_diagnostics()
        
        # Prepare response
        response_data = {
            'strategy_id': request.strategy_id,
            'date_range': {
                'start': request.start_date,
                'end': request.end_date or request.start_date
            },
            'mode': request.mode,
            'daily_results': results,
            'overall_summary': overall_summary,
            'metadata': {
                'total_days': len(date_range),
                'diagnostics_included': request.include_diagnostics,
                'generated_at': datetime.now().isoformat(),
                'ui_files_generated': ui_files_generated
            }
        }
        
        return BacktestResponse(
            success=True,
            data=response_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[API ERROR] {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/v1/backtest/stream")
async def stream_backtest(request: BacktestRequest):
    """
    Stream backtest results progressively (NDJSON format)
    
    Perfect for large date ranges (e.g., 1 year backtest)
    Results are streamed as they're generated - no need to wait for completion!
    
    Response Format: Newline-Delimited JSON (NDJSON)
    Each line is a complete JSON object:
    
    {"type": "metadata", "data": {...}}
    {"type": "day_start", "date": "2024-10-29"}
    {"type": "transaction", "data": {...}}
    {"type": "transaction", "data": {...}}
    {"type": "day_summary", "date": "2024-10-29", "summary": {...}}
    {"type": "day_start", "date": "2024-10-30"}
    ...
    {"type": "complete", "overall_summary": {...}}
    """
    async def generate_backtest_stream():
        try:
            # Parse dates
            try:
                start_dt = datetime.strptime(request.start_date, '%Y-%m-%d').date()
            except ValueError:
                error_msg = {"type": "error", "message": "Invalid start_date format. Use YYYY-MM-DD"}
                yield json.dumps(error_msg, cls=DateTimeEncoder) + "\n"
                return
            
            if request.end_date:
                try:
                    end_dt = datetime.strptime(request.end_date, '%Y-%m-%d').date()
                except ValueError:
                    error_msg = {"type": "error", "message": "Invalid end_date format. Use YYYY-MM-DD"}
                    yield json.dumps(error_msg, cls=DateTimeEncoder) + "\n"
                    return
            else:
                end_dt = start_dt
            
            # Validate date range
            if end_dt < start_dt:
                error_msg = {"type": "error", "message": "end_date must be >= start_date"}
                yield json.dumps(error_msg, cls=DateTimeEncoder) + "\n"
                return
            
            # Calculate date range
            date_range = []
            current_date = start_dt
            while current_date <= end_dt:
                date_range.append(current_date)
                current_date += timedelta(days=1)
            
            # Send metadata
            metadata = {
                "type": "metadata",
                "data": {
                    "strategy_id": request.strategy_id,
                    "start_date": request.start_date,
                    "end_date": request.end_date or request.start_date,
                    "total_days": len(date_range),
                    "include_diagnostics": request.include_diagnostics,
                    "started_at": datetime.now().isoformat()
                }
            }
            yield json.dumps(metadata, cls=DateTimeEncoder) + "\n"
            await asyncio.sleep(0)  # Allow other tasks to run
            
            # Initialize overall summary
            overall_summary = {
                'total_positions': 0,
                'total_pnl': 0,
                'total_winning_trades': 0,
                'total_losing_trades': 0,
                'total_breakeven_trades': 0,
                'largest_win': 0,
                'largest_loss': 0,
                'days_completed': 0
            }
            
            # Stream results for each date
            for idx, test_date in enumerate(date_range, 1):
                # Send day start event
                day_start = {
                    "type": "day_start",
                    "date": test_date.strftime('%Y-%m-%d'),
                    "day_number": idx,
                    "total_days": len(date_range)
                }
                yield json.dumps(day_start, cls=DateTimeEncoder) + "\n"
                await asyncio.sleep(0)
                
                try:
                    # Run backtest for this date
                    daily_data = run_dashboard_backtest(request.strategy_id, test_date, request.strategy_scale)
                    
                    # Track position numbers for this day
                    position_numbers = {}
                    next_pos_num = 1
                    
                    # Stream each transaction
                    for pos in daily_data['positions']:
                        pos_id = pos['position_id']
                        if pos_id not in position_numbers:
                            position_numbers[pos_id] = next_pos_num
                            next_pos_num += 1
                        
                        pos_num = position_numbers[pos_id]
                        txn_num = pos.get('re_entry_num', 0) + 1
                        
                        # Generate diagnostic text if requested
                        if request.include_diagnostics:
                            pos['diagnostic_text'] = generate_diagnostic_text(pos, pos_num, txn_num)
                        
                        # Add position/transaction numbers
                        pos['position_number'] = pos_num
                        pos['transaction_number'] = txn_num
                        
                        # Stream transaction
                        transaction_event = {
                            "type": "transaction",
                            "date": test_date.strftime('%Y-%m-%d'),
                            "data": pos
                        }
                        yield json.dumps(transaction_event, cls=DateTimeEncoder) + "\n"
                        await asyncio.sleep(0)  # Allow other tasks to run
                    
                    # Update overall summary
                    overall_summary['total_positions'] += daily_data['summary']['total_positions']
                    overall_summary['total_pnl'] += daily_data['summary']['total_pnl']
                    overall_summary['total_winning_trades'] += daily_data['summary']['winning_trades']
                    overall_summary['total_losing_trades'] += daily_data['summary']['losing_trades']
                    overall_summary['total_breakeven_trades'] += daily_data['summary']['breakeven_trades']
                    overall_summary['largest_win'] = max(overall_summary['largest_win'], daily_data['summary']['largest_win'])
                    overall_summary['largest_loss'] = min(overall_summary['largest_loss'], daily_data['summary']['largest_loss'])
                    overall_summary['days_completed'] += 1
                    
                    # Send day summary
                    day_summary = {
                        "type": "day_summary",
                        "date": test_date.strftime('%Y-%m-%d'),
                        "summary": daily_data['summary']
                    }
                    yield json.dumps(day_summary, cls=DateTimeEncoder) + "\n"
                    await asyncio.sleep(0)
                    
                except Exception as day_error:
                    # Send error for this specific day but continue
                    error_event = {
                        "type": "day_error",
                        "date": test_date.strftime('%Y-%m-%d'),
                        "error": str(day_error)
                    }
                    yield json.dumps(error_event, cls=DateTimeEncoder) + "\n"
                    await asyncio.sleep(0)
            
            # Calculate overall averages
            if overall_summary['total_positions'] > 0:
                overall_summary['overall_win_rate'] = (
                    overall_summary['total_winning_trades'] / overall_summary['total_positions'] * 100
                )
            else:
                overall_summary['overall_win_rate'] = 0
            
            # Generate UI files after completion
            print("[API] Stream complete. Generating UI files...")
            ui_files_generated = generate_ui_files_from_diagnostics()
            
            # Send completion event
            complete_event = {
                "type": "complete",
                "overall_summary": overall_summary,
                "completed_at": datetime.now().isoformat(),
                "ui_files_generated": ui_files_generated
            }
            yield json.dumps(complete_event, cls=DateTimeEncoder) + "\n"
            
        except Exception as e:
            import traceback
            error_event = {
                "type": "fatal_error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            yield json.dumps(error_event, cls=DateTimeEncoder) + "\n"
    
    return StreamingResponse(
        generate_backtest_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )

@app.get("/api/v1/backtest/status")
async def get_backtest_status():
    """Get status of backtest service"""
    return {
        "status": "ready",
        "available_modes": ["backtesting", "live_simulation"],
        "features": {
            "single_day": True,
            "multi_day": True,
            "diagnostic_text": True,
            "compression": True,
            "streaming": True,
            "live_simulation": True,
            "ui_files_generation": True
        }
    }

# ============================================================================
# LIVE SIMULATION ENDPOINTS (SSE) - NEW IMPLEMENTATION
# ============================================================================

class LiveSimulationRequest(BaseModel):
    """Request model for starting a live simulation with SSE"""
    user_id: str = Field(..., description="User UUID")
    strategy_id: str = Field(..., description="Strategy UUID")
    broker_connection_id: str = Field(..., description="Broker connection UUID to fetch metadata from Supabase")
    speed_multiplier: float = Field(5000.0, description="Speed multiplier (1.0=real-time, 5000.0=5000x faster)")
    initial_capital: float = Field(100000.0, description="Initial capital for the simulation")

class LiveSimulationSSEState(BaseModel):
    """Live simulation state for SSE updates"""
    timestamp: str
    status: str  # 'starting', 'running', 'paused', 'completed', 'error'
    progress: float  # 0-100
    current_time: str  # Current simulated time
    positions: List[Dict[str, Any]] = []
    pnl: Dict[str, Any] = {}
    indicators: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []

async def live_simulation_generator(session_id: str):
    """Generator function for SSE events"""
    try:
        # Get the simulation state
        session = active_sessions.get(session_id)
        if not session:
            yield {"event": "error", "data": json.dumps({"error": "Session not found"}, cls=DateTimeEncoder)}
            return

        # Send initial state
        state = {
            "event": "state",
            "data": json.dumps({
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "status": "starting",
                "progress": 0.0,
                "current_time": session.get("current_time", ""),
                "positions": [],
                "pnl": {},
                "indicators": {}
            })
        }
        yield state

        # Simulate updates (in a real implementation, this would be connected to the actual simulation)
        while session["status"] in ["starting", "running"]:
            await asyncio.sleep(1.0 / session.get("speed_multiplier", 1.0))
            
            # Get updated state (in a real implementation, this would come from the simulation)
            state = {
                "event": "state",
                "data": json.dumps({
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "status": session["status"],
                    "progress": session.get("progress", 0.0),
                    "current_time": session.get("current_time", ""),
                    "positions": session.get("positions", []),
                    "pnl": session.get("pnl", {}),
                    "indicators": session.get("indicators", {})
                })
            }
            yield state
            
            # Send events if any
            while session.get("events"):
                event = session["events"].pop(0)
                yield {
                    "event": "event",
                    "data": json.dumps({
                        "type": event.get("type"),
                        "timestamp": datetime.now().isoformat(),
                        "data": event.get("data", {})
                    })
                }
                
    except asyncio.CancelledError:
        # Client disconnected
        if session_id in active_sse_connections:
            del active_sse_connections[session_id]
        raise
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }

@app.post("/api/v1/live/start", response_model=Dict[str, Any])
async def start_live_simulation_sse(request: LiveSimulationRequest):
    """
    Start a new live simulation with SSE streaming (UI endpoint)
    
    Fetches broker metadata from Supabase broker_connections table.
    Launches actual CentralizedBacktestEngine as background task.
    Returns session ID for SSE stream connection.
    
    This is the primary endpoint used by the UI.
    """
    try:
        # Fetch broker connection metadata from Supabase
        broker_response = supabase.table('broker_connections').select('broker_metadata').eq('id', request.broker_connection_id).execute()
        
        if not broker_response.data or len(broker_response.data) == 0:
            raise HTTPException(status_code=404, detail=f"Broker connection {request.broker_connection_id} not found")
        
        # Parse broker_metadata JSON string
        broker_metadata_str = broker_response.data[0].get('broker_metadata', '{}')
        broker_metadata = json.loads(broker_metadata_str) if isinstance(broker_metadata_str, str) else broker_metadata_str
        
        # Extract simulation parameters from broker_metadata
        start_date = broker_metadata.get('simulation_date', datetime.now().strftime('%Y-%m-%d'))
        metadata_speed = broker_metadata.get('speed_multiplier', 1.0)
        broker_type = broker_metadata.get('type', 'unknown')
        
        # Generate session ID
        session_id = f"sim-{os.urandom(8).hex()}"
        
        # Create session in sse_manager (real backtest data)
        session = sse_manager.create_session(
            session_id=session_id,
            strategy_id=request.strategy_id,
            user_id=request.user_id,
            start_date=start_date
        )
        
        # Store metadata
        session.status = "initializing"
        session.broker_connection_id = request.broker_connection_id
        session.broker_metadata = broker_metadata
        session.broker_type = broker_type
        session.speed_multiplier = request.speed_multiplier or metadata_speed
        
        # Launch actual backtest as background task
        asyncio.create_task(
            run_live_backtest(
                session_id=session_id,
                strategy_id=request.strategy_id,
                user_id=request.user_id,
                start_date=start_date,
                speed_multiplier=session.speed_multiplier
            )
        )
        
        print(f"[API v1] Started live backtest for session {session_id}")
        print(f"[API v1] Strategy: {request.strategy_id}")
        print(f"[API v1] Date: {start_date}")
        print(f"[API v1] Speed: {session.speed_multiplier}x")
        
        return {
            "session_id": session_id,
            "stream_url": f"/api/live-trading/stream/{request.user_id}",
            "status": "initializing"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/live/stream/{session_id}")
async def stream_live_simulation(session_id: str):
    """
    SSE stream for live simulation updates
    
    Connect to this endpoint using EventSource to receive real-time updates
    about the simulation progress, including positions, P&L, and indicators.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    response = EventSourceResponse(
        live_simulation_generator(session_id),
        media_type="text/event-stream"
    )
    
    # Set headers for SSE
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # Disable buffering in Nginx
    
    # Store the connection
    active_sse_connections[session_id] = response
    
    return response

@app.get("/api/live-trading/strategies/{user_id}")
async def get_user_strategies(user_id: str):
    """
    Get all strategies for a user from Supabase.
    Returns strategies with queue toggle flags for READY cards.
    This is used to populate the strategy grid with READY status cards.
    """
    try:
        # Fetch user's strategies from Supabase
        strategies_response = supabase.table('strategies').select('*').eq('user_id', user_id).execute()
        
        if not strategies_response.data:
            return {
                "total_strategies": 0,
                "strategies": []
            }
        
        strategies_list = []
        
        for strategy in strategies_response.data:
            strategy_id = strategy['id']
            
            # Check if strategy is currently in admin_tester queue
            is_queued = strategy_id in strategy_queues.get('admin_tester', {})
            
            # Check if there's an active session for this strategy
            active_session = None
            for session_id, session in sse_manager.sessions.items():
                if session.strategy_id == strategy_id and session.status not in ["completed", "stopped", "error"]:
                    active_session = session
                    break
            
            # Determine status
            if active_session:
                status = active_session.status
                show_queue_toggle = status in ["ready", "starting"]
            else:
                status = "ready"  # Default status for strategies without active sessions
                show_queue_toggle = True  # Always show queue toggle for READY cards
            
            strategies_list.append({
                "strategy_id": strategy_id,
                "strategy_name": strategy.get('name', 'Unnamed Strategy'),
                "status": status,
                "show_queue_toggle": show_queue_toggle,
                "is_queued": is_queued,
                "has_trades": True,  # Always show View Trades button
                "created_at": strategy.get('created_at'),
                "updated_at": strategy.get('updated_at')
            })
        
        return {
            "total_strategies": len(strategies_list),
            "strategies": strategies_list
        }
        
    except Exception as e:
        print(f"[API ERROR] Error fetching strategies: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "total_strategies": 0,
            "strategies": []
        }

@app.post("/api/strategies/clone/{strategy_id}")
async def clone_strategy(strategy_id: str):
    """
    Clone a strategy by creating a duplicate in Supabase.
    Returns the new strategy ID.
    """
    try:
        # Fetch original strategy from Supabase
        strategy_response = supabase.table('strategies').select('*').eq('id', strategy_id).execute()
        
        if not strategy_response.data or len(strategy_response.data) == 0:
            return {"success": False, "error": "Strategy not found"}
        
        original_strategy = strategy_response.data[0]
        
        # Create clone with modified name - only copy columns that exist
        cloned_strategy = {
            "user_id": original_strategy['user_id'],
            "name": f"{original_strategy['name']} (Copy)",
        }
        
        # Copy optional fields if they exist
        if 'description' in original_strategy:
            cloned_strategy['description'] = original_strategy['description']
        
        # Insert cloned strategy
        insert_response = supabase.table('strategies').insert(cloned_strategy).execute()
        
        if not insert_response.data:
            return {"success": False, "error": "Failed to clone strategy"}
        
        new_strategy = insert_response.data[0]
        
        return {
            "success": True,
            "strategy_id": new_strategy['id'],
            "strategy_name": new_strategy['name']
        }
        
    except Exception as e:
        print(f"[API ERROR] Error cloning strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.get("/api/live-trading/dashboard/{user_id}")
async def get_live_trading_dashboard(user_id: str):
    """
    Get live trading dashboard for a user.
    Returns ONLY active/running simulation sessions with their current state.
    Completed/stopped sessions are excluded.
    Reads from sse_manager (real simulation data).
    """
    try:
        # Filter sessions by user_id from sse_manager - ONLY active sessions
        user_sessions = {}
        active_count = 0
        
        for session_id, session in sse_manager.sessions.items():
            if session.user_id == user_id:
                # Include all sessions: ready, starting, running (exclude only completed/stopped)
                if session.status in ["completed", "stopped", "error"]:
                    continue  # Skip completed/stopped/error sessions
                
                if session.status == "running":
                    active_count += 1
                
                # Fetch strategy name from Supabase
                try:
                    strategy_response = supabase.table('strategies').select('name').eq('id', session.strategy_id).execute()
                    strategy_name = strategy_response.data[0]['name'] if strategy_response.data else "Unknown Strategy"
                except:
                    strategy_name = "Unknown Strategy"
                
                # Get broker type from session
                broker_type = getattr(session, 'broker_type', 'unknown')
                broker_connection_id = getattr(session, 'broker_connection_id', '')
                
                # Extract real-time data from tick_state
                tick_state = session.tick_state
                
                # Always show View Trades button on strategy cards
                # Button will be enabled regardless of status or whether trades exist
                # This allows users to view historical data or empty state message
                trades_list = session.trades.get("trades", [])
                has_trades = True  # Always show button
                
                # Check if strategy should show queue toggle (READY/starting status)
                show_queue_toggle = session.status in ["ready", "starting"]
                
                # Check if strategy is currently in admin_tester queue
                is_queued = session.strategy_id in strategy_queues.get('admin_tester', {})
                
                # Build session response with REAL data
                user_sessions[session_id] = {
                    "session_id": session_id,
                    "strategy_name": strategy_name,
                    "broker_info": {
                        "broker_type": broker_type,
                        "account_id": broker_connection_id
                    },
                    "status": session.status,
                    "has_trades": has_trades,  # Flag for UI to show View Trades button
                    "show_queue_toggle": show_queue_toggle,  # Flag to show queue toggle checkbox
                    "is_queued": is_queued,  # Flag indicating if currently in queue
                    "data": {
                        "timestamp": tick_state.get("timestamp", datetime.now().isoformat()),
                        "is_fresh": session.status == "running",
                        "gps_data": {
                            "positions": tick_state.get("open_positions", []),
                            "trades": trades_list,
                            "pnl": tick_state.get("pnl_summary", {
                                "realized_pnl": "0.00",
                                "unrealized_pnl": "0.00",
                                "total_pnl": "0.00",
                                "closed_trades": 0,
                                "open_trades": 0
                            })
                        },
                        "broker_data": {
                            "orders": [],
                            "account_info": {
                                "available_margin": 0.0,
                                "used_margin": 0.0,
                                "total_value": 0.0
                            }
                        },
                        "market_data": {
                            "ltp_store": tick_state.get("ltp_store", {}),
                            "candle_data": tick_state.get("candle_data", {})
                        }
                    }
                }
        
        # Build response
        response = {
            "total_sessions": len(user_sessions),
            "active_sessions": active_count,
            "cache_time": datetime.now().isoformat() + "Z",
            "sessions": user_sessions
        }
        
        return response
        
    except Exception as e:
        print(f"[API ERROR] Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty dashboard on error
        return {
            "total_sessions": 0,
            "active_sessions": 0,
            "cache_time": datetime.now().isoformat() + "Z",
            "sessions": {}
        }

class StopSessionRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to stop")
    square_off: bool = Field(False, description="Whether to square off positions before stopping")
    user_id: str = Field(..., description="User ID for validation")

@app.get("/api/live-trading/session/{session_id}")
async def get_live_trading_session(session_id: str):
    """
    Get detailed data for a specific live trading session.
    Used for: session detail page, single card refresh, direct URL access.
    Reads from sse_manager (real simulation data).
    """
    # Check if session exists in sse_manager
    session = sse_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Fetch strategy name from Supabase
        try:
            strategy_response = supabase.table('strategies').select('name').eq('id', session.strategy_id).execute()
            strategy_name = strategy_response.data[0]['name'] if strategy_response.data else "Unknown Strategy"
        except:
            strategy_name = "Unknown Strategy"
        
        # Get broker type from session
        broker_type = getattr(session, 'broker_type', 'unknown')
        broker_connection_id = getattr(session, 'broker_connection_id', '')
        
        # Extract real-time data from tick_state
        tick_state = session.tick_state
        
        # Build response matching frontend LiveSessionData type with REAL data
        return {
            "session_id": session_id,
            "strategy_name": strategy_name,
            "broker_info": {
                "broker_type": broker_type,
                "account_id": broker_connection_id
            },
            "status": session.status,
            "data": {
                "timestamp": tick_state.get("timestamp", datetime.now().isoformat()),
                "is_fresh": session.status == "running",
                "gps_data": {
                    "positions": tick_state.get("open_positions", []),
                    "trades": session.trades.get("trades", []),
                    "pnl": tick_state.get("pnl_summary", {
                        "realized_pnl": "0.00",
                        "unrealized_pnl": "0.00",
                        "total_pnl": "0.00",
                        "closed_trades": 0,
                        "open_trades": 0
                    })
                },
                "broker_data": {
                    "orders": [],
                    "account_info": {
                        "available_margin": 0.0,
                        "used_margin": 0.0,
                        "total_value": 0.0
                    }
                },
                "market_data": {
                    "ltp_store": tick_state.get("ltp_store", {}),
                    "candle_data": tick_state.get("candle_data", {})
                }
            }
        }
        
    except Exception as e:
        print(f"[API ERROR] Session fetch error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live-trading/session/stop")
async def stop_live_trading_session(request: StopSessionRequest):
    """
    Stop a live trading session (UI-compatible endpoint).
    
    Accepts body: {session_id, square_off, user_id}
    Used by frontend to stop individual strategy sessions.
    """
    session = sse_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate user owns this session
    if session.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to stop this session")
    
    # Mark as stopped
    session.status = "stopped"
    
    # Clear event queue
    while not session.event_queue.empty():
        try:
            session.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
    
    # Brief delay for cleanup
    await asyncio.sleep(0.3)
    
    # Remove session
    sse_manager.remove_session(request.session_id)
    
    return {
        "success": True,
        "session_id": request.session_id,
        "status": "stopped",
        "message": "Session stopped successfully"
    }

@app.post("/api/v1/live/stop/{session_id}", response_model=Dict[str, Any])
async def stop_live_simulation_sse(session_id: str):
    """Stop a running live simulation"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session status
    session = active_sessions[session_id]
    session["status"] = "stopping"
    session["last_updated"] = datetime.now().isoformat()
    
    # In a real implementation, you would signal the simulation to stop
    # and wait for it to clean up
    
    # After a short delay, mark as stopped
    await asyncio.sleep(1)
    session["status"] = "stopped"
    session["last_updated"] = datetime.now().isoformat()
    
    # Clean up SSE connection if it exists
    if session_id in active_sse_connections:
        await active_sse_connections[session_id].stop_streaming()
        del active_sse_connections[session_id]
    
    return {"session_id": session_id, "status": "stopped"}

# ============================================================================
# LEGACY LIVE SIMULATION ENDPOINTS (POLLING)
# ============================================================================

class SimulationStartRequest(BaseModel):
    user_id: str = Field(..., description="User UUID")
    strategy_id: str = Field(..., description="Strategy UUID")
    start_date: str = Field(..., description="Simulation date in YYYY-MM-DD format")
    mode: str = Field("live", description="Mode (live for simulation)")
    broker_connection_id: str = Field("clickhouse", description="Data source (clickhouse for now)")
    speed_multiplier: float = Field(5000.0, description="Speed multiplier (1.0=real-time, 5000.0=5000x faster)")


@app.post("/api/v1/simulation/start")
async def start_live_simulation(request: SimulationStartRequest):
    """
    Start live simulation with per-second state tracking.
    
    Returns session_id for polling state updates.
    
    Request:
    {
      "user_id": "user_xxx",
      "strategy_id": "strategy_xxx",
      "start_date": "2024-10-29",
      "mode": "live",
      "broker_connection_id": "clickhouse",
      "speed_multiplier": 1.0
    }
    
    Response:
    {
      "session_id": "sim-abc123",
      "status": "running",
      "poll_url": "/api/v1/simulation/sim-abc123/state"
    }
    """
    try:
        from src.backtesting.live_simulation_session import LiveSimulationSession
        
        # Create session
        session_id = LiveSimulationSession.create_session(
            user_id=request.user_id,
            strategy_id=request.strategy_id,
            backtest_date=request.start_date,
            speed_multiplier=request.speed_multiplier
        )
        
        # Get session
        session = LiveSimulationSession.get_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        # Start simulation in background
        session.start_simulation()
        
        return {
            "session_id": session_id,
            "user_id": request.user_id,
            "strategy_id": request.strategy_id,
            "start_date": request.start_date,
            "status": "running",
            "speed_multiplier": request.speed_multiplier,
            "poll_url": f"/api/v1/simulation/{session_id}/state",
            "stop_url": f"/api/v1/simulation/{session_id}/stop"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start simulation: {str(e)}"
        )


@app.get("/api/v1/simulation/{session_id}/state")
async def get_simulation_state(session_id: str):
    """
    Get current state of running simulation (poll this every 1 second).
    
    Response:
    {
      "session_id": "sim-abc123",
      "status": "running",
      "timestamp": "2024-10-29T10:15:23+05:30",
      "progress_percentage": 15.2,
      
      "active_nodes": [
        {
          "node_id": "entry-2",
          "node_type": "EntryNode",
          "status": "Active"
        }
      ],
      
      "latest_candles": {
        "NIFTY": {
          "1m": {
            "current": {...},
            "previous": {...}
          }
        }
      },
      
      "ltp_store": {
        "NIFTY": {"ltp": 24145.0},
        "NIFTY:2024-11-07:OPT:24250:PE": {"ltp": 260.05}
      },
      
      "open_positions": [
        {
          "position_id": "entry-2-pos1",
          "symbol": "NIFTY:2024-11-07:OPT:24250:PE",
          "entry_price": 181.6,
          "current_ltp": 260.05,
          "unrealized_pnl": -78.45
        }
      ],
      
      "total_unrealized_pnl": -78.45,
      
      "stats": {
        "ticks_processed": 25000,
        "total_ticks": 165000,
        "progress_percentage": 15.2
      }
    }
    """
    try:
        from src.backtesting.live_simulation_session import LiveSimulationSession
        
        session = LiveSimulationSession.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get current state
        state = session.get_current_state()
        
        return state
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get simulation state: {str(e)}"
        )


@app.post("/api/v1/simulation/{session_id}/stop")
async def stop_simulation(session_id: str):
    """
    Stop running simulation.
    
    Response:
    {
      "session_id": "sim-abc123",
      "status": "stopped"
    }
    """
    try:
        from src.backtesting.live_simulation_session import LiveSimulationSession
        
        session = LiveSimulationSession.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Stop simulation
        session.stop()
        
        return {
            "session_id": session_id,
            "status": "stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop simulation: {str(e)}"
        )


@app.get("/api/v1/simulation/sessions")
async def list_active_sessions():
    """
    List all active simulation sessions.
    
    Response:
    {
      "sessions": [
        {
          "session_id": "sim-abc123",
          "user_id": "user_xxx",
          "strategy_id": "strategy_xxx",
          "status": "running",
          "progress_percentage": 15.2
        }
      ]
    }
    """
    try:
        from src.backtesting.live_simulation_session import LiveSimulationSession
        
        sessions = LiveSimulationSession.list_sessions()
        
        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "strategy_id": s.strategy_id,
                    "backtest_date": s.backtest_date,
                    "status": s.status,
                    "speed_multiplier": s.speed_multiplier,
                    "progress_percentage": s.latest_state.get('stats', {}).get('progress_percentage', 0)
                }
                for s in sessions
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


# ============================================================================
# NEW SSE-BASED BACKTEST ENDPOINTS
# ============================================================================

class BacktestStartRequest(BaseModel):
    strategy_id: str = Field(..., description="Strategy UUID")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    initial_capital: Optional[float] = Field(100000, description="Initial capital")
    slippage_percentage: Optional[float] = Field(0.05, description="Slippage percentage")
    commission_percentage: Optional[float] = Field(0.01, description="Commission percentage")
    strategy_scale: Optional[float] = Field(1.0, description="Strategy scaling factor (multiplies all position quantities)")

@app.post("/api/v1/backtest/start")
async def start_backtest(request: BacktestStartRequest):
    """
    Start a backtest and return backtest_id immediately.
    Use the stream endpoint to monitor progress.
    
    Returns:
    {
        "backtest_id": "strategy_id_start_end",
        "total_days": 8,
        "status": "ready",
        "stream_url": "/api/v1/backtest/{id}/stream"
    }
    """
    try:
        # Validate dates
        try:
            start_dt = datetime.strptime(request.start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(request.end_date, '%Y-%m-%d').date()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        if end_dt < start_dt:
            raise HTTPException(status_code=400, detail="end_date must be >= start_date")
        
        # Calculate total days
        date_range = []
        current_date = start_dt
        while current_date <= end_dt:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        total_days = len(date_range)
        
        # Create backtest_id
        backtest_id = create_backtest_id(
            request.strategy_id,
            request.start_date,
            request.end_date
        )
        
        print(f"[API] Backtest started: {backtest_id} ({total_days} days)")
        
        return {
            "backtest_id": backtest_id,
            "total_days": total_days,
            "status": "ready",
            "stream_url": f"/api/v1/backtest/{backtest_id}/stream"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start backtest: {str(e)}")

@app.get("/api/v1/backtest/{backtest_id}/stream")
async def stream_backtest_progress(backtest_id: str):
    """
    Server-Sent Events stream for backtest progress.
    
    Events:
    - day_started: {"date": "2024-10-24", "day_number": 1}
    - day_completed: {"date": "2024-10-24", "summary": {...}}
    - backtest_completed: {"overall_summary": {...}}
    - error: {"message": "..."}
    """
    async def event_generator():
        # Parse backtest_id
        strategy_id, start_date, end_date = parse_backtest_id(backtest_id)
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Calculate date range
        date_range = []
        current_date = start_dt
        while current_date <= end_dt:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        total_days = len(date_range)
        
        # TODO: Extract strategy_scale from stored metadata when backtest is started
        # For now, default to 1.0
        strategy_scale = 1.0
        
        # Overall tracking
        overall_summary = {
            'total_positions': 0,
            'total_pnl': 0,
            'total_winning_trades': 0,
            'total_losing_trades': 0,
            'total_breakeven_trades': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'days_tested': total_days
        }
        
        # Process each day
        for idx, test_date in enumerate(date_range, 1):
            # Send day_started event
            yield {
                "event": "day_started",
                "data": json.dumps({
                    "date": test_date.strftime('%Y-%m-%d'),
                    "day_number": idx,
                    "total_days": total_days
                })
            }
            
            await asyncio.sleep(0)  # Allow other tasks
            
            print(f"[API] Processing day {idx}/{total_days}: {test_date}")
            
            # Run backtest for this day (no exception handling - let errors propagate)
            daily_data = run_dashboard_backtest(strategy_id, test_date, strategy_scale)
            
            # Save files to disk for view trades functionality
            save_daily_files(strategy_id, test_date.strftime('%Y-%m-%d'), daily_data)
            
            # Update overall summary
            overall_summary['total_positions'] += daily_data['summary']['total_positions']
            overall_summary['total_pnl'] += daily_data['summary']['total_pnl']
            overall_summary['total_winning_trades'] += daily_data['summary']['winning_trades']
            overall_summary['total_losing_trades'] += daily_data['summary']['losing_trades']
            overall_summary['total_breakeven_trades'] += daily_data['summary']['breakeven_trades']
            overall_summary['largest_win'] = max(overall_summary['largest_win'], daily_data['summary']['largest_win'])
            overall_summary['largest_loss'] = min(overall_summary['largest_loss'], daily_data['summary']['largest_loss'])
            
            # Send day_completed event with summary only
            yield {
                "event": "day_completed",
                "data": json.dumps({
                    "date": test_date.strftime('%Y-%m-%d'),
                    "day_number": idx,
                    "total_days": total_days,
                    "summary": {
                        "total_trades": daily_data['summary']['total_positions'],
                        "total_pnl": f"{daily_data['summary']['total_pnl']:.2f}",
                        "winning_trades": daily_data['summary']['winning_trades'],
                        "losing_trades": daily_data['summary']['losing_trades'],
                        "win_rate": f"{daily_data['summary']['win_rate']:.2f}"
                    },
                    "has_detail_data": True
                })
            }
            
            await asyncio.sleep(0)
        
        # Calculate overall averages
        if overall_summary['total_winning_trades'] > 0:
            overall_summary['overall_win_rate'] = (
                overall_summary['total_winning_trades'] / overall_summary['total_positions'] * 100
            ) if overall_summary['total_positions'] > 0 else 0
        else:
            overall_summary['overall_win_rate'] = 0
        
        # Send completion event
        yield {
            "event": "backtest_completed",
            "data": json.dumps({
                "backtest_id": backtest_id,
                "overall_summary": {
                    "total_days": overall_summary['days_tested'],
                    "total_trades": overall_summary['total_positions'],
                    "total_pnl": f"{overall_summary['total_pnl']:.2f}",
                    "win_rate": f"{overall_summary['overall_win_rate']:.2f}",
                    "largest_win": f"{overall_summary['largest_win']:.2f}",
                    "largest_loss": f"{overall_summary['largest_loss']:.2f}"
                }
            }, cls=DateTimeEncoder)
        }
        
        print(f"[API] Backtest complete: {backtest_id}")
    
    return EventSourceResponse(event_generator())

@app.get("/api/v1/backtest/{backtest_id}/day/{date}")
async def download_day_details(backtest_id: str, date: str):
    """
    Download detailed trades and diagnostics for a specific day as ZIP file.
    
    Returns: ZIP containing:
    - trades_daily.json.gz
    - diagnostics_export.json.gz
    """
    try:
        # Parse backtest_id to get strategy_id
        strategy_id, _, _ = parse_backtest_id(backtest_id)
        
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get day directory
        day_dir = get_day_dir(strategy_id, date)
        
        # Check if files exist
        trades_file = f"{day_dir}/trades_daily.json.gz"
        diagnostics_file = f"{day_dir}/diagnostics_export.json.gz"
        
        if not os.path.exists(trades_file) or not os.path.exists(diagnostics_file):
            raise HTTPException(
                status_code=404,
                detail=f"Data not found for {date}. Run backtest first."
            )
        
        # Create ZIP in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(trades_file, 'trades_daily.json.gz')
            zf.write(diagnostics_file, 'diagnostics_export.json.gz')
        
        zip_buffer.seek(0)
        
        print(f"[API] Downloaded day details: {date}")
        
        return StreamingResponse(
            zip_buffer,
            media_type='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename=backtest_{date}.zip'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[API ERROR] Download failed: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download day details: {str(e)}"
        )


# ============================================================================
# LIVE SIMULATION V2 ENDPOINTS (Exact Backtest JSON Structure)
# ============================================================================

class LiveSimulationRequestV2(BaseModel):
    """Request for V2 live simulation with exact backtest JSON structure"""
    user_id: str = Field(..., description="User UUID")
    strategy_id: str = Field(..., description="Strategy UUID")
    broker_connection_id: str = Field(..., description="Broker connection UUID to fetch metadata from Supabase")
    speed_multiplier: float = Field(1.0, description="Speed multiplier")

@app.post("/api/v2/live/start")
async def start_live_simulation_v2(request: LiveSimulationRequestV2):
    """
    Start live simulation with SSE (V2 - Actual backtest execution)
    
    Fetches broker metadata from Supabase broker_connections table.
    Launches CentralizedBacktestEngine as background task.
    Returns session_id for connecting to SSE stream.
    Events: initial_state, node_events (gzip), trade_update (gzip), tick_update
    """
    try:
        # Fetch broker connection metadata from Supabase
        broker_response = supabase.table('broker_connections').select('broker_metadata').eq('id', request.broker_connection_id).execute()
        
        if not broker_response.data or len(broker_response.data) == 0:
            raise HTTPException(status_code=404, detail=f"Broker connection {request.broker_connection_id} not found")
        
        # Parse broker_metadata JSON string
        broker_metadata_str = broker_response.data[0].get('broker_metadata', '{}')
        broker_metadata = json.loads(broker_metadata_str) if isinstance(broker_metadata_str, str) else broker_metadata_str
        
        # Extract simulation parameters from broker_metadata
        start_date = broker_metadata.get('simulation_date', datetime.now().strftime('%Y-%m-%d'))
        metadata_speed = broker_metadata.get('speed_multiplier', 1.0)
        broker_type = broker_metadata.get('type', 'unknown')
        
        # Create session
        session_id = f"sim-{os.urandom(8).hex()}"
        session = sse_manager.create_session(
            session_id=session_id,
            strategy_id=request.strategy_id,
            user_id=request.user_id,
            start_date=start_date
        )
        
        # Store metadata (don't mark as running yet - backtest will do that)
        session.status = "initializing"
        session.broker_connection_id = request.broker_connection_id
        session.broker_metadata = broker_metadata
        session.broker_type = broker_type
        session.speed_multiplier = request.speed_multiplier or metadata_speed
        
        # Launch backtest as background task
        asyncio.create_task(
            run_live_backtest(
                session_id=session_id,
                strategy_id=request.strategy_id,
                user_id=request.user_id,
                start_date=start_date,
                speed_multiplier=session.speed_multiplier
            )
        )
        
        print(f"[API] Started live backtest for session {session_id}")
        print(f"[API] Strategy: {request.strategy_id}")
        print(f"[API] Date: {start_date}")
        print(f"[API] Speed: {session.speed_multiplier}x")
        
        return {
            "session_id": session_id,
            "stream_url": f"/api/v2/live/stream/{session_id}",
            "status": "initializing"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v2/live/stream/{session_id}")
async def stream_live_simulation_v2(session_id: str):
    """
    SSE stream for live simulation (V2)
    
    Events emitted:
    - initial_state: Full diagnostics + trades (gzip compressed)
    - node_events: Node execution events (gzip compressed)
    - trade_update: Trade updates (gzip compressed)  
    - tick_update: Per-tick updates (uncompressed)
    - heartbeat: Keep-alive
    """
    session = sse_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return EventSourceResponse(
        sse_manager.stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/live-trading/stream/{user_id}")
async def stream_user_sessions(user_id: str):
    """
    User-level SSE stream - aggregates events from all user's strategies.
    
    Events emitted (with session_id included):
    - initial_state: Full diagnostics + trades for all user sessions (gzip compressed)
    - node_events: Node execution events per session (gzip compressed)
    - trade_update: Trade updates per session (gzip compressed)  
    - tick_update: Per-tick updates per session (includes P&L, LTP store, candles)
    - heartbeat: Keep-alive every 30s if idle
    """
    async def user_event_generator():
        try:
            # Get all sessions for this user
            user_sessions = {
                sid: session for sid, session in sse_manager.sessions.items()
                if session.user_id == user_id
            }
            
            if not user_sessions:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": "No active sessions for user"}, cls=DateTimeEncoder)
                }
                return
            
            # Send initial state for all user's sessions
            for session_id, session in user_sessions.items():
                yield {
                    "event": "initial_state",
                    "data": json.dumps({
                        "session_id": session_id,
                        "strategy_id": session.strategy_id,
                        "diagnostics": session.diagnostics,
                        "trades": session.trades
                    }, cls=DateTimeEncoder)
                }
            
            # Stream events from all user's sessions
            last_heartbeat = asyncio.get_event_loop().time()
            
            while True:
                # Refresh user sessions (in case new ones started)
                user_sessions = {
                    sid: session for sid, session in sse_manager.sessions.items()
                    if session.user_id == user_id
                }
                
                if not user_sessions:
                    break
                
                # Check for events from any of user's sessions
                events_emitted = False
                for session_id, session in user_sessions.items():
                    try:
                        event = await asyncio.wait_for(session.event_queue.get(), timeout=0.1)
                        event_type = event.get("type")
                        event_data = event.get("data")
                        
                        # Debug: Print event type being processed
                        # print(f"[SSE] Processing event: {event_type}")
                        
                        if event_type == "node_events":
                            yield {
                                "event": "node_events",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "diagnostics": event_data
                                }, cls=DateTimeEncoder)
                            }
                            events_emitted = True
                        
                        elif event["type"] == "trade_update":
                            yield {
                                "event": "trade_update",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "trades": event_data
                                }, cls=DateTimeEncoder)
                            }
                            events_emitted = True
                        
                        elif event["type"] == "tick_update":
                            yield {
                                "event": "tick_update",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "tick_state": event_data
                                }, cls=DateTimeEncoder)
                            }
                            events_emitted = True
                        
                        elif event["type"] == "trade_closed":
                            yield {
                                "event": "trade_closed",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "trade": event_data
                                }, cls=DateTimeEncoder)
                            }
                            events_emitted = True
                        
                        elif event["type"] == "diagnostics_snapshot":
                            # Full diagnostics snapshot (same format as backtest)
                            # Sent when nodes complete or on client request
                            yield {
                                "event": "diagnostics_snapshot",
                                "data": json.dumps({
                                    "session_id": session_id,
                                    "diagnostics": event_data.get("diagnostics", {}, cls=DateTimeEncoder),
                                    "trades": event_data.get("trades", {})
                                }, cls=DateTimeEncoder)
                            }
                            events_emitted = True
                    
                    except asyncio.TimeoutError:
                        continue
                
                # Send heartbeat if no events in 30s
                current_time = asyncio.get_event_loop().time()
                if not events_emitted and (current_time - last_heartbeat) > 30:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.now().isoformat()})
                    }
                    last_heartbeat = current_time
                
                await asyncio.sleep(0.01)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e, cls=DateTimeEncoder)})
            }
    
    return EventSourceResponse(
        user_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/v2/live/stop/{session_id}")
async def stop_live_simulation_v2(session_id: str):
    """
    Stop a single live simulation session.
    
    This will:
    - Mark session as stopped
    - Clear event queue
    - Remove session from manager
    - Close any active SSE connections
    
    Returns:
        {"session_id": str, "status": "stopped"}
    """
    session = sse_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Mark as stopped
    session.status = "stopped"
    
    # Clear event queue to stop streaming
    while not session.event_queue.empty():
        try:
            session.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
    
    # Brief delay for cleanup
    await asyncio.sleep(0.5)
    
    # Remove session
    sse_manager.remove_session(session_id)
    
    return {
        "session_id": session_id,
        "status": "stopped",
        "message": "Session stopped successfully"
    }


@app.post("/api/v2/live/stop/user/{user_id}")
async def stop_user_sessions(user_id: str):
    """
    Stop all live simulation sessions for a specific user.
    
    Use this to:
    - Stop all user's strategies at once
    - Clean up when user logs out
    - Emergency stop for user account
    
    Returns:
        {
            "user_id": str,
            "sessions_stopped": int,
            "stopped_sessions": [session_id, ...]
        }
    """
    # Find all user sessions
    user_sessions = [
        session_id for session_id, session in sse_manager.sessions.items()
        if session.user_id == user_id
    ]
    
    if not user_sessions:
        return {
            "user_id": user_id,
            "sessions_stopped": 0,
            "stopped_sessions": [],
            "message": "No active sessions found for this user"
        }
    
    # Stop each session
    stopped_sessions = []
    for session_id in user_sessions:
        session = sse_manager.get_session(session_id)
        if session:
            session.status = "stopped"
            
            # Clear event queue
            while not session.event_queue.empty():
                try:
                    session.event_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            sse_manager.remove_session(session_id)
            stopped_sessions.append(session_id)
    
    return {
        "user_id": user_id,
        "sessions_stopped": len(stopped_sessions),
        "stopped_sessions": stopped_sessions,
        "message": f"Stopped {len(stopped_sessions)} session(s) for user {user_id}"
    }


@app.post("/api/v2/live/stop/all")
async def stop_all_sessions():
    """
    Stop all live simulation sessions (system-wide).
    
    Use this for:
    - Server shutdown/maintenance
    - Emergency stop all
    - System-level cleanup
    
    ⚠️  WARNING: This stops ALL active sessions for ALL users!
    
    Returns:
        {
            "sessions_stopped": int,
            "stopped_sessions": [{session_id, user_id, strategy_id}, ...]
        }
    """
    all_sessions = list(sse_manager.sessions.keys())
    
    if not all_sessions:
        return {
            "sessions_stopped": 0,
            "stopped_sessions": [],
            "message": "No active sessions to stop"
        }
    
    # Stop each session
    stopped_sessions = []
    for session_id in all_sessions:
        session = sse_manager.get_session(session_id)
        if session:
            session.status = "stopped"
            
            # Clear event queue
            while not session.event_queue.empty():
                try:
                    session.event_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            stopped_sessions.append({
                "session_id": session_id,
                "user_id": session.user_id,
                "strategy_id": session.strategy_id
            })
            
            sse_manager.remove_session(session_id)
    
    return {
        "sessions_stopped": len(stopped_sessions),
        "stopped_sessions": stopped_sessions,
        "message": f"Stopped all {len(stopped_sessions)} active session(s)"
    }

@app.get("/api/v2/live/status/{session_id}")
async def get_live_status_v2(session_id: str):
    """Get live simulation status (V2)"""
    session = sse_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "status": session.status,
        "progress": session.tick_state.get("progress", {}),
        "pnl_summary": session.tick_state.get("pnl_summary", {})
    }


# ============================================================================
# SIMPLE LIVE API - Clone of Backtesting Pattern
# Sends accumulated + delta data every second via SSE
# ============================================================================

@app.post("/api/queue/submit")
async def submit_to_queue(
    user_id: str,
    strategies: List[Dict[str, Any]],
    queue_type: str = "testing"
):
    """
    Submit strategies to queue for batch processing.
    
    Phase 1 MVP: Testing queue only (manual trigger).
    Future: Production queue with scheduled trigger.
    
    Args:
        user_id: User ID
        strategies: List of {strategy_id, broker_connection_id} dicts
        queue_type: 'testing' (Phase 1), 'production' (Phase 2+)
    
    Returns:
        Queue status
    """
    # Phase 1: Only testing queue supported
    if queue_type not in ['testing', 'admin_tester']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid queue_type: {queue_type}. Phase 1 supports 'testing' or 'admin_tester' only."
        )
    
    # Normalize to admin_tester for backward compatibility
    if queue_type == 'testing':
        queue_type = 'admin_tester'
    
    # Validate strategies list
    if not strategies or len(strategies) == 0:
        raise HTTPException(status_code=400, detail="strategies list cannot be empty")
    
    # Validate each strategy has required fields
    for idx, strategy in enumerate(strategies):
        if 'strategy_id' not in strategy or 'broker_connection_id' not in strategy:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy {idx} missing required fields: strategy_id, broker_connection_id"
            )
    
    # Create queue entry
    queue_entry = {
        'user_id': user_id,
        'strategies': strategies,
        'submitted_at': datetime.now().isoformat()
    }
    
    # Add/update strategies in queue (dict prevents duplicates)
    with queue_locks[queue_type]:
        for strategy in strategies:
            strategy_id = strategy['strategy_id']
            scale = strategy.get('scale', 1)  # Default scale to 1 if not provided
            # Upsert: overwrite if already exists, preventing duplicates
            strategy_queues[queue_type][strategy_id] = {
                'user_id': user_id,
                'strategy_id': strategy_id,
                'broker_connection_id': strategy['broker_connection_id'],
                'scale': scale
            }
        
        queue_position = len(strategy_queues[queue_type])
        total_strategies = len(strategy_queues[queue_type])
    
    return {
        "queued": True,
        "user_id": user_id,
        "queue_type": queue_type,
        "strategy_count": len(strategies),
        "queue_position": queue_position,
        "total_strategies_queued": total_strategies,
        "execution_mode": "manual",
        "next_step": "Admin trigger via POST /api/queue/execute"
    }


# ============================================================================
# QUEUE EXECUTION HELPER FUNCTIONS
# ============================================================================

async def _preprocess_historical_data(
    data_manager: Any,
    symbols_timeframes: List[tuple],
    backtest_date: str
):
    """
    Preprocess historical data from ClickHouse for backtesting.
    Loads 500 candles + indicators for each symbol:timeframe pair.
    
    Args:
        data_manager: DataManager instance
        symbols_timeframes: List of (symbol, timeframe) tuples
        backtest_date: Date string in YYYY-MM-DD format
    """
    print(f"📊 Preprocessing historical data for {len(symbols_timeframes)} symbols...")
    
    # Convert backtest_date to date object
    if isinstance(backtest_date, str):
        backtest_date_obj = datetime.strptime(backtest_date, '%Y-%m-%d').date()
    else:
        backtest_date_obj = backtest_date
    
    # Load data using DataManager's existing methods
    # symbols_timeframes is a dict: {symbol: Set[timeframe]}
    for symbol, timeframes in symbols_timeframes.items():
        for timeframe in timeframes:
            try:
                print(f"  Loading {symbol}:{timeframe}...")
                # This will trigger ClickHouse load if using backtest mode
                await asyncio.to_thread(
                    data_manager.load_historical_data,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_date=backtest_date_obj,
                    lookback_candles=500
                )
            except Exception as e:
                print(f"  ⚠️ Failed to load {symbol}:{timeframe}: {e}")
    
    print("✅ Historical data preprocessing complete")


async def _preprocess_live_data(
    data_manager: Any,
    symbols_timeframes: Dict[str, set]
):
    """
    Preprocess live data for production trading.
    Loads initial candles from yfinance or broker API.
    
    Args:
        data_manager: DataManager instance
        symbols_timeframes: List of (symbol, timeframe) tuples
    """
    print(f"📊 Preprocessing live data for {len(symbols_timeframes)} symbols...")
    
    # Load initial candles using DataManager's catchup mechanism
    for symbol, timeframe in symbols_timeframes:
        try:
            print(f"  Loading {symbol}:{timeframe}...")
            # This will use yfinance or broker API for live data
            await asyncio.to_thread(
                data_manager.load_live_catchup_data,
                symbol=symbol,
                timeframe=timeframe
            )
        except Exception as e:
            print(f"  ⚠️ Failed to load {symbol}:{timeframe}: {e}")
    
    print("✅ Live data preprocessing complete")


async def _run_historical_tick_processor(
    instance_type: str,
    backtest_date: str,
    speed_multiplier: float = 500.0
):
    """
    Run historical tick processor for simulation.
    Fetches ticks from ClickHouse and processes them at specified speed.
    
    Reuses existing working centralized backtest tick processing logic.
    
    Args:
        instance_type: Instance type (e.g., 'admin_tester')
        backtest_date: Date string in YYYY-MM-DD format
        speed_multiplier: Speed multiplier for playback (default 500x)
    """
    print(f"🎬 Starting historical tick processor: date={backtest_date}, speed={speed_multiplier}x")
    
    # Get instances
    instance_manager = get_instance_manager()
    
    # CRITICAL: Create DataManager with DictCache (not CacheManager) to match backtesting
    # DictCache has get_candles() method required by DataManager
    from src.backtesting.dict_cache import DictCache
    from src.core.shared_data_cache import SharedDataCache
    from src.backtesting.data_manager import DataManager
    
    dict_cache = DictCache(max_candles=20)
    shared_cache = SharedDataCache()
    data_manager = DataManager(
        cache=dict_cache,
        broker_name='clickhouse',
        shared_cache=shared_cache
    )
    
    # Get other instances
    tick_processor = instance_manager.get_or_create_tick_processor(instance_type)
    strategy_subscription_manager = instance_manager.get_or_create_strategy_subscription_manager(instance_type)
    
    # Get aggregated requirements
    aggregated = strategy_subscription_manager.aggregate_requirements_for_all_strategies()
    symbols_timeframes = aggregated['symbols_timeframes']  # Dict[symbol, Set[timeframe]]
    
    # Convert backtest_date to date object if it's a string
    if isinstance(backtest_date, str):
        from datetime import datetime as dt
        backtest_date_obj = dt.strptime(backtest_date, '%Y-%m-%d').date()
    else:
        backtest_date_obj = backtest_date
    
    # CRITICAL: Initialize DataManager components (matches working backtesting flow)
    print("🔧 Initializing DataManager components...")
    
    # Store backtest date
    data_manager.backtest_date = backtest_date_obj
    
    # 1. Initialize symbol cache
    if not data_manager.symbol_cache or not hasattr(data_manager.symbol_cache, '_loaded') or not data_manager.symbol_cache._loaded:
        data_manager._initialize_symbol_cache()
    
    # 2. Initialize ClickHouse
    if not data_manager.clickhouse_client:
        data_manager._initialize_clickhouse()
    
    # 3. Initialize option components
    data_manager._initialize_option_components()
    
    # 4. Setup candle builders for all timeframes
    unique_timeframes = set()
    for symbol, tf_set in symbols_timeframes.items():
        unique_timeframes.update(tf_set)
    data_manager._setup_candle_builders(list(unique_timeframes))
    
    print(f"✅ DataManager initialized with {len(unique_timeframes)} timeframes")
    
    # 5. CRITICAL FIX: Register indicators (missing in original queue execution)
    # Without this, indicators return None and entry conditions never trigger
    print("🔧 Registering indicators...")
    import ta_hybrid as ta
    import json
    
    registered_count = 0
    subscriptions = strategy_subscription_manager.cache.get_strategy_subscriptions()
    
    for instance_id, subscription in subscriptions.items():
        if subscription.get('status') != 'active':
            continue
        
        strategy_config = subscription.get('config', {})
        
        # DEBUG: Print actual structure to understand format
        print(f"\n🔍 DEBUG: Strategy config structure for {instance_id}:")
        print(f"   Config keys: {list(strategy_config.keys())}")
        
        # Use scan_results if available (from aggregate_requirements)
        if 'scan_results' in subscription:
            print(f"   📊 Using scan_results from subscription")
            ind_reqs = subscription['scan_results'].get('indicators', {})
            print(f"   Indicator requirements: {list(ind_reqs.keys())[:5]}...")  # Show first 5
            
            # Extract indicators from metadata (same approach as strategy scanner)
            metadata = strategy_config.get('metadata', {})
            instruments_meta = metadata.get('instruments', {})
            
            print(f"   📊 Extracting indicators from metadata...")
            print(f"      Available instrument aliases: {list(instruments_meta.keys())}")
            
            # Process each instrument alias (TI, SI, etc.)
            for alias, inst in instruments_meta.items():
                if not isinstance(inst, dict):
                    continue
                
                inst_symbol = inst.get('symbol')
                print(f"      Processing {alias}: symbol={inst_symbol}")
                
                timeframes_meta = inst.get('timeframes', [])
                for tf_meta in timeframes_meta:
                    if not isinstance(tf_meta, dict):
                        continue
                    
                    tf_timeframe = tf_meta.get('timeframe')
                    tf_indicators = tf_meta.get('indicators', [])
                    
                    print(f"         Timeframe {tf_timeframe}: {len(tf_indicators)} indicators")
                    
                    # Register each indicator
                    for ind_meta in tf_indicators:
                        if not isinstance(ind_meta, dict):
                            continue
                        
                        indicator_name = ind_meta.get('indicator_name')
                        indicator_params = ind_meta.get('params', {})
                        indicator_key = ind_meta.get('key')
                        
                        if not indicator_name or not inst_symbol or not tf_timeframe:
                            print(f"            ❌ Missing data: name={indicator_name}, symbol={inst_symbol}, tf={tf_timeframe}")
                            continue
                        
                        # Get indicator class from ta_hybrid
                        indicator_name_lower = indicator_name.lower()
                        indicator_class = ta._INDICATOR_REGISTRY.get(indicator_name_lower)
                        if indicator_class is None:
                            print(f"            ⚠️ Indicator '{indicator_name_lower}' not found in ta_hybrid")
                            continue
                        
                        # Create and register indicator
                        try:
                            indicator = indicator_class(**indicator_params)
                            
                            data_manager.register_indicator(
                                symbol=inst_symbol,
                                timeframe=tf_timeframe,
                                indicator=indicator,
                                database_key=indicator_key
                            )
                            registered_count += 1
                            print(f"            ✅ Registered {indicator_name} for {inst_symbol}:{tf_timeframe}")
                        except Exception as e:
                            print(f"            ⚠️ Failed to register {indicator_name}: {e}")
                            import traceback
                            traceback.print_exc()
        else:
            print(f"   ⚠️ No scan_results in subscription - manual extraction")
            # Fallback: manual extraction from nodes
            nodes = strategy_config.get('nodes', [])
            print(f"   Found {len(nodes)} nodes")
            
            for idx, node in enumerate(nodes):
                print(f"   Node {idx}: type={node.get('type')}, id={node.get('id')}")
                if node.get('type') == 'condition':
                    node_config = node.get('config', {})
                    print(f"      Config keys: {list(node_config.keys())}")
    
    print(f"\n✅ Registered {registered_count} indicators total")
    
    # 6. CRITICAL: Load historical candles for indicators
    # Indicators need past data to calculate initial values (e.g., RSI needs 14+ candles)
    print("📊 Loading historical candles for indicator warmup...")
    
    from src.config.clickhouse_config import ClickHouseConfig
    market_open, _ = ClickHouseConfig.get_market_hours()
    
    for symbol in symbols_timeframes.keys():
        for timeframe in symbols_timeframes[symbol]:
            try:
                # Use same query pattern as backtesting (_load_historical_candles_from_agg)
                query = f"""
                    SELECT 
                        timestamp,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        symbol,
                        timeframe
                    FROM nse_ohlcv_indices
                    WHERE symbol = '{symbol}'
                      AND timeframe = '{timeframe}'
                      AND timestamp < '{backtest_date_obj.strftime('%Y-%m-%d')} {market_open}'
                    ORDER BY timestamp DESC
                    LIMIT 500
                """
                
                candles_df = data_manager.clickhouse_client.query_df(query)
                
                if not candles_df.empty:
                    # Reverse to chronological order (query was DESC to get most recent)
                    candles_df = candles_df.sort_values('timestamp', ascending=True)
                    
                    # Initialize indicators with this data (same as backtesting)
                    data_manager.initialize_from_historical_data(symbol, timeframe, candles_df)
                    print(f"   ✅ Loaded {len(candles_df)} historical candles for {symbol}:{timeframe}")
                else:
                    print(f"   ℹ️  No historical candles for {symbol}:{timeframe}")
            except Exception as e:
                print(f"   ⚠️ Failed to load candles for {symbol}:{timeframe}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"✅ Historical candles loaded and indicators initialized")
    
    # Extract unique symbols from symbols_timeframes dict
    symbols = list(symbols_timeframes.keys())
    
    # Load ticks from ClickHouse (reuse existing DataManager method)
    ticks = data_manager.load_ticks(
        date=backtest_date_obj,
        symbols=symbols
    )
    
    if not ticks:
        print("⚠️ No ticks loaded from ClickHouse")
        return
    
    print(f"✅ Loaded {len(ticks):,} ticks from ClickHouse")
    
    # Process ticks with speed control (reuse existing logic)
    from collections import defaultdict
    import time
    
    # Group ticks by second
    ticks_by_second = defaultdict(list)
    for tick in ticks:
        tick_timestamp = tick['timestamp']
        second_key = tick_timestamp.replace(microsecond=0)
        ticks_by_second[second_key].append(tick)
    
    sorted_seconds = sorted(ticks_by_second.keys())
    total_seconds = len(sorted_seconds)
    
    print(f"📦 Batched {len(ticks):,} ticks into {total_seconds:,} seconds")
    print(f"   Average: {len(ticks)/total_seconds:.1f} ticks/second")
    print(f"   Time range: {sorted_seconds[0].strftime('%H:%M:%S')} → {sorted_seconds[-1].strftime('%H:%M:%S')}")
    
    processed_tick_count = 0
    
    # Process each second's batch
    for second_idx, second_timestamp in enumerate(sorted_seconds):
        tick_batch = ticks_by_second[second_timestamp]
        
        # Process all ticks in this second's batch
        last_processed_tick = None
        for tick in tick_batch:
            last_processed_tick = data_manager.process_tick(tick)
            processed_tick_count += 1
        
        # Process option ticks for this timestamp
        option_ticks = data_manager.get_option_ticks_for_timestamp(second_timestamp)
        for option_tick in option_ticks:
            data_manager.process_tick(option_tick)
            processed_tick_count += 1
        
        # Execute strategy once per second with final state
        if last_processed_tick:
            tick_data = {
                'symbol': last_processed_tick.get('symbol'),
                'ltp': last_processed_tick.get('ltp'),
                'timestamp': second_timestamp,
                'volume': last_processed_tick.get('volume', 0),
                'batch_size': len(tick_batch)
            }
            
            # Debug first few ticks
            if second_idx < 5:
                print(f"🔍 Tick {second_idx}: {tick_data['symbol']} @ {tick_data['ltp']} at {second_timestamp.strftime('%H:%M:%S')}")
                print(f"   Active strategies before: {len(tick_processor.strategy_manager.active_strategies)}")
            
            # Execute strategy via centralized tick processor
            tick_processor.on_tick(tick_data)
            
            # Debug first few ticks
            if second_idx < 5:
                print(f"   Active strategies after: {len(tick_processor.strategy_manager.active_strategies)}")
                if not tick_processor.strategy_manager.active_strategies:
                    print(f"   ⚠️ No active strategies after tick {second_idx}")
            
            # Speed control: Sleep to simulate real-time playback
            if speed_multiplier > 0:
                sleep_duration = 1.0 / speed_multiplier  # seconds
                await asyncio.sleep(sleep_duration)
            
            # Check if all strategies terminated
            active_strategies = tick_processor.strategy_manager.active_strategies
            if not active_strategies:
                print(f"\n🛑 All strategies terminated at {second_timestamp.strftime('%H:%M:%S')}")
                print(f"   Total ticks processed before termination: {processed_tick_count}")
                break
        
        # Progress reporting every 100 seconds
        if (second_idx + 1) % 100 == 0:
            print(f"   Progress: {second_idx + 1}/{total_seconds} seconds ({100*(second_idx+1)/total_seconds:.1f}%)")
    
    print(f"✅ Processed {processed_tick_count:,} ticks in {total_seconds:,} seconds")
    print(f"⚡ Strategies executed {total_seconds:,} times")
    
    # Print position results from GPS before cleanup
    print("\n" + "="*80)
    print("📊 STRATEGY EXECUTION RESULTS")
    print("="*80)
    
    for strategy_instance_id, strategy_state in tick_processor.strategy_manager.active_strategies.items():
        context = strategy_state.get('context', {})
        gps = context.get('gps')
        
        if gps and hasattr(gps, 'positions'):
            positions = gps.positions
            closed_positions = [p for p in positions.values() if p.get('status') == 'closed']
            open_positions = [p for p in positions.values() if p.get('status') != 'closed']
            
            print(f"\nStrategy: {strategy_instance_id}")
            print(f"Total Positions: {len(positions)}")
            print(f"  Closed: {len(closed_positions)}")
            print(f"  Open: {len(open_positions)}")
            
            if positions:
                total_pnl = 0
                
                print("\n" + "-"*80)
                for pos_id, pos_data in positions.items():
                    status = pos_data.get('status', 'unknown')
                    status_icon = '✅' if status == 'closed' else '⏳'
                    
                    print(f"\n{status_icon} Position: {pos_id}")
                    print(f"   Symbol: {pos_data.get('symbol')}")
                    print(f"   Side: {pos_data.get('side')}")
                    print(f"   Entry Price: ₹{pos_data.get('entry_price', 0):.2f}")
                    print(f"   Quantity: {pos_data.get('actual_quantity', 0)}")
                    print(f"   Entry Time: {pos_data.get('entry_time')}")
                    
                    if status == 'closed':
                        exit_price = pos_data.get('exit_price', 0)
                        entry_price = pos_data.get('entry_price', 0)
                        qty = pos_data.get('actual_quantity', 0)
                        side = pos_data.get('side', 'BUY')
                        
                        if side.upper() == 'BUY':
                            pnl = (exit_price - entry_price) * qty
                        else:
                            pnl = (entry_price - exit_price) * qty
                        
                        total_pnl += pnl
                        pnl_icon = '🟢' if pnl >= 0 else '🔴'
                        print(f"   Exit Price: ₹{exit_price:.2f}")
                        print(f"   Exit Time: {pos_data.get('exit_time')}")
                        print(f"   P&L: {pnl_icon} ₹{pnl:.2f}")
                        print(f"   Exit Reason: {pos_data.get('exit_reason', 'N/A')}")
                
                print("\n" + "-"*80)
                pnl_icon = '🟢' if total_pnl >= 0 else '🔴'
                print(f"Total P&L: {pnl_icon} ₹{total_pnl:.2f}")
    
    print("\n" + "="*80)
    print("✅ Historical tick processor completed")


@app.post("/api/queue/execute")
async def execute_queue(
    queue_type: str = "admin_tester",
    trigger_type: str = "manual"
):
    """
    Execute all queued strategies (admin/manual trigger).
    
    Phase 1 MVP: Testing queue only with historical data.
    
    Steps:
    1. Get queue entries
    2. Subscribe strategies to cache (shared via GlobalInstanceManager)
    3. Aggregate requirements (DataManager aggregation)
    4. Preprocess data (load 500 candles + indicators)
    5. Start tick processor (historical ticks from ClickHouse)
    6. Clear queue
    
    Args:
        queue_type: 'admin_tester' (Phase 1), 'production' (Phase 2+)
        backtest_date: Historical date for testing (YYYY-MM-DD)
        speed_multiplier: Playback speed (default 500x)
        trigger_type: 'manual' (admin) or 'scheduled' (future)
    
    Returns:
        Execution result
    """
    # Validate queue type
    if queue_type not in strategy_queues:
        raise HTTPException(status_code=400, detail=f"Invalid queue_type: {queue_type}")
    
    # Check if already processing
    if active_processing[queue_type]:
        raise HTTPException(
            status_code=400,
            detail=f"{queue_type} queue is already being processed"
        )
    
    # Get queue entries
    with queue_locks[queue_type]:
        if len(strategy_queues[queue_type]) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"No strategies in {queue_type} queue"
            )
        
        # Convert dict values to list for processing
        queue_entries = list(strategy_queues[queue_type].values())
        active_processing[queue_type] = True
    
    try:
        # Get singleton instances
        cache = instance_manager.get_or_create_cache(queue_type)
        data_manager = instance_manager.get_or_create_data_manager(queue_type)
        strategy_subscription_manager = instance_manager.get_or_create_strategy_subscription_manager(queue_type)
        
        # Fetch broker metadata from first strategy's broker_connection
        # All strategies in queue should use same ClickHouse broker connection
        backtest_date = None
        speed_multiplier = 500.0
        
        if len(queue_entries) > 0:
            first_entry = queue_entries[0]
            broker_connection_id = first_entry.get('broker_connection_id')
            
            if broker_connection_id:
                # Fetch from Supabase (same pattern as /api/v1/live/start)
                broker_response = supabase.table('broker_connections').select('broker_metadata').eq('id', broker_connection_id).execute()
                
                if broker_response.data and len(broker_response.data) > 0:
                    broker_metadata_str = broker_response.data[0].get('broker_metadata', '{}')
                    broker_metadata = json.loads(broker_metadata_str) if isinstance(broker_metadata_str, str) else broker_metadata_str
                    
                    # Extract simulation parameters
                    backtest_date = broker_metadata.get('simulation_date', '2024-10-29')
                    speed_multiplier = broker_metadata.get('speed_multiplier', 500.0)
                    
                    print(f"📅 Using broker metadata: date={backtest_date}, speed={speed_multiplier}x")
        
        # Step 1: Subscribe all strategies to cache
        total_strategies = 0
        
        for entry in queue_entries:
            user_id = entry['user_id']
            strategy_id = entry['strategy_id']
            broker_connection_id = entry['broker_connection_id']
            
            # Fetch strategy from Supabase
            response = supabase.table('strategies').select('*').eq('id', strategy_id).execute()
            
            if response.data and len(response.data) > 0:
                strategy_row = response.data[0]
                
                print(f"📋 Strategy {strategy_id} database keys: {list(strategy_row.keys())}")
                
                # Extract the actual strategy config from the 'strategy' field
                if 'strategy' in strategy_row:
                    strategy_data = strategy_row['strategy']
                    
                    # Parse if it's a JSON string
                    if isinstance(strategy_data, str):
                        try:
                            strategy_data = json.loads(strategy_data)
                            print(f"   ✅ Parsed 'strategy' field from JSON string")
                        except Exception as e:
                            print(f"   ❌ Failed to parse 'strategy' field: {e}")
                            continue
                    
                    print(f"   Strategy config keys: {list(strategy_data.keys()) if isinstance(strategy_data, dict) else 'not a dict'}")
                    print(f"   Has 'nodes': {'nodes' in strategy_data if isinstance(strategy_data, dict) else False}")
                    print(f"   Has 'instrument_configs': {'instrument_configs' in strategy_data if isinstance(strategy_data, dict) else False}")
                    
                    # Parse nested fields if they're JSON strings
                    if isinstance(strategy_data, dict):
                        if 'nodes' in strategy_data and isinstance(strategy_data['nodes'], str):
                            try:
                                strategy_data['nodes'] = json.loads(strategy_data['nodes'])
                                print(f"   ✅ Parsed nested 'nodes' from JSON string")
                            except:
                                pass
                        
                        if 'instrument_configs' in strategy_data and isinstance(strategy_data['instrument_configs'], str):
                            try:
                                strategy_data['instrument_configs'] = json.loads(strategy_data['instrument_configs'])
                                print(f"   ✅ Parsed nested 'instrument_configs' from JSON string")
                            except:
                                pass
                else:
                    print(f"   ⚠️ No 'strategy' field found, using entire row")
                    strategy_data = strategy_row
                
                # Create instance_id for this strategy run
                instance_id = f"{queue_type}_{user_id}_{strategy_id}"
                
                # Subscribe to cache using correct method
                strategy_subscription_manager.create_and_sync_backtest_subscription(
                    instance_id=instance_id,
                    user_id=user_id,
                    strategy_id=strategy_id,
                    account_id=broker_connection_id,
                    strategy_config=strategy_data,
                    strategy_metadata=None
                )
                total_strategies += 1
            else:
                print(f"⚠️ Strategy {strategy_id} not found in database")
        
        # Step 2: Aggregate requirements (reuse existing method!)
        aggregated = strategy_subscription_manager.aggregate_requirements_for_all_strategies()
        
        indicator_reqs = aggregated['indicator_reqs']
        symbols_timeframes = aggregated['symbols_timeframes']
        option_reqs = aggregated['option_reqs']
        
        # Note: Data preprocessing is optional - the historical tick processor 
        # will call data_manager.load_ticks() which loads from ClickHouse
        print(f"📊 Ready to process {len(symbols_timeframes)} symbols")
        
        # Subscribe option patterns if needed (optional, handled during tick processing)
        if option_reqs:
            print(f"📋 {len(option_reqs)} option requirements detected (will be handled during execution)")
        
        # CRITICAL: Sync strategies into tick processor AFTER subscribing to cache
        tick_processor = instance_manager.get_or_create_tick_processor(queue_type)
        print(f"🔄 Syncing {total_strategies} strategies into tick processor...")
        tick_processor.sync_all_strategies()
        active_count = tick_processor.get_active_strategy_count()
        print(f"✅ Tick processor has {active_count} active strategies")
        
        # Clear queue after successful processing
        with queue_locks[queue_type]:
            strategy_queues[queue_type].clear()
            active_processing[queue_type] = False
        
        # Queue processed - ready for ticks
        
        # Start historical tick processor
        asyncio.create_task(
            _run_historical_tick_processor(
                instance_type=queue_type,
                backtest_date=backtest_date,
                speed_multiplier=speed_multiplier
            )
        )
        
        return {
            "started": True,
            "queue_type": queue_type,
            "trigger_type": trigger_type,
            "user_count": len(queue_entries),
            "strategy_count": total_strategies,
            "symbols_count": len(symbols_timeframes),
            "indicator_count": len(indicator_reqs),
            "option_count": len(option_reqs),
            "preprocessing_complete": True,
            "mode": "historical_simulation",
            "backtest_date": backtest_date,
            "speed_multiplier": speed_multiplier
        }
        
    except Exception as e:
        # Reset processing flag on error
        with queue_locks[queue_type]:
            active_processing[queue_type] = False
        
        import traceback
        print(f"❌ Queue execution error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/api/queue/status/{queue_type}")
async def get_queue_status(queue_type: str):
    """
    Get status of a specific queue.
    
    Args:
        queue_type: 'admin_tester' or 'production'
    
    Returns:
        Queue status information
    """
    if queue_type not in strategy_queues:
        raise HTTPException(status_code=400, detail=f"Invalid queue_type: {queue_type}")
    
    with queue_locks[queue_type]:
        entries = strategy_queues[queue_type]
        total_strategies = len(entries)
        
        # Get detailed entries for preview
        detailed_entries = [
            {
                'user_id': entry['user_id'],
                'strategy_id': entry['strategy_id'],
                'broker_connection_id': entry['broker_connection_id']
            }
            for entry in entries.values()
        ]
    
    return {
        "queue_type": queue_type,
        "pending_entries": len(entries),
        "total_strategies": total_strategies,
        "is_processing": active_processing[queue_type],
        "entries": detailed_entries
    }


@app.delete("/api/queue/remove/{queue_type}/{strategy_id}")
async def remove_strategy_from_queue(queue_type: str, strategy_id: str):
    """
    Remove a specific strategy from the queue (idempotent - no error if not found).
    
    Args:
        queue_type: 'admin_tester' or 'production'
        strategy_id: Strategy ID to remove
    
    Returns:
        Removal confirmation
    """
    if queue_type not in strategy_queues:
        raise HTTPException(status_code=400, detail=f"Invalid queue_type: {queue_type}")
    
    if active_processing[queue_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot modify queue while processing. Queue is currently executing."
        )
    
    with queue_locks[queue_type]:
        if strategy_id in strategy_queues[queue_type]:
            del strategy_queues[queue_type][strategy_id]
            was_present = True
        else:
            was_present = False
    
    # Always return success (idempotent operation)
    return {
        "removed": was_present,
        "queue_type": queue_type,
        "strategy_id": strategy_id,
        "remaining_strategies": len(strategy_queues[queue_type])
    }


@app.delete("/api/queue/clear/{queue_type}")
async def clear_queue(queue_type: str):
    """
    Clear all entries from a queue (for testing/debugging).
    
    Args:
        queue_type: 'admin_tester' or 'production'
    
    Returns:
        Cleared count
    """
    if queue_type not in strategy_queues:
        raise HTTPException(status_code=400, detail=f"Invalid queue_type: {queue_type}")
    
    if active_processing[queue_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot clear queue while processing. Queue is currently executing."
        )
    
    with queue_locks[queue_type]:
        cleared_strategies = len(strategy_queues[queue_type])
        strategy_queues[queue_type].clear()
    
    # Minimal logging
    # print(f"🗑️ Cleared {queue_type}: {cleared_strategies} strategies")
    
    return {
        "cleared": True,
        "queue_type": queue_type,
        "strategies_removed": cleared_strategies
    }


@app.get("/api/simple/live/state/{session_id}")
async def get_simple_live_state(session_id: str):
    """
    Polling endpoint - Get current state (for UI polling instead of SSE)
    Returns data in same format as /api/v1/simulation/{session_id}/state
    """
    session = simple_stream_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get current data
    data = session.get_current_data()
    
    # Transform to match expected format
    return {
        "session_id": session.session_id,
        "status": session.status,
        "timestamp": data["timestamp"],
        "gps_data": {
            "trades": data["accumulated"]["trades"],
            "events_history": data["accumulated"]["events_history"],
            "pnl_summary": data["accumulated"]["summary"]
        },
        "tick_state": {
            "current_time": data.get("current_time", data["timestamp"])
        },
        "stats": {
            "progress_percentage": data["progress"]["percentage"]
        }
    }


@app.get("/api/simple/live/initial-state/{user_id}/{strategy_id}")
async def get_initial_state(
    user_id: str,
    strategy_id: str,
    backtest_date: str = Query(..., description="Backtest date in YYYY-MM-DD format"),
    last_event_id: Optional[str] = Query(None, description="Last event ID received by client (for delta updates)"),
    last_trade_id: Optional[str] = Query(None, description="Last trade ID received by client (for delta updates)")
):
    """
    Get initial state for reconnection/refresh.
    
    Returns both node events and trades:
    - If last_event_id provided: Returns only events after that ID (delta)
    - If last_trade_id provided: Returns only trades after that ID (delta)
    - If both None: Returns full state
    
    Used when:
    - User refreshes page
    - User logs in from different machine
    - Connection drops and needs to resume
    """
    from pathlib import Path
    
    try:
        # Parse date to create folder
        try:
            date_obj = datetime.strptime(backtest_date, '%Y-%m-%d')
            date_folder = date_obj.strftime('%Y-%m-%d')
        except:
            date_folder = backtest_date
        
        # Build file paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        state_base_dir = Path(script_dir) / 'live_state_cache'
        state_folder = state_base_dir / date_folder / user_id / strategy_id
        events_file = state_folder / 'node_events.jsonl'
        trades_file = state_folder / 'trades.jsonl'
        
        # Check if at least one file exists
        if not events_file.exists() and not trades_file.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"No state found for user={user_id}, strategy={strategy_id}, date={backtest_date}"
            )
        
        result = {
            "user_id": user_id,
            "strategy_id": strategy_id,
            "backtest_date": backtest_date,
            "events": {},
            "trades": [],
            "event_count": 0,
            "trade_count": 0,
            "is_delta": False,
            "last_event_id": last_event_id,
            "last_trade_id": last_trade_id
        }
        
        # Load node events
        if events_file.exists():
            all_events = {}
            event_order = []
            
            with open(events_file, 'r') as f:
                for line in f:
                    event_line = json.loads(line.strip())
                    exec_id = event_line['exec_id']
                    event = event_line['event']
                    all_events[exec_id] = event
                    event_order.append(exec_id)
            
            # Delta or full events
            if last_event_id and last_event_id in event_order:
                last_idx = event_order.index(last_event_id)
                delta_exec_ids = event_order[last_idx + 1:]
                result['events'] = {eid: all_events[eid] for eid in delta_exec_ids}
                result['is_delta'] = True
            else:
                result['events'] = all_events
            
            result['event_count'] = len(result['events'])
        
        # Load trades
        if trades_file.exists():
            all_trades = []
            
            with open(trades_file, 'r') as f:
                for line in f:
                    trade = json.loads(line.strip())
                    all_trades.append(trade)
            
            # Delta or full trades
            if last_trade_id:
                trade_ids = [t['trade_id'] for t in all_trades]
                if last_trade_id in trade_ids:
                    last_idx = trade_ids.index(last_trade_id)
                    result['trades'] = all_trades[last_idx + 1:]
                    result['is_delta'] = True
                else:
                    result['trades'] = all_trades
            else:
                result['trades'] = all_trades
            
            result['trade_count'] = len(result['trades'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading state: {str(e)}")


@app.get("/api/simple/live/stream/{session_id}")
async def stream_simple_live(session_id: str):
    """
    SSE stream - Sends accumulated + delta data every second
    Same pattern as backtesting
    """
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


@app.get("/api/simple/live/user/{user_id}")
async def stream_simple_user(user_id: str):
    """
    User-level SSE stream - All sessions for a user
    Aggregates data from all user's live sessions
    """
    return EventSourceResponse(
        simple_stream_manager.stream_user(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# Startup event: Clean up all stale sessions
@app.on_event("startup")
async def startup_cleanup():
    """Clean up ALL sessions on startup to prevent memory leaks from previous runs"""
    print("\n" + "="*80)
    print("🧹 STARTUP CLEANUP")
    print("="*80)
    
    # Clean up simple live stream sessions
    cleaned = simple_stream_manager.cleanup_all_sessions()
    print(f"✅ Cleaned up {cleaned} stale sessions from previous runs")
    
    # Clean up active_sessions dict
    if active_sessions:
        count = len(active_sessions)
        active_sessions.clear()
        print(f"✅ Cleaned up {count} active sessions from memory")
    
    print("="*80 + "\n")


# Background task: Periodic cleanup every 30 minutes
@app.on_event("startup")
async def start_background_cleanup():
    """Start periodic cleanup task"""
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            print("\n🧹 Running periodic session cleanup...")
            cleaned = simple_stream_manager.cleanup_stale_sessions(max_age_minutes=60)
            print(f"✅ Cleaned up {cleaned} stale sessions (older than 60 min)\n")
    
    asyncio.create_task(periodic_cleanup())
    print("⏰ Started periodic cleanup task (runs every 30 minutes)")


if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print("🚀 Starting TradeLayout Backtest API Server")
    print("="*80)
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("="*80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
