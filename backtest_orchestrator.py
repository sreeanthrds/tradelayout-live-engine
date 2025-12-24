"""
Backtest Orchestrator - Modular Execution for Backtesting

10-Step Process:
1. Parse session payload (session_id: {user_id, strategy_id, broker_connection_id})
2. Extract strategy config from Supabase strategies table
3. Extract broker metadata (date, scale) from broker_connections table
4. Metadata scanner: Extract symbols, timeframes, indicators
5. Data initializer: Load 500 candles, apply indicators, store last 20
6. Data source manager: Subscribe symbols, prepare tick batches
7. Tick batch processor: Update candles, update LTP
8. Strategy executor: Process nodes
9. Event generation: Generate JSONL events
10. Verification: Compare with legacy output
"""

import os
import json
from datetime import datetime, date
from typing import Dict, Any, List
from pathlib import Path
from supabase import create_client, Client

# Set environment variables
if 'SUPABASE_URL' not in os.environ:
    os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
if 'SUPABASE_SERVICE_ROLE_KEY' not in os.environ:
    os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
if 'CLICKHOUSE_DATA_TIMEZONE' not in os.environ:
    os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

from src.utils.logger import log_info, log_error


class BacktestOrchestrator:
    """
    Orchestrates modular backtest execution following 10-step process
    """
    
    def __init__(self, offline_mode: bool = False):
        self.offline_mode = offline_mode
        
        if not offline_mode:
            try:
                self.supabase: Client = create_client(
                    os.environ['SUPABASE_URL'],
                    os.environ['SUPABASE_SERVICE_ROLE_KEY']
                )
            except Exception as e:
                log_error(f"Supabase connection failed: {e}, switching to offline mode")
                self.offline_mode = True
                self.supabase = None
        else:
            self.supabase = None
        
        self.sessions = {}
        self.session_cache = {}
        self.cache_dir = Path("/tmp/backtest_cache")
    
    # ============================================================================
    # STEP 1: Parse Session Payload
    # ============================================================================
    
    def parse_session_payload(self, session_registry: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Parse session payload dictionary
        
        Args:
            session_registry: {
                "session_id_1": {
                    "user_id": "...",
                    "strategy_id": "...",
                    "broker_connection_id": "..."
                },
                "session_id_2": {...}
            }
        
        Returns:
            List of parsed sessions with metadata
        """
        log_info(f"[Step 1] Parsing session payload: {len(session_registry)} sessions")
        
        parsed_sessions = []
        
        for session_id, session_data in session_registry.items():
            user_id = session_data.get("user_id")
            strategy_id = session_data.get("strategy_id")
            broker_connection_id = session_data.get("broker_connection_id")
            
            if not all([user_id, strategy_id, broker_connection_id]):
                log_error(f"[Step 1] Incomplete session data for {session_id}")
                continue
            
            parsed_session = {
                "session_id": session_id,
                "user_id": user_id,
                "strategy_id": strategy_id,
                "broker_connection_id": broker_connection_id
            }
            
            parsed_sessions.append(parsed_session)
            log_info(f"[Step 1] Parsed session: {session_id}")
        
        log_info(f"[Step 1] ✅ Parsed {len(parsed_sessions)} sessions successfully")
        return parsed_sessions
    
    # ============================================================================
    # STEP 2: Extract Strategy Config from Supabase
    # ============================================================================
    
    def extract_strategy_config(self, strategy_id: str) -> Dict[str, Any]:
        """
        Extract strategy config from Supabase strategies table
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            {
                "id": "...",
                "name": "...",
                "user_id": "...",
                "config": {...}  # Full strategy JSON
            }
        """
        log_info(f"[Step 2] Extracting strategy config for {strategy_id}")
        
        # Check cache first
        cache_file = self.cache_dir / f"strategy_{strategy_id}.json"
        if cache_file.exists():
            log_info(f"[Step 2] Using cached strategy from {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_error(f"[Step 2] Error loading cache: {e}")
        
        # Offline mode: Use mock data
        if self.offline_mode:
            log_info(f"[Step 2] Offline mode: Using mock strategy config")
            strategy_data = self._get_mock_strategy(strategy_id)
            self._cache_strategy(strategy_id, strategy_data)
            return strategy_data
        
        try:
            response = self.supabase.table("strategies").select("*").eq("id", strategy_id).execute()
            
            if not response.data or len(response.data) == 0:
                log_error(f"[Step 2] Strategy {strategy_id} not found in Supabase")
                return None
            
            strategy = response.data[0]
            
            strategy_data = {
                "id": strategy.get("id"),
                "name": strategy.get("name"),
                "user_id": strategy.get("user_id"),
                "config": strategy.get("strategy", {})  # Field is 'strategy' not 'config'
            }
            
            # Cache for offline use
            self._cache_strategy(strategy_id, strategy_data)
            
            log_info(f"[Step 2] ✅ Extracted strategy: {strategy_data['name']}")
            return strategy_data
            
        except Exception as e:
            log_error(f"[Step 2] Error extracting strategy: {e}")
            return None
    
    # ============================================================================
    # STEP 3: Extract Broker Metadata (ClickHouse)
    # ============================================================================
    
    def extract_broker_metadata(self, broker_connection_id: str) -> Dict[str, Any]:
        """
        Extract broker metadata from broker_connections table
        
        For ClickHouse broker, metadata contains:
        - date: Trade date
        - scale: Strategy scale multiplier
        
        Other brokers may have different parameters
        
        Args:
            broker_connection_id: Broker connection UUID
        
        Returns:
            {
                "broker_name": "clickhouse",
                "date": "2024-10-29",
                "scale": 1.0,
                "meta_data": {...}  # Full metadata JSON
            }
        """
        log_info(f"[Step 3] Extracting broker metadata for {broker_connection_id}")
        
        # Check cache first
        cache_file = self.cache_dir / f"broker_{broker_connection_id}.json"
        if cache_file.exists():
            log_info(f"[Step 3] Using cached broker from {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_error(f"[Step 3] Error loading cache: {e}")
        
        # Offline mode: Use mock data
        if self.offline_mode:
            log_info(f"[Step 3] Offline mode: Using mock broker metadata")
            broker_metadata = self._get_mock_broker(broker_connection_id)
            self._cache_broker(broker_connection_id, broker_metadata)
            return broker_metadata
        
        try:
            response = self.supabase.table("broker_connections").select("*").eq("id", broker_connection_id).execute()
            
            if not response.data or len(response.data) == 0:
                log_error(f"[Step 3] Broker connection {broker_connection_id} not found in Supabase")
                return None
            
            broker_conn = response.data[0]
            broker_name = broker_conn.get("broker_name", "").lower()
            meta_data = broker_conn.get("meta_data", {})
            
            # Extract ClickHouse-specific metadata
            if broker_name == "clickhouse":
                broker_metadata = {
                    "broker_name": broker_name,
                    "date": meta_data.get("date"),
                    "scale": meta_data.get("scale", 1.0),
                    "meta_data": meta_data
                }
                
                # Cache for offline use
                self._cache_broker(broker_connection_id, broker_metadata)
                
                log_info(f"[Step 3] ✅ Extracted ClickHouse metadata: date={broker_metadata['date']}, scale={broker_metadata['scale']}")
                return broker_metadata
            else:
                log_error(f"[Step 3] Unsupported broker: {broker_name}")
                return None
            
        except Exception as e:
            log_error(f"[Step 3] Error extracting broker metadata: {e}")
            return None
    
    # ============================================================================
    # STEP 1-3 COMBINED: Prepare Enriched Sessions
    # ============================================================================
    
    def prepare_enriched_sessions(self, session_registry: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Execute Steps 1-3: Parse payload, extract strategy config, extract broker metadata
        
        Args:
            session_registry: Session payload dictionary
        
        Returns:
            List of enriched sessions ready for execution
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEPS 1-3: Session Preparation")
        log_info(f"{'='*80}\n")
        
        # Step 1: Parse session payload
        parsed_sessions = self.parse_session_payload(session_registry)
        
        enriched_sessions = []
        
        for session in parsed_sessions:
            session_id = session["session_id"]
            strategy_id = session["strategy_id"]
            broker_connection_id = session["broker_connection_id"]
            
            # Step 2: Extract strategy config
            strategy_data = self.extract_strategy_config(strategy_id)
            if not strategy_data:
                log_error(f"[Steps 1-3] Skipping session {session_id}: Strategy config not found")
                continue
            
            # Step 3: Extract broker metadata
            broker_metadata = self.extract_broker_metadata(broker_connection_id)
            if not broker_metadata:
                log_error(f"[Steps 1-3] Skipping session {session_id}: Broker metadata not found")
                continue
            
            # Combine into enriched session
            enriched_session = {
                "session_id": session_id,
                "user_id": session["user_id"],
                "strategy_id": strategy_id,
                "broker_connection_id": broker_connection_id,
                
                # Strategy details
                "strategy_name": strategy_data["name"],
                "strategy_config": strategy_data["config"],
                
                # Broker details
                "broker_name": broker_metadata["broker_name"],
                "execution_date": broker_metadata["date"] or "2024-10-29",  # Fallback date
                "scale": broker_metadata["scale"],
                "broker_meta_data": broker_metadata["meta_data"]
            }
            
            enriched_sessions.append(enriched_session)
            
            # Cache for later use
            self.sessions[session_id] = enriched_session
            
            log_info(f"[Steps 1-3] ✅ Enriched session: {session_id}")
            log_info(f"  Strategy: {enriched_session['strategy_name']}")
            log_info(f"  Date: {enriched_session['execution_date']}")
            log_info(f"  Scale: {enriched_session['scale']}")
        
        log_info(f"\n[Steps 1-3] ✅ Prepared {len(enriched_sessions)} enriched sessions\n")
        return enriched_sessions
    
    # ============================================================================
    # STEP 4: Metadata Scanner
    # ============================================================================
    
    def scan_metadata(self, enriched_sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Step 4: Scan strategy configs to extract metadata
        
        Extracts:
        - TI (Trading Instrument) symbols and timeframes
        - SI (Supporting Instrument) symbols and timeframes (if enabled)
        - Indicators per timeframe
        - Option patterns
        
        Returns:
            {
                "symbols": ["NIFTY", ...],
                "timeframes": ["1m", "5m", ...],
                "indicators": {
                    "NIFTY:1m": ["rsi", "ema", ...],
                    ...
                },
                "options_config": {
                    "enabled": True,
                    "underlying": "NIFTY",
                    "type": "index"
                }
            }
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEP 4: Metadata Scanner")
        log_info(f"{'='*80}\n")
        
        all_symbols = set()
        all_timeframes = set()
        all_indicators = {}
        options_enabled = False
        options_config = {}
        
        for session in enriched_sessions:
            session_id = session["session_id"]
            strategy_config = session["strategy_config"]
            
            log_info(f"[Step 4] Scanning session: {session_id}")
            
            # Extract from React Flow nodes structure
            nodes = strategy_config.get("nodes", [])
            
            # Find StartNode (strategy-controller) which has trading instrument config
            start_node = None
            for node in nodes:
                if node.get("id") == "strategy-controller" or node.get("type") == "startNode":
                    start_node = node
                    break
            
            if not start_node:
                log_error(f"[Step 4] No start node found in strategy config")
                continue
            
            node_data = start_node.get("data", {})
            
            # Extract Trading Instrument (TI) config
            ti_config = node_data.get("tradingInstrumentConfig", {})
            ti_type = ti_config.get("type", "")
            ti_symbol = ti_config.get("symbol", "")
            ti_timeframes = ti_config.get("timeframes", [])
            
            if ti_symbol:
                all_symbols.add(ti_symbol)
                log_info(f"[Step 4]   TI Symbol: {ti_symbol} ({ti_type})")
            
            # Extract timeframes and indicators from TI
            for tf in ti_timeframes:
                tf_str = tf.get("timeframe", "")
                if tf_str:
                    all_timeframes.add(tf_str)
                    
                    # Extract indicators for this timeframe (FULL CONFIG, not just keys)
                    indicators = tf.get("indicators", {})
                    if indicators:
                        key = f"{ti_symbol}:{tf_str}"
                        # Store full indicator configs: {indicator_id: {config}}
                        all_indicators[key] = indicators
                        log_info(f"[Step 4]   {key} → {len(indicators)} indicators")
                        
                        # Log indicator details
                        for ind_id, ind_config in indicators.items():
                            ind_name = ind_config.get('indicator_name', ind_config.get('display_name', 'Unknown'))
                            log_info(f"[Step 4]     - {ind_name}: {ind_config}")
            
            # Check if options trading enabled
            ti_instrument = node_data.get("tradingInstrument", {})
            if ti_instrument.get("type", "").lower() == "options":
                options_enabled = True
                options_config = {
                    "enabled": True,
                    "underlying": ti_symbol,
                    "type": ti_instrument.get("underlyingType", "")
                }
                log_info(f"[Step 4]   Options enabled: {ti_symbol} ({options_config['type']})")
            
            # Extract Supporting Instrument (SI) config
            si_enabled = node_data.get("supportingInstrumentEnabled", False)
            if si_enabled:
                si_config = node_data.get("supportingInstrumentConfig", {})
                si_symbol = si_config.get("symbol", "")
                si_timeframes = si_config.get("timeframes", [])
                
                if si_symbol:
                    all_symbols.add(si_symbol)
                    log_info(f"[Step 4]   SI Symbol: {si_symbol}")
                    
                    # Extract SI timeframes and indicators
                    for tf in si_timeframes:
                        tf_str = tf.get("timeframe", "")
                        if tf_str:
                            all_timeframes.add(tf_str)
                            
                            indicators = tf.get("indicators", {})
                            if indicators:
                                key = f"{si_symbol}:{tf_str}"
                                all_indicators[key] = indicators
                                log_info(f"[Step 4]   {key} → {len(indicators)} indicators")
                                
                                # Log indicator details
                                for ind_id, ind_config in indicators.items():
                                    ind_name = ind_config.get('indicator_name', ind_config.get('display_name', 'Unknown'))
                                    log_info(f"[Step 4]     - {ind_name}: {ind_config}")
        
        # Build metadata summary
        metadata = {
            "symbols": sorted(list(all_symbols)),
            "timeframes": sorted(list(all_timeframes)),
            "indicators": all_indicators,
            "options_config": options_config if options_enabled else {"enabled": False}
        }
        
        # Cache metadata for session
        for session in enriched_sessions:
            session_id = session["session_id"]
            self.session_cache[session_id] = metadata
        
        log_info(f"\n[Step 4] ✅ Metadata scanned:")
        log_info(f"  Symbols: {metadata['symbols']}")
        log_info(f"  Timeframes: {metadata['timeframes']}")
        log_info(f"[Step 4]   Indicators: {metadata['indicators']}")
        log_info(f"[Step 4]   Options enabled: {metadata['options_config']['enabled']}")
        
        # CRITICAL DEBUG: Print indicator details
        print(f"\n[Step 4] INDICATOR DETAILS:")
        indicators_dict = metadata.get('indicators', {})
        print(f"  Total symbol:timeframe keys with indicators: {len(indicators_dict)}")
        for key, ind_configs in indicators_dict.items():
            print(f"  {key}: {len(ind_configs)} indicator(s)")
            for ind_id, ind_cfg in list(ind_configs.items())[:2]:  # Show first 2 per key
                ind_name = ind_cfg.get('indicator_name', 'Unknown')
                print(f"    - {ind_id}: {ind_name}, params={ind_cfg}")
        
        log_info(f"")
        
        return metadata
    
    # ============================================================================
    # STEP 5: Data Initializer
    # ============================================================================
    
    def initialize_data_stores(
        self,
        enriched_sessions: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 5: Initialize data stores with historical candles
        
        For each symbol:timeframe:
        1. Load 500 candles from ClickHouse
        2. Apply indicators (RSI, EMA, etc.)
        3. Store last 20 candles in CandleStore
        4. Register symbols in LTPStore
        
        Returns:
            {
                "candle_store": CandleStore instance,
                "ltp_store": LTPStore instance,
                "indicator_registry": IndicatorRegistry instance
            }
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEP 5: Data Initializer")
        log_info(f"{'='*80}\n")
        
        from datetime import datetime, timedelta
        
        # Get execution date from first session
        session = enriched_sessions[0]
        execution_date_str = session["execution_date"]
        execution_date = datetime.strptime(execution_date_str, "%Y-%m-%d")
        
        log_info(f"[Step 5] Execution date: {execution_date_str}")
        
        # Initialize data structure to hold metadata
        # Actual stores will be initialized in Step 6 by modular components
        data_config = {
            "symbols": metadata['symbols'],
            "timeframes": metadata['timeframes'],
            "indicators": metadata['indicators'],
            "execution_date": execution_date,
            "user_id": session["user_id"]
        }
        
        symbols = metadata['symbols']
        timeframes = metadata['timeframes']
        
        log_info(f"[Step 5] Preparing data configuration for {len(symbols)} symbols, {len(timeframes)} timeframes")
        
        # Prepare data requirements for each symbol:timeframe combination
        data_requirements = []
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}:{timeframe}"
                
                # Calculate lookback period for 500 candles
                lookback_days = self._calculate_lookback_days(timeframe, 500)
                from_date = execution_date - timedelta(days=lookback_days)
                
                requirement = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "from_date": from_date,
                    "to_date": execution_date,
                    "num_candles": 500,
                    "indicators": metadata['indicators'].get(key, [])
                }
                
                data_requirements.append(requirement)
                log_info(f"[Step 5]   {key}: {lookback_days} days lookback, {len(requirement['indicators'])} indicators")
        
        log_info(f"\n[Step 5] ✅ Data configuration prepared:")
        log_info(f"  Symbols: {', '.join(symbols)}")
        log_info(f"  Timeframes: {', '.join(timeframes)}")
        log_info(f"  Total requirements: {len(data_requirements)}")
        log_info(f"  Note: Actual data stores (CandleStore, LTPStore) will be initialized")
        log_info(f"        by modular components in Step 6 (Data Source Manager)")
        log_info(f"")
        
        return {
            "data_config": data_config,
            "data_requirements": data_requirements,
            "metadata": metadata
        }
    
    # ============================================================================
    # STEP 6: Data Source Manager (Broker-Agnostic)
    # ============================================================================
    
    def initialize_data_source(
        self,
        enriched_sessions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        broker_type: str = 'clickhouse'
    ) -> Dict[str, Any]:
        """
        Step 6: Initialize broker-agnostic data source
        
        Broker Types:
        - 'clickhouse': Load historical ticks from ClickHouse table (backtesting)
        - 'websocket': Subscribe to live WebSocket feed (live trading)
        
        Returns:
            {
                "broker_type": str,
                "data_source": DataSource instance,
                "subscriptions": List of subscribed symbols
            }
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEP 6: Data Source Manager (Broker Type: {broker_type})")
        log_info(f"{'='*80}\n")
        
        session = enriched_sessions[0]
        symbols = metadata['symbols']
        execution_date = session['execution_date']
        
        log_info(f"[Step 6] Symbols to subscribe: {symbols}")
        log_info(f"[Step 6] Execution date: {execution_date}")
        
        if broker_type == 'clickhouse':
            # Backtesting: Load ticks from ClickHouse
            from src.core.clickhouse_tick_source import ClickHouseTickSource
            from clickhouse_driver import Client as ClickHouseClient
            from datetime import datetime
            
            log_info(f"[Step 6] Initializing ClickHouse tick source")
            log_info(f"[Step 6]   Symbols: {symbols}")
            log_info(f"[Step 6]   Date: {execution_date}")
            
            # Initialize ClickHouse client
            ch_client = ClickHouseClient(
                host=os.environ.get('CLICKHOUSE_HOST', 'localhost'),
                port=int(os.environ.get('CLICKHOUSE_PORT', 9000)),
                database=os.environ.get('CLICKHOUSE_DB', 'default')
            )
            
            # Convert date string to datetime
            if isinstance(execution_date, str):
                backtest_date = datetime.strptime(execution_date, "%Y-%m-%d")
            else:
                backtest_date = execution_date
            
            # Initialize tick source with correct parameters
            tick_source = ClickHouseTickSource(
                clickhouse_client=ch_client,
                backtest_date=backtest_date,
                symbols=symbols,  # List of symbols
                cache_manager=None  # Will be initialized by centralized processor
            )
            
            log_info(f"[Step 6] ✅ ClickHouse tick source initialized")
            log_info(f"[Step 6]   Broker type: clickhouse")
            log_info(f"[Step 6]   Symbols subscribed: {', '.join(symbols)}")
            log_info(f"[Step 6]   Date: {backtest_date.date()}")
            log_info(f"[Step 6]   Ready to process ticks batch-by-batch")
            
            return {
                "broker_type": broker_type,
                "data_source": tick_source,
                "subscriptions": symbols,
                "backtest_date": backtest_date,
                "ch_client": ch_client
            }
            
        else:
            # Live trading: WebSocket subscription (future implementation)
            log_info(f"[Step 6] WebSocket subscription not yet implemented")
            log_info(f"[Step 6] Broker type '{broker_type}' requires WebSocket integration")
            
            # Placeholder for future WebSocket implementation
            return {
                "broker_type": broker_type,
                "data_source": None,
                "subscriptions": symbols,
                "total_ticks": 0,
                "message": "WebSocket implementation pending"
            }
    
    # ============================================================================
    # STEP 7: Tick Batch Processor
    # ============================================================================
    
    def process_ticks(
        self,
        enriched_sessions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        data_prep: Dict[str, Any],
        data_source_info: Dict[str, Any],
        max_ticks: int = None
    ) -> Dict[str, Any]:
        """
        Step 7: Process ticks batch-by-batch and update market data
        
        For each tick:
        1. Update LTP store
        2. Build candles (aggregate ticks into timeframe candles)
        3. Calculate indicators (incremental on completed candles)
        4. Update context for strategy execution
        
        Returns:
            {
                "ticks_processed": int,
                "candles_built": dict,
                "context": prepared context for Step 8
            }
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEP 7: Tick Batch Processor")
        log_info(f"{'='*80}\n")
        
        from src.backtesting.data_manager import DataManager
        from src.backtesting.dict_cache import DictCache
        from datetime import datetime
        
        # Initialize components
        session = enriched_sessions[0]
        symbols = metadata['symbols']
        timeframes = metadata['timeframes']
        tick_source = data_source_info['data_source']
        
        log_info(f"[Step 7] Initializing data manager and indicators")
        log_info(f"[Step 7]   Symbols: {symbols}")
        log_info(f"[Step 7]   Timeframes: {timeframes}")
        
        # Initialize cache and data manager for candle building
        from src.backtesting.dict_cache import DictCache
        from src.backtesting.backtest_candle_builder import BacktestCandleBuilder
        from src.backtesting.backtest_indicator_engine import BacktestIndicatorEngine
        
        cache = DictCache()
        
        # Data writer that adds indicator values directly to candle dict
        class CandleIndicatorWriter:
            def __init__(self):
                self.current_candle = None  # Reference to candle being processed
            
            def write_candle(self, *args, **kwargs):
                # Candle writing handled by BacktestCandleBuilder directly
                pass
            
            def set_current_candle(self, candle):
                """Set the candle dict that indicators should be written to"""
                self.current_candle = candle
            
            def write_indicator(self, ind_data):
                """Add indicator value directly to the current candle dict"""
                if self.current_candle is None:
                    return
                
                indicator_name = ind_data['indicator_name']
                value = ind_data['value']
                
                # Add indicator as a column to the candle (modifies in-place)
                self.current_candle[indicator_name] = value
                # Also add with uppercase name for compatibility (RSI, EMA, etc.)
                ind_type = indicator_name.split('_')[0].upper() if '_' in indicator_name else indicator_name.upper()
                self.current_candle[ind_type] = value
                
                # DEBUG: Log first few indicator calculations
                tick_count = self.current_candle.get('tick_count', 0)
                if tick_count <= 3:
                    log_info(f"[Step 7]   ✅ Calculated {ind_type}={value:.2f} for candle at {ind_data.get('timestamp')}")
        
        data_writer = CandleIndicatorWriter()
        
        # Initialize indicator engine
        indicator_engine = BacktestIndicatorEngine(data_writer, cache)
        
        # Register indicators from metadata
        indicators_dict = metadata.get('indicators', {})
        print(f"\n[Step 7] Registering indicators from metadata...")
        print(f"[Step 7] indicators_dict keys: {list(indicators_dict.keys())}")
        
        for key, ind_configs in indicators_dict.items():
            symbol, timeframe = key.split(':')
            print(f"[Step 7] Processing {key}: {len(ind_configs)} indicators")
            
            for ind_id, ind_config in ind_configs.items():
                ind_name = ind_config.get('indicator_name', '')
                ind_type = ind_name.upper()  # RSI, EMA, etc.
                
                # Extract parameters
                params = {
                    'period': ind_config.get('length', ind_config.get('period', 14)),
                    'price_field': ind_config.get('price_field', 'close')
                }
                
                # Register indicator
                indicator_engine.register_indicator(
                    symbol=symbol,
                    timeframe=timeframe,
                    indicator_name=ind_id,
                    indicator_type=ind_type,
                    params=params
                )
                print(f"[Step 7]   ✓ Registered {ind_type}({params['period']}) for {symbol}:{timeframe}")
        
        # Initialize candle builders for each symbol:timeframe
        candle_builders = {}
        timeframe_to_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60}
        
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}:{timeframe}"
                interval_minutes = timeframe_to_minutes.get(timeframe, 1)
                # Create a callback that sets current candle before indicator calculation
                def make_indicator_callback(writer):
                    def callback(candle):
                        # Set the candle reference so indicators write to it
                        writer.set_current_candle(candle)
                        # Calculate indicators (will modify candle dict in-place)
                        indicator_engine.on_candle_complete(candle)
                        # Clear reference
                        writer.set_current_candle(None)
                    return callback
                
                candle_builders[key] = BacktestCandleBuilder(
                    data_writer=data_writer,
                    cache=cache,
                    interval_minutes=interval_minutes,
                    timeframe=timeframe,
                    on_candle_complete=make_indicator_callback(data_writer)  # Hook with candle ref
                )
                log_info(f"[Step 7]   Initialized BacktestCandleBuilder for {key} (with indicator callback)")
        
        # LTP store
        ltp_store = {}
        
        # Step 7: Load and PROCESS tick data
        log_info(f"\n[Step 7] Loading and processing tick data...")
        if max_ticks:
            log_info(f"[Step 7]   Limiting to first {max_ticks:,} ticks for testing")
        
        tick_count = 0
        tick_data_sample = []
        
        try:
            # Load ticks directly from ClickHouse
            ch_client = data_source_info['ch_client']
            backtest_date = data_source_info['backtest_date']
            
            query = f"""
                SELECT timestamp, symbol, ltp, ltq
                FROM nse_ticks_indices
                WHERE toDate(timestamp) = '{backtest_date.date()}'
                AND symbol IN {tuple(symbols) if len(symbols) > 1 else f"('{symbols[0]}')"}
                ORDER BY timestamp
                {'LIMIT ' + str(max_ticks) if max_ticks else ''}
            """
            
            log_info(f"[Step 7]   Loading ticks from ClickHouse...")
            ticks = ch_client.execute(query)
            tick_count = len(ticks)
            log_info(f"[Step 7]   Loaded {tick_count:,} ticks")
            
            # Process each tick through candle builders
            completed_candles = {}
            
            log_info(f"\n[Step 7]   Processing ticks through candle builders...")
            for i, tick_row in enumerate(ticks):
                timestamp, symbol, ltp, ltq = tick_row
                
                # Update LTP store
                ltp_store[symbol] = ltp
                
                # Process through candle builders
                for timeframe in timeframes:
                    key = f"{symbol}:{timeframe}"
                    builder = candle_builders[key]
                    
                    # Update candle builder with tick data
                    tick_data = {
                        'symbol': symbol,
                        'ltp': ltp,
                        'ltq': ltq,
                        'timestamp': timestamp
                    }
                    builder.process_tick(tick_data)
                    
                    # Check if candle was completed (from builder's current_candles)
                    # Note: BacktestCandleBuilder writes to cache, we need to read from it
                    candles_from_cache = cache.get_candles(symbol, timeframe, count=100)
                    if candles_from_cache:
                        if key not in completed_candles:
                            completed_candles[key] = candles_from_cache
                        else:
                            # Only add new candles
                            completed_candles[key] = candles_from_cache
                
                # Sample first 5 ticks
                if i < 5:
                    tick_data_sample.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'ltp': ltp,
                        'ltq': ltq
                    })
                
                # Progress logging
                if (i + 1) % 1000 == 0:
                    log_info(f"[Step 7]     Processed {i + 1:,} ticks...")
            
            # Calculate time range
            if ticks:
                first_ts = ticks[0][0]
                last_ts = ticks[-1][0]
                duration_seconds = (last_ts - first_ts).total_seconds()
                duration_minutes = duration_seconds / 60
                
                log_info(f"\n[Step 7] Tick processing complete:")
                log_info(f"[Step 7]   First tick: {first_ts}")
                log_info(f"[Step 7]   Last tick: {last_ts}")
                log_info(f"[Step 7]   Duration: {duration_minutes:.1f} minutes")
                log_info(f"[Step 7]   Avg ticks/minute: {tick_count/duration_minutes:.1f}")
                
                # Show completed candles per symbol:timeframe
                log_info(f"\n[Step 7] Completed candles:")
                for key, candles in completed_candles.items():
                    log_info(f"[Step 7]   {key}: {len(candles)} candles")
                    if candles:
                        first_candle = candles[0]
                        last_candle = candles[-1]
                        log_info(f"[Step 7]     First: {first_candle['timestamp']} | O:{first_candle['open']:.2f} H:{first_candle['high']:.2f} L:{first_candle['low']:.2f} C:{first_candle['close']:.2f}")
                        log_info(f"[Step 7]     Last:  {last_candle['timestamp']} | O:{last_candle['open']:.2f} H:{last_candle['high']:.2f} L:{last_candle['low']:.2f} C:{last_candle['close']:.2f}")
                
                # Show current forming candle (from builder's current_candles)
                log_info(f"\n[Step 7] Current forming candles:")
                for key, builder in candle_builders.items():
                    # BacktestCandleBuilder stores in current_candles[symbol]
                    symbol = key.split(':')[0]
                    if symbol in builder.current_candles:
                        forming = builder.current_candles[symbol]
                        log_info(f"[Step 7]   {key}: {forming['timestamp']} | O:{forming['open']:.2f} H:{forming['high']:.2f} L:{forming['low']:.2f} C:{forming['close']:.2f} V:{forming['volume']}")
                
                # Show LTP store
                log_info(f"\n[Step 7] LTP Store:")
                for symbol, ltp in ltp_store.items():
                    log_info(f"[Step 7]   {symbol}: {ltp:.2f}")
                    
        except Exception as e:
            log_error(f"[Step 7] Tick loading failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Prepare context for Step 8 (strategy execution)
        context = {
            'ticks': ticks if 'ticks' in locals() else [],
            'session': session,
            'metadata': metadata,
            'data_prep': data_prep,
            'data_source_info': data_source_info,
            'tick_count': tick_count,
            'ltp_store': ltp_store,
            'candle_builders': candle_builders,
            'completed_candles': completed_candles if 'completed_candles' in locals() else {},
            'cache': cache  # CRITICAL: Pass the same cache that builders write to
        }
        
        return {
            "ticks_loaded": tick_count,
            "tick_data_sample": tick_data_sample,
            "context": context,
            "ticks": ticks if 'ticks' in locals() else [],
            "ltp_store": ltp_store,
            "candle_builders": candle_builders,
            "completed_candles": completed_candles if 'completed_candles' in locals() else {}
        }
    
    # ============================================================================
    # STEP 8: Strategy Executor
    # ============================================================================
    
    def execute_strategy(
        self,
        enriched_sessions: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        data_prep: Dict[str, Any],
        data_source_info: Dict[str, Any],
        tick_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 8: Execute strategy nodes on all ticks
        
        Process each tick through the strategy graph:
        1. Update context with current tick data
        2. Reset visited flags for all nodes
        3. Execute StartNode (activates children)
        4. Track positions, orders, and events
        
        Returns:
            {
                "gps": GlobalPositionStore with all positions,
                "events": List of execution events,
                "metrics": Performance metrics
            }
        """
        log_info(f"\n{'='*80}")
        log_info(f"STEP 8: Strategy Executor")
        log_info(f"{'='*80}\n")
        
        from src.core.gps import GlobalPositionStore
        from src.backtesting.dict_cache import DictCache
        
        session = enriched_sessions[0]
        strategy_config = session['strategy_config']
        
        # Initialize GPS
        gps = GlobalPositionStore()
        
        # Use the SAME cache that candle builders are writing to (from Step 7)
        # This is critical - otherwise we read from empty cache while builders write to different one
        cache = tick_result['context']['cache'] if 'cache' in tick_result.get('context', {}) else DictCache()
        
        # Initialize nodes from strategy config
        log_info(f"[Step 8] Initializing strategy nodes...")
        
        # Create node instances dict (global registry)
        node_instances = {}
        
        # Create nodes
        nodes_config = strategy_config.get('nodes', [])
        edges_config = strategy_config.get('edges', [])
        
        print(f"[Step 8]   Total nodes: {len(nodes_config)}")
        print(f"[Step 8]   Total edges: {len(edges_config)}")
        
        # Debug: Show node types
        print(f"\n[Step 8] Node types in config:")
        for node_config in nodes_config:
            print(f"[Step 8]   ID: {node_config['id']}, Type: {node_config['type']}")
        
        # Import node classes
        from strategy.nodes.start_node import StartNode
        from strategy.nodes.entry_node import EntryNode
        from strategy.nodes.exit_node import ExitNode
        from strategy.nodes.entry_signal_node import EntrySignalNode
        from strategy.nodes.exit_signal_node import ExitSignalNode
        from strategy.nodes.re_entry_signal_node import ReEntrySignalNode
        
        # Map lowercase config types to node classes
        node_class_map = {
            'startNode': StartNode,
            'entryNode': EntryNode,
            'exitNode': ExitNode,
            'entrySignalNode': EntrySignalNode,
            'exitSignalNode': ExitSignalNode,
            'reEntrySignalNode': ReEntrySignalNode,
            'squareOffNode': ExitNode,  # SquareOff is a type of exit
            'strategyOverview': None  # Skip virtual nodes
        }
        
        # Get trading instrument config from strategy metadata
        # Build it from what we already extracted in metadata
        symbols = metadata['symbols']
        timeframes = metadata['timeframes']
        
        trading_instrument = {
            'symbol': symbols[0] if symbols else 'NIFTY',
            'timeframes': [{'timeframe': tf} for tf in timeframes]
        }
        
        print(f"\n[Step 8] Strategy trading instrument: {trading_instrument.get('symbol')}")
        print(f"[Step 8] Timeframes: {timeframes}")
        
        # Create node instances
        for node_config in nodes_config:
            node_id = node_config['id']
            node_type = node_config['type']
            
            if node_type in node_class_map:
                node_class = node_class_map[node_type]
                
                # Skip virtual nodes
                if node_class is None:
                    print(f"[Step 8]     Skipping virtual node: {node_type} ({node_id})")
                    continue
                
                # For StartNode, inject trading instrument config if missing
                if node_type == 'startNode' and 'tradingInstrumentConfig' not in node_config:
                    node_config['tradingInstrumentConfig'] = trading_instrument
                    print(f"[Step 8]     Injecting trading instrument config into StartNode")
                
                # ALL nodes use the same signature: __init__(self, node_id, data)
                node_instance = node_class(node_id, node_config)
                node_instances[node_id] = node_instance
                print(f"[Step 8]     ✓ Created {node_type}: {node_id}")
            else:
                print(f"[Step 8]     ⚠ Unknown node type: {node_type} for {node_id}")
        
        # Build parent-child relationships from edges
        for edge in edges_config:
            source_id = edge['source']
            target_id = edge['target']
            
            if source_id in node_instances and target_id in node_instances:
                source_node = node_instances[source_id]
                if not hasattr(source_node, 'children'):
                    source_node.children = []
                if target_id not in source_node.children:
                    source_node.children.append(target_id)
        
        # Find StartNode
        start_node_id = None
        for node_id, node in node_instances.items():
            if isinstance(node, StartNode):
                start_node_id = node_id
                break
        
        if not start_node_id:
            log_error("[Step 8] No StartNode found!")
            return {"error": "No StartNode found"}
        
        log_info(f"[Step 8]   StartNode: {start_node_id}")
        
        # Prepare context
        context = {
            'gps': gps,
            'cache': cache,
            'ltp_store': tick_result['ltp_store'],
            'candle_builders': tick_result['candle_builders'],
            'user_id': session['user_id'],
            'strategy_id': session['strategy_id'],
            'session_id': session['session_id'],
            'backtest_date': data_source_info['backtest_date'],
            'strategy_config': strategy_config,
            'candle_df_dict': {},  # Will be populated per tick
            'tick_count': 0,
            'events': [],
            'node_instances': node_instances  # CRITICAL: Needed for children execution
        }
        
        # Execute strategy on all ticks
        log_info(f"\n[Step 8] Executing strategy on all ticks...")
        
        ticks = tick_result['ticks']
        total_ticks = len(ticks)
        
        log_info(f"[Step 8]   Total ticks to process: {total_ticks:,}")
        
        ch_client = data_source_info['ch_client']
        backtest_date = data_source_info['backtest_date']
        symbols = metadata['symbols']
        timeframes = metadata['timeframes']
        
        # Load ALL ticks for full day execution
        query = f"""
            SELECT timestamp, symbol, ltp, ltq
            FROM nse_ticks_indices
            WHERE toDate(timestamp) = '{backtest_date.date()}'
            AND symbol IN {tuple(symbols) if len(symbols) > 1 else f"('{symbols[0]}')"}
            ORDER BY timestamp
        """
        
        log_info(f"[Step 8]   Loading full day ticks from ClickHouse...")
        all_ticks = ch_client.execute(query)
        log_info(f"[Step 8]   Loaded {len(all_ticks):,} ticks")
        
        # Initialize node_states in context
        if 'node_states' not in context:
            context['node_states'] = {}
        
        # Mark StartNode as Active (critical - nodes only execute if Active)
        context['node_states'][start_node_id] = {
            'status': 'Active',
            'visited': False
        }
        print(f"[Step 8] Marked StartNode ({start_node_id}) as Active")
        
        # Get candle builders from tick_result
        candle_builders = tick_result['context']['candle_builders']
        
        log_info(f"[Step 8] Starting tick processing loop...")
        
        for i, tick_row in enumerate(all_ticks):
            timestamp, symbol, ltp, ltq = tick_row
            
            # Prepare tick_data dict for candle builders
            tick_data = {
                'timestamp': timestamp,
                'symbol': symbol,
                'ltp': ltp,
                'ltq': ltq
            }
            
            # 1. Process tick through candle builders (builds candles + calculates indicators)
            for key, builder in candle_builders.items():
                builder_symbol = key.split(':')[0]
                if builder_symbol == symbol:
                    builder.process_tick(tick_data)
            
            # 2. Update LTP store
            context['ltp_store'][symbol] = ltp
            
            # 3. Read latest candles from cache (now includes indicators from callback)
            candle_df_dict = {}
            for key, builder in candle_builders.items():
                symbol_key = key.split(':')[0]
                timeframe = key.split(':')[1]
                # Get completed candles from cache (includes RSI from indicator callback)
                candles = cache.get_candles(symbol_key, timeframe, count=500)
                if candles:
                    candle_df_dict[key] = candles
            
            context['candle_df_dict'] = candle_df_dict
            context['tick_count'] = i + 1
            context['current_timestamp'] = timestamp
            context['current_ltp'] = ltp
            
            # Reset visited flags for all nodes
            for node_id, node in node_instances.items():
                if hasattr(node, 'reset_visited'):
                    node.reset_visited(context)
            
            # Execute StartNode (will cascade to children)
            start_node = node_instances[start_node_id]
            result = start_node.execute(context)
            
            # Detailed logging at specific time (09:19:00) and first few ticks
            time_str = timestamp.strftime('%H:%M:%S') if hasattr(timestamp, 'strftime') else str(timestamp)
            is_debug_time = '09:19:' in time_str
            
            if i < 3 or is_debug_time:
                print(f"\n{'='*80}")
                print(f"[Step 8] Tick {i+1} execution at {timestamp}")
                print(f"{'='*80}")
                print(f"  LTP: {ltp}")
                
                # Show LTP Store
                print(f"\n  LTP STORE:")
                for sym, ltp_val in context.get('ltp_store', {}).items():
                    print(f"    {sym}: ₹{ltp_val:.2f}")
                
                # Show Candle Store
                print(f"\n  CANDLE STORE:")
                candle_df_dict = context.get('candle_df_dict', {})
                for key, candles in candle_df_dict.items():
                    if candles and isinstance(candles, list):
                        print(f"\n    {key}: {len(candles)} candles")
                        # Show last 3 candles with all their data
                        for idx, candle in enumerate(candles[-3:], start=len(candles)-2):
                            print(f"      [{idx}] {candle.get('timestamp')}")
                            print(f"          OHLC: O={candle.get('open'):.2f} H={candle.get('high'):.2f} L={candle.get('low'):.2f} C={candle.get('close'):.2f}")
                            # Check for indicators
                            indicators = {k: v for k, v in candle.items() if k.upper() in ['RSI', 'EMA', 'SMA'] or '_' in k}
                            if indicators:
                                print(f"          Indicators: {indicators}")
                            else:
                                print(f"          Indicators: NONE")
                
                # Show Entry Condition Nodes
                print(f"\n  ENTRY CONDITION NODES:")
                for node_id in ['entry-condition-1', 'entry-condition-2']:
                    if node_id in node_instances:
                        node = node_instances[node_id]
                        state = context.get('node_states', {}).get(node_id, {})
                        print(f"\n    {node_id}:")
                        print(f"      Status: {state.get('status', 'Unknown')}")
                        print(f"      Signal Triggered: {getattr(node, 'signal_triggered', 'N/A')}")
                        
                        # Show conditions
                        conditions = getattr(node, 'conditions', [])
                        print(f"      Conditions ({len(conditions)}):")
                        for idx, cond in enumerate(conditions, 1):
                            print(f"        [{idx}] {cond}")
                
                print(f"\n  Strategy Execution Result:")
                print(f"    Node: {result.get('node_id', 'Unknown')}")
                print(f"    Executed: {result.get('executed', False)}")
                print(f"    GPS Positions: {len(gps.positions)}")
                print(f"{'='*80}\n")
            
            # Check for errors in result
            if result and 'error' in result:
                if i == 0:
                    print(f"[Step 8] StartNode error: {result['error']}")
            
            # Progress logging
            if (i + 1) % 5000 == 0:
                print(f"[Step 8]     Processed {i + 1:,} / {len(all_ticks):,} ticks...")
                print(f"[Step 8]     GPS positions: {len(gps.positions)}")
        
        log_info(f"\n[Step 8] ✅ Strategy execution complete")
        log_info(f"[Step 8]   Total ticks processed: {len(all_ticks):,}")
        log_info(f"[Step 8]   Total positions: {len(gps.positions)}")
        
        # Show GPS state
        log_info(f"\n[Step 8] GlobalPositionStore (GPS) Summary:")
        log_info(f"[Step 8]   Total positions: {len(gps.positions)}")
        
        for position_id, position_list in gps.positions.items():
            log_info(f"\n[Step 8]   Position ID: {position_id}")
            log_info(f"[Step 8]     Transactions: {len(position_list)}")
            
            for transaction in position_list:
                status = "OPEN" if transaction.get('exit_time') is None else "CLOSED"
                entry_price = transaction.get('entry_price', 0)
                exit_price = transaction.get('exit_price', 0)
                quantity = transaction.get('actual_quantity', 0)
                pnl = transaction.get('pnl', 0)
                
                log_info(f"[Step 8]       Position #{transaction.get('position_num')}: {status}")
                log_info(f"[Step 8]         Entry: {transaction.get('entry_time')} @ ₹{entry_price:.2f} x {quantity}")
                if exit_price:
                    log_info(f"[Step 8]         Exit:  {transaction.get('exit_time')} @ ₹{exit_price:.2f}")
                    log_info(f"[Step 8]         P&L:   ₹{pnl:.2f}")
        
        return {
            "gps": gps,
            "positions_count": len(gps.positions),
            "context": context,
            "nodes": node_instances
        }
    
    def _calculate_lookback_days(self, timeframe: str, num_candles: int) -> int:
        """
        Calculate number of days needed to load num_candles for given timeframe
        
        Uses LOOKBACK_DAYS_CONFIG logic with buffer for holidays/weekends
        """
        # Simplified mapping (should use existing LOOKBACK_DAYS_CONFIG)
        lookback_map = {
            "1m": {500: 7},
            "3m": {500: 15},
            "5m": {500: 20},
            "15m": {500: 50},
            "1h": {500: 120},
            "1d": {500: 750}
        }
        
        return lookback_map.get(timeframe, {}).get(num_candles, 30)
    
    def _extract_indicator_name(self, indicator_key: str) -> str:
        """
        Extract indicator name from key like 'rsi_1764509210372'
        Returns: 'rsi'
        """
        if '_' in indicator_key:
            return indicator_key.split('_')[0]
        return indicator_key
    
    # ============================================================================
    # HELPER METHODS: Cache & Mock Data
    # ============================================================================
    
    def _cache_strategy(self, strategy_id: str, strategy_data: Dict[str, Any]):
        """Cache strategy data to file"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"strategy_{strategy_id}.json"
            with open(cache_file, 'w') as f:
                json.dump(strategy_data, f, indent=2)
            log_info(f"[Cache] Saved strategy to {cache_file}")
        except Exception as e:
            log_error(f"[Cache] Error saving strategy: {e}")
    
    def _cache_broker(self, broker_id: str, broker_data: Dict[str, Any]):
        """Cache broker data to file"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"broker_{broker_id}.json"
            with open(cache_file, 'w') as f:
                json.dump(broker_data, f, indent=2)
            log_info(f"[Cache] Saved broker to {cache_file}")
        except Exception as e:
            log_error(f"[Cache] Error saving broker: {e}")
    
    def _get_mock_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Get mock strategy data for offline testing"""
        return {
            "id": strategy_id,
            "name": "Test Straddle Strategy (Mock)",
            "user_id": "d70ec04a-1025-46c5-94c4-3e6bff499644",
            "config": {
                "id": strategy_id,
                "name": "Test Straddle Strategy (Mock)",
                "trading_instrument_type": "OPTIONS",
                "symbol": "NIFTY",
                "timeframe": "1m",
                "nodes": {
                    "strategy-controller": {
                        "node_id": "strategy-controller",
                        "node_type": "StartNode",
                        "node_name": "Start"
                    }
                }
            }
        }
    
    def _get_mock_broker(self, broker_id: str) -> Dict[str, Any]:
        """Get mock broker data for offline testing"""
        return {
            "broker_name": "clickhouse",
            "date": "2024-10-29",
            "scale": 1.0,
            "meta_data": {
                "date": "2024-10-29",
                "scale": 1.0
            }
        }


# ============================================================================
# TEST STEPS 1-3
# ============================================================================

def test_steps_1_8():
    """
    Test Steps 1-8: Complete strategy execution with GPS tracking
    """
    print("\n" + "="*80)
    print("TESTING STEPS 1-8: Modular Backtest Orchestration (Full Day)")
    print("="*80 + "\n")
    
    # Sample payload (exact format from requirements)
    session_payload = {
        "5708424d-5962-4629-978c-05b3a174e104_acf98a95-1547-4a72-b824-3ce7068f05b4": {
            "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
            "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
            "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4"
        }
    }
    
    # Initialize orchestrator (will use cached data from previous Supabase fetch)
    orchestrator = BacktestOrchestrator(offline_mode=False)
    
    # Execute Steps 1-3
    enriched_sessions = orchestrator.prepare_enriched_sessions(session_payload)
    
    if enriched_sessions:
        print("\n✅ Steps 1-3 completed successfully!")
        print(f"\nEnriched Sessions: {len(enriched_sessions)}")
        
        for session in enriched_sessions:
            print(f"\nSession ID: {session['session_id']}")
            print(f"  Strategy: {session['strategy_name']}")
            print(f"  Date: {session['execution_date']}")
            print(f"  Scale: {session['scale']}")
            print(f"  Broker: {session['broker_name']}")
            
            config = session['strategy_config']
            print(f"\n  Strategy Config Keys: {list(config.keys())}")
            if 'nodes' in config:
                print(f"  Nodes: {len(config['nodes'])} nodes")
        
        # Execute Step 4: Metadata Scanner
        metadata = orchestrator.scan_metadata(enriched_sessions)
        
        print("\n✅ Steps 1-4 completed successfully!")
        print(f"\nMetadata Summary:")
        print(f"  Symbols: {metadata['symbols']}")
        print(f"  Timeframes: {metadata['timeframes']}")
        print(f"  Indicators: {list(metadata['indicators'].keys())}")
        print(f"  Options Enabled: {metadata['options_config'].get('enabled', False)}")
        
        # Execute Step 5: Data Initializer
        try:
            data_prep = orchestrator.initialize_data_stores(enriched_sessions, metadata)
            
            print("\n✅ Step 5 completed successfully!")
            print(f"\nData Configuration Summary:")
            print(f"  Data requirements: {len(data_prep['data_requirements'])}")
            for req in data_prep['data_requirements']:
                print(f"    {req['symbol']}:{req['timeframe']} - {req['num_candles']} candles, {len(req['indicators'])} indicators")
            
        except Exception as e:
            print(f"\n❌ Step 5 failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Execute Step 6: Data Source Manager
        try:
            data_source_info = orchestrator.initialize_data_source(
                enriched_sessions, 
                metadata,
                broker_type='clickhouse'  # Backtesting uses ClickHouse
            )
            
            print("\n✅ Steps 1-6 completed successfully!")
            print(f"\nData Source Summary:")
            print(f"  Broker Type: {data_source_info['broker_type']}")
            print(f"  Subscriptions: {', '.join(data_source_info['subscriptions'])}")
            print(f"  Backtest Date: {data_source_info.get('backtest_date', 'N/A')}")
            
            # VERIFICATION: Test actual data loading from ClickHouse
            print(f"\n{'='*80}")
            print("VERIFICATION: Testing Real Data from ClickHouse")
            print(f"{'='*80}\n")
            
            try:
                tick_source = data_source_info['data_source']
                ch_client = data_source_info['ch_client']
                
                # Query tick count
                query = f"""
                    SELECT COUNT(*) as count
                    FROM nse_ticks_indices
                    WHERE toDate(timestamp) = '{data_source_info['backtest_date'].date()}'
                    AND symbol = 'NIFTY'
                """
                result = ch_client.execute(query)
                total_ticks = result[0][0] if result else 0
                
                print(f"Total NIFTY ticks on {data_source_info['backtest_date'].date()}: {total_ticks:,}")
                
                # Get sample ticks
                sample_query = f"""
                    SELECT timestamp, symbol, ltp, ltq, oi
                    FROM nse_ticks_indices
                    WHERE toDate(timestamp) = '{data_source_info['backtest_date'].date()}'
                    AND symbol = 'NIFTY'
                    ORDER BY timestamp
                    LIMIT 5
                """
                sample_ticks = ch_client.execute(sample_query)
                
                if sample_ticks:
                    print(f"\nFirst 5 ticks:")
                    print(f"  {'Timestamp':<25} {'Symbol':<10} {'LTP':<10} {'LTQ':<10} {'OI':<10}")
                    print(f"  {'-'*70}")
                    for tick in sample_ticks:
                        ts, sym, ltp, ltq, oi = tick
                        print(f"  {str(ts):<25} {sym:<10} {ltp:<10.2f} {ltq:<10} {oi:<10}")
                    
                    # Get time range
                    range_query = f"""
                        SELECT 
                            MIN(timestamp) as first_tick,
                            MAX(timestamp) as last_tick
                        FROM nse_ticks_indices
                        WHERE toDate(timestamp) = '{data_source_info['backtest_date'].date()}'
                        AND symbol = 'NIFTY'
                    """
                    range_result = ch_client.execute(range_query)
                    if range_result:
                        first_tick, last_tick = range_result[0]
                        print(f"\nTime Range:")
                        print(f"  First tick: {first_tick}")
                        print(f"  Last tick:  {last_tick}")
                        
                        # Calculate duration
                        duration = last_tick - first_tick
                        hours = duration.total_seconds() / 3600
                        print(f"  Duration:   {hours:.2f} hours")
                    
                    print(f"\n✅ Data verification successful!")
                    print(f"   - {total_ticks:,} ticks available")
                    print(f"   - Data format validated")
                    print(f"   - Ready for tick processing")
                else:
                    print(f"❌ No tick data found for NIFTY on {data_source_info['backtest_date'].date()}")
                    
            except Exception as e:
                print(f"❌ Data verification failed: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"\n{'='*80}")
            
        except Exception as e:
            print(f"\n❌ Step 6 failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Execute Step 7: Tick Batch Processor
        try:
            print(f"\n{'='*80}")
            print("STEP 7: Starting tick processing (limited to 5,000 ticks for testing)")
            print(f"{'='*80}\n")
            
            tick_result = orchestrator.process_ticks(
                enriched_sessions,
                metadata,
                data_prep,
                data_source_info,
                max_ticks=5000  # Limit for fast testing
            )
            
            print(f"\n✅ Steps 1-7 completed successfully!")
            print(f"\n{'='*80}")
            print("CANDLE STORE & LTP STORE AFTER 5,000 TICKS")
            print(f"{'='*80}\n")
            
            # Show completed candles
            print("COMPLETED CANDLES:")
            for key, candles in tick_result['completed_candles'].items():
                print(f"\n  {key}: {len(candles)} completed candles")
                if candles:
                    print(f"    First candle: {candles[0]['timestamp']}")
                    print(f"      O: {candles[0]['open']:.2f} | H: {candles[0]['high']:.2f} | L: {candles[0]['low']:.2f} | C: {candles[0]['close']:.2f} | V: {candles[0]['volume']}")
                    print(f"    Last candle:  {candles[-1]['timestamp']}")
                    print(f"      O: {candles[-1]['open']:.2f} | H: {candles[-1]['high']:.2f} | L: {candles[-1]['low']:.2f} | C: {candles[-1]['close']:.2f} | V: {candles[-1]['volume']}")
            
            # Show forming candles
            print(f"\nFORMING CANDLES (Current incomplete candle):")
            for key, builder in tick_result['candle_builders'].items():
                symbol = key.split(':')[0]
                if symbol in builder.current_candles:
                    forming = builder.current_candles[symbol]
                    print(f"  {key}:")
                    print(f"    Timestamp: {forming['timestamp']}")
                    print(f"    O: {forming['open']:.2f} | H: {forming['high']:.2f} | L: {forming['low']:.2f} | C: {forming['close']:.2f} | V: {forming['volume']}")
            
            # Show LTP store
            print(f"\nLTP STORE:")
            for symbol, ltp in tick_result['ltp_store'].items():
                print(f"  {symbol}: ₹{ltp:.2f}")
            
            print(f"\n{'='*80}")
            print(f"Ready for Step 8: Strategy execution with {tick_result['ticks_loaded']:,} ticks")
            print(f"{'='*80}")
            
        except Exception as e:
            print(f"\n❌ Step 7 failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Execute Step 8: Strategy Execution (Full Day)
        try:
            print(f"\n{'='*80}")
            print("STEP 8: Starting strategy execution (FULL DAY - 47,438 ticks)")
            print(f"{'='*80}\n")
            
            strategy_result = orchestrator.execute_strategy(
                enriched_sessions,
                metadata,
                data_prep,
                data_source_info,
                tick_result
            )
            
            # Check if strategy execution succeeded
            if 'gps' not in strategy_result:
                print(f"\n❌ Strategy execution returned incomplete result")
                print(f"   Keys returned: {list(strategy_result.keys())}")
                if 'error' in strategy_result:
                    print(f"   Error: {strategy_result['error']}")
                return
            
            print(f"\n✅ Steps 1-8 completed successfully!")
            print(f"\n{'='*80}")
            print("GLOBAL POSITION STORE (GPS) - FULL DAY RESULTS")
            print(f"{'='*80}\n")
            
            gps = strategy_result['gps']
            
            print(f"Total Position IDs: {len(gps.positions)}")
            print(f"Total Transactions: {sum(len(pos_list) for pos_list in gps.positions.values())}\n")
            
            # Show detailed position breakdown
            for position_id, position_list in gps.positions.items():
                print(f"\n{'─'*80}")
                print(f"POSITION ID: {position_id}")
                print(f"{'─'*80}")
                print(f"Total Transactions: {len(position_list)}\n")
                
                for idx, transaction in enumerate(position_list, 1):
                    status = "🟢 OPEN" if transaction.get('exit_time') is None else "🔴 CLOSED"
                    entry_price = transaction.get('entry_price', 0)
                    exit_price = transaction.get('exit_price', 0)
                    quantity = transaction.get('actual_quantity', 0)
                    pnl = transaction.get('pnl', 0)
                    position_num = transaction.get('position_num', idx)
                    
                    print(f"  Position #{position_num}: {status}")
                    print(f"    Entry Time:  {transaction.get('entry_time')}")
                    print(f"    Entry Price: ₹{entry_price:.2f}")
                    print(f"    Quantity:    {quantity}")
                    
                    if exit_price:
                        print(f"    Exit Time:   {transaction.get('exit_time')}")
                        print(f"    Exit Price:  ₹{exit_price:.2f}")
                        print(f"    P&L:         ₹{pnl:.2f} ({'+' if pnl >= 0 else ''}{pnl:.2f})")
                    else:
                        print(f"    Status:      Position still OPEN")
                    print()
            
            # Calculate summary statistics
            total_pnl = 0
            closed_positions = 0
            open_positions = 0
            winning_trades = 0
            losing_trades = 0
            
            for position_list in gps.positions.values():
                for transaction in position_list:
                    if transaction.get('exit_time'):
                        closed_positions += 1
                        pnl = transaction.get('pnl', 0)
                        total_pnl += pnl
                        if pnl > 0:
                            winning_trades += 1
                        elif pnl < 0:
                            losing_trades += 1
                    else:
                        open_positions += 1
            
            print(f"\n{'='*80}")
            print("SUMMARY STATISTICS")
            print(f"{'='*80}")
            print(f"  Total Positions:    {closed_positions + open_positions}")
            print(f"  Closed Positions:   {closed_positions}")
            print(f"  Open Positions:     {open_positions}")
            print(f"  Winning Trades:     {winning_trades}")
            print(f"  Losing Trades:      {losing_trades}")
            print(f"  Total P&L:          ₹{total_pnl:.2f}")
            if closed_positions > 0:
                print(f"  Avg P&L per trade:  ₹{total_pnl/closed_positions:.2f}")
                print(f"  Win Rate:           {winning_trades/closed_positions*100:.1f}%")
            print(f"{'='*80}")
            
        except Exception as e:
            print(f"\n❌ Step 8 failed: {e}")
            import traceback
            traceback.print_exc()
        
    else:
        print("\n❌ Steps 1-3 failed - no sessions enriched")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    test_steps_1_8()
