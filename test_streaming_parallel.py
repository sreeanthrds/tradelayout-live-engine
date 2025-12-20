"""
Test streaming API with parallel sessions
Simulates multiple UI clients consuming backtest streams simultaneously
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading
from collections import defaultdict

API_BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path("backtest_results_parallel")

# Statistics tracking
stats_lock = threading.Lock()
global_stats = defaultdict(lambda: {
    'days_processed': 0,
    'transactions': 0,
    'total_pnl': 0,
    'data_received_kb': 0,
    'start_time': None,
    'end_time': None,
    'status': 'pending'
})


def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def consume_stream_and_save(session_id, strategy_id, start_date, end_date):
    """
    Consume streaming API and save results per day
    Simulates a single UI client
    """
    session_dir = OUTPUT_DIR / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize stats
    with stats_lock:
        global_stats[session_id]['start_time'] = datetime.now()
        global_stats[session_id]['status'] = 'running'
    
    print(f"\n[Session {session_id}] 🚀 Starting stream: {start_date} to {end_date}")
    
    request_data = {
        "strategy_id": strategy_id,
        "start_date": start_date,
        "end_date": end_date,
        "mode": "backtesting",
        "include_diagnostics": True
    }
    
    try:
        # Start streaming request
        response = requests.post(
            f"{API_BASE_URL}/api/v1/backtest/stream",
            json=request_data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=3600  # 1 hour timeout
        )
        
        if response.status_code != 200:
            print(f"[Session {session_id}] ❌ Error: {response.status_code}")
            with stats_lock:
                global_stats[session_id]['status'] = 'failed'
            return
        
        # Track current day for file storage
        current_day = None
        current_day_data = {
            'date': None,
            'transactions': [],
            'summary': None
        }
        
        bytes_received = 0
        transaction_count = 0
        
        # Process stream line by line
        for line in response.iter_lines():
            if not line:
                continue
            
            bytes_received += len(line)
            
            # Parse JSON event
            event = json.loads(line.decode('utf-8'))
            event_type = event.get('type')
            
            if event_type == 'metadata':
                # Save metadata
                with open(session_dir / 'metadata.json', 'w') as f:
                    json.dump(event['data'], f, indent=2)
                print(f"[Session {session_id}] 📊 Metadata: {event['data']['total_days']} days to process")
            
            elif event_type == 'day_start':
                # Save previous day's data if exists
                if current_day_data['date']:
                    day_file = session_dir / f"{current_day_data['date']}.json"
                    with open(day_file, 'w') as f:
                        json.dump(current_day_data, f, indent=2)
                    
                    file_size = day_file.stat().st_size
                    print(f"[Session {session_id}] 💾 Saved {current_day_data['date']}: "
                          f"{len(current_day_data['transactions'])} txns, {format_size(file_size)}")
                
                # Start new day
                current_day = event['date']
                current_day_data = {
                    'date': current_day,
                    'day_number': event['day_number'],
                    'total_days': event['total_days'],
                    'transactions': [],
                    'summary': None
                }
                
                with stats_lock:
                    global_stats[session_id]['days_processed'] = event['day_number']
            
            elif event_type == 'transaction':
                # Add transaction to current day
                current_day_data['transactions'].append(event['data'])
                transaction_count += 1
                
                with stats_lock:
                    global_stats[session_id]['transactions'] = transaction_count
                    global_stats[session_id]['total_pnl'] += event['data'].get('pnl', 0)
            
            elif event_type == 'day_summary':
                # Add summary to current day
                current_day_data['summary'] = event['summary']
            
            elif event_type == 'complete':
                # Save last day's data
                if current_day_data['date']:
                    day_file = session_dir / f"{current_day_data['date']}.json"
                    with open(day_file, 'w') as f:
                        json.dump(current_day_data, f, indent=2)
                    print(f"[Session {session_id}] 💾 Saved {current_day_data['date']}: "
                          f"{len(current_day_data['transactions'])} txns")
                
                # Save overall summary
                with open(session_dir / 'overall_summary.json', 'w') as f:
                    json.dump(event['overall_summary'], f, indent=2)
                
                print(f"\n[Session {session_id}] ✅ COMPLETED!")
                print(f"[Session {session_id}] 📊 Overall Summary:")
                overall = event['overall_summary']
                print(f"   Total Days: {overall['days_completed']}")
                print(f"   Total Transactions: {overall['total_positions']}")
                print(f"   Total P&L: ₹{overall['total_pnl']:.2f}")
                print(f"   Win Rate: {overall['overall_win_rate']:.2f}%")
                print(f"   Data Received: {format_size(bytes_received)}")
                
                with stats_lock:
                    global_stats[session_id]['status'] = 'completed'
                    global_stats[session_id]['data_received_kb'] = bytes_received / 1024
                    global_stats[session_id]['end_time'] = datetime.now()
                
                break
            
            elif event_type in ['error', 'fatal_error', 'day_error']:
                print(f"[Session {session_id}] ❌ Error: {event.get('message', event.get('error'))}")
                if event_type == 'fatal_error':
                    with stats_lock:
                        global_stats[session_id]['status'] = 'failed'
                    break
    
    except Exception as e:
        print(f"[Session {session_id}] ❌ Exception: {e}")
        with stats_lock:
            global_stats[session_id]['status'] = 'failed'


def print_live_stats():
    """Print live statistics while sessions are running"""
    while True:
        time.sleep(5)  # Update every 5 seconds
        
        with stats_lock:
            active_sessions = sum(1 for s in global_stats.values() if s['status'] == 'running')
            if active_sessions == 0:
                break
            
            print("\n" + "="*80)
            print("📊 LIVE STATISTICS (All Sessions)")
            print("="*80)
            
            for session_id in sorted(global_stats.keys()):
                stats = global_stats[session_id]
                status_icon = {
                    'pending': '⏳',
                    'running': '🔄',
                    'completed': '✅',
                    'failed': '❌'
                }.get(stats['status'], '❓')
                
                elapsed = ''
                if stats['start_time']:
                    elapsed_sec = (datetime.now() - stats['start_time']).total_seconds()
                    elapsed = f"{elapsed_sec:.0f}s"
                
                print(f"Session {session_id} {status_icon}: "
                      f"Days: {stats['days_processed']} | "
                      f"Txns: {stats['transactions']} | "
                      f"P&L: ₹{stats['total_pnl']:.2f} | "
                      f"Data: {format_size(stats['data_received_kb']*1024)} | "
                      f"Time: {elapsed}")
            
            print("="*80)


def main():
    """Main test runner"""
    print("="*80)
    print("🧪 STREAMING API PARALLEL TEST")
    print("="*80)
    print(f"Date Range: February 2024 to December 2024")
    print(f"Strategy: 5708424d-5962-4629-978c-05b3a174e104")
    print(f"Parallel Sessions: 5")
    print(f"Output Directory: {OUTPUT_DIR.absolute()}")
    print("="*80)
    
    # Clean output directory
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    
    print("\n⚠️  This will run 5 concurrent backtests from Feb-Dec 2024.")
    print("⚠️  Each backtest will process ~230 days (~10 months)")
    print("⚠️  Total compute: ~1150 days across all sessions")
    print("⚠️  Expected time: 30-60 minutes depending on your machine")
    print("⚠️  Expected data: 5-20 MB per session (25-100 MB total)")
    
    response = input("\n❓ Proceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Check if API is running
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"\n❌ API server not responding properly")
            return
    except Exception as e:
        print(f"\n❌ Cannot connect to API server at {API_BASE_URL}")
        print(f"   Error: {e}")
        print(f"\n💡 Start the server first:")
        print(f"   python backtest_api_server.py")
        return
    
    print(f"\n✅ API server is running")
    
    # Define 5 parallel sessions with different date ranges
    strategy_id = "5708424d-5962-4629-978c-05b3a174e104"
    
    # Split Feb-Dec into 5 overlapping ranges to truly test parallel load
    sessions = [
        (1, strategy_id, "2024-02-01", "2024-04-30"),  # Feb-Apr
        (2, strategy_id, "2024-05-01", "2024-07-31"),  # May-Jul
        (3, strategy_id, "2024-08-01", "2024-10-31"),  # Aug-Oct
        (4, strategy_id, "2024-11-01", "2024-12-31"),  # Nov-Dec
        (5, strategy_id, "2024-02-01", "2024-12-31"),  # Full range (stress test)
    ]
    
    print(f"\n🚀 Starting 5 parallel sessions...")
    print(f"   Session 1: Feb-Apr (3 months)")
    print(f"   Session 2: May-Jul (3 months)")
    print(f"   Session 3: Aug-Oct (3 months)")
    print(f"   Session 4: Nov-Dec (2 months)")
    print(f"   Session 5: Feb-Dec (11 months) - Full stress test")
    
    # Start threads
    threads = []
    start_time = datetime.now()
    
    for session_id, strat_id, start_date, end_date in sessions:
        thread = threading.Thread(
            target=consume_stream_and_save,
            args=(session_id, strat_id, start_date, end_date)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Stagger starts slightly
    
    # Start stats monitoring thread
    stats_thread = threading.Thread(target=print_live_stats)
    stats_thread.daemon = True
    stats_thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    # Final statistics
    print("\n" + "="*80)
    print("🏁 FINAL RESULTS")
    print("="*80)
    
    total_transactions = 0
    total_data_kb = 0
    total_pnl = 0
    completed = 0
    failed = 0
    
    with stats_lock:
        for session_id in sorted(global_stats.keys()):
            stats = global_stats[session_id]
            total_transactions += stats['transactions']
            total_data_kb += stats['data_received_kb']
            total_pnl += stats['total_pnl']
            
            if stats['status'] == 'completed':
                completed += 1
            elif stats['status'] == 'failed':
                failed += 1
            
            duration = 0
            if stats['start_time'] and stats['end_time']:
                duration = (stats['end_time'] - stats['start_time']).total_seconds()
            
            status_icon = {
                'completed': '✅',
                'failed': '❌',
                'running': '🔄',
                'pending': '⏳'
            }.get(stats['status'], '❓')
            
            print(f"\nSession {session_id} {status_icon}:")
            print(f"   Status: {stats['status']}")
            print(f"   Days Processed: {stats['days_processed']}")
            print(f"   Transactions: {stats['transactions']}")
            print(f"   Total P&L: ₹{stats['total_pnl']:.2f}")
            print(f"   Data Received: {format_size(stats['data_received_kb']*1024)}")
            print(f"   Duration: {duration:.0f}s ({duration/60:.1f}m)")
    
    print("\n" + "="*80)
    print("📊 AGGREGATE STATISTICS")
    print("="*80)
    print(f"Total Duration: {total_duration:.0f}s ({total_duration/60:.1f}m)")
    print(f"Sessions Completed: {completed}/5")
    print(f"Sessions Failed: {failed}/5")
    print(f"Total Transactions: {total_transactions:,}")
    print(f"Total Data Transferred: {format_size(total_data_kb*1024)}")
    print(f"Total P&L (All Sessions): ₹{total_pnl:.2f}")
    print(f"Average Data Per Session: {format_size((total_data_kb/5)*1024)}")
    print(f"Output Directory: {OUTPUT_DIR.absolute()}")
    print("="*80)
    
    # List generated files
    print("\n📁 Generated Files:")
    for session_id in range(1, 6):
        session_dir = OUTPUT_DIR / f"session_{session_id}"
        if session_dir.exists():
            files = list(session_dir.glob('*.json'))
            total_size = sum(f.stat().st_size for f in files)
            print(f"   Session {session_id}: {len(files)} files, {format_size(total_size)}")
    
    print("\n" + "="*80)
    print("✅ Test completed!")
    print("="*80)


if __name__ == "__main__":
    main()
