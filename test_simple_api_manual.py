"""
Quick diagnostic test for /api/simple/live/start endpoint
Run this to verify the backend is working correctly.
"""
import requests
import json
import time
from sseclient import SSEClient

API_BASE = "https://tradelayout.loca.lt"
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"
SPEED = 500

def test_start_api():
    """Test the /api/simple/live/start endpoint"""
    print("=" * 80)
    print("STEP 1: Testing /api/simple/live/start")
    print("=" * 80)
    
    url = f"{API_BASE}/api/simple/live/start"
    params = {
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "backtest_date": BACKTEST_DATE,
        "speed_multiplier": SPEED
    }
    
    print(f"\nPOST {url}")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.post(url, params=params, timeout=10)
        print(f"\nStatus: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            session_id = response.json().get('session_id')
            print(f"\n✅ Session started: {session_id}")
            return session_id
        else:
            print(f"\n❌ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def test_sse_stream(session_id):
    """Test the SSE stream for tick_update events"""
    print("\n" + "=" * 80)
    print("STEP 2: Testing /api/live-trading/stream/{user_id}")
    print("=" * 80)
    
    url = f"{API_BASE}/api/live-trading/stream/{USER_ID}"
    print(f"\nGET {url} (SSE stream)")
    print("Listening for tick_update events (will wait 30 seconds)...\n")
    
    try:
        messages = SSEClient(url)
        tick_count = 0
        start_time = time.time()
        
        for msg in messages:
            if time.time() - start_time > 30:
                print("\n⏱️  30 seconds elapsed, stopping...")
                break
                
            if msg.event == 'tick_update':
                tick_count += 1
                data = json.loads(msg.data)
                session = data.get('session_id', 'unknown')
                tick_state = data.get('tick_state', {})
                pnl_summary = tick_state.get('pnl_summary', {})
                
                print(f"📥 tick_update #{tick_count} - Session: {session[:12]}...")
                print(f"   Total P&L: {pnl_summary.get('total_pnl', 0)}")
                print(f"   Realized: {pnl_summary.get('realized_pnl', 0)}")
                print(f"   Unrealized: {pnl_summary.get('unrealized_pnl', 0)}")
                print(f"   Open Positions: {len(tick_state.get('open_positions', []))}")
                
                if tick_count >= 5:
                    print("\n✅ Received 5 tick_update events - SSE is working!")
                    break
                    
            elif msg.event == 'initial_state':
                print(f"📡 Received initial_state")
                
            elif msg.event == 'heartbeat':
                print(f"💓 Heartbeat")
                
        if tick_count == 0:
            print("\n❌ No tick_update events received in 30 seconds")
            print("   This means backend simulation is not emitting events")
            
    except Exception as e:
        print(f"\n❌ SSE Error: {e}")

if __name__ == "__main__":
    print("\n🔍 Backend Diagnostic Test")
    print("This will test if the backend is working correctly\n")
    
    # Test 1: Start simulation
    session_id = test_start_api()
    
    if not session_id:
        print("\n❌ FAILED: Could not start simulation")
        exit(1)
    
    # Wait a moment for simulation to initialize
    print("\n⏳ Waiting 2 seconds for simulation to initialize...")
    time.sleep(2)
    
    # Test 2: Check SSE stream
    test_sse_stream(session_id)
    
    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)
