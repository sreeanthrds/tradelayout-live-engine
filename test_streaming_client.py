"""
Test client for Streaming Backtest API
Demonstrates how to consume streaming backtest results in real-time
"""

import requests
import json
from datetime import datetime

# API Base URL
API_BASE_URL = "http://localhost:8000"

def test_streaming_backtest():
    """
    Test streaming backtest - processes results in real-time as they arrive
    Perfect for 1 year backtests!
    """
    print("="*80)
    print("🌊 Testing Streaming Backtest (Real-time Progressive Results)")
    print("="*80)
    
    request_data = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "end_date": "2024-10-31",  # Change to "2024-12-31" for longer test
        "mode": "backtesting",
        "include_diagnostics": True
    }
    
    print(f"\n📤 Request:")
    print(f"   Strategy: {request_data['strategy_id']}")
    print(f"   Date Range: {request_data['start_date']} to {request_data['end_date']}")
    print(f"   Diagnostics: {request_data['include_diagnostics']}")
    print(f"\n⏳ Streaming results (press Ctrl+C to stop)...\n")
    
    # Use streaming=True to get response line by line
    response = requests.post(
        f"{API_BASE_URL}/api/v1/backtest/stream",
        json=request_data,
        headers={"Content-Type": "application/json"},
        stream=True  # Enable streaming
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return
    
    # Process stream line by line
    current_day = None
    transaction_count = 0
    day_transaction_count = 0
    
    try:
        for line in response.iter_lines():
            if not line:
                continue
            
            # Parse JSON event
            event = json.loads(line.decode('utf-8'))
            event_type = event.get('type')
            
            if event_type == 'metadata':
                data = event['data']
                print(f"📊 Backtest Metadata:")
                print(f"   Total Days: {data['total_days']}")
                print(f"   Started: {data['started_at']}")
                print(f"   Diagnostics: {'Enabled' if data['include_diagnostics'] else 'Disabled'}")
                print()
            
            elif event_type == 'day_start':
                current_day = event['date']
                day_transaction_count = 0
                print(f"\n{'─'*80}")
                print(f"📅 Day {event['day_number']}/{event['total_days']}: {current_day}")
                print(f"{'─'*80}")
            
            elif event_type == 'transaction':
                transaction_count += 1
                day_transaction_count += 1
                pos = event['data']
                
                # Show transaction summary (compact format)
                pnl_icon = '🟢' if pos['pnl'] >= 0 else '🔴'
                status_icon = '✅' if pos['status'] == 'CLOSED' else '⏳'
                
                print(f"{status_icon} Txn #{transaction_count} (Pos #{pos['position_number']}, Day Txn #{day_transaction_count}): "
                      f"{pos['strike']} {pos['option_type']} | "
                      f"Entry: {pos['entry_timestamp']} @ ₹{pos['entry_price']:.2f} | "
                      f"Exit: {pos.get('exit_timestamp', 'N/A')} @ ₹{pos.get('exit_price', 0):.2f} | "
                      f"P&L: {pnl_icon} ₹{pos['pnl']:.2f}")
                
                # Optionally show diagnostic text (uncomment to see full details)
                # if 'diagnostic_text' in pos:
                #     print("\n" + pos['diagnostic_text'] + "\n")
            
            elif event_type == 'day_summary':
                summary = event['summary']
                pnl_icon = '🟢' if summary['total_pnl'] >= 0 else '🔴'
                print(f"\n📈 Day Summary:")
                print(f"   Transactions: {summary['total_positions']}")
                print(f"   P&L: {pnl_icon} ₹{summary['total_pnl']:.2f}")
                print(f"   Win Rate: {summary['win_rate']:.2f}%")
                print(f"   Wins: {summary['winning_trades']} | Losses: {summary['losing_trades']}")
            
            elif event_type == 'day_error':
                print(f"❌ Error on {event['date']}: {event['error']}")
            
            elif event_type == 'complete':
                overall = event['overall_summary']
                pnl_icon = '🟢' if overall['total_pnl'] >= 0 else '🔴'
                
                print(f"\n{'='*80}")
                print(f"✅ BACKTEST COMPLETE!")
                print(f"{'='*80}")
                print(f"\n📊 Overall Summary:")
                print(f"   Days Completed: {overall['days_completed']}")
                print(f"   Total Transactions: {overall['total_positions']}")
                print(f"   Total P&L: {pnl_icon} ₹{overall['total_pnl']:.2f}")
                print(f"   Win Rate: {overall['overall_win_rate']:.2f}%")
                print(f"   Wins: {overall['total_winning_trades']} | Losses: {overall['total_losing_trades']}")
                print(f"   Largest Win: 🟢 ₹{overall['largest_win']:.2f}")
                print(f"   Largest Loss: 🔴 ₹{overall['largest_loss']:.2f}")
                print(f"\n   Completed At: {event['completed_at']}")
                print(f"{'='*80}")
            
            elif event_type == 'error' or event_type == 'fatal_error':
                print(f"❌ ERROR: {event.get('message')}")
                if 'traceback' in event:
                    print(f"\nTraceback:\n{event['traceback']}")
                break
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Stream interrupted by user")
    except Exception as e:
        print(f"\n❌ Client error: {e}")

def test_streaming_with_ui_simulation():
    """
    Simulate UI behavior - collect data progressively and update display
    """
    print("\n" + "="*80)
    print("🖥️  Simulating UI Progressive Update")
    print("="*80)
    
    request_data = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "end_date": "2024-10-29",
        "mode": "backtesting",
        "include_diagnostics": False  # Faster without diagnostics
    }
    
    print(f"\n📤 Fetching: {request_data['start_date']}")
    print(f"⏳ Processing stream...\n")
    
    # Simulate UI state
    transactions = []
    daily_summaries = {}
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/backtest/stream",
        json=request_data,
        stream=True
    )
    
    for line in response.iter_lines():
        if not line:
            continue
        
        event = json.loads(line.decode('utf-8'))
        event_type = event.get('type')
        
        if event_type == 'transaction':
            # Add to UI transaction list
            transactions.append(event['data'])
            
            # Update UI display (simulated)
            print(f"📝 UI Updated: {len(transactions)} transactions loaded", end='\r')
        
        elif event_type == 'day_summary':
            # Store day summary
            daily_summaries[event['date']] = event['summary']
        
        elif event_type == 'complete':
            print(f"\n\n✅ UI Ready: {len(transactions)} transactions loaded!")
            print(f"\n🎨 Rendering UI components:")
            print(f"   - Transactions Table: {len(transactions)} rows")
            print(f"   - Daily Charts: {len(daily_summaries)} days")
            print(f"   - Overall Summary: Win Rate {event['overall_summary']['overall_win_rate']:.2f}%")
            
            # Sample: Show first 3 transactions
            print(f"\n📋 Sample Transactions (showing first 3):")
            for idx, txn in enumerate(transactions[:3], 1):
                print(f"   {idx}. {txn['strike']} {txn['option_type']} | "
                      f"P&L: ₹{txn['pnl']:.2f}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TradeLayout Streaming Backtest API - Test Client")
    print("="*80 + "\n")
    
    print("Make sure the API server is running:")
    print("  python backtest_api_server.py")
    print()
    
    input("Press Enter to start streaming test...")
    print()
    
    # Test 1: Real-time streaming display
    test_streaming_backtest()
    
    print("\n")
    input("Press Enter for UI simulation test...")
    print()
    
    # Test 2: UI simulation
    test_streaming_with_ui_simulation()
    
    print("\n" + "="*80)
    print("✅ All streaming tests completed!")
    print("="*80)
