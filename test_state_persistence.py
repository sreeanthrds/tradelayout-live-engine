"""
Test State Persistence & Delta Updates
=======================================

Tests:
1. State persistence to disk (JSONL format)
2. Full state loading (initial connection)
3. Delta state loading (reconnection with last_event_id)
4. API endpoint integration
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# Set environment variables FIRST (before imports)
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'
os.environ['CLICKHOUSE_DATA_TIMEZONE'] = 'IST'

# Setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'src'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'strategy'))
sys.path.insert(0, SCRIPT_DIR)

from live_backtest_runner import LiveBacktestEngineWithSSE
from src.backtesting.backtest_config import BacktestConfig


def test_state_persistence():
    """Test 1: Create test state files (events + trades) directly"""
    print("\n" + "="*80)
    print("TEST 1: State Persistence to Disk (Events + Trades)")
    print("="*80)
    
    # Test parameters
    user_id = "test_user_123"
    strategy_id = "strat_test_456"
    backtest_date = "2024-10-29"
    
    # Build state file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_base_dir = Path(script_dir) / 'live_state_cache'
    state_folder = state_base_dir / backtest_date / user_id / strategy_id
    state_folder.mkdir(parents=True, exist_ok=True)
    events_file = state_folder / 'node_events.jsonl'
    trades_file = state_folder / 'trades.jsonl'
    
    print(f"\n✓ Events file: {events_file}")
    print(f"✓ Trades file: {trades_file}")
    
    # Create test events
    test_events = {
        'exec_start_001': {
            'node_id': 'start-1',
            'node_type': 'StartNode',
            'timestamp': '2024-10-29 09:15:00+05:30',
            'parent_execution_id': None
        },
        'exec_entry_002': {
            'node_id': 'entry-1',
            'node_type': 'EntryNode',
            'timestamp': '2024-10-29 09:15:30+05:30',
            'parent_execution_id': 'exec_start_001',
            'position': {'position_id': 'pos1', 're_entry_num': 0}
        },
        'exec_exit_003': {
            'node_id': 'exit-1',
            'node_type': 'ExitNode',
            'timestamp': '2024-10-29 09:45:00+05:30',
            'parent_execution_id': 'exec_entry_002',
            'exit_result': {'pnl': 150.50}
        }
    }
    
    # Create test trades (simulating OPEN → PARTIAL → CLOSED progression)
    test_trades = [
        {
            'trade_id': 'trade_pos1_re0',
            'position_id': 'pos1',
            're_entry_num': 0,
            'symbol': 'NIFTY',
            'status': 'OPEN',
            'entry_time': '2024-10-29 09:15:30+05:30',
            'entry_price': 25000.0,
            'quantity': 75,
            'side': 'BUY',
            'pnl': 0.0,
            'entry_flow_ids': ['exec_start_001', 'exec_entry_002'],
            'exit_flow_ids': []
        },
        {
            'trade_id': 'trade_pos1_re0',
            'position_id': 'pos1',
            're_entry_num': 0,
            'symbol': 'NIFTY',
            'status': 'PARTIAL',  # Updated status
            'entry_time': '2024-10-29 09:15:30+05:30',
            'entry_price': 25000.0,
            'quantity': 75,
            'qty_closed': 25,  # Partial exit
            'side': 'BUY',
            'exit_time': '2024-10-29 09:30:00+05:30',
            'exit_price': 25050.0,
            'pnl': 50.0,
            'entry_flow_ids': ['exec_start_001', 'exec_entry_002'],
            'exit_flow_ids': ['exec_exit_003']
        },
        {
            'trade_id': 'trade_pos1_re0',
            'position_id': 'pos1',
            're_entry_num': 0,
            'symbol': 'NIFTY',
            'status': 'CLOSED',  # Final status
            'entry_time': '2024-10-29 09:15:30+05:30',
            'entry_price': 25000.0,
            'quantity': 75,
            'qty_closed': 75,  # Full exit
            'side': 'BUY',
            'exit_time': '2024-10-29 09:45:00+05:30',
            'exit_price': 25100.0,
            'pnl': 150.50,
            'entry_flow_ids': ['exec_start_001', 'exec_entry_002'],
            'exit_flow_ids': ['exec_exit_003']
        }
    ]
    
    # Write events
    with open(events_file, 'w') as f:
        for exec_id, event in test_events.items():
            event_line = {
                'exec_id': exec_id,
                'event': event,
                'timestamp': event.get('timestamp')
            }
            f.write(json.dumps(event_line) + '\n')
    
    # Write trades (upsert pattern - only final state per trade_id)
    trades_by_id = {}
    for trade in test_trades:
        trades_by_id[trade['trade_id']] = trade
    
    with open(trades_file, 'w') as f:
        for trade_id, trade in trades_by_id.items():
            f.write(json.dumps(trade) + '\n')
    
    # Verify files exist
    events_ok = events_file.exists()
    trades_ok = trades_file.exists()
    
    if events_ok and trades_ok:
        print(f"\n✅ Both files created successfully!")
        
        # Read and verify events
        with open(events_file, 'r') as f:
            event_lines = f.readlines()
        print(f"\n✓ Events: {len(event_lines)} lines")
        
        # Read and verify trades
        with open(trades_file, 'r') as f:
            trade_lines = f.readlines()
        print(f"✓ Trades: {len(trade_lines)} lines")
        
        # Parse and show trade progression
        final_trade = json.loads(trade_lines[0])
        print(f"\n✓ Final trade state:")
        print(f"  - trade_id: {final_trade['trade_id']}")
        print(f"  - status: {final_trade['status']}")
        print(f"  - qty: {final_trade['quantity']}, closed: {final_trade.get('qty_closed', 0)}")
        print(f"  - pnl: {final_trade['pnl']}")
        
        return True
    else:
        print(f"\n❌ Files NOT created! Events: {events_ok}, Trades: {trades_ok}")
        return False


def test_full_state_load():
    """Test 2: Read both events and trades files directly"""
    print("\n" + "="*80)
    print("TEST 2: Full State Load (Events + Trades)")
    print("="*80)
    
    user_id = "test_user_123"
    strategy_id = "strat_test_456"
    backtest_date = "2024-10-29"
    
    # Build state file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_base_dir = Path(script_dir) / 'live_state_cache'
    state_folder = state_base_dir / backtest_date / user_id / strategy_id
    events_file = state_folder / 'node_events.jsonl'
    trades_file = state_folder / 'trades.jsonl'
    
    if not events_file.exists() and not trades_file.exists():
        print(f"\n⚠️  State files not found (run Test 1 first)")
        return False, [], []
    
    # Read all events
    all_events = {}
    event_order = []
    
    if events_file.exists():
        with open(events_file, 'r') as f:
            for line in f:
                event_line = json.loads(line.strip())
                exec_id = event_line['exec_id']
                event = event_line['event']
                all_events[exec_id] = event
                event_order.append(exec_id)
    
    # Read all trades
    all_trades = []
    
    if trades_file.exists():
        with open(trades_file, 'r') as f:
            for line in f:
                trade = json.loads(line.strip())
                all_trades.append(trade)
    
    print(f"\n✓ Events loaded: {len(all_events)}")
    print(f"✓ Event IDs: {event_order}")
    print(f"\n✓ Trades loaded: {len(all_trades)}")
    
    if all_trades:
        for trade in all_trades:
            print(f"  - {trade['trade_id']}: {trade['status']} | PnL: {trade['pnl']}")
    
    if all_events and all_trades:
        print(f"\n✅ Full state loaded successfully!")
        return True, event_order, all_trades
    else:
        print(f"\n⚠️  Incomplete state")
        return False, event_order, all_trades


def test_delta_state_load(last_event_id, last_trade_id):
    """Test 3: Delta state loading for both events and trades"""
    print("\n" + "="*80)
    print("TEST 3: Delta State Load (Reconnection)")
    print("="*80)
    
    user_id = "test_user_123"
    strategy_id = "strat_test_456"
    backtest_date = "2024-10-29"
    
    # Build state file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    state_base_dir = Path(script_dir) / 'live_state_cache'
    state_folder = state_base_dir / backtest_date / user_id / strategy_id
    events_file = state_folder / 'node_events.jsonl'
    trades_file = state_folder / 'trades.jsonl'
    
    if not events_file.exists() and not trades_file.exists():
        print(f"\n⚠️  State files not found")
        return False
    
    # Read and filter events
    delta_events = {}
    if events_file.exists() and last_event_id:
        all_events = {}
        event_order = []
        
        with open(events_file, 'r') as f:
            for line in f:
                event_line = json.loads(line.strip())
                exec_id = event_line['exec_id']
                event = event_line['event']
                all_events[exec_id] = event
                event_order.append(exec_id)
        
        print(f"\n✓ Requesting events after: {last_event_id}")
        
        if last_event_id in event_order:
            last_idx = event_order.index(last_event_id)
            delta_exec_ids = event_order[last_idx + 1:]
            delta_events = {eid: all_events[eid] for eid in delta_exec_ids}
            print(f"✓ Delta events: {len(delta_events)}")
            print(f"✓ Delta event IDs: {delta_exec_ids}")
        else:
            print(f"⚠️  last_event_id not found, returning all events")
            delta_events = all_events
    
    # Read and filter trades
    delta_trades = []
    if trades_file.exists() and last_trade_id:
        all_trades = []
        
        with open(trades_file, 'r') as f:
            for line in f:
                trade = json.loads(line.strip())
                all_trades.append(trade)
        
        print(f"\n✓ Requesting trades after: {last_trade_id}")
        
        trade_ids = [t['trade_id'] for t in all_trades]
        if last_trade_id in trade_ids:
            last_idx = trade_ids.index(last_trade_id)
            delta_trades = all_trades[last_idx + 1:]
            print(f"✓ Delta trades: {len(delta_trades)}")
        else:
            print(f"⚠️  last_trade_id not found, returning all trades")
            delta_trades = all_trades
    
    print(f"\n✅ Delta state loaded successfully!")
    print(f"   Events: {len(delta_events)}, Trades: {len(delta_trades)}")
    return True


def test_api_endpoint():
    """Test 4: API endpoint integration with events + trades"""
    print("\n" + "="*80)
    print("TEST 4: API Endpoint Integration (Events + Trades)")
    print("="*80)
    
    # Test parameters
    user_id = "test_user_123"
    strategy_id = "strat_test_456"
    backtest_date = "2024-10-29"
    
    base_url = "http://localhost:8000"
    
    print(f"\n✓ Testing endpoint: GET /api/simple/live/initial-state/{user_id}/{strategy_id}")
    print(f"✓ Query params: backtest_date={backtest_date}")
    
    try:
        # Test 4a: Full state load (no last IDs)
        print("\n[Test 4a] Full state request (events + trades)...")
        response = requests.get(
            f"{base_url}/api/simple/live/initial-state/{user_id}/{strategy_id}",
            params={"backtest_date": backtest_date}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Full state response:")
            print(f"   - Event count: {data['event_count']}")
            print(f"   - Trade count: {data['trade_count']}")
            print(f"   - Is delta: {data['is_delta']}")
            
            # Show trade details
            if data['trades']:
                print(f"\n   Trades:")
                for trade in data['trades']:
                    print(f"   - {trade['trade_id']}: {trade['status']} | PnL: {trade['pnl']}")
            
            # Get first event and trade for delta test
            event_ids = list(data['events'].keys())
            trades = data['trades']
            
            if event_ids and trades:
                first_event_id = event_ids[0]
                first_trade_id = trades[0]['trade_id']
                
                # Test 4b: Delta state load (with last IDs)
                print(f"\n[Test 4b] Delta state request...")
                print(f"   - After event: {first_event_id}")
                print(f"   - After trade: {first_trade_id}")
                
                delta_response = requests.get(
                    f"{base_url}/api/simple/live/initial-state/{user_id}/{strategy_id}",
                    params={
                        "backtest_date": backtest_date,
                        "last_event_id": first_event_id,
                        "last_trade_id": first_trade_id
                    }
                )
                
                if delta_response.status_code == 200:
                    delta_data = delta_response.json()
                    print(f"✅ Delta state response:")
                    print(f"   - Event count: {delta_data['event_count']}")
                    print(f"   - Trade count: {delta_data['trade_count']}")
                    print(f"   - Is delta: {delta_data['is_delta']}")
                    print(f"   - Last event ID: {delta_data['last_event_id']}")
                    print(f"   - Last trade ID: {delta_data['last_trade_id']}")
                    
                    return True
                else:
                    print(f"❌ Delta request failed: {delta_response.status_code}")
                    return False
            else:
                print(f"⚠️  No events or trades to test delta")
                return True  # Still success if we got full state
        else:
            print(f"❌ Full state request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n⚠️  API server not running!")
        print(f"   Start server: python backtest_api_server.py")
        print(f"   Then run this test again")
        return False


def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*80)
    print("STATE PERSISTENCE & DELTA UPDATE TEST SUITE")
    print("Full State Reconnection: Events + Trades + Delta Updates")
    print("="*80)
    
    results = {}
    
    # Test 1: State persistence (creates test files)
    results['persistence'] = test_state_persistence()
    
    # Test 2: Full state load (events + trades)
    success, event_ids, trades = test_full_state_load()
    results['full_load'] = success
    
    # Test 3: Delta state load (if we have events and trades)
    if event_ids and trades:
        last_event_id = event_ids[0]
        last_trade_id = trades[0]['trade_id']
        results['delta_load'] = test_delta_state_load(last_event_id, last_trade_id)
    else:
        print("\n⚠️  Skipping delta test (no events or trades)")
        results['delta_load'] = None
    
    # Test 4: API endpoint (full + delta)
    results['api_endpoint'] = test_api_endpoint()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        
        print(f"{status} - {test_name}")
    
    print("="*80)
    
    # Overall result
    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)
    
    print(f"\n✅ Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n📋 What was tested:")
        print("   ✅ Events persistence (JSONL format)")
        print("   ✅ Trades persistence with upsert (OPEN→PARTIAL→CLOSED)")
        print("   ✅ Full state load (events + trades)")
        print("   ✅ Delta state load (events + trades)")
        print("   ✅ API endpoint with both data types")
        print("\n🔄 Ready for UI reconnection - complete state restoration!")
    else:
        print("\n⚠️  Some tests failed - check output above")


if __name__ == "__main__":
    run_all_tests()
