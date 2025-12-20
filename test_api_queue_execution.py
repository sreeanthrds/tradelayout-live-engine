#!/usr/bin/env python3
"""
Test Unified Engine via Queue Execution API
Tests the unified engine through the backtest API server's queue execution endpoint

Run this test:
1. Start API server: python backtest_api_server.py
2. Run test: python test_api_queue_execution.py

Expected: 9 positions created (matches baseline)
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

print("="*80)
print("🧪 QUEUE EXECUTION API TEST - Unified Engine")
print("="*80)
print()
print("Strategy: 5708424d-5962-4629-978c-05b3a174e104")
print("Date: October 29, 2024")
print("Mode: Queue execution (historical simulation)")
print()
print("="*80)
print()

# Test configuration
user_id = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
strategy_id = "5708424d-5962-4629-978c-05b3a174e104"
broker_connection_id = "clickhouse_backtest"

try:
    # Step 1: Submit to queue
    print("📤 Step 1: Submitting strategy to queue...")
    submit_response = requests.post(
        f"{API_BASE}/api/queue/submit",
        params={
            "user_id": user_id,
            "queue_type": "admin_tester"
        },
        json=[
            {
                "strategy_id": strategy_id,
                "broker_connection_id": broker_connection_id,
                "scale": 1.0
            }
        ]
    )
    
    if submit_response.status_code == 200:
        submit_data = submit_response.json()
        print(f"   ✅ Submitted to queue")
        print(f"   Queue position: {submit_data['queue_position']}")
        print(f"   Total strategies: {submit_data['total_strategies_queued']}")
    else:
        print(f"   ❌ Failed: {submit_response.status_code}")
        print(f"   {submit_response.text}")
        exit(1)
    
    # Step 2: Check queue status
    print(f"\n📊 Step 2: Checking queue status...")
    status_response = requests.get(f"{API_BASE}/api/queue/status/admin_tester")
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"   ✅ Queue status:")
        print(f"   Pending entries: {status_data['pending_entries']}")
        print(f"   Total strategies: {status_data['total_strategies']}")
        print(f"   Is processing: {status_data['is_processing']}")
    else:
        print(f"   ❌ Failed: {status_response.status_code}")
    
    # Step 3: Execute queue
    print(f"\n🚀 Step 3: Executing queue...")
    execute_response = requests.post(
        f"{API_BASE}/api/queue/execute",
        params={
            "queue_type": "admin_tester",
            "trigger_type": "manual"
        }
    )
    
    if execute_response.status_code == 200:
        execute_data = execute_response.json()
        print(f"   ✅ Queue execution started!")
        print(f"   Strategy count: {execute_data['strategy_count']}")
        print(f"   Symbols count: {execute_data['symbols_count']}")
        print(f"   Backtest date: {execute_data['backtest_date']}")
        print(f"   Speed: {execute_data['speed_multiplier']}x")
        print(f"   Mode: {execute_data['mode']}")
    else:
        print(f"   ❌ Failed: {execute_response.status_code}")
        print(f"   {execute_response.text}")
        exit(1)
    
    # Step 4: Wait for processing and check results
    print(f"\n⏳ Step 4: Waiting for processing to complete...")
    print(f"   (This will take ~70s with speed=500x)")
    
    # Poll for completion (check if positions file exists)
    max_wait = 120  # 2 minutes max
    wait_interval = 5
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval
        print(f"   Waiting... {elapsed}s elapsed")
        
        # Check if output file exists
        try:
            with open('backtest_dashboard_data.json', 'r') as f:
                data = json.load(f)
                positions = data.get('positions', [])
                if len(positions) > 0:
                    print(f"\n   ✅ Found {len(positions)} positions in output file!")
                    break
        except FileNotFoundError:
            continue
    
    # Step 5: Verify results
    print(f"\n{'='*80}")
    print(f"📊 QUEUE EXECUTION RESULTS")
    print(f"{'='*80}\n")
    
    try:
        with open('backtest_dashboard_data.json', 'r') as f:
            data = json.load(f)
        
        positions = data.get('positions', [])
        
        print(f"✅ Queue execution completed!")
        print(f"\n📊 Position Summary:")
        print(f"   Total Positions: {len(positions)}")
        
        if len(positions) == 9:
            print(f"\n✅ SUCCESS: Created 9 positions (matches baseline!)")
            print(f"\n📋 Position Details:")
            for i, pos in enumerate(positions[:10], 1):
                status = pos.get('status', 'UNKNOWN')
                entry = pos.get('entry_price', 0)
                exit_price = pos.get('exit_price', 'OPEN')
                pnl = pos.get('pnl', 0)
                print(f"   {i}. {pos['position_id']}")
                print(f"      {pos['side']} {pos.get('symbol', 'N/A')}")
                print(f"      Entry: {entry} → Exit: {exit_price}")
                print(f"      Status: {status}, P&L: {pnl}")
        else:
            print(f"\n⚠️  WARNING: Expected 9 positions, got {len(positions)}")
            
    except FileNotFoundError:
        print(f"❌ Output file not found - execution may have failed")
        
except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}\n")
