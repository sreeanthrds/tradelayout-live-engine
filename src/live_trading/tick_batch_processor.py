"""
TickBatchProcessor Module
Engine: Processes tick batches, converts to unified format, updates stores

Input: Raw tick batch (JSONL format)
Output: Processed tick batch in unified format
"""

from typing import Dict, List, Any
from datetime import datetime
import json

from src.utils.logger import log_info, log_error, log_debug


class UnifiedTickFormat:
    """
    Unified tick format for all data sources
    
    Standard format:
    {
        "symbol": "NIFTY",  # Unified symbol name
        "timestamp": "2024-10-29 09:15:00",
        "ltp": 25500.00,
        "volume": 1000,
        "oi": 50000,  # Optional for futures/options
        "bid": 25499.50,  # Optional
        "ask": 25500.50,  # Optional
        "source": "clickhouse"  # Data source identifier
    }
    """
    
    @staticmethod
    def from_clickhouse(raw_tick: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ClickHouse format to unified format"""
        return {
            "symbol": raw_tick.get("symbol", ""),
            "timestamp": raw_tick.get("timestamp", ""),
            "ltp": raw_tick.get("ltp", raw_tick.get("close", 0)),
            "volume": raw_tick.get("volume", 0),
            "oi": raw_tick.get("oi", 0),
            "high": raw_tick.get("high", 0),
            "low": raw_tick.get("low", 0),
            "open": raw_tick.get("open", 0),
            "source": "clickhouse"
        }
    
    @staticmethod
    def from_angelone(raw_tick: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AngelOne format to unified format"""
        return {
            "symbol": raw_tick.get("trading_symbol", ""),
            "timestamp": raw_tick.get("exchange_timestamp", ""),
            "ltp": raw_tick.get("last_traded_price", 0),
            "volume": raw_tick.get("volume", 0),
            "oi": raw_tick.get("open_interest", 0),
            "bid": raw_tick.get("best_bid_price", 0),
            "ask": raw_tick.get("best_ask_price", 0),
            "source": "angelone"
        }
    
    @staticmethod
    def from_zerodha(raw_tick: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zerodha format to unified format"""
        return {
            "symbol": raw_tick.get("instrument_token", ""),
            "timestamp": raw_tick.get("timestamp", ""),
            "ltp": raw_tick.get("last_price", 0),
            "volume": raw_tick.get("volume", 0),
            "oi": raw_tick.get("oi", 0),
            "bid": raw_tick.get("depth", {}).get("buy", [{}])[0].get("price", 0),
            "ask": raw_tick.get("depth", {}).get("sell", [{}])[0].get("price", 0),
            "source": "zerodha"
        }


class TickBatchProcessor:
    """
    Processes tick batches from various sources
    
    Responsibilities:
    - Parse JSONL batches
    - Convert to unified format
    - Update LTPStore
    - Feed to CandleBuilder
    """
    
    def __init__(self, ltp_store, candle_builder):
        self.ltp_store = ltp_store
        self.candle_builder = candle_builder
        self.converter = UnifiedTickFormat()
        
        # Track batch statistics
        self.batches_processed = 0
        self.ticks_processed = 0
    
    def process_batch(self, raw_batch: List[Dict[str, Any]], data_source: str = "clickhouse") -> List[Dict[str, Any]]:
        """
        Process a tick batch
        
        Input: raw_batch - List of raw ticks, data_source - source identifier
        Output: List of unified format ticks
        
        Engine Contract:
        - Input: raw_batch (List[Dict]), data_source (str)
        - Output: unified_batch (List[Dict])
        - Side Effects: Updates LTPStore, feeds CandleBuilder
        """
        self.batches_processed += 1
        unified_batch = []
        
        for raw_tick in raw_batch:
            try:
                # Convert to unified format
                unified_tick = self._convert_to_unified(raw_tick, data_source)
                
                if not unified_tick:
                    continue
                
                # Update LTPStore
                self._update_ltp_store(unified_tick)
                
                # Feed to CandleBuilder
                self._feed_to_candle_builder(unified_tick)
                
                unified_batch.append(unified_tick)
                self.ticks_processed += 1
                
            except Exception as e:
                log_error(f"[TickBatchProcessor] Error processing tick: {e}")
                continue
        
        log_debug(f"[TickBatchProcessor] Processed batch {self.batches_processed}: {len(unified_batch)} ticks")
        
        return unified_batch
    
    def _convert_to_unified(self, raw_tick: Dict[str, Any], data_source: str) -> Dict[str, Any]:
        """Convert raw tick to unified format based on data source"""
        converters = {
            "clickhouse": self.converter.from_clickhouse,
            "angelone": self.converter.from_angelone,
            "zerodha": self.converter.from_zerodha
        }
        
        converter = converters.get(data_source)
        
        if not converter:
            log_error(f"[TickBatchProcessor] Unknown data source: {data_source}")
            return None
        
        return converter(raw_tick)
    
    def _update_ltp_store(self, unified_tick: Dict[str, Any]):
        """Update LTPStore with tick data"""
        symbol = unified_tick["symbol"]
        ltp = unified_tick["ltp"]
        timestamp = unified_tick["timestamp"]
        volume = unified_tick.get("volume", 0)
        oi = unified_tick.get("oi", 0)
        
        self.ltp_store.update_ltp(symbol, ltp, timestamp, volume, oi)
    
    def _feed_to_candle_builder(self, unified_tick: Dict[str, Any]):
        """Feed tick to CandleBuilder for all timeframes"""
        symbol = unified_tick["symbol"]
        
        # CandleBuilder will handle all timeframes for this symbol
        self.candle_builder.process_tick(unified_tick)
    
    def get_statistics(self) -> Dict[str, int]:
        """Get processing statistics"""
        return {
            "batches_processed": self.batches_processed,
            "ticks_processed": self.ticks_processed
        }
