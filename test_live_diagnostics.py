"""
Test live simulation SSE stream and verify diagnostics match backtest output.
Speed: 5000x
"""

import requests
import json
import gzip
import base64
import time
from sseclient import SSEClient

# Configuration
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
BACKTEST_DATE = "2024-10-29"
SPEED_MULTIPLIER = 5000
API_URL = "http://localhost:8000"

def decompress_json(compressed_b64):
    """Decompress base64+gzip JSON data"""
    try:
        compressed = base64.b64decode(compressed_b64)
        decompressed = gzip.decompress(compressed)
        return json.loads(decompressed.decode('utf-8'))
    except Exception as e:
        print(f"Decompression error: {e}")
        return None

def start_live_simulation():
    """Start live simulation with 5000x speed"""
    print(f"\n{'='*80}")
    print(f"Starting Live Simulation (5000x speed)")
    print(f"{'='*80}")
    
    # Use v1 endpoint which doesn't require broker metadata
    response = requests.post(
        f"{API_URL}/api/v1/live/start",
        json={
            "user_id": USER_ID,
            "strategy_id": STRATEGY_ID,
            "strategy_name": "Test Strategy",
            "broker_connection_id": "acf98a95-1547-4a72-b824-3ce7068f05b4",
            "speed_multiplier": SPEED_MULTIPLIER
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        session_id = data.get('session_id')
        print(f"✅ Live simulation started: {session_id}")
        return session_id
    else:
        print(f"❌ Failed to start simulation: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def monitor_sse_stream(session_id):
    """Monitor SSE stream and capture events"""
    print(f"\n{'='*80}")
    print(f"Monitoring SSE Stream for session: {session_id}")
    print(f"{'='*80}\n")
    
    stream_url = f"{API_URL}/api/live-trading/stream/{USER_ID}"
    
    tick_count = 0
    diagnostics_snapshots = []
    last_tick_events = None
    
    try:
        response = requests.get(stream_url, stream=True, timeout=120)
        client = SSEClient(response)
        
        for msg in client.events():
            if not msg.data or msg.data.strip() == '':
                continue
            
            try:
                event_data = json.loads(msg.data)
                event_type = msg.event
                
                if event_type == "tick_update":
                    tick_state = event_data.get('tick_state', {})
                    tick_count += 1
                    
                    # Capture current_tick_events
                    current_tick_events = tick_state.get('current_tick_events', {})
                    if current_tick_events:
                        last_tick_events = current_tick_events
                    
                    # Print progress every 100 ticks or if there are tick events
                    if tick_count % 100 == 0 or current_tick_events:
                        progress = tick_state.get('progress', {})
                        print(f"Tick {tick_count}: {progress.get('progress_percentage', 0):.1f}% | "
                              f"Tick Events: {len(current_tick_events)} | "
                              f"Open Positions: {len(tick_state.get('open_positions', []))}")
                        
                        if current_tick_events:
                            print(f"  └─ Events: {list(current_tick_events.keys())[:3]}...")
                
                elif event_type == "diagnostics_snapshot":
                    print(f"\n🎯 Received diagnostics_snapshot!")
                    
                    # Decompress diagnostics and trades
                    diagnostics_compressed = event_data.get('diagnostics', '')
                    trades_compressed = event_data.get('trades', '')
                    
                    diagnostics = decompress_json(diagnostics_compressed)
                    trades = decompress_json(trades_compressed)
                    
                    if diagnostics and trades:
                        snapshot = {
                            'diagnostics': diagnostics,
                            'trades': trades,
                            'received_at_tick': tick_count
                        }
                        diagnostics_snapshots.append(snapshot)
                        
                        print(f"  └─ Events: {len(diagnostics.get('events_history', {}))} events")
                        print(f"  └─ Trades: {len(trades.get('trades', []))} trades")
                
                elif event_type == "heartbeat":
                    pass  # Ignore heartbeats
                
                elif event_type == "error":
                    print(f"❌ SSE Error: {event_data.get('error')}")
                    break
                
                # Stop after reasonable progress (or when stream ends)
                if tick_count > 50000:  # Safety limit
                    print("\n⚠️  Reached tick limit, stopping...")
                    break
                    
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                continue
            except Exception as e:
                print(f"Event processing error: {e}")
                continue
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ SSE stream error: {e}")
    
    print(f"\n{'='*80}")
    print(f"Stream Monitoring Complete")
    print(f"{'='*80}")
    print(f"Total ticks processed: {tick_count}")
    print(f"Diagnostics snapshots received: {len(diagnostics_snapshots)}")
    
    return {
        'tick_count': tick_count,
        'diagnostics_snapshots': diagnostics_snapshots,
        'last_tick_events': last_tick_events
    }

def save_and_compare_results(results):
    """Save final diagnostics and compare with backtest"""
    print(f"\n{'='*80}")
    print(f"Saving and Comparing Results")
    print(f"{'='*80}\n")
    
    diagnostics_snapshots = results.get('diagnostics_snapshots', [])
    
    if not diagnostics_snapshots:
        print("❌ No diagnostics snapshots received!")
        return
    
    # Use the last (most complete) snapshot
    final_snapshot = diagnostics_snapshots[-1]
    
    # Save live simulation output
    live_diagnostics_file = "live_diagnostics_export.json"
    live_trades_file = "live_trades_daily.json"
    
    with open(live_diagnostics_file, 'w') as f:
        json.dump(final_snapshot['diagnostics'], f, indent=2)
    print(f"✅ Saved: {live_diagnostics_file}")
    
    with open(live_trades_file, 'w') as f:
        json.dump(final_snapshot['trades'], f, indent=2)
    print(f"✅ Saved: {live_trades_file}")
    
    # Load backtest files for comparison
    backtest_diagnostics_file = "../tradelayout-engine/diagnostics_export.json"
    backtest_trades_file = "../tradelayout-engine/trades_daily.json"
    
    try:
        with open(backtest_diagnostics_file, 'r') as f:
            backtest_diagnostics = json.load(f)
        
        with open(backtest_trades_file, 'r') as f:
            backtest_trades = json.load(f)
        
        print(f"\n{'='*80}")
        print(f"Comparison: Live vs Backtest")
        print(f"{'='*80}\n")
        
        # Compare diagnostics
        live_events = final_snapshot['diagnostics'].get('events_history', {})
        backtest_events = backtest_diagnostics.get('events_history', {})
        
        print(f"📊 Diagnostics Events:")
        print(f"  Live:     {len(live_events)} events")
        print(f"  Backtest: {len(backtest_events)} events")
        print(f"  Match:    {'✅ YES' if len(live_events) == len(backtest_events) else '❌ NO'}")
        
        # Compare trades
        live_trades_list = final_snapshot['trades'].get('trades', [])
        backtest_trades_list = backtest_trades.get('trades', [])
        
        print(f"\n📈 Trades:")
        print(f"  Live:     {len(live_trades_list)} trades")
        print(f"  Backtest: {len(backtest_trades_list)} trades")
        print(f"  Match:    {'✅ YES' if len(live_trades_list) == len(backtest_trades_list) else '❌ NO'}")
        
        # Compare P&L
        live_summary = final_snapshot['trades'].get('summary', {})
        backtest_summary = backtest_trades.get('summary', {})
        
        print(f"\n💰 P&L Summary:")
        print(f"  Live Total P&L:     {live_summary.get('total_pnl', 'N/A')}")
        print(f"  Backtest Total P&L: {backtest_summary.get('total_pnl', 'N/A')}")
        print(f"  Match:              {'✅ YES' if live_summary.get('total_pnl') == backtest_summary.get('total_pnl') else '❌ NO'}")
        
        # Detailed comparison if counts don't match
        if len(live_events) != len(backtest_events):
            print(f"\n⚠️  Event count mismatch - analyzing...")
            live_event_types = {}
            for event in live_events.values():
                event_type = event.get('event_type', 'unknown')
                live_event_types[event_type] = live_event_types.get(event_type, 0) + 1
            
            backtest_event_types = {}
            for event in backtest_events.values():
                event_type = event.get('event_type', 'unknown')
                backtest_event_types[event_type] = backtest_event_types.get(event_type, 0) + 1
            
            print(f"\n  Live event types: {live_event_types}")
            print(f"  Backtest event types: {backtest_event_types}")
        
    except FileNotFoundError as e:
        print(f"❌ Backtest file not found: {e}")
    except Exception as e:
        print(f"❌ Comparison error: {e}")

def main():
    """Main test flow"""
    print(f"\n{'#'*80}")
    print(f"# Live Simulation SSE Test - 5000x Speed")
    print(f"# Strategy: {STRATEGY_ID}")
    print(f"# Date: {BACKTEST_DATE}")
    print(f"{'#'*80}")
    
    # Start simulation
    session_id = start_live_simulation()
    if not session_id:
        print("❌ Failed to start simulation, exiting...")
        return
    
    # Wait a moment for engine to initialize
    print("\n⏳ Waiting 2 seconds for engine initialization...")
    time.sleep(2)
    
    # Monitor SSE stream
    results = monitor_sse_stream(session_id)
    
    # Save and compare
    save_and_compare_results(results)
    
    print(f"\n{'#'*80}")
    print(f"# Test Complete")
    print(f"{'#'*80}\n")

if __name__ == "__main__":
    main()
