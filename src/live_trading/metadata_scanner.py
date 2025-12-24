"""
MetadataScanner Module
Engine: Scans all strategies from all users, extracts and aggregates metadata

Input: List of session dictionaries
Output: Aggregated metadata (symbols, timeframes, strategy configs)
"""

from typing import Dict, List, Any, Set
from pathlib import Path
import json

from src.utils.logger import log_info, log_error


class MetadataScanner:
    """
    Scans all strategy sessions and extracts metadata
    
    Purpose:
    - Identify all unique symbols required
    - Identify all unique timeframes required
    - Extract strategy configurations
    - Prepare for data initialization
    """
    
    def __init__(self):
        self.sessions: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "symbols": set(),
            "timeframes": set(),
            "strategy_configs": {},
            "broker_connections": {}
        }
    
    def scan(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scan all sessions and extract metadata
        
        Input: sessions - List of session dictionaries
        Output: Aggregated metadata dictionary
        
        Engine Contract:
        - Input: List[Session]
        - Output: {symbols: Set, timeframes: Set, strategy_configs: Dict, broker_connections: Dict}
        - Side Effects: None (pure function)
        """
        self.sessions = sessions
        log_info(f"[MetadataScanner] Scanning {len(sessions)} sessions")
        
        for session in sessions:
            self._scan_session(session)
        
        # Convert sets to lists for JSON serialization
        output = {
            "symbols": list(self.metadata["symbols"]),
            "timeframes": list(self.metadata["timeframes"]),
            "strategy_configs": self.metadata["strategy_configs"],
            "broker_connections": self.metadata["broker_connections"],
            "total_sessions": len(sessions)
        }
        
        log_info(f"[MetadataScanner] Scan complete: {len(output['symbols'])} symbols, {len(output['timeframes'])} timeframes")
        
        return output
    
    def _scan_session(self, session: Dict[str, Any]):
        """
        Scan a single session and extract metadata
        
        Note: Session already enriched by SessionDataLoader with strategy_config and meta_data
        """
        session_id = session["session_id"]
        
        try:
            # Get strategy config (already loaded by SessionDataLoader)
            strategy_config = session.get("strategy_config", {})
            
            if not strategy_config:
                log_error(f"[MetadataScanner] No strategy config for {session_id}")
                return
            
            # Extract symbol and timeframe
            symbol = strategy_config.get("symbol")
            timeframe = strategy_config.get("timeframe")
            
            if symbol:
                self.metadata["symbols"].add(symbol)
            if timeframe:
                self.metadata["timeframes"].add(timeframe)
            
            # Store strategy config
            self.metadata["strategy_configs"][session_id] = strategy_config
            
            # Store broker connection metadata (already loaded by SessionDataLoader)
            self.metadata["broker_connections"][session_id] = session.get("meta_data", {})
            
            log_info(f"[MetadataScanner] Scanned {session_id}: symbol={symbol}, timeframe={timeframe}")
            
        except Exception as e:
            log_error(f"[MetadataScanner] Error scanning session {session_id}: {e}")
