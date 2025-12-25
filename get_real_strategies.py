"""
Get real strategies from database for testing.
"""

import os
import json
from supabase import create_client

# Set Supabase credentials
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

# User ID
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"

# Date for testing
TEST_DATE = "2024-10-28"

def get_supabase_client():
    """Create Supabase client."""
    return create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_SERVICE_ROLE_KEY']
    )

def get_strategies():
    """Get all strategies for user."""
    supabase = get_supabase_client()
    
    print(f"\n🔍 Fetching strategies for user: {USER_ID}")
    
    result = supabase.table("strategies").select("id, name, user_id").eq("user_id", USER_ID).execute()
    
    if result.data:
        print(f"\n✅ Found {len(result.data)} strategy(ies):")
        for i, strategy in enumerate(result.data, 1):
            print(f"\n{i}. {strategy['name']}")
            print(f"   ID: {strategy['id']}")
        
        return result.data
    else:
        print("\n❌ No strategies found")
        return []

def get_broker_connections():
    """Get broker connections for user."""
    supabase = get_supabase_client()
    
    print(f"\n🔍 Fetching broker connections for user: {USER_ID}")
    
    result = supabase.table("broker_connections").select("id, broker_metadata").eq("user_id", USER_ID).execute()
    
    if result.data:
        print(f"\n✅ Found {len(result.data)} broker connection(s):")
        for i, conn in enumerate(result.data, 1):
            metadata = conn.get('broker_metadata', {})
            broker_type = metadata.get('broker_type', 'unknown') if metadata else 'unknown'
            print(f"\n{i}. Broker Type: {broker_type}")
            print(f"   ID: {conn['id']}")
            print(f"   Metadata: {json.dumps(conn.get('broker_metadata'), indent=2)}")
        
        return result.data
    else:
        print("\n❌ No broker connections found")
        return []

def create_test_broker_connections(strategy_ids: list):
    """Create test broker connections with correct metadata."""
    supabase = get_supabase_client()
    
    print(f"\n📝 Creating test broker connections with date 2024-10-28...")
    
    created_connections = []
    
    for i, strategy_id in enumerate(strategy_ids[:2], 1):  # Max 2 connections
        broker_metadata = {
            "broker_type": "clickhouse",
            "strategy_id": strategy_id,
            "scale": 1.0,
            "date": "2024-10-28"
        }
        
        connection_data = {
            "user_id": USER_ID,
            "broker": "clickhouse",
            "status": "active",
            "broker_metadata": broker_metadata
        }
        
        try:
            result = supabase.table("broker_connections").insert(connection_data).execute()
            
            if result.data:
                conn_id = result.data[0]['id']
                print(f"\n✅ Created connection {i}: {conn_id}")
                print(f"   Strategy: {strategy_id}")
                created_connections.append({
                    "connection_id": conn_id,
                    "strategy_id": strategy_id,
                    "broker_metadata": broker_metadata
                })
        except Exception as e:
            print(f"\n⚠️ Failed to create connection: {e}")
    
    return created_connections

def main():
    print("\n" + "="*80)
    print("GET REAL STRATEGIES FOR TESTING")
    print("="*80)
    
    # Get strategies
    strategies = get_strategies()
    
    if not strategies:
        print("\n❌ No strategies found. Cannot proceed.")
        return
    
    # Get existing broker connections
    broker_connections = get_broker_connections()
    
    # Check if we need to create new ones with correct date
    print("\n" + "="*80)
    print("OPTIONS:")
    print("="*80)
    print("\n1. Use existing broker connections (if metadata has correct date)")
    print("2. Create new broker connections with date 2024-10-28")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        # Create new connections
        strategy_ids = [s['id'] for s in strategies]
        created = create_test_broker_connections(strategy_ids)
        
        if created:
            print("\n" + "="*80)
            print("TEST DATA READY:")
            print("="*80)
            
            for i, conn in enumerate(created, 1):
                print(f"\nSession {i}:")
                print(f"  session_id: session_test_{i}")
                print(f"  strategy_id: {conn['strategy_id']}")
                print(f"  broker_connection_id: {conn['connection_id']}")
                print(f"  date: 2024-10-28")
    else:
        # Use existing connections
        if broker_connections and strategies:
            print("\n" + "="*80)
            print("EXISTING DATA:")
            print("="*80)
            
            for i in range(min(2, len(broker_connections), len(strategies))):
                print(f"\nSession {i+1}:")
                print(f"  session_id: session_test_{i+1}")
                print(f"  strategy_id: {strategies[i]['id']}")
                print(f"  broker_connection_id: {broker_connections[i]['id']}")
                print(f"  metadata: {broker_connections[i].get('broker_metadata')}")

if __name__ == "__main__":
    main()
