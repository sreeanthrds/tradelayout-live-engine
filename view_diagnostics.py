"""
View diagnostics from backtest results
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
os.environ['CLICKHOUSE_DATABASE'] = 'default'
os.environ['CLICKHOUSE_SECURE'] = 'false'

from show_dashboard_data import run_dashboard_backtest, dashboard_data
import json

# Configuration
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"

print("=" * 100)
print("🔍 DIAGNOSTICS VIEWER")
print("=" * 100)

try:
    # Run backtest
    print(f"\nRunning backtest for {STRATEGY_ID} on {BACKTEST_DATE}...")
    result = run_dashboard_backtest(STRATEGY_ID, BACKTEST_DATE)
    
    # Get diagnostics
    diagnostics = result.get('diagnostics', {})
    events_history = diagnostics.get('events_history', {})
    current_state = diagnostics.get('current_state', {})
    
    print(f"\n✅ Backtest complete!")
    print(f"   Positions: {len(result.get('positions', []))}")
    print(f"   Nodes with events: {len(events_history)}")
    print(f"   Nodes in current state: {len(current_state)}")
    
    # Show events by node type
    print(f"\n" + "=" * 100)
    print("📊 EVENTS SUMMARY BY NODE")
    print("=" * 100)
    
    entry_nodes = {k: v for k, v in events_history.items() if k.startswith('entry-')}
    exit_nodes = {k: v for k, v in events_history.items() if k.startswith('exit-')}
    start_nodes = {k: v for k, v in events_history.items() if k.startswith('start')}
    
    print(f"\n📥 Entry Nodes ({len(entry_nodes)} nodes):")
    for node_id, events in entry_nodes.items():
        print(f"   {node_id}: {len(events)} events")
        if events:
            # Show first event with action details
            first = events[0]
            if 'action' in first:
                action = first['action']
                print(f"      First: {action.get('type')} - {action.get('symbol')} @ ₹{action.get('price')}")
    
    print(f"\n📤 Exit Nodes ({len(exit_nodes)} nodes):")
    for node_id, events in exit_nodes.items():
        print(f"   {node_id}: {len(events)} events")
        if events:
            first = events[0]
            if 'action' in first:
                action = first['action']
                print(f"      First: {action.get('type')} for position {action.get('target_position_id')}")
    
    print(f"\n🚀 Start Node ({len(start_nodes)} nodes):")
    for node_id, events in start_nodes.items():
        print(f"   {node_id}: {len(events)} events")
        if events:
            # Check for termination event
            termination_events = [e for e in events if 'termination' in e]
            if termination_events:
                term = termination_events[0]['termination']
                print(f"      ⚠️ Strategy terminated: {term.get('reason')}")
                print(f"         At: {term.get('timestamp')}")
                print(f"         Tick: {term.get('tick_count')}")
    
    # Show detailed event for first entry node
    print(f"\n" + "=" * 100)
    print("📋 DETAILED EVENT EXAMPLE (First Entry Node)")
    print("=" * 100)
    
    if entry_nodes:
        node_id = list(entry_nodes.keys())[0]
        events = entry_nodes[node_id]
        
        if events:
            event = events[0]
            
            print(f"\nNode: {event.get('node_id')} ({event.get('node_name')})")
            print(f"Type: {event.get('node_type')}")
            print(f"Event: {event.get('event_type')}")
            print(f"Time: {event.get('timestamp')}")
            print(f"Duration: {event.get('duration_seconds')}s")
            
            # Parent/children
            if event.get('parent_node'):
                print(f"\nParent: {event['parent_node'].get('id')} ({event['parent_node'].get('name')})")
            
            if event.get('children_nodes'):
                print(f"\nChildren:")
                for child in event['children_nodes']:
                    print(f"   - {child.get('id')} ({child.get('name')})")
            
            # Action details
            if 'action' in event:
                action = event['action']
                print(f"\n📝 Action Details:")
                print(f"   Type: {action.get('type')}")
                print(f"   Symbol: {action.get('symbol')}")
                print(f"   Side: {action.get('side')}")
                print(f"   Quantity: {action.get('quantity')}")
                print(f"   Price: ₹{action.get('price')}")
                print(f"   Order ID: {action.get('order_id')}")
                print(f"   Status: {action.get('status')}")
            
            # Position details
            if 'position' in event:
                pos = event['position']
                print(f"\n💼 Position Details:")
                print(f"   Position ID: {pos.get('position_id')}")
                print(f"   Entry Price: ₹{pos.get('entry_price')}")
                print(f"   Entry Time: {pos.get('entry_time')}")
            
            # Configuration
            if 'entry_config' in event:
                config = event['entry_config']
                print(f"\n⚙️ Entry Configuration:")
                print(f"   Max Entries: {config.get('max_entries')}")
                print(f"   Current Entries: {config.get('current_entries')}")
    
    # Show current state (should be empty at end of backtest)
    print(f"\n" + "=" * 100)
    print("🔄 CURRENT STATE (Active/Pending Nodes)")
    print("=" * 100)
    
    if current_state:
        print(f"\n⚠️ {len(current_state)} nodes still active/pending:")
        for node_id, state in current_state.items():
            print(f"   {node_id}: {state.get('status')} for {state.get('time_in_state')}s")
            if state.get('pending_reason'):
                print(f"      Reason: {state['pending_reason']}")
    else:
        print("\n✅ No active/pending nodes (all inactive - normal)")
    
    # Export to JSON
    output_file = 'diagnostics_export.json'
    with open(output_file, 'w') as f:
        json.dump(diagnostics, f, indent=2, default=str)
    
    print(f"\n" + "=" * 100)
    print(f"✅ Diagnostics exported to: {output_file}")
    print("=" * 100)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
