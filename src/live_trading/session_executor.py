"""
Session Executor - Runs CentralizedBacktestEngine for live simulation sessions.

Executes strategies in background threads and streams events via SSE.
"""

import asyncio
import traceback
from datetime import datetime
from typing import Dict, Any
from src.live_trading.live_session_manager import live_session_manager
from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from src.utils.logger import log_info, log_error, log_warning
from live_simulation_sse import sse_manager, SSESession


def execute_session_async(session_id: str):
    """
    Execute a session asynchronously in a background thread.
    Runs CentralizedBacktestEngine and streams events to SSE.
    
    Args:
        session_id: Session identifier
    """
    try:
        log_info(f"🚀 Starting session execution: {session_id}")
        
        # Get session data
        session_data = live_session_manager.get_session(session_id)
        if not session_data:
            log_error(f"Session {session_id} not found")
            return
        
        # Update status to running
        live_session_manager.update_session_status(session_id, "running")
        
        # Get config and SSE session
        config = session_data['config']
        sse_session = session_data['sse_session']
        
        # Create backtest engine
        engine = CentralizedBacktestEngine(config)
        
        # Store engine reference
        session_data['engine'] = engine
        
        # Run backtest using standard engine.run() method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Monkey-patch to inject session_id after engine initialization
            original_subscribe = engine._subscribe_strategy_to_cache
            
            def patched_subscribe(strategy):
                # Call original subscribe
                original_subscribe(strategy)
                
                # Inject session_id into strategy_state after subscription
                active_strategies = engine.centralized_processor.strategy_manager.get_active_strategies()
                for instance_id, strategy_state in active_strategies.items():
                    if instance_id not in getattr(patched_subscribe, 'patched_instances', set()):
                        strategy_state['session_id'] = session_id
                        if 'output_writer' in strategy_state:
                            strategy_state['output_writer'].sse_session = sse_session
                        log_info(f"   🔗 Wired SSE session to strategy: {instance_id}")
                        
                        # Track that we patched this instance
                        if not hasattr(patched_subscribe, 'patched_instances'):
                            patched_subscribe.patched_instances = set()
                        patched_subscribe.patched_instances.add(instance_id)
            
            # Apply monkey-patch
            engine._subscribe_strategy_to_cache = patched_subscribe
            
            # Run standard engine.run() - this will use proper initialization flow
            results = loop.run_until_complete(engine.run())
            
            # Update status to completed
            live_session_manager.update_session_status(session_id, "completed")
            
            # Send completion event to SSE
            sse_session.add_node_event(
                execution_id=f"session_complete_{session_id}",
                event_data={
                    'event_type': 'session_complete',
                    'session_id': session_id,
                    'results': {
                        'ticks_processed': results.ticks_processed if hasattr(results, 'ticks_processed') else 0,
                        'duration_seconds': results.duration_seconds if hasattr(results, 'duration_seconds') else 0
                    },
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            log_info(f"✅ Session completed: {session_id}")
            
        except Exception as e:
            log_error(f"Error running session {session_id}: {e}")
            log_error(traceback.format_exc())
            
            # Update status to error
            live_session_manager.update_session_status(session_id, "error", str(e))
            
            # Send error event to SSE
            sse_session.add_node_event(
                execution_id=f"session_error_{session_id}",
                event_data={
                    'event_type': 'session_error',
                    'session_id': session_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            )
        
        finally:
            loop.close()
            
    except Exception as e:
        log_error(f"Fatal error in session executor for {session_id}: {e}")
        log_error(traceback.format_exc())
        live_session_manager.update_session_status(session_id, "error", str(e))
