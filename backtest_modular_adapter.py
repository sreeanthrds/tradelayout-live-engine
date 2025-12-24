"""
Backtest Modular Adapter
Bridges legacy backtest API and modular live_strategy_executor

Purpose:
- Load strategy config directly from Supabase (bypass SessionDataLoader)
- Prepare enriched session format for modular components
- Run modular execution to generate JSONL files
- Ensure JSONL outputs match legacy JSON.gz structure

Output Files:
- nodes.jsonl → should match diagnostics_export.json.gz events_history
- trades.jsonl → should match trades_daily.json.gz trades array
- Also generates trades_daily.json.gz + diagnostics_export.json.gz for compatibility
"""

import os
import json
import gzip
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from supabase import create_client, Client

# Set environment variables if not already set
if 'SUPABASE_URL' not in os.environ:
    os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokg.supabase.co'
if 'SUPABASE_SERVICE_ROLE_KEY' not in os.environ:
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
if 'CLICKHOUSE_DATA_TIMEZONE' not in os.environ:
    os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

from src.utils.logger import log_info, log_error

# Import modular components directly (bypass live_strategy_executor)
from src.live_trading import (
    MetadataScanner,
    DataInitializer,
    DataSourceManager,
    TickBatchProcessor,
    CandleBuilder,
    IndicatorRegistry,
    StrategyExecutor,
    EventEmitter
)


class BacktestModularAdapter:
    """
    Adapter to run modular live_strategy_executor for backtesting
    """
    
    def __init__(self):
        # Initialize Supabase client
        self.supabase: Client = create_client(
            os.environ['SUPABASE_URL'],
            os.environ['SUPABASE_SERVICE_ROLE_KEY']
        )
    
    def load_strategy_from_supabase(self, strategy_id: str) -> Dict[str, Any]:
        """
        Load strategy config directly from Supabase
        
        Returns:
            {
                "id": "...",
                "name": "...",
                "config": {...},  # Full strategy JSON
                "user_id": "..."
            }
        """
        log_info(f"[BacktestAdapter] Loading strategy {strategy_id} from Supabase")
        
        response = self.supabase.table("strategies").select("*").eq("id", strategy_id).execute()
        
        if not response.data or len(response.data) == 0:
            log_error(f"[BacktestAdapter] Strategy {strategy_id} not found")
            return None
        
        strategy = response.data[0]
        
        log_info(f"[BacktestAdapter] Loaded strategy: {strategy.get('name')}")
        
        return {
            "id": strategy.get("id"),
            "name": strategy.get("name"),
            "config": strategy.get("config", {}),
            "user_id": strategy.get("user_id")
        }

    def prepare_enriched_session(
        self,
        strategy_id: str,
        trade_date: str,
        user_id: str = "backtest_user",
        scale: float = 1.0
    ) -> Dict[str, Any]:
        """
        Prepare enriched session format that live_strategy_executor expects
        
        Args:
            strategy_id: Strategy UUID
            trade_date: Trade date in YYYY-MM-DD format
            user_id: User ID (default: backtest_user)
            scale: Strategy scale multiplier
        
        Returns:
            Enriched session dict with strategy_config ready for modular execution
        """
        # Load strategy from Supabase
        strategy = self.load_strategy_from_supabase(strategy_id)
        
        if not strategy:
            raise ValueError(f"Failed to load strategy {strategy_id}")
        
        # Prepare enriched session
        enriched_session = {
            "session_id": f"{strategy_id}_{trade_date}",
            "strategy_id": strategy_id,
            "user_id": user_id,
            "execution_date": trade_date,
            "scale": scale,
            "enabled": True,
            
            # Meta data for modular components
            "meta_data": {
                "trade_date": trade_date,
                "mode": "backtesting"
            },
            
            # Strategy details (loaded from Supabase)
            "strategy_name": strategy.get("name"),
            "strategy_config": strategy.get("config"),
            
            # Broker details (dummy for backtesting)
            "broker_name": "backtest_broker",
            "broker_connection_id": "backtest_connection"
        }
        
        log_info(f"[BacktestAdapter] Prepared enriched session for {strategy.get('name')}")
        
        return enriched_session
    
    async def run_modular_backtest(
        self,
        strategy_id: str,
        trade_date: str,
        user_id: str = "backtest_user",
        scale: float = 1.0
    ) -> Dict[str, Any]:
        """
        Run modular backtest using modular components directly
        
        Args:
            strategy_id: Strategy UUID
            trade_date: Trade date in YYYY-MM-DD format
            user_id: User ID
            scale: Strategy scale multiplier
        
        Returns:
            Execution results with JSONL files generated
        """
        log_info(f"[BacktestAdapter] Starting modular backtest for {trade_date}")
        
        # Prepare enriched session
        enriched_session = self.prepare_enriched_session(
            strategy_id=strategy_id,
            trade_date=trade_date,
            user_id=user_id,
            scale=scale
        )
        
        session_id = enriched_session["session_id"]
        trade_date_obj = datetime.strptime(trade_date, "%Y-%m-%d")
        
        # ================================================================
        # MODULE 1: MetadataScanner - Extract symbols/timeframes
        # ================================================================
        log_info("[BacktestAdapter] Scanning metadata...")
        metadata_scanner = MetadataScanner()
        metadata = metadata_scanner.scan([enriched_session])
        
        log_info(f"[BacktestAdapter] Found {len(metadata['symbols'])} symbols, {len(metadata['timeframes'])} timeframes")
        
        # ================================================================
        # MODULE 2: DataInitializer - Initialize stores
        # ================================================================
        log_info("[BacktestAdapter] Initializing data stores...")
        data_initializer = DataInitializer(trade_date_obj, user_id)
        stores = data_initializer.initialize(metadata)
        
        candle_store = stores["candle_store"]
        ltp_store = stores["ltp_store"]
        
        # ================================================================
        # MODULE 3: DataSourceManager - Load tick data
        # ================================================================
        log_info("[BacktestAdapter] Loading tick data...")
        data_source_manager = DataSourceManager(trade_date_obj, ltp_store)
        data_source_manager.initialize(metadata)
        
        # ================================================================
        # MODULE 4: Initialize components
        # ================================================================
        log_info("[BacktestAdapter] Initializing components...")
        indicator_registry = IndicatorRegistry()
        candle_builder = CandleBuilder(candle_store, indicator_registry)
        tick_batch_processor = TickBatchProcessor(ltp_store, candle_builder)
        
        # ================================================================
        # MODULE 5: EventEmitter - Initialize event emitter
        # ================================================================
        log_info("[BacktestAdapter] Initializing event emitter...")
        event_emitter = EventEmitter(Path("live_results"))
        event_emitter.register_session(session_id, user_id)
        
        # ================================================================
        # MODULE 6: StrategyExecutor - Initialize executor
        # ================================================================
        log_info("[BacktestAdapter] Initializing strategy executor...")
        executor = StrategyExecutor(
            session=enriched_session,
            trade_date=trade_date_obj,
            candle_store=candle_store,
            ltp_store=ltp_store,
            event_emitter=event_emitter
        )
        
        # Initialize with strategy config
        strategy_config = enriched_session.get("strategy_config", {})
        executor.initialize(strategy_config)
        
        # ================================================================
        # TICK PROCESSING: Process tick batches
        # ================================================================
        log_info("[BacktestAdapter] Processing ticks...")
        
        batch_count = 0
        total_ticks = 0
        
        tick_batches = list(data_source_manager.get_tick_batches())
        log_info(f"[BacktestAdapter] Processing {len(tick_batches)} tick batches")
        
        for raw_batch in tick_batches:
            batch_count += 1
            
            # Convert to unified format
            unified_batch = tick_batch_processor.process_batch(raw_batch, data_source="clickhouse")
            total_ticks += len(unified_batch)
            
            # Get completed candles
            completed_candles = candle_builder.get_completed_candles()
            
            # Get LTP snapshot
            ltp_snapshot = ltp_store.get_all_ltps()
            
            # Process tick batch
            executor.process_tick_batch(
                unified_batch,
                completed_candles=completed_candles,
                ltp_snapshot=ltp_snapshot
            )
            
            # Log progress
            if batch_count % 100 == 0:
                log_info(f"[BacktestAdapter] Processed {batch_count} batches, {total_ticks} ticks")
        
        log_info(f"[BacktestAdapter] Tick processing complete: {batch_count} batches, {total_ticks} ticks")
        
        # ================================================================
        # FINALIZE: Finalize executor
        # ================================================================
        log_info("[BacktestAdapter] Finalizing executor...")
        result = executor.finalize()
        
        # Convert JSONL files to backtest format
        self._convert_to_backtest_format(
            strategy_id=strategy_id,
            trade_date=trade_date,
            session_id=session_id,
            user_id=user_id,
            session_result=result
        )
        
        log_info(f"[BacktestAdapter] Modular backtest completed successfully")
        return result
    
    def _convert_to_backtest_format(
        self,
        strategy_id: str,
        trade_date: str,
        session_id: str,
        user_id: str,
        session_result: Dict[str, Any]
    ):
        """
        Convert JSONL files to backtest_results/ format
        Also generate compressed JSON.gz files for compatibility
        
        JSONL files location: live_results/{user_id}/{session_id}/
        - nodes.jsonl
        - trades.jsonl
        - events.jsonl
        - ticks.jsonl
        - positions.jsonl
        
        Backtest files location: backtest_results/{strategy_id}/{trade_date}/
        - nodes.jsonl (copy)
        - trades.jsonl (copy)
        - trades_daily.json.gz (converted)
        - diagnostics_export.json.gz (converted)
        """
        log_info(f"[BacktestAdapter] Converting to backtest format")
        
        # Source directory (JSONL files)
        source_dir = Path("live_results") / user_id / session_id
        
        # Destination directory
        dest_dir = Path("backtest_results") / strategy_id / trade_date
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy JSONL files
        import shutil
        jsonl_files = ["nodes.jsonl", "trades.jsonl", "events.jsonl", "ticks.jsonl", "positions.jsonl"]
        for filename in jsonl_files:
            source_file = source_dir / filename
            if source_file.exists():
                dest_file = dest_dir / filename
                shutil.copy2(source_file, dest_file)
                log_info(f"[BacktestAdapter] Copied {filename}")
        
        # Convert nodes.jsonl to diagnostics_export.json.gz
        self._convert_nodes_to_diagnostics(source_dir, dest_dir)
        
        # Convert trades.jsonl to trades_daily.json.gz
        self._convert_trades_to_daily(source_dir, dest_dir, trade_date, session_result)
        
        log_info(f"[BacktestAdapter] Conversion complete")
    
    def _convert_nodes_to_diagnostics(self, source_dir: Path, dest_dir: Path):
        """
        Convert nodes.jsonl to diagnostics_export.json.gz
        
        nodes.jsonl format (line per node execution):
        {"snapshot_id": 1, "execution_id": "...", "node_id": "...", ...}
        
        diagnostics_export.json.gz format:
        {
            "events_history": {
                "exec_...": {...},
                "exec_...": {...}
            }
        }
        """
        nodes_file = source_dir / "nodes.jsonl"
        
        if not nodes_file.exists():
            log_error(f"[BacktestAdapter] nodes.jsonl not found")
            return
        
        events_history = {}
        
        # Read nodes.jsonl line by line
        with open(nodes_file, 'r') as f:
            for line in f:
                if line.strip():
                    node_event = json.loads(line)
                    execution_id = node_event.get("execution_id")
                    if execution_id:
                        # Remove snapshot_id (not in diagnostics)
                        node_event.pop("snapshot_id", None)
                        events_history[execution_id] = node_event
        
        # Save as diagnostics_export.json.gz
        diagnostics_data = {"events_history": events_history}
        
        diagnostics_file = dest_dir / "diagnostics_export.json.gz"
        with gzip.open(diagnostics_file, 'wt') as f:
            json.dump(diagnostics_data, f, indent=2)
        
        log_info(f"[BacktestAdapter] Created diagnostics_export.json.gz with {len(events_history)} events")
    
    def _convert_trades_to_daily(
        self,
        source_dir: Path,
        dest_dir: Path,
        trade_date: str,
        session_result: Dict[str, Any]
    ):
        """
        Convert trades.jsonl to trades_daily.json.gz
        
        trades.jsonl format (line per trade):
        {"snapshot_id": 1, "event": "trade", "position_id": "...", ...}
        
        trades_daily.json.gz format:
        {
            "date": "2024-10-29",
            "summary": {...},
            "trades": [...]
        }
        """
        trades_file = source_dir / "trades.jsonl"
        
        if not trades_file.exists():
            log_error(f"[BacktestAdapter] trades.jsonl not found")
            return
        
        trades = []
        
        # Read trades.jsonl line by line
        with open(trades_file, 'r') as f:
            for line in f:
                if line.strip():
                    trade_event = json.loads(line)
                    # Remove snapshot_id and event type (not in trades_daily)
                    trade_event.pop("snapshot_id", None)
                    trade_event.pop("event", None)
                    trades.append(trade_event)
        
        # Get summary from session_result
        summary = session_result.get("summary", {})
        
        # Save as trades_daily.json.gz
        trades_data = {
            "date": trade_date,
            "summary": summary,
            "trades": trades
        }
        
        trades_daily_file = dest_dir / "trades_daily.json.gz"
        with gzip.open(trades_daily_file, 'wt') as f:
            json.dump(trades_data, f, indent=2)
        
        log_info(f"[BacktestAdapter] Created trades_daily.json.gz with {len(trades)} trades")


async def run_backtest_with_modular_executor(
    strategy_id: str,
    trade_date: str,
    user_id: str = "backtest_user",
    scale: float = 1.0
) -> Dict[str, Any]:
    """
    Convenience function to run modular backtest
    
    Args:
        strategy_id: Strategy UUID
        trade_date: Trade date in YYYY-MM-DD format
        user_id: User ID
        scale: Strategy scale multiplier
    
    Returns:
        Execution results
    """
    adapter = BacktestModularAdapter()
    return await adapter.run_modular_backtest(
        strategy_id=strategy_id,
        trade_date=trade_date,
        user_id=user_id,
        scale=scale
    )


if __name__ == "__main__":
    # Test the adapter
    import sys
    
    # if len(sys.argv) < 3:
    #     print("Usage: python backtest_modular_adapter.py <strategy_id> <trade_date>")
    #     sys.exit(1)
    #
    # strategy_id = sys.argv[1]
    # trade_date = sys.argv[2]

    strategy_id="d70ec04a-1025-46c5-94c4-3e6bff499644"
    trade_date="2024-10-29"
    
    result = asyncio.run(run_backtest_with_modular_executor(strategy_id, trade_date))
    
    if result.get("success"):
        print(f"✅ Modular backtest completed successfully")
        print(f"   Files generated in backtest_results/{strategy_id}/{trade_date}/")
    else:
        print(f"❌ Modular backtest failed: {result.get('error')}")
