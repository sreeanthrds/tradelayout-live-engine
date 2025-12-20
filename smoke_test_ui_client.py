#!/usr/bin/env python3
"""
Smoke Test: UI SSE Client Simulation

Simulates a UI client connecting to the live trading SSE stream,
receiving events, decompressing them, and writing to files in the
exact same format as backtesting results.

Usage:
    python smoke_test_ui_client.py <user_id> <session_id>
"""

import sys
import json
import gzip
import base64
import time
import os
from datetime import datetime
from pathlib import Path
import requests
import sseclient

def decompress_gzip(base64_string):
    """Decompress gzip + base64 encoded data"""
    try:
        # Decode base64
        compressed_data = base64.b64decode(base64_string)
        # Decompress gzip
        decompressed_data = gzip.decompress(compressed_data)
        # Parse JSON
        return json.loads(decompressed_data.decode('utf-8'))
    except Exception as e:
        print(f"[ERROR] Decompression failed: {e}")
        return None

def write_json_file(filepath, data, mode='w'):
    """Write JSON data to file"""
    with open(filepath, mode, encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[WRITE] {filepath} ({len(json.dumps(data))} bytes)")

def append_to_events_history(filepath, execution_id, event_data):
    """Append to events_history in diagnostics"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            diagnostics = json.load(f)
    else:
        diagnostics = {
            "events_history": {},
            "current_state": {}
        }
    
    # Append event
    diagnostics["events_history"][execution_id] = event_data
    
    # Update current_state if node_id present
    if "node_id" in event_data:
        diagnostics["current_state"][event_data["node_id"]] = event_data
    
    # Write back
    write_json_file(filepath, diagnostics, mode='w')

def append_to_trades(filepath, trades_data):
    """Update trades file with new trades"""
    write_json_file(filepath, trades_data, mode='w')

def create_output_dir(session_id):
    """Create output directory for test results"""
    output_dir = Path(f"smoke_test_output/{session_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def connect_sse(user_id):
    """Connect to user-level SSE stream"""
    url = f"http://localhost:8000/api/live-trading/stream/{user_id}"
    print(f"[SSE] Connecting to {url}")
    
    response = requests.get(url, stream=True, headers={'Accept': 'text/event-stream'})
    client = sseclient.SSEClient(response)
    
    return client

def main():
    if len(sys.argv) < 2:
        print("Usage: python smoke_test_ui_client.py <user_id> [session_id_to_track]")
        sys.exit(1)
    
    user_id = sys.argv[1]
    track_session_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("="*80)
    print("🧪 SMOKE TEST: UI SSE Client Simulation")
    print("="*80)
    print(f"User ID: {user_id}")
    print(f"Tracking Session: {track_session_id or 'ALL sessions'}")
    print(f"Output Dir: smoke_test_output/")
    print("="*80)
    
    # Track sessions
    session_dirs = {}
    event_counts = {}
    start_time = time.time()
    
    try:
        client = connect_sse(user_id)
        
        print("[SSE] Connected! Waiting for events...")
        print("")
        
        for event in client.events():
            # Parse event
            event_type = event.event
            
            if not event.data or event.data == '':
                continue
            
            try:
                data = json.loads(event.data)
            except json.JSONDecodeError:
                print(f"[ERROR] Failed to parse event data: {event.data[:100]}")
                continue
            
            session_id = data.get('session_id', 'unknown')
            
            # Filter by session if specified
            if track_session_id and session_id != track_session_id:
                continue
            
            # Create output dir for this session if not exists
            if session_id not in session_dirs:
                session_dirs[session_id] = create_output_dir(session_id)
                event_counts[session_id] = {
                    'initial_state': 0,
                    'node_events': 0,
                    'trade_update': 0,
                    'tick_update': 0,
                    'heartbeat': 0
                }
                print(f"[SESSION] Tracking new session: {session_id}")
            
            output_dir = session_dirs[session_id]
            event_counts[session_id][event_type] = event_counts[session_id].get(event_type, 0) + 1
            
            # Handle different event types
            if event_type == 'initial_state':
                print(f"[{session_id}] INITIAL_STATE received")
                
                # Decompress diagnostics
                if 'diagnostics' in data:
                    diagnostics = decompress_gzip(data['diagnostics'])
                    if diagnostics:
                        diagnostics_file = output_dir / "diagnostics_export.json"
                        write_json_file(diagnostics_file, diagnostics)
                
                # Decompress trades
                if 'trades' in data:
                    trades = decompress_gzip(data['trades'])
                    if trades:
                        trades_file = output_dir / "trades_daily.json"
                        write_json_file(trades_file, trades)
            
            elif event_type == 'node_events':
                diagnostics_compressed = data.get('diagnostics')
                if diagnostics_compressed:
                    diagnostics = decompress_gzip(diagnostics_compressed)
                    if diagnostics:
                        diagnostics_file = output_dir / "diagnostics_export.json"
                        write_json_file(diagnostics_file, diagnostics)
                        
                        num_events = len(diagnostics.get('events_history', {}))
                        print(f"[{session_id}] NODE_EVENTS: {num_events} total events in history")
            
            elif event_type == 'trade_update':
                trades_compressed = data.get('trades')
                if trades_compressed:
                    trades = decompress_gzip(trades_compressed)
                    if trades:
                        trades_file = output_dir / "trades_daily.json"
                        write_json_file(trades_file, trades)
                        
                        num_trades = len(trades.get('trades', []))
                        total_pnl = trades.get('summary', {}).get('total_pnl', '0.00')
                        print(f"[{session_id}] TRADE_UPDATE: {num_trades} trades, Total P&L: ₹{total_pnl}")
            
            elif event_type == 'tick_update':
                tick_state = data.get('tick_state', {})
                
                # Write tick update to separate file (append mode for stream)
                tick_file = output_dir / "tick_updates_stream.jsonl"
                with open(tick_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(tick_state) + '\n')
                
                # Print progress
                progress = tick_state.get('progress', {})
                pnl = tick_state.get('pnl_summary', {})
                positions = tick_state.get('open_positions', [])
                
                ticks_processed = progress.get('ticks_processed', 0)
                progress_pct = progress.get('progress_percentage', 0)
                total_pnl = pnl.get('total_pnl', '0.00')
                
                # Print every 100 ticks to avoid flooding
                if ticks_processed % 100 == 0:
                    print(f"[{session_id}] TICK {ticks_processed} ({progress_pct:.2f}%) | "
                          f"Positions: {len(positions)} | P&L: ₹{total_pnl}")
            
            elif event_type == 'heartbeat':
                timestamp = data.get('timestamp', '')
                if event_counts[session_id]['heartbeat'] % 10 == 1:  # Print every 10th heartbeat
                    print(f"[{session_id}] HEARTBEAT: {timestamp}")
            
            # Print statistics every 1000 events
            total_events = sum(event_counts[session_id].values())
            if total_events % 1000 == 0:
                elapsed = time.time() - start_time
                events_per_sec = total_events / elapsed if elapsed > 0 else 0
                print(f"\n[STATS] {session_id}: {total_events} events in {elapsed:.1f}s "
                      f"({events_per_sec:.1f} events/sec)")
                print(f"  └─ {event_counts[session_id]}\n")
    
    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print("📊 FINAL STATISTICS")
        print("="*80)
        print(f"Total Time: {elapsed:.2f}s")
        
        for session_id, counts in event_counts.items():
            print(f"\nSession: {session_id}")
            print(f"  Events Received:")
            for event_type, count in counts.items():
                print(f"    • {event_type}: {count}")
            
            # Print file locations
            output_dir = session_dirs[session_id]
            print(f"\n  Output Files:")
            
            diagnostics_file = output_dir / "diagnostics_export.json"
            if diagnostics_file.exists():
                size = diagnostics_file.stat().st_size
                print(f"    • {diagnostics_file} ({size:,} bytes)")
            
            trades_file = output_dir / "trades_daily.json"
            if trades_file.exists():
                size = trades_file.stat().st_size
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
                    num_trades = len(trades.get('trades', []))
                print(f"    • {trades_file} ({size:,} bytes, {num_trades} trades)")
            
            tick_file = output_dir / "tick_updates_stream.jsonl"
            if tick_file.exists():
                size = tick_file.stat().st_size
                lines = sum(1 for _ in open(tick_file))
                print(f"    • {tick_file} ({size:,} bytes, {lines} ticks)")
        
        print("\n✅ Test completed!")
        print("="*80)

if __name__ == "__main__":
    main()
