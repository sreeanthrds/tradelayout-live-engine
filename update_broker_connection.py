"""
Update broker connection metadata for testing.
"""

import os
import json
from supabase import create_client

# Set Supabase credentials
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

BROKER_CONNECTION_ID = "acf98a95-1547-4a72-b824-3ce7068f05b4"
TEST_DATE = "2024-10-28"
STRATEGY_ID = "d70ec04a-1025-46c5-94c4-3e6bff499644"  # My strategy 5

def update_connection():
    """Update broker connection metadata."""
    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_SERVICE_ROLE_KEY']
    )
    
    print(f"\n🔍 Updating broker connection: {BROKER_CONNECTION_ID}")
    
    # New metadata with correct date
    broker_metadata = {
        "broker_type": "clickhouse",
        "strategy_id": STRATEGY_ID,
        "scale": 1.0,
        "date": TEST_DATE
    }
    
    try:
        result = supabase.table("broker_connections").update({
            "broker_metadata": broker_metadata
        }).eq("id", BROKER_CONNECTION_ID).execute()
        
        if result.data:
            print(f"\n✅ Connection updated successfully!")
            print(f"   Connection ID: {BROKER_CONNECTION_ID}")
            print(f"   New metadata:")
            print(json.dumps(broker_metadata, indent=2))
            
            print("\n" + "="*80)
            print("TEST PAYLOAD:")
            print("="*80)
            
            payload = {
                "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
                "sessions": {
                    "session_test_1": {
                        "strategy_id": STRATEGY_ID,
                        "broker_connection_id": BROKER_CONNECTION_ID
                    }
                }
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
            
        else:
            print("\n❌ Failed to update connection")
    
    except Exception as e:
        print(f"\n❌ Error updating connection: {e}")

if __name__ == "__main__":
    update_connection()
