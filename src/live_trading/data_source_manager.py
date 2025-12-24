"""
DataSourceManager Module
Engine: Manages tick data loading and dynamic symbol registration

Input: Registered symbols from LTPStore
Output: Tick batches (JSONL format)
"""

from typing import Dict, List, Any, Set, Iterator
from datetime import datetime
import json

from src.utils.logger import log_info, log_error, log_debug


class DataSourceManager:
    """
    Manages tick data sources and dynamic symbol registration
    
    Responsibilities:
    - Load tick data for registered symbols
    - Support dynamic option symbol registration
    - Handle multiple data source formats
    - Emit tick batches
    """
    
    def __init__(self, trade_date: datetime, ltp_store):
        self.trade_date = trade_date
        self.ltp_store = ltp_store
        
        # Track loaded symbols
        self.loaded_symbols: Set[str] = set()
        
        # Tick iterator
        self.tick_iterator: Iterator = None
        
        # Data source (will be configured based on broker connection)
        self.data_source = None
    
    def initialize(self, metadata: Dict[str, Any]) -> bool:
        """
        Initialize data source and load ticks for registered symbols
        
        Input: metadata - {symbols: List, broker_connections: Dict}
        Output: True if successful
        
        Engine Contract:
        - Input: Metadata dictionary
        - Output: Boolean success status
        - Side Effects: Loads tick data, creates iterator
        """
        log_info(f"[DataSourceManager] Initializing for {len(metadata['symbols'])} symbols")
        
        # Get data source from broker connection metadata
        # For now, use ClickHouse as default
        self.data_source = self._create_data_source(metadata)
        
        # Load ticks for all registered symbols
        for symbol in metadata["symbols"]:
            self._load_symbol_ticks(symbol)
        
        log_info(f"[DataSourceManager] Initialization complete, loaded {len(self.loaded_symbols)} symbols")
        
        return True
    
    def _create_data_source(self, metadata: Dict[str, Any]):
        """Create appropriate data source based on broker connection"""
        # For now, use ClickHouse
        # In future, support multiple brokers
        try:
            from src.backtesting.clickhouse_data_loader import ClickHouseDataLoader
            return ClickHouseDataLoader()
        except Exception as e:
            log_error(f"[DataSourceManager] Error creating data source: {e}")
            return None
    
    def _load_symbol_ticks(self, symbol: str):
        """
        Load tick data for a symbol
        
        For now, this is a placeholder - actual tick loading happens
        during batch iteration
        """
        self.loaded_symbols.add(symbol)
        log_info(f"[DataSourceManager] Registered symbol for tick loading: {symbol}")
    
    def register_dynamic_symbol(self, symbol: str):
        """
        Register a new symbol dynamically (e.g., option contracts)
        
        Input: symbol - New symbol to track
        Output: None (updates internal state)
        
        Engine Contract:
        - Input: Symbol string
        - Output: None
        - Side Effects: Registers symbol in LTPStore, loads ticks
        """
        if symbol in self.loaded_symbols:
            return
        
        log_info(f"[DataSourceManager] Dynamically registering symbol: {symbol}")
        
        # Register in LTP store
        self.ltp_store.register_symbol(symbol)
        
        # Load ticks for this symbol (if available)
        self._load_symbol_ticks(symbol)
    
    def get_tick_batches(self) -> Iterator[List[Dict[str, Any]]]:
        """
        Get tick batches iterator
        
        Input: None
        Output: Iterator yielding tick batches
        
        Engine Contract:
        - Input: None
        - Output: Iterator[List[Dict]] - tick batches
        - Side Effects: Reads from data source
        
        Tick Batch Format:
        - List of ticks (JSONL-compatible)
        - Each tick: {symbol, timestamp, ltp, volume, etc.}
        """
        # For now, load all ticks and batch them
        # In future, support streaming from broker
        
        try:
            # Load ticks from ClickHouse
            all_ticks = self._load_all_ticks()
            
            # Batch ticks by timestamp (1-second batches)
            batches = self._batch_ticks_by_time(all_ticks)
            
            for batch in batches:
                yield batch
                
        except Exception as e:
            log_error(f"[DataSourceManager] Error getting tick batches: {e}")
            return
    
    def _load_all_ticks(self) -> List[Dict[str, Any]]:
        """Load all ticks for registered symbols"""
        all_ticks = []
        
        if not self.data_source:
            return all_ticks
        
        try:
            # Load ticks for each symbol
            for symbol in self.loaded_symbols:
                # Use existing data loader to get tick data
                # For now, we'll use candle data as tick proxy
                # In production, load actual tick data
                
                from src.backtesting.clickhouse_data_loader import ClickHouseDataLoader
                loader = ClickHouseDataLoader()
                
                # Load minute data as tick proxy
                df = loader.load_data(
                    symbol=symbol,
                    timeframe="1m",
                    start_date=self.trade_date,
                    end_date=self.trade_date
                )
                
                if df is not None and not df.empty:
                    # Convert to tick format
                    for _, row in df.iterrows():
                        tick = {
                            "symbol": symbol,
                            "timestamp": row.get("timestamp", row.get("time", "")),
                            "ltp": row.get("close", 0),
                            "volume": row.get("volume", 0),
                            "high": row.get("high", 0),
                            "low": row.get("low", 0),
                            "open": row.get("open", 0)
                        }
                        all_ticks.append(tick)
            
            # Sort by timestamp
            all_ticks.sort(key=lambda x: x["timestamp"])
            
            log_info(f"[DataSourceManager] Loaded {len(all_ticks)} ticks")
            
        except Exception as e:
            log_error(f"[DataSourceManager] Error loading ticks: {e}")
        
        return all_ticks
    
    def _batch_ticks_by_time(self, ticks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Batch ticks by timestamp (1-second batches)
        
        Input: all_ticks sorted by timestamp
        Output: List of batches
        """
        if not ticks:
            return []
        
        batches = []
        current_batch = []
        current_timestamp = None
        
        for tick in ticks:
            tick_timestamp = tick["timestamp"]
            
            if current_timestamp is None:
                current_timestamp = tick_timestamp
                current_batch.append(tick)
            elif tick_timestamp == current_timestamp:
                current_batch.append(tick)
            else:
                # New timestamp, save current batch and start new one
                if current_batch:
                    batches.append(current_batch)
                current_batch = [tick]
                current_timestamp = tick_timestamp
        
        # Add last batch
        if current_batch:
            batches.append(current_batch)
        
        log_info(f"[DataSourceManager] Created {len(batches)} tick batches")
        
        return batches
