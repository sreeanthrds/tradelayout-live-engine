#!/usr/bin/env python3
"""
Test script to verify that re-entry signal nodes show explicit conditions
and implicit checks in the live simulation state.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_node_conditions():
    """Start simulation and check first snapshot for node condition details."""
    
    # 1. Start simulation
    print("🚀 Starting simulation...")
    start_response = requests.post(f"{BASE_URL}/api/v1/simulation/start", json={
        "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "broker_connection_id": "clickhouse",
        "speed_multiplier": 4.0
    })
    
    if start_response.status_code != 200:
        print(f"❌ Failed to start simulation: {start_response.status_code}")
        print(start_response.text)
        return
    
    session_data = start_response.json()
    session_id = session_data['session_id']
    print(f"✅ Simulation started: {session_id}")
    
    # 2. Wait a bit for simulation to process first second
    time.sleep(2)
    
    # 3. Poll state
    print("\n📊 Polling state...")
    state_response = requests.get(f"{BASE_URL}/api/v1/simulation/{session_id}/state")
    
    if state_response.status_code != 200:
        print(f"❌ Failed to poll state: {state_response.status_code}")
        return
    
    state = state_response.json()
    
    # 4. Check active nodes for conditions
    print(f"\n📍 Status: {state.get('status')}")
    print(f"📍 Timestamp: {state.get('timestamp')}")
    print(f"📍 Active Nodes: {len(state.get('active_nodes', []))}\n")
    
    for node in state.get('active_nodes', []):
        node_type = node.get('node_type')
        node_name = node.get('node_name')
        node_id = node.get('node_id')
        
        print(f"\n{'='*80}")
        print(f"📦 Node: {node_name} ({node_type})")
        print(f"   ID: {node_id}")
        print(f"   Status: {node.get('status')}")
        print(f"   Re-entry num: {node.get('re_entry_num')}")
        
        # Check for explicit conditions
        if 'explicit_conditions' in node:
            print(f"\n   ✅ EXPLICIT CONDITIONS FOUND:")
            print(f"      {json.dumps(node['explicit_conditions'], indent=6)[:300]}...")
        else:
            print(f"\n   ⚠️  No explicit conditions")
        
        # Check for implicit checks (ReEntrySignalNode)
        if 'implicit_checks' in node:
            print(f"\n   ✅ IMPLICIT CHECKS FOUND:")
            for check_name, check_value in node['implicit_checks'].items():
                print(f"      • {check_name}: {check_value}")
        else:
            print(f"   ℹ️  No implicit checks")
        
        # Check for diagnostic data
        if 'diagnostic_data' in node:
            diag = node['diagnostic_data']
            print(f"\n   📊 DIAGNOSTIC DATA:")
            for key, value in list(diag.items())[:5]:  # Show first 5 items
                print(f"      • {key}: {value}")
        
        # Check for condition result
        if 'condition_result' in node:
            print(f"\n   🎯 Condition Result: {node['condition_result']}")
    
    # 5. Stop simulation
    print(f"\n\n🛑 Stopping simulation...")
    stop_response = requests.post(f"{BASE_URL}/api/v1/simulation/{session_id}/stop")
    
    if stop_response.status_code == 200:
        print("✅ Simulation stopped")
    else:
        print(f"⚠️  Stop failed: {stop_response.status_code}")
    
    print("\n" + "="*80)
    print("✅ Test completed!")

if __name__ == "__main__":
    test_node_conditions()
