#!/usr/bin/env python3
"""
Test Live Trading Queue Execution APIs
Tests the complete queue workflow:
1. Submit strategy to queue
2. Check queue status
3. Execute queue
4. Monitor execution via SSE
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BROKER_CONNECTION_ID = "acf98a95-1547-4a72-b824-3ce7068f05b4"  # ClickHouse broker from Supabase
QUEUE_TYPE = "admin_tester"

print("="*80)
print("🧪 LIVE TRADING QUEUE EXECUTION API TEST")
print("="*80)
print(f"API Base: {API_BASE}")
print(f"User ID: {USER_ID}")
print(f"Strategy ID: {STRATEGY_ID}")
print(f"Queue Type: {QUEUE_TYPE}")
print("="*80)
print()

# Step 1: Clear existing queue entries (optional)
print("🧹 Step 1: Clearing existing queue...")
try:
    response = requests.delete(f"{API_BASE}/api/queue/clear/{QUEUE_TYPE}")
    if response.status_code == 200:
        print(f"   ✅ Queue cleared")
    else:
        print(f"   ⚠️  Queue clear status: {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Could not clear queue: {e}")

# Step 2: Submit strategy to queue
print(f"\n📤 Step 2: Submitting strategy to queue...")
try:
    submit_payload = [
        {
            "strategy_id": STRATEGY_ID,
            "broker_connection_id": BROKER_CONNECTION_ID,
            "scale": 1.0
        }
    ]
    
    response = requests.post(
        f"{API_BASE}/api/queue/submit",
        params={
            "user_id": USER_ID,
            "queue_type": QUEUE_TYPE
        },
        json=submit_payload
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Strategy submitted to queue")
        print(f"   Queue position: {data.get('queue_position', 'N/A')}")
        print(f"   Total strategies: {data.get('total_strategies_queued', 0)}")
    else:
        print(f"   ❌ Submit failed: {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        print("\n⚠️  Stopping test - cannot proceed without successful submission")
        exit(1)
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Step 3: Check queue status
print(f"\n📊 Step 3: Checking queue status...")
try:
    response = requests.get(f"{API_BASE}/api/queue/status/{QUEUE_TYPE}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Queue status retrieved")
        print(f"   Queue type: {data.get('queue_type', 'N/A')}")
        print(f"   Total strategies: {data.get('total_strategies', 0)}")
        print(f"   Pending entries: {data.get('pending_entries', 0)}")
        print(f"   Is processing: {data.get('is_processing', False)}")
        
        if data.get('strategies'):
            print(f"\n   Strategies in queue:")
            for strat in data['strategies']:
                print(f"   - {strat.get('strategy_id', 'N/A')}: {strat.get('strategy_name', 'Unknown')}")
    else:
        print(f"   ❌ Status check failed: {response.status_code}")
        print(f"   {response.text[:500]}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# Step 4: Execute queue
print(f"\n🚀 Step 4: Executing queue...")
try:
    response = requests.post(
        f"{API_BASE}/api/queue/execute",
        params={
            "queue_type": QUEUE_TYPE,
            "trigger_type": "manual"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Queue execution started!")
        print(f"   Strategy count: {data.get('strategy_count', 0)}")
        print(f"   Symbols count: {data.get('symbols_count', 0)}")
        print(f"   Backtest date: {data.get('backtest_date', 'N/A')}")
        print(f"   Speed: {data.get('speed_multiplier', 'N/A')}x")
        print(f"   Mode: {data.get('mode', 'N/A')}")
        
        session_ids = data.get('session_ids', [])
        if session_ids:
            print(f"\n   Created sessions:")
            for sid in session_ids:
                print(f"   - {sid}")
    else:
        print(f"   ❌ Execution failed: {response.status_code}")
        print(f"   Response: {response.text[:1000]}")
        exit(1)
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 5: Monitor execution status
print(f"\n⏳ Step 5: Monitoring execution (30s)...")
print(f"   Waiting for execution to complete...")

for i in range(6):  # Check 6 times over 30 seconds
    time.sleep(5)
    print(f"   ... {(i+1)*5}s elapsed")
    
    try:
        # Check dashboard for session status
        response = requests.get(f"{API_BASE}/api/live-trading/dashboard/{USER_ID}")
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', {})
            
            if sessions:
                for session_id, session in sessions.items():
                    status = session.get('status', 'unknown')
                    pnl = session.get('data', {}).get('gps_data', {}).get('pnl', {})
                    total_pnl = pnl.get('total_pnl', '0.00')
                    
                    if i == 5:  # Last check
                        print(f"\n   Session: {session_id[:20]}...")
                        print(f"   Status: {status}")
                        print(f"   P&L: ₹{total_pnl}")
    except:
        pass

# Step 6: Final results
print(f"\n{'='*80}")
print(f"📊 FINAL RESULTS")
print(f"{'='*80}")

try:
    response = requests.get(f"{API_BASE}/api/live-trading/dashboard/{USER_ID}")
    if response.status_code == 200:
        data = response.json()
        
        total_sessions = data.get('total_sessions', 0)
        active_sessions = data.get('active_sessions', 0)
        agg_pnl = data.get('aggregated_pnl', {})
        
        print(f"\n✅ Queue execution test complete!")
        print(f"\n📈 Summary:")
        print(f"   Total Sessions: {total_sessions}")
        print(f"   Active Sessions: {active_sessions}")
        print(f"   Aggregated P&L: ₹{agg_pnl.get('total_pnl', '0.00')}")
        print(f"   Closed Trades: {agg_pnl.get('closed_trades', 0)}")
        print(f"   Open Trades: {agg_pnl.get('open_trades', 0)}")
        
        sessions = data.get('sessions', {})
        if sessions:
            print(f"\n📋 Sessions:")
            for session_id, session in sessions.items():
                print(f"\n   {session.get('strategy_name', 'Unknown')}:")
                print(f"   - Status: {session.get('status', 'unknown')}")
                pnl = session.get('data', {}).get('gps_data', {}).get('pnl', {})
                print(f"   - P&L: ₹{pnl.get('total_pnl', '0.00')}")
        
        if total_sessions == 0:
            print(f"\n⚠️  WARNING: No sessions created - queue execution may have failed")
        elif active_sessions > 0:
            print(f"\n✅ SUCCESS: Live trading session(s) active!")
        else:
            print(f"\n⚠️  INFO: Sessions exist but not active (may be completed)")
    else:
        print(f"❌ Could not fetch final results: {response.status_code}")
        
except Exception as e:
    print(f"❌ Error fetching results: {e}")

print(f"\n{'='*80}\n")
