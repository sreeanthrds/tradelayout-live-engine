# Unified Execution Engine Architecture

**Date:** December 20, 2024  
**Objective:** Transform `CentralizedBacktestEngine` into a unified execution engine supporting multiple strategies for both backtesting and live simulation modes.

---

## 🎯 Vision

**One Engine, Three Modes:**
1. **Backtesting** (speed=0): Fast historical replay, no delays
2. **Live Simulation** (speed>0): Real-time simulation with configurable speed (500x, 1000x, etc.)
3. **Live Trading** (future): Real broker integration, incremental addition

**Key Principle:** Live simulation executes EXACTLY the same code path as backtesting, just with different speed control.

---

## 📋 Current State Analysis

### Working Components ✅
- `CentralizedBacktestEngine`: Proven, reliable, creates 9 positions
- DataManager: Proper cache, indicators, historical candles
- Strategy nodes: Entry, Exit, SquareOff all working
- File output: Single strategy writes to dashboard JSON

### Issues to Resolve ❌
- **Single strategy only**: Current engine runs one strategy at a time
- **Duplicate code paths**: Queue execution has separate flow (incomplete)
- **No speed control**: Backtesting runs at max speed only
- **Monolithic output**: All strategies write to single file

---

## 🏗️ Architecture Changes

### 1. Multi-Strategy Support

**Current Flow (Single Strategy):**
```python
CentralizedBacktestEngine(
    strategy_config=strategy,  # Single strategy dict
    backtest_date="2024-10-29",
    broker_name="clickhouse"
)
```

**New Flow (Multiple Strategies):**
```python
UnifiedExecutionEngine(
    strategies=[
        {
            'strategy_id': '5708424d-...',
            'user_id': 'user_2yfjT...',
            'strategy_config': {...},
            'broker_connection_id': 'acf98a95-...',
            'scale': 1
        },
        {
            'strategy_id': 'another-id',
            'user_id': 'user_2yfjT...',
            'strategy_config': {...},
            'broker_connection_id': 'acf98a95-...',
            'scale': 2
        }
    ],
    execution_date="2024-10-29",
    mode="live_simulation",  # or "backtest"
    speed_multiplier=500,    # 0 for backtest, >0 for live sim
    broker_name="clickhouse"
)
```

**Key Changes:**
- Accept list of strategies instead of single strategy
- Each strategy tracked independently with unique instance ID
- Shared DataManager (one cache for all strategies)
- Per-strategy context, GPS, and state

---

### 2. Speed Control Architecture

**Implementation:**
```python
class UnifiedExecutionEngine:
    def __init__(self, ..., speed_multiplier=0):
        self.speed_multiplier = speed_multiplier
        self.mode = "backtest" if speed_multiplier == 0 else "live_simulation"
    
    async def _process_tick_batch(self, tick_batch):
        """Process ticks with optional speed control"""
        for tick in tick_batch:
            # Execute strategy logic (SAME for both modes)
            self._execute_strategies(tick)
            
            # Speed control (ONLY difference between modes)
            if self.speed_multiplier > 0:
                await asyncio.sleep(1.0 / self.speed_multiplier)
```

**Modes:**
- **Backtesting (speed=0)**: No sleep, runs at max CPU speed
- **Live Simulation (speed=500)**: Sleep 2ms per tick (500x real-time)
- **Live Simulation (speed=1)**: Sleep 1s per tick (real-time speed)

**Benefits:**
- Zero code duplication
- Easy mode switching
- Predictable behavior

---

### 3. Per-Strategy File Output

**Current (Monolithic):**
```
backtest_dashboard_data.json  # ALL strategies write here
```

**New (Per-Strategy with Idempotent Re-runs):**
```
backtest_data/
  ├── user_2yfjTGEKjL7XkklQyBaMP6SN2Lc/
  │   ├── 5708424d-5962_acf98a95-1547/     # strategy_id + broker_connection_id
  │   │   ├── positions.json               # Incremental writes
  │   │   ├── trades.json                  # Incremental writes
  │   │   ├── metrics.json                 # Updated per tick
  │   │   └── events.jsonl                 # Streaming events
  │   └── another-strategy_another-broker/
  │       ├── positions.json
  │       └── ...
```

**Folder Naming Convention:**
```python
folder_name = f"{strategy_id[:13]}_{broker_connection_id[:13]}"
# Example: 5708424d-5962_acf98a95-1547
```

**Benefits:**
- **Idempotent re-runs**: Running the same strategy+broker replaces existing results
- **Broker isolation**: Same strategy with different brokers = separate folders
- **Clean overwrites**: No stale data from previous runs
- **Easy identification**: Folder name shows both strategy and broker config

**File Format Changes:**

**positions.json** (Incremental append):
```json
{
  "pos_1": {
    "entry_time": "2024-10-29T09:45:23",
    "symbol": "NIFTY28OCT2525900CE",
    "side": "BUY",
    "quantity": 75,
    "entry_price": 125.50,
    "status": "open"
  }
}
```

**Write Strategy:**
- **Backtesting**: Batch write at end (fast)
- **Live Simulation**: Incremental write on position changes (UI real-time)

---

### 4. Shared vs Isolated Components

**Shared (One per execution):**
```python
# Data layer - shared across all strategies
data_manager = DataManager(cache, shared_cache)
clickhouse_client = HttpClient()

# One engine instance manages all strategies
engine = UnifiedExecutionEngine(strategies=[...])
```

**Isolated (One per strategy):**
```python
# Each strategy gets independent state
for strategy in strategies:
    context = {
        'strategy_id': strategy['strategy_id'],
        'user_id': strategy['user_id'],
        'gps': GPS(strategy_config),           # Independent position tracking
        'data_manager': data_manager,          # SHARED
        'output_writer': FileWriter(strategy_dir)  # Independent files
    }
```

---

## 🔧 Implementation Plan

### Phase 1: Rename and Restructure
**Goal:** Rename `CentralizedBacktestEngine` → `UnifiedExecutionEngine`

**Files to modify:**
- `src/backtesting/centralized_backtest_engine.py` → `src/execution/unified_execution_engine.py`
- Update imports across codebase

**Changes:**
- Rename class
- Add `mode` parameter (`backtest` | `live_simulation` | `live_trading`)
- Add `speed_multiplier` parameter

---

### Phase 2: Multi-Strategy Core
**Goal:** Support multiple strategies in single execution

**Key Changes in UnifiedExecutionEngine:**

```python
class UnifiedExecutionEngine:
    def __init__(self, strategies: List[Dict], execution_date, mode, speed_multiplier=0):
        self.strategies = strategies
        self.mode = mode
        self.speed_multiplier = speed_multiplier
        
        # Shared components (ONE for all strategies)
        self.data_manager = self._create_shared_data_manager()
        
        # Strategy-specific state (ONE per strategy)
        self.strategy_states = {}
        for strategy in strategies:
            instance_id = self._get_instance_id(strategy)
            self.strategy_states[instance_id] = {
                'config': strategy['strategy_config'],
                'context': self._create_context(strategy),
                'output_writer': FileWriter(strategy),
                'active': True
            }
    
    def _aggregate_metadata(self) -> Dict:
        """Combine all strategies' metadata for data loading"""
        agg = {
            'symbols': set(),
            'timeframes': set(),
            'indicators': {}
        }
        
        for strategy in self.strategies:
            metadata = strategy['strategy_config'].get('metadata', {})
            # Extract symbols, timeframes, indicators
            # Merge into aggregated structure
        
        return agg
    
    async def run(self):
        """Main execution loop - SAME for both modes"""
        # 1. Aggregate metadata from all strategies
        strategies_agg = self._aggregate_metadata()
        
        # 2. Initialize data manager (shared)
        self.data_manager.initialize(strategies_agg)
        
        # 3. Register indicators (shared)
        self.data_manager.register_indicators_from_agg(strategies_agg)
        
        # 4. Load historical candles (shared)
        self.data_manager.load_historical_candles(strategies_agg)
        
        # 5. Load ticks (shared)
        ticks = self.data_manager.load_ticks(date, symbols)
        
        # 6. Process ticks with speed control
        await self._process_ticks(ticks)
        
        # 7. Finalize outputs (per-strategy)
        self._write_final_outputs()
```

**Critical Change - Tick Processing:**
```python
async def _process_ticks(self, ticks):
    """Process ticks with optional speed control"""
    for tick in ticks:
        # Execute ALL active strategies on this tick
        for instance_id, state in self.strategy_states.items():
            if state['active']:
                self._execute_strategy_tick(state, tick)
                
                # Write incremental updates (live simulation only)
                if self.mode == "live_simulation":
                    state['output_writer'].write_position_updates()
        
        # Speed control (ONLY difference between modes)
        if self.speed_multiplier > 0:
            await asyncio.sleep(1.0 / self.speed_multiplier)
        
        # Check if all strategies terminated
        if not any(s['active'] for s in self.strategy_states.values()):
            break
```

---

### Phase 3: Per-Strategy Output Writers

**New Component: `StrategyOutputWriter`**

```python
class StrategyOutputWriter:
    """Handles file I/O for a single strategy"""
    
    def __init__(self, user_id, strategy_instance_id, mode):
        self.user_id = user_id
        self.instance_id = strategy_instance_id
        self.mode = mode
        self.output_dir = self._create_output_dir()
        
        # File handles for incremental writes
        self.positions_file = self.output_dir / "positions.json"
        self.trades_file = self.output_dir / "trades.json"
        self.metrics_file = self.output_dir / "metrics.json"
        
    def write_position_update(self, position_data):
        """Write/update single position (incremental)"""
        if self.mode == "live_simulation":
            # Read existing, update, write back
            positions = self._read_json(self.positions_file)
            positions[position_data['id']] = position_data
            self._write_json(self.positions_file, positions)
    
    def write_batch(self, all_positions, all_trades, metrics):
        """Batch write at end (backtesting)"""
        self._write_json(self.positions_file, all_positions)
        self._write_json(self.trades_file, all_trades)
        self._write_json(self.metrics_file, metrics)
```

---

### Phase 4: Update API Integration

**Replace Queue Execution with Unified Engine:**

```python
# backtest_api_server.py

@app.post("/api/queue/execute")
async def execute_queue(queue_type: str, trigger_type: str):
    """Execute strategies using unified engine"""
    
    # Get queued strategies
    strategies = queue_manager.get_queued_strategies(queue_type)
    
    # Determine mode and speed
    if queue_type == "admin_tester":
        mode = "live_simulation"
        speed_multiplier = 500  # 500x speed
    else:
        mode = "backtest"
        speed_multiplier = 0
    
    # Execute using unified engine
    engine = UnifiedExecutionEngine(
        strategies=strategies,
        execution_date=datetime(2024, 10, 29),
        mode=mode,
        speed_multiplier=speed_multiplier
    )
    
    await engine.run()
    
    return {"status": "completed", "strategy_count": len(strategies)}
```

**Backtesting endpoint (UNCHANGED in behavior):**
```python
@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest):
    """Run backtesting using unified engine"""
    
    # Single strategy for backtest
    strategies = [{
        'strategy_id': request.strategy_id,
        'user_id': request.user_id,
        'strategy_config': strategy_config,
        'broker_connection_id': request.broker_connection_id,
        'scale': 1
    }]
    
    # Execute in backtest mode (speed=0)
    engine = UnifiedExecutionEngine(
        strategies=strategies,
        execution_date=request.backtest_date,
        mode="backtest",
        speed_multiplier=0  # Max speed
    )
    
    await engine.run()
    
    return {"status": "completed"}
```

---

## 📊 Benefits

### 1. Code Simplification
- **Before:** 2 separate execution paths (backtesting + queue execution)
- **After:** 1 unified execution path

### 2. Reliability
- Queue execution uses proven backtesting logic
- 9 positions problem solved automatically
- No more initialization mismatches

### 3. Multi-Strategy Support
- Run multiple strategies simultaneously
- Shared data loading (efficiency)
- Independent position tracking

### 4. Maintainability
- Single codebase to maintain
- Bug fixes apply to both modes
- Easy to add live trading later

### 5. Scalability
- Per-strategy file isolation
- UI can load individual strategy data
- Parallel strategy execution (future)

---

## 🔮 Future: Live Trading Mode

**Phase 5 (Later): Add Live Trading**

**Minimal Changes Needed:**
```python
class UnifiedExecutionEngine:
    async def _process_ticks(self, ticks):
        if self.mode == "live_trading":
            # Connect to broker WebSocket
            async for tick in broker_websocket:
                self._execute_strategies(tick)
        else:
            # Backtesting/simulation (existing code)
            for tick in ticks:
                self._execute_strategies(tick)
                if self.speed_multiplier > 0:
                    await asyncio.sleep(1.0 / self.speed_multiplier)
```

**Additional Components:**
- Broker WebSocket adapter
- Order execution module (already exists in `order_placer_impl.py`)
- Real-time risk management

**Key Point:** Strategy execution logic remains UNCHANGED. Only tick source and order placement differ.

---

## ✅ Success Criteria

### Must Have:
1. ✅ Backtesting produces 9 positions (existing behavior preserved)
2. ✅ Live simulation produces 9 positions (same logic, with speed control)
3. ✅ Multiple strategies execute independently
4. ✅ Per-strategy file output working
5. ✅ UI can load individual strategy data

### Performance:
- Backtesting: Same speed as current (no regression)
- Live simulation: Smooth playback at 500x speed
- Multi-strategy: Minimal overhead (<10% per additional strategy)

---

## 🧪 Testing Strategy (Old vs New Comparison)

### Backup Files Created
```
src/backtesting/
  ├── centralized_backtest_engine.py              # Will become unified engine
  ├── centralized_backtest_engine_v1_backup.py    # OLD engine (frozen)
  └── ...

test_old_backtest_baseline.py                      # Test old engine (9 positions baseline)
test_new_unified_engine.py                         # Test new engine (should match)
```

### Comparison Testing Workflow
1. **Run old engine** → Verify 9 positions created ✅
2. **Implement new engine** → Transform to unified architecture
3. **Run new engine (backtest mode)** → Should also create 9 positions
4. **Compare results** → Positions, trades, P&L must match exactly
5. **Test live simulation** → Same 9 positions, just with speed control
6. **Test multi-strategy** → Multiple strategies simultaneously

### Success Criteria
- ✅ Old engine: 9 positions (baseline)
- ✅ New engine backtest mode: 9 positions (matching baseline)
- ✅ New engine live simulation: 9 positions (same logic, with delays)
- ✅ P&L matches exactly between old and new
- ✅ Multi-strategy: Each strategy produces expected positions independently

---

## 🚀 Implementation Order

1. **Document architecture** ✅
2. **Create backup** ✅
   - Backup old engine: `centralized_backtest_engine_v1_backup.py`
   - Create baseline test: `test_old_backtest_baseline.py`
3. **Run baseline test** → Verify old engine creates 9 positions
4. **Transform to unified engine**
   - Keep same file: `centralized_backtest_engine.py`
   - Rename class: `CentralizedBacktestEngine` → `UnifiedExecutionEngine`
   - Add multi-strategy support
   - Add speed control
5. **Create per-strategy output** with folder naming: `{strategy_id}_{broker_connection_id}`
6. **Test new engine backtest mode** → Compare with baseline
7. **Test new engine live simulation** → Verify smooth playback
8. **Test multi-strategy** → Run 2+ strategies simultaneously
9. **Update API integration** → Replace queue execution with unified engine

---

## 📝 Notes

- **Backward compatibility:** Existing backtesting scripts can still call engine with single strategy
- **No UI changes:** File structure compatible with current UI expectations
- **Safe migration:** Each phase independently testable
- **Incremental approach:** Add features without breaking existing functionality

---

**Next Step:** Begin Phase 1 - Rename and add mode/speed parameters
