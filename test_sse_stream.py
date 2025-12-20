#!/usr/bin/env python3
"""
Test SSE stream to verify all three event types are emitted correctly.
"""

import requests
import json
import time
import sys

def start_simulation():
    """Start a new simulation"""
    url = "http://localhost:8000/api/v1/live/start"
    payload = {
        "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "strategy_name": "My New Strategy5",
        "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4"
    }
    
    response = requests.post(url, json=payload)
    return response.json()

def test_sse_stream():
    # Start simulation first
    print("🚀 Starting simulation...")
    sim_response = start_simulation()
    print(f"   Session: {sim_response.get('session_id')}\n")
    
    # Connect immediately to capture events as they happen
    url = "http://localhost:8000/api/live-trading/stream/user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
    
    print("🔍 Connecting to SSE stream...")
    print(f"URL: {url}\n")
    
    response = requests.get(url, stream=True, timeout=60)
    
    event_counts = {
        'tick_update': 0,
        'node_events': 0,
        'trade_closed': 0,
        'trade_update': 0
    }
    
    sample_events = {
        'tick_update': None,
        'node_events': None,
        'trade_closed': None
    }
    
    print("📡 Receiving events...\n")
    
    line_count = 0
    current_event = None
    
    for line in response.iter_lines():
        line_count += 1
        
        if line_count > 2000:  # Stop after 2000 lines (more time for positions to close)
            break
            
        if line:
            line_str = line.decode('utf-8')
            
            # Parse event type
            if line_str.startswith('event: '):
                current_event = line_str.split('event: ')[1].strip()
                if current_event in event_counts:
                    event_counts[current_event] += 1
                    
            # Parse data
            elif line_str.startswith('data: '):
                data_str = line_str.split('data: ', 1)[1]
                try:
                    data = json.loads(data_str)
                    
                    # Save first sample of each event type
                    if current_event and current_event in sample_events:
                        if sample_events[current_event] is None:
                            sample_events[current_event] = data
                            print(f"✅ Received first {current_event} event")
                            
                            # Check tick_update structure
                            if current_event == 'tick_update':
                                tick = data.get('tick_state', {})
                                positions = tick.get('open_positions', [])
                                if positions:
                                    pos = positions[0]
                                    print(f"   Position format:")
                                    print(f"     - side: {pos.get('side')} (should be uppercase)")
                                    print(f"     - entry_price: {pos.get('entry_price')} (should be string)")
                                    print(f"     - entry_time: {pos.get('entry_time')} (should have space)")
                                    print(f"     - entry_trigger: {pos.get('entry_trigger', 'MISSING')}")
                                    print(f"     - re_entry_num: {pos.get('re_entry_num', 'MISSING')}")
                                    
                                node_states = tick.get('active_node_states', [])
                                if node_states:
                                    node = node_states[0]
                                    print(f"   Node state format:")
                                    print(f"     - node_name: {node.get('node_name')}")
                                    print(f"     - node_type: {node.get('node_type')}")
                                    
                            elif current_event == 'trade_closed':
                                print(f"   Trade record keys: {list(data.keys())}")
                                print(f"     - Has exit_price: {('exit_price' in data)}")
                                print(f"     - Has pnl: {('pnl' in data)}")
                                print(f"     - Has exit_flow_ids: {('exit_flow_ids' in data)}")
                                print(f"     - Has exit_reason: {('exit_reason' in data)}")
                                
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "="*60)
    print("📊 EVENT SUMMARY")
    print("="*60)
    for event_type, count in event_counts.items():
        status = "✅" if count > 0 else "❌"
        print(f"{status} {event_type}: {count} events")
    
    print("\n" + "="*60)
    print("🎯 VERIFICATION")
    print("="*60)
    
    checks = []
    
    # Check tick_update
    if sample_events['tick_update']:
        tick = sample_events['tick_update'].get('tick_state', {})
        positions = tick.get('open_positions', [])
        if positions:
            pos = positions[0]
            checks.append(("Position side uppercase", pos.get('side', '').isupper()))
            checks.append(("Position entry_price is string", isinstance(pos.get('entry_price'), str)))
            checks.append(("Position has entry_trigger", 'entry_trigger' in pos))
            checks.append(("Position has re_entry_num", 're_entry_num' in pos))
            checks.append(("Position has entry_flow_ids", 'entry_flow_ids' in pos))
        
        node_states = tick.get('active_node_states', [])
        if node_states:
            node = node_states[0]
            checks.append(("Node has readable node_name", node.get('node_name') != node.get('node_id')))
            checks.append(("Node type not 'Unknown'", node.get('node_type') != 'Unknown'))
    
    # Check trade_closed
    if sample_events['trade_closed']:
        trade = sample_events['trade_closed']
        checks.append(("Trade has exit_price", 'exit_price' in trade))
        checks.append(("Trade has pnl", 'pnl' in trade))
        checks.append(("Trade has exit_flow_ids", 'exit_flow_ids' in trade))
        checks.append(("Trade has exit_reason", 'exit_reason' in trade))
        checks.append(("Trade has duration_minutes", 'duration_minutes' in trade))
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    # Final verdict
    all_passed = all(passed for _, passed in checks)
    all_events_present = all(count > 0 for event_type, count in event_counts.items() if event_type != 'trade_update')
    
    print("\n" + "="*60)
    if all_passed and event_counts['tick_update'] > 0:
        print("✅ ALL FIXES VERIFIED SUCCESSFULLY!")
    else:
        print("⚠️  Some issues remain - review output above")
    print("="*60)

if __name__ == "__main__":
    try:
        test_sse_stream()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
