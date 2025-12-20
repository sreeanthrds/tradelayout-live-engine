"""Quick check for strategy 5708424d-5962-4629-978c-05b3a174e104"""
import os
import json
import sys

# Add timeout
import signal
signal.alarm(10)  # 10 second timeout

from supabase import create_client

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

try:
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    strategy_id = '5708424d-5962-4629-978c-05b3a174e104'
    print(f"Fetching strategy {strategy_id}...")
    
    response = supabase.table('strategies').select('*').eq('id', strategy_id).execute()
    
    if not response.data:
        print("❌ Strategy not found")
        sys.exit(1)
    
    db_strategy = response.data[0]
    print(f"✅ Found: {db_strategy.get('name')}")
    
    config = db_strategy.get('strategy') or db_strategy.get('config')
    if isinstance(config, str):
        config = json.loads(config)
    
    # Find entry-condition-2
    nodes = config.get('nodes', [])
    for node in nodes:
        if node.get('id') == 'entry-condition-2':
            data = node.get('data', {})
            conditions = data.get('conditions', [])
            if conditions:
                root = conditions[0]
                sub_conds = root.get('conditions', [])
                print(f"\nEntry-Condition-2: {len(sub_conds)} conditions")
                
                has_rsi = False
                for cond in sub_conds:
                    if cond.get('lhs', {}).get('type') == 'indicator':
                        has_rsi = True
                        break
                
                if has_rsi:
                    print("✅ RSI CONDITION EXISTS")
                else:
                    print("❌ RSI CONDITION MISSING")
            break

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
