"""
CandleBuilder Module
Engine: Builds candles from ticks, applies indicators incrementally

Input: Unified tick
Output: Completed candles with indicators
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

from src.utils.logger import log_info, log_error, log_debug


class CandleBuilder:
    """
    Builds candles from tick data for all symbols and timeframes
    Applies indicators incrementally when candle completes
    
    Responsibilities:
    - Maintain incomplete candles per symbol:timeframe
    - Complete candles when timeframe period ends
    - Apply indicators incrementally
    - Append to CandleStore
    """
    
    def __init__(self, candle_store, indicator_registry):
        self.candle_store = candle_store
        self.indicator_registry = indicator_registry
        
        # Incomplete candles: {symbol: {timeframe: current_candle}}
        self.incomplete_candles: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
        
        # Track completed candles for broadcasting
        self.completed_candles: List[Dict[str, Any]] = []
        
        # Timeframe to minutes mapping
        self.timeframe_minutes = {
            "1m": 1, "3m": 3, "5m": 5, "10m": 10, "15m": 15,
            "30m": 30, "1h": 60, "1d": 1440
        }
        
        # Tracking
        self.candles_completed = 0
    
    def process_tick(self, unified_tick: Dict[str, Any]):
        """
        Process a tick for all timeframes
        
        Input: unified_tick - Tick in unified format
        Output: None (updates internal state, appends to CandleStore)
        
        Engine Contract:
        - Input: unified_tick (Dict)
        - Output: None
        - Side Effects: Updates incomplete candles, appends completed candles to CandleStore
        """
        symbol = unified_tick["symbol"]
        timestamp = unified_tick["timestamp"]
        ltp = unified_tick["ltp"]
        volume = unified_tick.get("volume", 0)
        
        # Process for all registered timeframes for this symbol
        for timeframe in self._get_timeframes_for_symbol(symbol):
            self._process_tick_for_timeframe(symbol, timeframe, timestamp, ltp, volume)
    
    def _get_timeframes_for_symbol(self, symbol: str) -> List[str]:
        """Get all timeframes registered for a symbol"""
        if symbol in self.candle_store.candles:
            return list(self.candle_store.candles[symbol].keys())
        return []
    
    def _process_tick_for_timeframe(self, symbol: str, timeframe: str, timestamp: str, ltp: float, volume: int):
        """Process tick for a specific symbol:timeframe"""
        try:
            # Parse timestamp
            tick_time = datetime.fromisoformat(timestamp.replace('+05:30', ''))
            
            # Get or create incomplete candle
            candle = self.incomplete_candles[symbol].get(timeframe)
            
            if not candle:
                # Start new candle
                candle = self._start_new_candle(symbol, timeframe, tick_time, ltp, volume)
                self.incomplete_candles[symbol][timeframe] = candle
            else:
                # Update existing candle
                candle_complete = self._update_candle(candle, timeframe, tick_time, ltp, volume)
                
                if candle_complete:
                    # Complete candle and apply indicators
                    self._complete_candle(symbol, timeframe, candle)
                    
                    # Start new candle
                    candle = self._start_new_candle(symbol, timeframe, tick_time, ltp, volume)
                    self.incomplete_candles[symbol][timeframe] = candle
        
        except Exception as e:
            log_error(f"[CandleBuilder] Error processing tick for {symbol}:{timeframe}: {e}")
    
    def _start_new_candle(self, symbol: str, timeframe: str, tick_time: datetime, ltp: float, volume: int) -> Dict[str, Any]:
        """Start a new candle"""
        # Calculate candle start time (aligned to timeframe)
        candle_start = self._align_to_timeframe(tick_time, timeframe)
        
        candle = {
            "timestamp": candle_start.isoformat(),
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp,
            "volume": volume,
            "ticks": 1
        }
        
        return candle
    
    def _update_candle(self, candle: Dict[str, Any], timeframe: str, tick_time: datetime, ltp: float, volume: int) -> bool:
        """
        Update incomplete candle with new tick
        
        Returns: True if candle is complete, False otherwise
        """
        # Calculate candle boundaries
        candle_start = datetime.fromisoformat(candle["timestamp"])
        candle_end = self._get_candle_end(candle_start, timeframe)
        
        # Check if tick belongs to this candle
        if tick_time >= candle_end:
            # Candle is complete
            return True
        
        # Update OHLC
        candle["high"] = max(candle["high"], ltp)
        candle["low"] = min(candle["low"], ltp)
        candle["close"] = ltp
        candle["volume"] += volume
        candle["ticks"] += 1
        
        return False
    
    def _complete_candle(self, symbol: str, timeframe: str, candle: Dict[str, Any]):
        """
        Complete candle and apply indicators
        
        Input: symbol, timeframe, completed candle
        Output: None (appends to CandleStore with indicators, tracks for broadcasting)
        """
        try:
            # Apply indicators incrementally
            candle_with_indicators = self._apply_indicators(symbol, timeframe, candle)
            
            # Append to CandleStore
            self.candle_store.append_candle(symbol, timeframe, candle_with_indicators)
            
            # Track completed candle for broadcasting
            self.completed_candles.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "candle": candle_with_indicators
            })
            
            self.candles_completed += 1
            
            log_debug(f"[CandleBuilder] Completed candle {symbol}:{timeframe} @ {candle['timestamp']}")
            
        except Exception as e:
            log_error(f"[CandleBuilder] Error completing candle: {e}")
    
    def _apply_indicators(self, symbol: str, timeframe: str, candle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply indicators incrementally to completed candle
        
        Uses indicator instances from registry to update incrementally
        """
        # Get indicators for this symbol:timeframe
        indicators = self.indicator_registry.get_indicators(symbol, timeframe)
        
        if not indicators:
            return candle
        
        # Apply each indicator incrementally
        for indicator_name, indicator_instance in indicators.items():
            try:
                # Incremental update (uses indicator's internal state)
                new_value = indicator_instance.update(candle)
                
                # Add to candle
                candle[indicator_name] = new_value
                
            except Exception as e:
                log_error(f"[CandleBuilder] Error applying indicator {indicator_name}: {e}")
        
        return candle
    
    def _align_to_timeframe(self, tick_time: datetime, timeframe: str) -> datetime:
        """Align timestamp to timeframe boundary"""
        minutes = self.timeframe_minutes.get(timeframe, 1)
        
        if timeframe == "1d":
            # Align to day start (09:15 for Indian markets)
            return tick_time.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # Align to nearest timeframe boundary
        minute = (tick_time.minute // minutes) * minutes
        return tick_time.replace(minute=minute, second=0, microsecond=0)
    
    def _get_candle_end(self, candle_start: datetime, timeframe: str) -> datetime:
        """Calculate candle end time"""
        minutes = self.timeframe_minutes.get(timeframe, 1)
        
        if timeframe == "1d":
            # End at 15:30
            return candle_start.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return candle_start + timedelta(minutes=minutes)
    
    def get_completed_candles(self) -> List[Dict[str, Any]]:
        """
        Get completed candles since last call and clear the list
        
        Returns: List of completed candles with symbol, timeframe, candle data
        """
        completed = self.completed_candles.copy()
        self.completed_candles.clear()
        return completed
    
    def get_statistics(self) -> Dict[str, int]:
        """Get builder statistics"""
        return {
            "candles_completed": self.candles_completed
        }


class IndicatorRegistry:
    """
    Registry of indicator instances for incremental calculation
    
    Maintains one indicator instance per symbol:timeframe:indicator
    Indicators maintain internal state for incremental updates
    """
    
    def __init__(self):
        # Structure: {symbol: {timeframe: {indicator_name: indicator_instance}}}
        self.indicators: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    
    def initialize_indicators(self, symbol: str, timeframe: str, indicator_configs: List[Dict[str, Any]]):
        """
        Initialize indicators for a symbol:timeframe
        
        Input: symbol, timeframe, indicator_configs
        Output: None (creates indicator instances)
        """
        for config in indicator_configs:
            try:
                indicator_name = config["name"]
                indicator_type = config["type"]
                params = config.get("params", {})
                
                # Create indicator instance (using ta_hybrid)
                indicator_instance = self._create_indicator(indicator_type, params)
                
                if indicator_instance:
                    self.indicators[symbol][timeframe][indicator_name] = indicator_instance
                    log_info(f"[IndicatorRegistry] Initialized {indicator_name} for {symbol}:{timeframe}")
                
            except Exception as e:
                log_error(f"[IndicatorRegistry] Error initializing indicator: {e}")
    
    def _create_indicator(self, indicator_type: str, params: Dict[str, Any]):
        """Create indicator instance"""
        try:
            # Import ta_hybrid indicators
            from src.indicators import ta_hybrid
            
            # Get indicator class
            indicator_class = getattr(ta_hybrid, indicator_type, None)
            
            if not indicator_class:
                log_error(f"[IndicatorRegistry] Unknown indicator type: {indicator_type}")
                return None
            
            # Create instance
            return indicator_class(**params)
            
        except Exception as e:
            log_error(f"[IndicatorRegistry] Error creating indicator: {e}")
            return None
    
    def get_indicators(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Get all indicators for a symbol:timeframe"""
        if symbol in self.indicators and timeframe in self.indicators[symbol]:
            return self.indicators[symbol][timeframe]
        return {}
