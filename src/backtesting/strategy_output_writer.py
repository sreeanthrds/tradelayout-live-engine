"""
Strategy Output Writer
======================

Handles per-strategy file output for unified execution engine.
Creates isolated output directories and manages incremental/batch writes.

Directory Structure:
    backtest_data/
        ├── {user_id}/
        │   ├── {strategy_id}_{broker_connection_id}/
        │   │   ├── positions.json
        │   │   ├── trades.json
        │   │   ├── metrics.json
        │   │   └── events.jsonl
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class StrategyOutputWriter:
    """
    Manages file output for a single strategy in unified execution engine.
    
    Supports two write modes:
    - Batch mode (backtesting): Write all results at end
    - Incremental mode (live simulation): Write updates as they happen
    """
    
    def __init__(
        self,
        user_id: str,
        strategy_id: str,
        broker_connection_id: str,
        mode: str = "backtest",
        base_dir: str = "backtest_data"
    ):
        """
        Initialize output writer for a strategy.
        
        Args:
            user_id: User ID
            strategy_id: Strategy ID
            broker_connection_id: Broker connection ID
            mode: "backtest" (batch writes) or "live_simulation" (incremental writes)
            base_dir: Base directory for output files
        """
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.broker_connection_id = broker_connection_id
        self.mode = mode
        
        # Create folder name: {strategy_id}_{broker_connection_id}
        # Truncate IDs to 13 chars for reasonable folder names
        strategy_short = strategy_id[:13] if len(strategy_id) > 13 else strategy_id
        broker_short = broker_connection_id[:13] if len(broker_connection_id) > 13 else broker_connection_id
        folder_name = f"{strategy_short}_{broker_short}"
        
        # Create output directory structure
        self.output_dir = Path(base_dir) / user_id / folder_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.positions_file = self.output_dir / "positions.json"
        self.trades_file = self.output_dir / "trades.json"
        self.metrics_file = self.output_dir / "metrics.json"
        self.events_file = self.output_dir / "events.jsonl"
        
        # In-memory buffers for batch mode
        self.positions_buffer: Dict[str, Any] = {}
        self.trades_buffer: List[Dict[str, Any]] = []
        self.metrics_buffer: Dict[str, Any] = {}
        
        logger.info(f"📁 Output writer initialized: {self.output_dir}")
    
    def write_position_update(self, position_data: Dict[str, Any]):
        """
        Write or update a single position.
        
        In batch mode: Stores in buffer
        In incremental mode: Writes to file immediately
        
        Args:
            position_data: Position data dict
        """
        position_id = position_data.get('position_id')
        
        if self.mode == "live_simulation":
            # Incremental write: Read existing, update, write back
            try:
                existing = self._read_json(self.positions_file) if self.positions_file.exists() else {}
                existing[position_id] = position_data
                self._write_json(self.positions_file, existing)
            except Exception as e:
                logger.warning(f"Failed to write position update: {e}")
        else:
            # Batch mode: Store in buffer
            self.positions_buffer[position_id] = position_data
    
    def write_trade(self, trade_data: Dict[str, Any]):
        """
        Write a trade record.
        
        Args:
            trade_data: Trade data dict
        """
        if self.mode == "live_simulation":
            # Incremental: Append to trades file
            try:
                existing = self._read_json(self.trades_file) if self.trades_file.exists() else []
                existing.append(trade_data)
                self._write_json(self.trades_file, existing)
            except Exception as e:
                logger.warning(f"Failed to write trade: {e}")
        else:
            # Batch mode: Store in buffer
            self.trades_buffer.append(trade_data)
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """
        Update strategy metrics.
        
        Args:
            metrics: Metrics dict (P&L, positions count, etc.)
        """
        if self.mode == "live_simulation":
            # Incremental: Overwrite metrics file
            try:
                self._write_json(self.metrics_file, metrics)
            except Exception as e:
                logger.warning(f"Failed to write metrics: {e}")
        else:
            # Batch mode: Store in buffer
            self.metrics_buffer = metrics
    
    def write_event(self, event_data: Dict[str, Any]):
        """
        Write an event to the events log (JSONL format).
        
        Args:
            event_data: Event data dict
        """
        try:
            with open(self.events_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write event: {e}")
    
    def flush_batch(self):
        """
        Write all buffered data to files (batch mode).
        Called at end of backtest.
        """
        if self.mode == "backtest":
            try:
                # Write positions
                if self.positions_buffer:
                    self._write_json(self.positions_file, self.positions_buffer)
                    logger.info(f"✅ Wrote {len(self.positions_buffer)} positions to {self.positions_file}")
                
                # Write trades
                if self.trades_buffer:
                    self._write_json(self.trades_file, self.trades_buffer)
                    logger.info(f"✅ Wrote {len(self.trades_buffer)} trades to {self.trades_file}")
                
                # Write metrics
                if self.metrics_buffer:
                    self._write_json(self.metrics_file, self.metrics_buffer)
                    logger.info(f"✅ Wrote metrics to {self.metrics_file}")
                
            except Exception as e:
                logger.error(f"Failed to flush batch: {e}")
    
    def get_positions(self) -> Dict[str, Any]:
        """Get all positions (from buffer or file)."""
        if self.mode == "backtest":
            return self.positions_buffer.copy()
        else:
            return self._read_json(self.positions_file) if self.positions_file.exists() else {}
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all trades (from buffer or file)."""
        if self.mode == "backtest":
            return self.trades_buffer.copy()
        else:
            return self._read_json(self.trades_file) if self.trades_file.exists() else []
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics (from buffer or file)."""
        if self.mode == "backtest":
            return self.metrics_buffer.copy()
        else:
            return self._read_json(self.metrics_file) if self.metrics_file.exists() else {}
    
    def _read_json(self, file_path: Path) -> Any:
        """Read JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return {} if file_path.name == "positions.json" or file_path.name == "metrics.json" else []
    
    def _write_json(self, file_path: Path, data: Any):
        """Write JSON file with pretty formatting."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")
