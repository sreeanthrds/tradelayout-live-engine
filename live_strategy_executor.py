"""
Live Multi-Strategy Orchestrator
Coordinates modular engines to execute multiple strategies simultaneously

Modular Architecture:
1. MetadataScanner: Scan all strategies, extract metadata
2. DataInitializer: Initialize CandleStore + LTPStore
3. DataSourceManager: Load tick data for registered symbols
4. TickBatchProcessor: Convert ticks to unified format
5. CandleBuilder: Build candles, apply indicators incrementally
6. StrategyExecutor: Execute strategy nodes per session
7. EventEmitter: Emit events to JSONL files

Flow:
- Single tick stream → All strategies simultaneously
- Each module is a pure engine (input → output)
- No adhoc modifications during execution
"""

import json
import gzip
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from src.live_trading import (
    SessionDataLoader,
    MetadataScanner,
    DataInitializer,
    DataSourceManager,
    TickBatchProcessor,
    CandleBuilder,
    IndicatorRegistry,
    StrategyExecutor,
    EventEmitter
)
from src.utils.logger import log_info, log_error, log_debug


async def start_multi_strategy_execution(sessions: List[Dict[str, Any]]):
    """
    Orchestrate modular engines to execute multiple strategies
    
    Modular Flow:
    1. MetadataScanner: Scan all strategies
    2. DataInitializer: Initialize stores
    3. DataSourceManager: Load tick data
    4. Loop on tick batches:
       a. TickBatchProcessor: Convert to unified format
       b. Broadcast to all StrategyExecutors
    5. Finalize all executors
    
    Input: sessions - List of enabled session data
    Output: Execution results
    """
    log_info(f"[Orchestrator] Starting multi-strategy execution for {len(sessions)} sessions")
    
    if not sessions:
        log_error("[Orchestrator] No sessions provided")
        return {"total_sessions": 0, "successful": 0, "failed": 0, "results": []}
    
    # Get trade_date from first session (either from meta_data or execution_date)
    first_session = sessions[0]
    trade_date_str = first_session.get("meta_data", {}).get("trade_date") or first_session.get("execution_date")
    
    if not trade_date_str:
        log_error("[Orchestrator] No trade_date or execution_date in session")
        return {"total_sessions": 0, "successful": 0, "failed": len(sessions), "results": []}
    
    try:
        trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
    except ValueError:
        log_error(f"[Orchestrator] Invalid trade_date format: {trade_date_str}")
        return {"total_sessions": 0, "successful": 0, "failed": len(sessions), "results": []}
    
    # Validate same trade_date for all sessions
    for session in sessions:
        session_date = session.get("meta_data", {}).get("trade_date") or session.get("execution_date")
        if session_date != trade_date_str:
            log_error(f"[Orchestrator] Mismatched trade_date: {session_date} vs {trade_date_str}")
            return {"total_sessions": 0, "successful": 0, "failed": len(sessions), "results": []}
    
    log_info(f"[Orchestrator] Trade date: {trade_date_str}")
    
    try:
        # =================================================================
        # MODULE 0: SessionDataLoader - Load strategy + broker details from Supabase
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 0: SessionDataLoader =====")
        session_data_loader = SessionDataLoader()
        enriched_sessions = session_data_loader.load_sessions(sessions)
        
        if not enriched_sessions:
            log_error("[Orchestrator] No sessions loaded from Supabase")
            return {"total_sessions": 0, "successful": 0, "failed": len(sessions), "results": []}
        
        log_info(f"[Orchestrator] Loaded {len(enriched_sessions)} enriched sessions")
        
        # =================================================================
        # MODULE 1: MetadataScanner - Scan enriched sessions
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 1: MetadataScanner =====")
        metadata_scanner = MetadataScanner()
        metadata = metadata_scanner.scan(enriched_sessions)
        
        log_info(f"[Orchestrator] Metadata: {len(metadata['symbols'])} symbols, {len(metadata['timeframes'])} timeframes")
        
        # =================================================================
        # MODULE 2: DataInitializer - Initialize CandleStore + LTPStore
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 2: DataInitializer =====")
        data_initializer = DataInitializer(trade_date, enriched_sessions[0]["user_id"])
        stores = data_initializer.initialize(metadata)
        
        candle_store = stores["candle_store"]
        ltp_store = stores["ltp_store"]
        
        log_info("[Orchestrator] Stores initialized")
        
        # =================================================================
        # MODULE 3: DataSourceManager - Load tick data
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 3: DataSourceManager =====")
        data_source_manager = DataSourceManager(trade_date, ltp_store)
        data_source_manager.initialize(metadata)
        
        log_info("[Orchestrator] Data source initialized")
        
        # =================================================================
        # MODULE 4: IndicatorRegistry - Initialize indicators
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 4: IndicatorRegistry =====")
        indicator_registry = IndicatorRegistry()
        
        # Initialize indicators for each symbol:timeframe
        # (For now, we'll skip indicator initialization - add later)
        log_info("[Orchestrator] Indicator registry initialized")
        
        # =================================================================
        # MODULE 5: CandleBuilder - Initialize candle builder
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 5: CandleBuilder =====")
        candle_builder = CandleBuilder(candle_store, indicator_registry)
        
        log_info("[Orchestrator] Candle builder initialized")
        
        # =================================================================
        # MODULE 6: TickBatchProcessor - Initialize tick processor
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 6: TickBatchProcessor =====")
        tick_batch_processor = TickBatchProcessor(ltp_store, candle_builder)
        
        log_info("[Orchestrator] Tick batch processor initialized")
        
        # =================================================================
        # MODULE 7: EventEmitter - Initialize event emitter
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 7: EventEmitter =====")
        event_emitter = EventEmitter(Path("live_results"))
        
        # Register all enriched sessions
        for session in enriched_sessions:
            event_emitter.register_session(session["session_id"], session["user_id"])
        
        log_info("[Orchestrator] Event emitter initialized")
        
        # =================================================================
        # MODULE 8: StrategyExecutor - Initialize executors for each session
        # =================================================================
        log_info("[Orchestrator] ===== MODULE 8: StrategyExecutor =====")
        # Initialize executors (one per session using enriched data)
        executors: List[StrategyExecutor] = []
        
        for session in enriched_sessions:
            executor = StrategyExecutor(
                session=session,
                trade_date=trade_date,
                candle_store=candle_store,
                ltp_store=ltp_store,
                event_emitter=event_emitter
            )
            
            # Initialize with strategy config (already in enriched session)
            strategy_config = session.get("strategy_config", {})
            executor.initialize(strategy_config)
            
            executors.append(executor)
        
        log_info(f"[Orchestrator] Initialized {len(executors)} strategy executors")
        
        # =================================================================
        # TICK PROCESSING: Loop through tick batches
        # =================================================================
        log_info("[Orchestrator] ===== TICK PROCESSING =====")
        
        batch_count = 0
        total_ticks = 0
        
        tick_batches = list(data_source_manager.get_tick_batches())
        log_info(f"[Orchestrator] DataSourceManager returned {len(tick_batches)} tick batches")
        
        if len(tick_batches) == 0:
            log_error("[Orchestrator] No tick data available - check DataSourceManager initialization")
        
        for raw_batch in tick_batches:
            batch_count += 1
            
            # Convert to unified format
            unified_batch = tick_batch_processor.process_batch(raw_batch, data_source="clickhouse")
            
            total_ticks += len(unified_batch)
            
            # Get completed candles from CandleBuilder
            completed_candles = candle_builder.get_completed_candles()
            
            # Get LTP snapshot from LTPStore
            ltp_snapshot = ltp_store.get_all_ltps()
            
            # Broadcast to ALL executors simultaneously
            for executor in executors:
                executor.process_tick_batch(
                    unified_batch, 
                    completed_candles=completed_candles,
                    ltp_snapshot=ltp_snapshot
                )
            
            # Log progress
            if batch_count % 100 == 0:
                log_info(f"[Orchestrator] Processed {batch_count} batches, {total_ticks} ticks")
                if completed_candles:
                    log_info(f"[Orchestrator] Completed {len(completed_candles)} candles in last 100 batches")
        
        log_info(f"[Orchestrator] Tick processing complete: {batch_count} batches, {total_ticks} ticks")
        
        # =================================================================
        # FINALIZE: Finalize all executors
        # =================================================================
        log_info("[Orchestrator] ===== FINALIZING EXECUTORS =====")
        
        results = []
        for executor in executors:
            result = executor.finalize()
            results.append(result)
            
            # Save results to files
            if result.get("success"):
                _save_executor_results(executor.session, result)
        
        # Calculate summary
        successful = sum(1 for r in results if r.get("success"))
        failed = len(results) - successful
        
        log_info(f"[Orchestrator] Execution complete: {successful} successful, {failed} failed")
        
        # Print statistics
        _print_statistics(tick_batch_processor, candle_builder, event_emitter, executors)
        
        return {
            "total_sessions": len(sessions),
            "successful": successful,
            "failed": failed,
            "results": results,
            "batches_processed": batch_count,
            "ticks_processed": total_ticks
        }
        
    except Exception as e:
        log_error(f"[Orchestrator] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "total_sessions": len(sessions),
            "successful": 0,
            "failed": len(sessions),
            "results": [],
            "error": str(e)
        }


def _save_executor_results(session: Dict[str, Any], result: Dict[str, Any]):
    """Save executor results to session directory"""
    try:
        session_dir = Path("live_results") / session["user_id"] / session["session_id"]
        session_dir.mkdir(parents=True, exist_ok=True)
        
        dashboard_data = result.get("dashboard_data", {})
        diagnostics = result.get("diagnostics", {})
        summary = result.get("summary", {})
        
        # Save trades_daily.json.gz
        trades_data = {
            "date": session.get("meta_data", {}).get("trade_date"),
            "summary": summary,
            "trades": dashboard_data.get("positions", [])
        }
        
        trades_file = session_dir / "trades_daily.json.gz"
        with gzip.open(trades_file, 'wt') as f:
            json.dump(trades_data, f, indent=2)
        
        # Save diagnostics_export.json.gz
        diagnostics_file = session_dir / "diagnostics_export.json.gz"
        with gzip.open(diagnostics_file, 'wt') as f:
            json.dump(diagnostics, f, indent=2)
        
        log_info(f"[Orchestrator] Saved results for {session['session_id']}")
        
    except Exception as e:
        log_error(f"[Orchestrator] Error saving results: {e}")


def _print_statistics(tick_processor, candle_builder, event_emitter, executors):
    """Print execution statistics"""
    log_info("[Orchestrator] ===== EXECUTION STATISTICS =====")
    
    # Tick processor stats
    tick_stats = tick_processor.get_statistics()
    log_info(f"  TickBatchProcessor: {tick_stats['batches_processed']} batches, {tick_stats['ticks_processed']} ticks")
    
    # Candle builder stats
    candle_stats = candle_builder.get_statistics()
    log_info(f"  CandleBuilder: {candle_stats['candles_completed']} candles")
    
    # Event emitter stats
    event_stats = event_emitter.get_statistics()
    log_info(f"  EventEmitter: {event_stats['events_emitted']} events, {event_stats['sessions_registered']} sessions")
    
    # Executor stats
    for executor in executors:
        exec_stats = executor.get_statistics()
        log_info(f"  Executor[{executor.session_id}]: {exec_stats['ticks_processed']} ticks, {exec_stats['trades_completed']} trades")
    
    log_info("[Orchestrator] ==========================================")
