#!/usr/bin/env python3
"""
Debug Strategy 5708424d-5962-4629-978c-05b3a174e104 on Oct 29, 2024
Focus on timestamps: 09:17:00 (entry) and 10:48:00 (exit)

Expected Entry Conditions:
- RSI < 30 (potential_entry = True at 09:17:00, RSI=27.39)
- Time after 09:17:00
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from datetime import datetime, time as dt_time
import pandas as pd
from src.adapters.supabase_adapter import SupabaseStrategyAdapter
from strategy.strategy_builder import build_strategy
from src.utils.logger import log_info, log_error, log_warning
from src.backtesting.backtest_context_manager import BacktestContextManager
from src.core.gps import GlobalPositionStore
import json

print(f"\n{'='*100}")
print(f"DEBUG STRATEGY: 5708424d-5962-4629-978c-05b3a174e104")
print(f"Date: 2024-10-29")
print(f"Focus Timestamps: 09:17:00 (entry), 10:48:00 (exit)")
print(f"{'='*100}\n")

# Load strategy
strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
user_id = 'user_2yfjTGEKjL7XkklQyBaMP6SN2Lc'  # From strategy_config.json

adapter = SupabaseStrategyAdapter()
strategy_config = adapter.get_strategy(strategy_id, user_id)

if not strategy_config:
    print(f"❌ Strategy {strategy_id} not found!")
    sys.exit(1)

print(f"✅ Strategy loaded: {strategy_config.get('name', 'Unknown')}")
print(f"   User ID: {strategy_config.get('user_id')}")

# Load candle data for Oct 29, 2024
csv_file = '/Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine/candles_rsi_NIFTY_2024-10-29.csv'
print(f"\n📊 Loading candle data from: {csv_file}")

df = pd.read_csv(csv_file)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

print(f"   Candles loaded: {len(df)}")
print(f"   Time range: {df.index[0]} to {df.index[-1]}")

# Check RSI values at key timestamps
print(f"\n🔍 RSI Values at Key Timestamps:")
key_times = ['2024-10-29 09:17:00', '2024-10-29 09:18:00', '2024-10-29 10:45:00', '2024-10-29 10:47:00', '2024-10-29 10:48:00']
for ts in key_times:
    if ts in df.index.astype(str).values:
        row = df.loc[ts]
        print(f"   {ts}: RSI={row['rsi_14']:.2f}, Close={row['close']:.2f}, Open={row['open']:.2f}")

# Build strategy
print(f"\n🏗️  Building strategy...")
start_node = build_strategy(strategy_config)

print(f"\n📋 Strategy Structure:")
print(f"   Start Node ID: {start_node.id}")
print(f"   Start Node Type: {type(start_node).__name__}")
print(f"   Children: {start_node.children if hasattr(start_node, 'children') else 'None'}")

# Show entry conditions
entry_signal_data = strategy_config.get('tradeConfig', {}).get('entry', {})
entry_conditions = entry_signal_data.get('conditions', [])
print(f"\n📝 Entry Conditions:")
print(json.dumps(entry_conditions, indent=2))

# Initialize GPS and context manager
gps = GlobalPositionStore()
context_manager = BacktestContextManager(
    start_node=start_node,
    gps=gps,
    date=datetime(2024, 10, 29).date(),
    max_positions=10,
    mode='backtesting'
)

print(f"\n🎯 Processing Focus Timestamps...")
print(f"{'='*100}\n")

# Process key timestamps
focus_timestamps = [
    '2024-10-29 09:16:00',  # Before first entry
    '2024-10-29 09:17:00',  # Expected entry #1 (RSI=27.39)
    '2024-10-29 09:18:00',  # Expected entry #2 (RSI=26.07)
    '2024-10-29 09:19:00',  # After entries
    '2024-10-29 10:45:00',  # Expected entry #3 (RSI=29.56)
    '2024-10-29 10:47:00',  # Expected entry #4 (RSI=28.57)
    '2024-10-29 10:48:00',  # Expected exit
]

for ts_str in focus_timestamps:
    ts = pd.Timestamp(ts_str)
    
    if ts not in df.index:
        print(f"⚠️  Timestamp {ts_str} not in data")
        continue
    
    candle = df.loc[ts].to_dict()
    
    print(f"\n{'─'*100}")
    print(f"⏰ Timestamp: {ts_str}")
    print(f"   RSI: {candle['rsi_14']:.2f}")
    print(f"   Close: {candle['close']:.2f}")
    print(f"   Open: {candle['open']:.2f}")
    print(f"   RSI < 30: {candle['rsi_14'] < 30}")
    
    # Execute strategy for this tick
    try:
        context_manager.execute_tick(ts, candle)
        
        # Check positions
        all_positions = gps.get_all_positions()
        open_positions = [p for p in all_positions if p.get('status') == 'open']
        
        print(f"   📊 GPS Status:")
        print(f"      Total Positions: {len(all_positions)}")
        print(f"      Open Positions: {len(open_positions)}")
        print(f"      Position Counters: {gps.position_counters}")
        
        # Check node states
        node_states = context_manager.context.get('node_states', {})
        print(f"   🔧 Node States (Active nodes):")
        for node_id, state in node_states.items():
            if state.get('status') == 'active':
                print(f"      - {node_id}: {state.get('status')}, visited={state.get('visited', False)}")
        
        # Show diagnostic data if entry happened
        if len(all_positions) > 0:
            latest_pos = all_positions[-1]
            print(f"\n   ✅ POSITION CREATED!")
            print(f"      Position ID: {latest_pos.get('position_id')}")
            print(f"      Entry Time: {latest_pos.get('entry_time')}")
            print(f"      Entry Price: {latest_pos.get('entry_price')}")
            print(f"      Quantity: {latest_pos.get('quantity')}")
            
            # Show condition text
            diagnostic_data = latest_pos.get('diagnostic_data', {})
            conditions_evaluated = diagnostic_data.get('conditions_evaluated', [])
            if conditions_evaluated:
                print(f"\n      📋 Condition Evaluations:")
                for cond in conditions_evaluated:
                    cond_text = cond.get('condition_text', 'No text')
                    print(f"         {cond_text}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*100}")
print(f"FINAL RESULTS")
print(f"{'='*100}\n")

all_positions = gps.get_all_positions()
print(f"Total Positions Created: {len(all_positions)}")

if all_positions:
    print(f"\n📝 Position Details:\n")
    for idx, pos in enumerate(all_positions, 1):
        print(f"{idx}. Position ID: {pos.get('position_id')}")
        print(f"   Entry Time: {pos.get('entry_time')}")
        print(f"   Entry Price: {pos.get('entry_price')}")
        print(f"   Exit Time: {pos.get('exit_time', 'Still Open')}")
        print(f"   Exit Price: {pos.get('exit_price', 'N/A')}")
        print(f"   Status: {pos.get('status')}")
        print(f"   PNL: {pos.get('pnl', 'N/A')}")
        print()
else:
    print("\n❌ No positions created - investigating why...")
    print("\n🔍 Potential Issues:")
    print("   1. Check if entry signal node is activating")
    print("   2. Check if conditions are evaluating correctly")
    print("   3. Check if node graph is traversing properly")
    print("   4. Check if RSI indicator is calculating correctly")

print(f"{'='*100}\n")
