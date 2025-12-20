"""
Test diagnostics system with simple backtest
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

os.environ['CLICKHOUSE_HOST'] = 'localhost'
os.environ['CLICKHOUSE_PORT'] = '8123'
os.environ['CLICKHOUSE_USER'] = 'default'
os.environ['CLICKHOUSE_PASSWORD'] = ''
os.environ['CLICKHOUSE_DATABASE'] = 'tradelayout'
os.environ['CLICKHOUSE_SECURE'] = 'false'

from show_dashboard_data import run_dashboard_backtest, dashboard_data
import json

# Configuration
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"

print("=" * 80)
print("🧪 TESTING DIAGNOSTICS SYSTEM")
print("=" * 80)

try:
    # Run backtest
    result = run_dashboard_backtest(STRATEGY_ID, BACKTEST_DATE)
    
    # Get diagnostics from result
    diagnostics_data = result.get('diagnostics', {})
    events_history = diagnostics_data.get('events_history', {})
    current_state = diagnostics_data.get('current_state', {})
    
    print(f"\n📊 DIAGNOSTICS SUMMARY")
    print("=" * 80)
    print(f"Nodes with events: {len(events_history)}")
    print(f"Nodes in current state: {len(current_state)}")
    
    # Show events for first few nodes
    print(f"\n📝 EVENT HISTORY")
    print("=" * 80)
    for node_id, events in list(events_history.items())[:3]:
        print(f"\n{node_id}: {len(events)} events")
        if events:
            first_event = events[0]
            print(f"  First event: {first_event.get('event_type')} at {first_event.get('timestamp')}")
            
            if len(events) > 1:
                last_event = events[-1]
                print(f"  Last event: {last_event.get('event_type')} at {last_event.get('timestamp')}")
    
    # Show current state (should be empty at end of backtest)
    print(f"\n🔄 CURRENT STATE (should be empty after backtest)")
    print("=" * 80)
    if current_state:
        for node_id, state in list(current_state.items())[:5]:
            print(f"\n{node_id}:")
            print(f"  Status: {state.get('status')}")
            print(f"  Timestamp: {state.get('timestamp')}")
    else:
        print("✅ All nodes inactive (as expected)")
    
    # Show example of detailed event
    print(f"\n🔍 DETAILED EVENT EXAMPLE")
    print("=" * 80)
    if events_history:
        node_id = list(events_history.keys())[0]
        events = events_history[node_id]
        if events:
            event = events[0]
            print(json.dumps(event, indent=2, default=str))
    
    print("\n" + "=" * 80)
    print("✅ DIAGNOSTICS TEST COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
