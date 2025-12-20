"""
Quick streaming test - single month to validate the system
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

API_BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path("backtest_results_test")


def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def test_single_month():
    """Test streaming API with a single month"""
    print("="*80)
    print("🧪 Quick Streaming Test - Single Month (October 2024)")
    print("="*80)
    
    # Check if API is running
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"\n❌ API server not responding properly")
            return
    except Exception as e:
        print(f"\n❌ Cannot connect to API server at {API_BASE_URL}")
        print(f"   Error: {e}")
        return
    
    print(f"✅ API server is running")
    
    # Clean output directory
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    
    print(f"\n📤 Starting backtest: October 2024")
    print(f"   Output: {OUTPUT_DIR.absolute()}")
    
    request_data = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-01",
        "end_date": "2024-10-31",
        "mode": "backtesting",
        "include_diagnostics": True
    }
    
    start_time = datetime.now()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/backtest/stream",
            json=request_data,
            stream=True,
            timeout=600
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        # Track data
        current_day_data = {'date': None, 'transactions': [], 'summary': None}
        bytes_received = 0
        transaction_count = 0
        days_processed = 0
        
        print(f"\n⏳ Streaming results...\n")
        
        # Process stream
        for line in response.iter_lines():
            if not line:
                continue
            
            bytes_received += len(line)
            event = json.loads(line.decode('utf-8'))
            event_type = event.get('type')
            
            if event_type == 'metadata':
                with open(OUTPUT_DIR / 'metadata.json', 'w') as f:
                    json.dump(event['data'], f, indent=2)
                print(f"📊 Metadata: {event['data']['total_days']} days to process")
            
            elif event_type == 'day_start':
                # Save previous day
                if current_day_data['date']:
                    day_file = OUTPUT_DIR / f"{current_day_data['date']}.json"
                    with open(day_file, 'w') as f:
                        json.dump(current_day_data, f, indent=2)
                    file_size = day_file.stat().st_size
                    print(f"💾 Saved {current_day_data['date']}: "
                          f"{len(current_day_data['transactions'])} txns, {format_size(file_size)}")
                
                # Start new day
                current_day_data = {
                    'date': event['date'],
                    'day_number': event['day_number'],
                    'total_days': event['total_days'],
                    'transactions': [],
                    'summary': None
                }
                days_processed = event['day_number']
            
            elif event_type == 'transaction':
                current_day_data['transactions'].append(event['data'])
                transaction_count += 1
                
                # Print progress every 10 transactions
                if transaction_count % 10 == 0:
                    pnl = event['data'].get('pnl', 0)
                    pnl_icon = '🟢' if pnl >= 0 else '🔴'
                    print(f"   Txn #{transaction_count}: "
                          f"{event['data']['strike']} {event['data']['option_type']} | "
                          f"{pnl_icon} ₹{pnl:.2f}")
            
            elif event_type == 'day_summary':
                current_day_data['summary'] = event['summary']
            
            elif event_type == 'complete':
                # Save last day
                if current_day_data['date']:
                    day_file = OUTPUT_DIR / f"{current_day_data['date']}.json"
                    with open(day_file, 'w') as f:
                        json.dump(current_day_data, f, indent=2)
                
                # Save overall summary
                with open(OUTPUT_DIR / 'overall_summary.json', 'w') as f:
                    json.dump(event['overall_summary'], f, indent=2)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"\n{'='*80}")
                print(f"✅ BACKTEST COMPLETE!")
                print(f"{'='*80}")
                
                overall = event['overall_summary']
                print(f"\n📊 Results:")
                print(f"   Days Processed: {overall['days_completed']}")
                print(f"   Total Transactions: {overall['total_positions']}")
                print(f"   Total P&L: ₹{overall['total_pnl']:.2f}")
                print(f"   Win Rate: {overall['overall_win_rate']:.2f}%")
                print(f"   Winning Trades: {overall['total_winning_trades']}")
                print(f"   Losing Trades: {overall['total_losing_trades']}")
                print(f"   Largest Win: ₹{overall['largest_win']:.2f}")
                print(f"   Largest Loss: ₹{overall['largest_loss']:.2f}")
                
                print(f"\n📈 Performance:")
                print(f"   Duration: {duration:.0f}s ({duration/60:.1f}m)")
                print(f"   Data Received: {format_size(bytes_received)}")
                print(f"   Average: {format_size(bytes_received/duration)}/s")
                
                # List generated files
                files = list(OUTPUT_DIR.glob('*.json'))
                total_size = sum(f.stat().st_size for f in files)
                print(f"\n📁 Generated Files:")
                print(f"   Count: {len(files)} files")
                print(f"   Total Size: {format_size(total_size)}")
                print(f"   Location: {OUTPUT_DIR.absolute()}")
                
                # Show sample file
                if files:
                    sample_file = [f for f in files if f.name.startswith('2024-10')][0]
                    print(f"\n📄 Sample Day File ({sample_file.name}):")
                    with open(sample_file) as f:
                        sample_data = json.load(f)
                        print(f"   Date: {sample_data['date']}")
                        print(f"   Transactions: {len(sample_data['transactions'])}")
                        if sample_data['summary']:
                            print(f"   Day P&L: ₹{sample_data['summary']['total_pnl']:.2f}")
                
                print(f"\n{'='*80}")
                break
            
            elif event_type in ['error', 'fatal_error']:
                print(f"❌ Error: {event.get('message')}")
                break
    
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_single_month()
