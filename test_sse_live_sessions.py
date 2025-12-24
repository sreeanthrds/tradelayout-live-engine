"""
Test SSE Live Sessions - Start multiple concurrent sessions and verify SSE streaming.
"""

import requests
import json
import time
from datetime import datetime
from sseclient import SSEClient  # pip install sseclient-py

# API Base URL
API_BASE = "http://localhost:8001"

# Test data - REAL strategies and connections for date 2024-10-28
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"

# Using same broker connection for both sessions
BROKER_CONNECTION = "acf98a95-1547-4a72-b824-3ce7068f05b4"

# Strategy 1: My strategy 5
STRATEGY_1 = "d70ec04a-1025-46c5-94c4-3e6bff499644"
BROKER_CONNECTION_1 = BROKER_CONNECTION

# Strategy 2: My New Strategy5
STRATEGY_2 = "5708424d-5962-4629-978c-05b3a174e104"
BROKER_CONNECTION_2 = BROKER_CONNECTION

TEST_DATE = "2024-10-28"


def test_start_sessions():
    """Test starting multiple SSE sessions."""
    print("\n" + "="*60)
    print("TEST: Start SSE Sessions")
    print("="*60)
    
    # Prepare request
    payload = {
        "user_id": USER_ID,
        "sessions": {
            "session_test_1": {
                "strategy_id": STRATEGY_1,
                "broker_connection_id": BROKER_CONNECTION_1
            },
            "session_test_2": {
                "strategy_id": STRATEGY_2,
                "broker_connection_id": BROKER_CONNECTION_2
            }
        }
    }
    
    print("\n📤 Starting sessions...")
    print(f"   User: {USER_ID}")
    print(f"   Session 1: {STRATEGY_1}")
    print(f"   Session 2: {STRATEGY_2}")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/live/session/start-sse",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Sessions started successfully!")
            print(f"   Created: {result.get('total_created', 0)}")
            print(f"   Errors: {len(result.get('errors', []))}")
            
            for session in result.get('created_sessions', []):
                print(f"\n   📊 Session: {session['session_id']}")
                print(f"      Status: {session['status']}")
                print(f"      Created: {session['created_at']}")
            
            return result.get('created_sessions', [])
        else:
            print(f"\n❌ Failed to start sessions: {response.status_code}")
            print(f"   {response.text}")
            return []
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return []


def test_list_sessions():
    """Test listing sessions for user."""
    print("\n" + "="*60)
    print("TEST: List Sessions (Per User)")
    print("="*60)
    
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/live/sessions",
            params={"user_id": USER_ID},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            sessions = result.get('sessions', [])
            print(f"\n✅ Found {len(sessions)} session(s) for user {USER_ID}")
            
            for session in sessions:
                print(f"\n   📊 {session.get('session_id', 'unknown')}")
                print(f"      Strategy: {session.get('strategy_id', 'unknown')[:20]}...")
                print(f"      Status: {session.get('status', 'unknown')}")
            
            return sessions
        else:
            print(f"\n❌ Failed to list sessions: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return []


def test_sse_stream(session_id: str, duration: int = 10):
    """
    Test SSE streaming for a session.
    
    Args:
        session_id: Session ID to stream
        duration: Duration to listen (seconds)
    """
    print("\n" + "="*60)
    print(f"TEST: SSE Stream for {session_id}")
    print("="*60)
    
    url = f"{API_BASE}/api/v1/live/session/{session_id}/stream"
    print(f"\n📡 Connecting to: {url}")
    print(f"   Listening for {duration} seconds...")
    
    try:
        # Connect to SSE stream
        response = requests.get(url, stream=True, timeout=duration+5)
        client = SSEClient(response)
        
        start_time = time.time()
        event_counts = {
            'node_event': 0,
            'trade_event': 0,
            'position_update': 0,
            'ltp_snapshot': 0,
            'candle_update': 0,
            'other': 0
        }
        
        for msg in client.events():
            # Check timeout
            if time.time() - start_time > duration:
                print(f"\n⏱️ Timeout reached ({duration}s)")
                break
            
            # Skip empty events
            if not msg.data:
                continue
            
            # Parse event
            try:
                event_type = msg.event or 'unknown'
                data = json.loads(msg.data)
                
                # Count events
                if event_type in event_counts:
                    event_counts[event_type] += 1
                else:
                    event_counts['other'] += 1
                
                # Print sample events
                if event_type == 'ltp_snapshot' and event_counts[event_type] <= 3:
                    print(f"\n📥 Event: {event_type}")
                    sample_ltps = dict(list(data.items())[:3])
                    print(f"   Sample LTPs: {sample_ltps}")
                elif event_type == 'position_update':
                    positions = data.get('positions', [])
                    # Print first 5 position updates, then every 100th, and last 5
                    if event_counts[event_type] <= 5 or event_counts[event_type] % 100 == 0:
                        print(f"\n📥 Position Update #{event_counts[event_type]}")
                        print(f"   Positions: {len(positions)}")
                        print(f"   Unrealized P&L: ₹{data.get('total_unrealized_pnl', 0):,.2f}")
                        print(f"   Realized P&L: ₹{data.get('total_realized_pnl', 0):,.2f}")
                        print(f"   Total P&L: ₹{data.get('total_pnl', 0):,.2f}")
                        if positions:
                            pos = positions[0]
                            print(f"   Sample: {pos.get('symbol', 'N/A')[:35]} Qty={pos.get('quantity', 0)} P&L=₹{pos.get('pnl', 0):,.2f}")
                elif event_type == 'node_event' and event_counts[event_type] <= 3:
                    print(f"\n📥 Event: {event_type}")
                    print(f"   Node: {data.get('node_name', 'unknown')}")
                    print(f"   Execution ID: {data.get('execution_id', 'unknown')}")
                elif event_type == 'trade_event' and event_counts[event_type] <= 3:
                    print(f"\n📥 Event: {event_type}")
                    print(f"   Position: {data.get('position_id', 'unknown')}")
                    print(f"   Side: {data.get('side', 'unknown')}")
                
            except Exception as e:
                print(f"\n⚠️ Error parsing event: {e}")
                continue
        
        # Print summary
        print("\n" + "-"*60)
        print("📊 Event Summary:")
        for event_type, count in event_counts.items():
            if count > 0:
                print(f"   {event_type}: {count}")
        print("-"*60)
        
        return event_counts
        
    except Exception as e:
        print(f"\n❌ Error connecting to SSE: {e}")
        return {}


def test_session_status(session_id: str):
    """Test getting session status."""
    print("\n" + "="*60)
    print(f"TEST: Session Status for {session_id}")
    print("="*60)
    
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/live/session/{session_id}/status",
            timeout=5
        )
        
        if response.status_code == 200:
            status = response.json()
            print(f"\n✅ Session Status:")
            print(f"   Status: {status.get('status', 'unknown')}")
            print(f"   Strategy: {status.get('strategy_id', 'unknown')[:20]}...")
            print(f"   Created: {status.get('created_at', 'unknown')}")
            return status
        else:
            print(f"\n❌ Failed to get status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("SSE LIVE SESSIONS TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}")
    
    # Test 1: Start sessions
    created_sessions = test_start_sessions()
    
    if not created_sessions:
        print("\n❌ No sessions created. Exiting.")
        return
    
    # Wait for sessions to initialize
    print("\n⏱️ Waiting 5 seconds for sessions to initialize...")
    time.sleep(5)
    
    # Test 2: List sessions
    test_list_sessions()
    
    # Test 3: Check status of first session
    if created_sessions:
        first_session_id = created_sessions[0]['session_id']
        test_session_status(first_session_id)
    
    # Test 4: Stream events from first session
    # Note: This will block for specified duration
    if created_sessions:
        first_session_id = created_sessions[0]['session_id']
        print("\n💡 Note: SSE streaming test will run for 10 seconds...")
        test_sse_stream(first_session_id, duration=10)
    
    print("\n" + "="*80)
    print("✅ TEST SUITE COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
