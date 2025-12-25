"""
Setup test data for SSE live sessions with real strategies and date 2024-10-28.
"""

import os
import json
from supabase import create_client

# Set Supabase credentials
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
TEST_DATE = "2024-10-28"

# Real strategy IDs from database
STRATEGIES = [
    {"id": "d70ec04a-1025-46c5-94c4-3e6bff499644", "name": "My strategy 5"},
    {"id": "5708424d-5962-4629-978c-05b3a174e104", "name": "My New Strategy5"}
]

def create_broker_connections():
    """Create broker connections with correct metadata for testing."""
    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_SERVICE_ROLE_KEY']
    )
    
    print(f"\n📝 Creating test broker connections for date: {TEST_DATE}")
    
    created = []
    
    for i, strategy in enumerate(STRATEGIES, 1):
        broker_metadata = {
            "strategy_id": strategy['id'],
            "scale": 1.0,
            "date": TEST_DATE
        }
        
        connection_data = {
            "user_id": USER_ID,
            "broker_type": "clickhouse",
            "connection_name": f"SSE Test {i} - {TEST_DATE}",
            "broker_metadata": broker_metadata,
            "status": "connected"  # Valid status: connected, disconnected, error
        }
        
        try:
            result = supabase.table("broker_connections").insert(connection_data).execute()
            
            if result.data:
                conn_id = result.data[0]['id']
                print(f"\n✅ Connection {i} created: {conn_id}")
                print(f"   Strategy: {strategy['name']}")
                print(f"   Strategy ID: {strategy['id']}")
                
                created.append({
                    "connection_id": conn_id,
                    "strategy_id": strategy['id'],
                    "strategy_name": strategy['name']
                })
        except Exception as e:
            print(f"\n❌ Failed to create connection {i}: {e}")
    
    return created

def print_test_payload(connections):
    """Print the test payload for API."""
    print("\n" + "="*80)
    print("TEST PAYLOAD FOR SSE API:")
    print("="*80)
    
    sessions = {}
    for i, conn in enumerate(connections, 1):
        session_id = f"session_test_{i}"
        sessions[session_id] = {
            "strategy_id": conn['strategy_id'],
            "broker_connection_id": conn['connection_id']
        }
    
    payload = {
        "user_id": USER_ID,
        "sessions": sessions
    }
    
    print(json.dumps(payload, indent=2))
    
    print("\n" + "="*80)
    print("CURL COMMAND:")
    print("="*80)
    
    print(f"""
curl -X POST http://localhost:8001/api/v1/live/session/start-sse \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(payload)}'
""")
    
    print("\n" + "="*80)
    print("PYTHON TEST SCRIPT DATA:")
    print("="*80)
    
    for i, conn in enumerate(connections, 1):
        print(f"\nSTRATEGY_{i} = \"{conn['strategy_id']}\"  # {conn['strategy_name']}")
        print(f"BROKER_CONNECTION_{i} = \"{conn['connection_id']}\"")
    
    print(f"\nTEST_DATE = \"{TEST_DATE}\"")
    print(f"USER_ID = \"{USER_ID}\"")

def main():
    print("\n" + "="*80)
    print("SETUP TEST DATA FOR SSE LIVE SESSIONS")
    print("="*80)
    print(f"Date: {TEST_DATE}")
    print(f"User: {USER_ID}")
    print(f"Strategies: {len(STRATEGIES)}")
    
    # Create connections
    connections = create_broker_connections()
    
    if connections:
        print(f"\n✅ Created {len(connections)} broker connection(s)")
        print_test_payload(connections)
    else:
        print("\n❌ No connections created")

if __name__ == "__main__":
    main()
