"""
SessionDataLoader Module
Engine: Loads strategy and broker connection details from Supabase

Input: Global session dictionary {session_id: {strategy_id, broker_connection_id, scale}}
Output: Enriched session list with full details
"""

from typing import Dict, List, Any
import os

from src.utils.logger import log_info, log_error
from supabase import create_client, Client


class SessionDataLoader:
    """
    Loads full session data from Supabase
    
    Input: session_registry (Dict) - {session_id: {strategy_id, broker_connection_id, scale, user_id, enabled}}
    Output: enriched_sessions (List[Dict]) - Full session data with strategy + broker details
    
    Purpose:
    - Fetch strategy configuration from Supabase
    - Fetch broker connection details from Supabase
    - Enrich session data with complete information
    - Prepare for MetadataScanner
    
    Engine Contract:
    - Input: session_registry (Dict)
    - Output: enriched_sessions (List[Dict])
    - Side Effects: Queries Supabase
    """
    
    def __init__(self):
        # Initialize Supabase client
        SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "your-anon-key")
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Cache for loaded data
        self.strategy_cache: Dict[str, Dict[str, Any]] = {}
        self.broker_cache: Dict[str, Dict[str, Any]] = {}
    
    def load_sessions(self, session_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Load full session data from Supabase
        
        Input Structure:
        {
            "session_id_1": {
                "strategy_id": "uuid",
                "broker_connection_id": "uuid",
                "scale": 1.0,
                "user_id": "uuid",
                "enabled": True
            },
            ...
        }
        
        Output Structure:
        [
            {
                "session_id": "session_id_1",
                "user_id": "uuid",
                "strategy_id": "uuid",
                "broker_connection_id": "uuid",
                "scale": 1.0,
                "enabled": True,
                "strategy_name": "...",
                "strategy_config": {...},  # Full strategy JSON
                "broker_name": "...",
                "meta_data": {...}  # Broker connection metadata
            },
            ...
        ]
        """
        log_info(f"[SessionDataLoader] Loading {len(session_registry)} sessions from Supabase")
        
        enriched_sessions = []
        
        for session_id, session_data in session_registry.items():
            try:
                # Extract basic info
                strategy_id = session_data.get("strategy_id")
                broker_connection_id = session_data.get("broker_connection_id")
                user_id = session_data.get("user_id")
                scale = session_data.get("scale", 1.0)
                enabled = session_data.get("enabled", False)
                
                if not strategy_id:
                    log_error(f"[SessionDataLoader] Invalid session data for {session_id}: missing strategy_id")
                    continue
                
                # Load strategy details
                strategy = self._load_strategy(strategy_id)
                if not strategy:
                    log_error(f"[SessionDataLoader] Failed to load strategy {strategy_id}")
                    continue
                
                # Load broker connection details (optional - None means use backtesting adapter)
                broker_connection = None
                broker_name = "Backtesting"
                broker_metadata = {}
                
                if broker_connection_id:
                    broker_connection = self._load_broker_connection(broker_connection_id)
                    if broker_connection:
                        broker_name = broker_connection.get("broker_name", "Unknown")
                        broker_metadata = broker_connection.get("meta_data", {})
                    else:
                        log_error(f"[SessionDataLoader] Failed to load broker connection {broker_connection_id}, using backtesting adapter")
                else:
                    log_info(f"[SessionDataLoader] No broker connection specified for {session_id}, using backtesting adapter")
                
                # Enrich session data
                enriched_session = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "strategy_id": strategy_id,
                    "broker_connection_id": broker_connection_id,
                    "scale": scale,
                    "enabled": enabled,
                    "strategy_name": strategy.get("name", "Unknown"),
                    "strategy_config": strategy,  # Full strategy configuration
                    "broker_name": broker_name,
                    "meta_data": broker_metadata,  # Broker metadata
                    "created_at": session_data.get("created_at"),
                    "execution_date": session_data.get("execution_date")  # Pass through execution date
                }
                
                enriched_sessions.append(enriched_session)
                
                log_info(f"[SessionDataLoader] Loaded session {session_id}: {strategy.get('name')} + {broker_name}")
                
            except Exception as e:
                log_error(f"[SessionDataLoader] Error loading session {session_id}: {e}")
                continue
        
        log_info(f"[SessionDataLoader] Successfully loaded {len(enriched_sessions)}/{len(session_registry)} sessions")
        
        return enriched_sessions
    
    def _load_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """
        Load strategy from Supabase (with caching)
        
        Returns: Strategy configuration dictionary
        """
        # Check cache
        if strategy_id in self.strategy_cache:
            return self.strategy_cache[strategy_id]
        
        try:
            result = self.supabase.table("strategies").select("*").eq("id", strategy_id).execute()
            
            if result.data and len(result.data) > 0:
                strategy = result.data[0]
                self.strategy_cache[strategy_id] = strategy
                return strategy
            
            log_error(f"[SessionDataLoader] Strategy {strategy_id} not found in Supabase")
            return {}
            
        except Exception as e:
            log_error(f"[SessionDataLoader] Error fetching strategy {strategy_id}: {e}")
            return {}
    
    def _load_broker_connection(self, broker_connection_id: str) -> Dict[str, Any]:
        """
        Load broker connection from Supabase (with caching)
        
        Returns: Broker connection dictionary with meta_data
        """
        # Check cache
        if broker_connection_id in self.broker_cache:
            return self.broker_cache[broker_connection_id]
        
        try:
            result = self.supabase.table("broker_connections").select("*").eq("id", broker_connection_id).execute()
            
            if result.data and len(result.data) > 0:
                broker_connection = result.data[0]
                self.broker_cache[broker_connection_id] = broker_connection
                return broker_connection
            
            log_error(f"[SessionDataLoader] Broker connection {broker_connection_id} not found in Supabase")
            return {}
            
        except Exception as e:
            log_error(f"[SessionDataLoader] Error fetching broker connection {broker_connection_id}: {e}")
            return {}
    
    def get_statistics(self) -> Dict[str, int]:
        """Get loader statistics"""
        return {
            "strategies_cached": len(self.strategy_cache),
            "broker_connections_cached": len(self.broker_cache)
        }
