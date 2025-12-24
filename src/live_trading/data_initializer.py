"""
DataInitializer Module
Engine: Initializes CandleStore and LTPStore for all required symbols/timeframes

Input: Metadata (symbols, timeframes)
Output: Initialized CandleStore and LTPStore
"""

from typing import Dict, List, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict

from src.backtesting.data_manager import DataManager
from src.utils.logger import log_info, log_error


class CandleStore:
    """
    Stores historical candles for all symbols and timeframes
    Maintains 500 historical candles per symbol:timeframe
    """
    
    def __init__(self):
        # Structure: {symbol: {timeframe: [candles]}}
        self.candles: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self.max_candles = 500
    
    def initialize(self, symbol: str, timeframe: str, historical_candles: List[Dict[str, Any]]):
        """
        Initialize candle buffer for a symbol:timeframe
        
        Input: symbol, timeframe, historical_candles (500 candles)
        Output: None (updates internal state)
        """
        # Take last 500 candles
        self.candles[symbol][timeframe] = historical_candles[-self.max_candles:]
        log_info(f"[CandleStore] Initialized {symbol}:{timeframe} with {len(self.candles[symbol][timeframe])} candles")
    
    def append_candle(self, symbol: str, timeframe: str, candle: Dict[str, Any]):
        """
        Append a completed candle and maintain buffer size
        
        Input: symbol, timeframe, candle
        Output: None (updates internal state)
        """
        if symbol not in self.candles or timeframe not in self.candles[symbol]:
            log_error(f"[CandleStore] Symbol {symbol}:{timeframe} not initialized")
            return
        
        self.candles[symbol][timeframe].append(candle)
        
        # Maintain max buffer size
        if len(self.candles[symbol][timeframe]) > self.max_candles:
            self.candles[symbol][timeframe] = self.candles[symbol][timeframe][-self.max_candles:]
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get candles for a symbol:timeframe
        
        Input: symbol, timeframe, optional limit
        Output: List of candles
        """
        if symbol not in self.candles or timeframe not in self.candles[symbol]:
            return []
        
        candles = self.candles[symbol][timeframe]
        return candles[-limit:] if limit else candles


class LTPStore:
    """
    Stores Latest Traded Price (LTP) for all symbols
    Includes underlying and derivatives
    """
    
    def __init__(self):
        # Structure: {symbol: {ltp: float, timestamp: str, volume: int, oi: int}}
        self.ltps: Dict[str, Dict[str, Any]] = {}
        self.registered_symbols: Set[str] = set()
    
    def register_symbol(self, symbol: str):
        """
        Register a symbol for LTP tracking
        
        Input: symbol
        Output: None (updates internal state)
        """
        if symbol not in self.registered_symbols:
            self.registered_symbols.add(symbol)
            self.ltps[symbol] = {"ltp": 0.0, "timestamp": None, "volume": 0, "oi": 0}
            log_info(f"[LTPStore] Registered symbol: {symbol}")
    
    def update_ltp(self, symbol: str, ltp: float, timestamp: str = None, volume: int = None, oi: int = None):
        """
        Update LTP for a symbol
        
        Input: symbol, ltp, optional metadata
        Output: None (updates internal state)
        """
        if symbol not in self.registered_symbols:
            # Auto-register if not registered (for dynamic options)
            self.register_symbol(symbol)
        
        self.ltps[symbol] = {
            "ltp": ltp,
            "timestamp": timestamp or datetime.now().isoformat(),
            "volume": volume or 0,
            "oi": oi or 0
        }
    
    def get_ltp(self, symbol: str) -> Dict[str, Any]:
        """
        Get LTP data for a symbol
        
        Input: symbol
        Output: LTP data dictionary
        """
        return self.ltps.get(symbol, {"ltp": 0.0, "timestamp": None, "volume": 0, "oi": 0})
    
    def is_registered(self, symbol: str) -> bool:
        """Check if symbol is registered"""
        return symbol in self.registered_symbols


class DataInitializer:
    """
    Initializes CandleStore and LTPStore based on metadata
    One-time activity per execution
    """
    
    def __init__(self, trade_date: datetime, user_id: str):
        self.trade_date = trade_date
        self.user_id = user_id
        
        self.candle_store: CandleStore = None
        self.ltp_store: LTPStore = None
    
    def initialize(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize data stores based on scanned metadata
        
        Input: metadata - {symbols: List, timeframes: List, strategy_configs: Dict}
        Output: {candle_store: CandleStore, ltp_store: LTPStore}
        
        Engine Contract:
        - Input: Metadata dictionary
        - Output: {candle_store, ltp_store}
        - Side Effects: Loads historical data from data sources
        """
        log_info(f"[DataInitializer] Initializing data stores for {len(metadata['symbols'])} symbols")
        
        # Initialize stores
        self.candle_store = CandleStore()
        self.ltp_store = LTPStore()
        
        # Load data for each symbol:timeframe combination
        for symbol in metadata["symbols"]:
            for timeframe in metadata["timeframes"]:
                self._initialize_symbol_timeframe(symbol, timeframe)
        
        # Register all symbols in LTP store
        for symbol in metadata["symbols"]:
            self.ltp_store.register_symbol(symbol)
        
        log_info(f"[DataInitializer] Initialization complete")
        
        return {
            "candle_store": self.candle_store,
            "ltp_store": self.ltp_store
        }
    
    def _initialize_symbol_timeframe(self, symbol: str, timeframe: str):
        """
        Load 500 historical candles for a symbol:timeframe
        Apply indicators during initialization
        """
        try:
            log_info(f"[DataInitializer] Loading historical data for {symbol}:{timeframe}")
            
            # Use existing DataManager to load historical data
            # We'll create a temporary DataManager just for loading
            # This reuses existing data loading logic
            from src.backtesting.data_manager import DataManager
            
            # Create temporary data manager for this symbol:timeframe
            # We need a strategy_id for DataManager - use first strategy that has this symbol
            # For now, we'll use a placeholder approach
            
            # Load historical candles (500 candles)
            historical_candles = self._load_historical_candles(symbol, timeframe)
            
            # Initialize candle store with historical data
            self.candle_store.initialize(symbol, timeframe, historical_candles)
            
            log_info(f"[DataInitializer] Loaded {len(historical_candles)} candles for {symbol}:{timeframe}")
            
        except Exception as e:
            log_error(f"[DataInitializer] Error loading data for {symbol}:{timeframe}: {e}")
    
    def _load_historical_candles(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Load historical candles from data source
        
        For now, use existing ClickHouse loader
        In future, this will be abstracted to support multiple data sources
        """
        try:
            from src.backtesting.clickhouse_data_loader import ClickHouseDataLoader
            
            loader = ClickHouseDataLoader()
            
            # Calculate start date (need enough days to get 500 candles)
            # Use conservative estimate based on timeframe
            days_needed = self._calculate_days_needed(timeframe, 500)
            start_date = self.trade_date - timedelta(days=days_needed)
            
            # Load data
            df = loader.load_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=self.trade_date
            )
            
            if df is not None and not df.empty:
                # Convert to list of dicts
                candles = df.to_dict('records')
                return candles[-500:]  # Take last 500
            
            return []
            
        except Exception as e:
            log_error(f"[DataInitializer] Error loading candles: {e}")
            return []
    
    def _calculate_days_needed(self, timeframe: str, candles_count: int) -> int:
        """
        Calculate how many calendar days needed to get N candles
        
        Includes buffer for holidays/weekends
        """
        # Conservative estimates with 50% buffer for holidays
        timeframe_to_days = {
            "1m": 7,    # 500 candles ≈ 8.3 hours ≈ 2 trading days → 7 calendar days
            "3m": 10,
            "5m": 15,
            "10m": 20,
            "15m": 30,
            "30m": 50,
            "1h": 80,
            "1d": 750   # 500 trading days ≈ 2 years → 750 calendar days
        }
        
        return timeframe_to_days.get(timeframe, 30)
