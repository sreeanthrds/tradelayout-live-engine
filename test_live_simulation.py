"""
Test Live Simulation - Simulates UI Polling

This script:
1. Starts a live simulation
2. Polls state every 1 second
3. Saves snapshots to a JSON file
4. Stops when simulation completes
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, Any

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Test Configuration
TEST_USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
TEST_STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
TEST_DATE = "2024-10-29"
SPEED_MULTIPLIER = 1.0  # Real-time
POLL_INTERVAL = 1  # 1 second

# Output file
OUTPUT_FILE = f"live_simulation_snapshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def start_simulation() -> str:
    """Start live simulation and return session_id"""
    print("=" * 80)
    print("🚀 STARTING LIVE SIMULATION TEST")
    print("=" * 80)
    
    url = f"{API_BASE_URL}/api/v1/simulation/start"
    payload = {
        "user_id": TEST_USER_ID,
        "strategy_id": TEST_STRATEGY_ID,
        "start_date": TEST_DATE,
        "mode": "live",
        "broker_connection_id": "clickhouse",
        "speed_multiplier": SPEED_MULTIPLIER
    }
    
    print(f"\n📡 Sending request to: {url}")
    print(f"📋 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        session_id = result.get('session_id')
        
        print(f"\n✅ Simulation started successfully!")
        print(f"   Session ID: {session_id}")
        print(f"   Status: {result.get('status')}")
        print(f"   Poll URL: {result.get('poll_url')}")
        print(f"   Speed: {SPEED_MULTIPLIER}x")
        
        return session_id
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to start simulation: {e}")
        return None


def poll_simulation_state(session_id: str) -> Dict[str, Any]:
    """Poll simulation state (called every second)"""
    url = f"{API_BASE_URL}/api/v1/simulation/{session_id}/state"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        state = response.json()
        return state
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Poll error: {e}")
        return None


def stop_simulation(session_id: str):
    """Stop simulation"""
    url = f"{API_BASE_URL}/api/v1/simulation/{session_id}/stop"
    
    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        
        print(f"\n🛑 Simulation stopped")
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Stop error: {e}")


def print_state_summary(state: Dict[str, Any], snapshot_num: int):
    """Print human-readable state summary"""
    status = state.get('status', 'unknown')
    timestamp = state.get('timestamp', 'N/A')
    stats = state.get('stats', {})
    active_nodes = state.get('active_nodes', [])
    open_positions = state.get('open_positions', [])
    total_pnl = state.get('total_unrealized_pnl', 0)
    
    # Progress
    progress = stats.get('progress_percentage', 0)
    ticks_processed = stats.get('ticks_processed', 0)
    total_ticks = stats.get('total_ticks', 0)
    
    print(f"\n{'='*80}")
    print(f"📸 SNAPSHOT #{snapshot_num}")
    print(f"{'='*80}")
    print(f"⏰ Timestamp: {timestamp}")
    print(f"📊 Status: {status}")
    print(f"📈 Progress: {progress:.1f}% ({ticks_processed:,}/{total_ticks:,} ticks)")
    
    # Active nodes
    print(f"\n🔵 Active Nodes: {len(active_nodes)}")
    for node in active_nodes:
        node_id = node.get('node_id')
        node_type = node.get('node_type')
        node_status = node.get('status')
        print(f"   • {node_id} ({node_type}): {node_status}")
    
    # Open positions
    print(f"\n💼 Open Positions: {len(open_positions)}")
    for pos in open_positions:
        symbol = pos.get('symbol', 'N/A')
        entry_price = pos.get('entry_price', 0)
        current_ltp = pos.get('current_ltp', 0)
        unrealized_pnl = pos.get('unrealized_pnl', 0)
        print(f"   • {symbol}")
        print(f"     Entry: {entry_price:.2f} | LTP: {current_ltp:.2f} | PNL: {unrealized_pnl:.2f}")
    
    print(f"\n💰 Total Unrealized PNL: {total_pnl:.2f}")
    print(f"{'='*80}")


def save_snapshots_to_file(snapshots: list):
    """Save all snapshots to JSON file"""
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump({
                'test_info': {
                    'user_id': TEST_USER_ID,
                    'strategy_id': TEST_STRATEGY_ID,
                    'test_date': TEST_DATE,
                    'speed_multiplier': SPEED_MULTIPLIER,
                    'total_snapshots': len(snapshots),
                    'generated_at': datetime.now().isoformat()
                },
                'snapshots': snapshots
            }, f, indent=2)
        
        print(f"\n💾 Snapshots saved to: {OUTPUT_FILE}")
        print(f"   Total snapshots: {len(snapshots)}")
        
    except Exception as e:
        print(f"❌ Failed to save snapshots: {e}")


def run_test():
    """Main test runner"""
    # Step 1: Start simulation
    session_id = start_simulation()
    if not session_id:
        print("❌ Cannot proceed without session ID")
        return
    
    # Step 2: Poll every second and collect snapshots
    snapshots = []
    snapshot_num = 0
    
    print(f"\n{'='*80}")
    print(f"🔄 STARTING POLLING (Every {POLL_INTERVAL} second)")
    print(f"{'='*80}")
    print(f"Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Poll state
            state = poll_simulation_state(session_id)
            
            if state:
                snapshot_num += 1
                
                # Add metadata
                state['_snapshot_num'] = snapshot_num
                state['_polled_at'] = datetime.now().isoformat()
                
                # Save snapshot
                snapshots.append(state)
                
                # Print summary
                print_state_summary(state, snapshot_num)
                
                # Check if completed
                status = state.get('status')
                if status in ['completed', 'stopped', 'error']:
                    print(f"\n✅ Simulation {status}!")
                    
                    # Print error if any
                    if status == 'error':
                        error = state.get('error', 'Unknown error')
                        print(f"❌ Error: {error}")
                    
                    break
                
                # Check if strategy complete (all nodes inactive, no positions)
                active_nodes = state.get('active_nodes', [])
                open_positions = state.get('open_positions', [])
                if len(active_nodes) == 0 and len(open_positions) == 0:
                    print(f"\n✅ Strategy execution complete (all nodes inactive, no open positions)")
                    break
            
            # Wait before next poll
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrupted by user")
        stop_simulation(session_id)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Step 3: Save snapshots to file
        if snapshots:
            save_snapshots_to_file(snapshots)
        
        print(f"\n{'='*80}")
        print(f"✅ TEST COMPLETE")
        print(f"{'='*80}")
        print(f"Total snapshots captured: {len(snapshots)}")
        print(f"Output file: {OUTPUT_FILE}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Check if API server is running
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/backtest/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ API Server is running at {API_BASE_URL}")
        else:
            print(f"⚠️  API Server returned status code: {response.status_code}")
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to API server at {API_BASE_URL}")
        print(f"   Please start the server first: python backtest_api_server.py")
        exit(1)
    
    # Run test
    run_test()
