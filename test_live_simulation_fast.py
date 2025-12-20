"""
Fast Live Simulation Test - 10x speed
Quickly test if state capture is working by running simulation at 10x speed
"""

import requests
import time
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"
TEST_USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
TEST_STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
TEST_DATE = "2024-10-29"
SPEED_MULTIPLIER = 4.0  # 4x speed
POLL_INTERVAL = 0.1  # Poll every 0.1 seconds (10x per second)
MAX_SNAPSHOTS = 100  # Capture max 100 snapshots

OUTPUT_FILE = f"live_simulation_fast_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

print("=" * 80)
print(f"🚀 FAST LIVE SIMULATION TEST ({SPEED_MULTIPLIER}x speed)")
print("=" * 80)

# Start simulation
url = f"{API_BASE_URL}/api/v1/simulation/start"
payload = {
    "user_id": TEST_USER_ID,
    "strategy_id": TEST_STRATEGY_ID,
    "start_date": TEST_DATE,
    "mode": "live",
    "broker_connection_id": "clickhouse",
    "speed_multiplier": SPEED_MULTIPLIER
}

print(f"\n📡 Starting simulation at {SPEED_MULTIPLIER}x speed...")
response = requests.post(url, json=payload, timeout=30)
result = response.json()
session_id = result.get('session_id')

print(f"✅ Session ID: {session_id}")
print(f"📊 Polling every {POLL_INTERVAL} seconds for max {MAX_SNAPSHOTS} snapshots...\n")

# Poll for snapshots
snapshots = []
for i in range(MAX_SNAPSHOTS):
    time.sleep(POLL_INTERVAL)
    
    state_url = f"{API_BASE_URL}/api/v1/simulation/{session_id}/state"
    state = requests.get(state_url, timeout=10).json()
    
    state['_snapshot_num'] = i + 1
    state['_polled_at'] = datetime.now().isoformat()
    snapshots.append(state)
    
    status = state.get('status')
    timestamp = state.get('timestamp', 'N/A')
    progress = state.get('stats', {}).get('progress_percentage', 0)
    active_nodes = len(state.get('active_nodes', []))
    open_positions = len(state.get('open_positions', []))
    
    print(f"📸 Snapshot #{i+1}: {status} | {timestamp} | {progress:.1f}% | Nodes: {active_nodes} | Positions: {open_positions}")
    
    if status in ['completed', 'stopped', 'error']:
        print(f"\n✅ Simulation {status}!")
        break

# Save snapshots
with open(OUTPUT_FILE, 'w') as f:
    json.dump({
        'test_info': {
            'speed_multiplier': SPEED_MULTIPLIER,
            'total_snapshots': len(snapshots)
        },
        'snapshots': snapshots
    }, f, indent=2)

print(f"\n💾 Saved {len(snapshots)} snapshots to: {OUTPUT_FILE}")
print("=" * 80)
