"""
Worker Process for Backtest Execution
======================================

Runs backtest in separate process to avoid blocking FastAPI event loop.
Each strategy runs in its own isolated process.
"""

import os
import sys
import asyncio

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

def run_backtest_worker(session_id: str, strategy_id: str, user_id: str, 
                       start_date: str, speed_multiplier: float):
    """
    Worker function that runs in separate process.
    
    Args:
        session_id: Unique session identifier (strategy_id + broker_connection_id)
        strategy_id: Strategy UUID
        user_id: User UUID
        start_date: Backtest date (YYYY-MM-DD)
        speed_multiplier: Simulation speed (500 = 500x real-time)
    """
    print(f"🔧 [Worker {os.getpid()}] Starting backtest for session {session_id}")
    
    try:
        # Import here to avoid pickling issues
        from live_backtest_runner import run_live_backtest
        
        # Run the async backtest function
        asyncio.run(run_live_backtest(
            session_id=session_id,
            strategy_id=strategy_id,
            user_id=user_id,
            start_date=start_date,
            speed_multiplier=speed_multiplier
        ))
        
        print(f"✅ [Worker {os.getpid()}] Completed session {session_id}")
        
    except Exception as e:
        print(f"❌ [Worker {os.getpid()}] Error in session {session_id}: {e}")
        import traceback
        traceback.print_exc()
