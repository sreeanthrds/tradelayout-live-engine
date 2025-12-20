#!/usr/bin/env python3
"""
Get broker connections for user from Supabase
"""

import os
from supabase import create_client

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_SERVICE_ROLE_KEY']
)

USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"

print("="*80)
print("🔍 FETCHING BROKER CONNECTIONS")
print("="*80)
print(f"User ID: {USER_ID}")
print()

# Fetch broker connections
try:
    response = supabase.table('broker_connections').select('*').eq('user_id', USER_ID).execute()
    
    if response.data:
        print(f"✅ Found {len(response.data)} broker connection(s):\n")
        for conn in response.data:
            print(f"ID: {conn['id']}")
            print(f"Broker Type: {conn.get('broker_type', 'N/A')}")
            print(f"Name: {conn.get('name', 'N/A')}")
            print(f"Status: {conn.get('status', 'N/A')}")
            print(f"Created: {conn.get('created_at', 'N/A')}")
            print("-" * 80)
    else:
        print("⚠️  No broker connections found for this user")
        print("\nCreating a test broker connection...")
        
        # Create a test broker connection
        new_conn = {
            'user_id': USER_ID,
            'broker_type': 'clickhouse_backtest',
            'name': 'Backtest Broker',
            'status': 'active',
            'credentials': {}
        }
        
        insert_response = supabase.table('broker_connections').insert(new_conn).execute()
        
        if insert_response.data:
            print(f"✅ Created test broker connection:")
            print(f"ID: {insert_response.data[0]['id']}")
            print(f"Type: {insert_response.data[0]['broker_type']}")
        else:
            print(f"❌ Failed to create broker connection")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
