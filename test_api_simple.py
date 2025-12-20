"""
Simple API Test Script
Tests all backtest API endpoints step-by-step
"""
import requests
import time
import json

# Configuration
API_BASE = "http://localhost:8000"
USER_ID = "user_123"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"

def print_header(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_1_check_server():
    """Test 1: Check if server is running"""
    print_header("TEST 1: Check Server Status")
    
    try:
        response = requests.get(f"{API_BASE}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is running")
            print(f"   Service: {data['service']}")
            print(f"   Version: {data['version']}")
            print(f"   Status: {data['status']}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {API_BASE}")
        print(f"\n💡 Start the server first:")
        print(f"   python backtest_file_api_server.py")
        return False


def test_2_start_backtest():
    """Test 2: Start a backtest"""
    print_header("TEST 2: Start Backtest")
    
    # Use a short date range for quick testing
    payload = {
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "start_date": "2024-10-01",
        "end_date": "2024-10-03"  # Just 3 days for quick test
    }
    
    print(f"📤 Request:")
    print(f"   User ID: {payload['user_id']}")
    print(f"   Strategy ID: {payload['strategy_id']}")
    print(f"   Date Range: {payload['start_date']} to {payload['end_date']}")
    
    response = requests.post(f"{API_BASE}/api/v1/backtest/run", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Backtest started successfully!")
        print(f"   Job ID: {data['job_id']}")
        print(f"   Status: {data['status']}")
        print(f"   Message: {data['message']}")
        return data['job_id']
    else:
        print(f"\n❌ Failed to start backtest")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def test_3_monitor_progress(job_id):
    """Test 3: Monitor backtest progress"""
    print_header("TEST 3: Monitor Progress")
    
    print(f"Job ID: {job_id}")
    print(f"\nMonitoring progress (updates every 2 seconds)...")
    print(f"-" * 80)
    
    while True:
        response = requests.get(f"{API_BASE}/api/v1/backtest/status/{job_id}")
        
        if response.status_code != 200:
            print(f"❌ Failed to check status: {response.status_code}")
            break
        
        data = response.json()
        status = data['status']
        
        # Display progress
        if data.get('progress'):
            progress = data['progress']
            print(f"[{status.upper():10}] {progress['current_date']} | "
                  f"{progress['completed_days']}/{progress['total_days']} days | "
                  f"{progress['percentage']:.1f}%")
        else:
            print(f"[{status.upper():10}] Waiting to start...")
        
        # Check if completed or failed
        if status == 'completed':
            print(f"\n✅ Backtest completed successfully!")
            if data.get('started_at'):
                print(f"   Started: {data['started_at']}")
            break
        elif status == 'failed':
            print(f"\n❌ Backtest failed!")
            print(f"   Error: {data.get('error', 'Unknown error')}")
            break
        
        # Wait before next check
        time.sleep(2)
    
    print(f"-" * 80)


def test_4_get_metadata():
    """Test 4: Get backtest metadata"""
    print_header("TEST 4: Get Backtest Metadata")
    
    response = requests.get(f"{API_BASE}/api/v1/backtest/metadata/{USER_ID}/{STRATEGY_ID}")
    
    if response.status_code != 200:
        print(f"❌ Failed to get metadata: {response.status_code}")
        print(f"   {response.text}")
        return None
    
    data = response.json()
    
    print(f"✅ Metadata retrieved successfully!\n")
    print(f"Strategy Information:")
    print(f"   Strategy ID: {data['strategy_id']}")
    print(f"   Date Range: {data['start_date']} to {data['end_date']}")
    print(f"   Total Days: {data['total_days']}")
    print(f"   Status: {data['status']}")
    print(f"   Created: {data['created_at']}")
    print(f"   Expires: {data['expires_at']}")
    
    print(f"\nOverall Summary:")
    summary = data['overall_summary']
    print(f"   Total Positions: {summary['total_positions']}")
    print(f"   Total P&L: ₹{summary['total_pnl']:,.2f}")
    print(f"   Win Rate: {summary['win_rate']:.2f}%")
    print(f"   Winning Trades: {summary['total_winning_trades']}")
    print(f"   Losing Trades: {summary['total_losing_trades']}")
    
    print(f"\nDaily Breakdown:")
    print(f"   {'Date':<15} {'Positions':<10} {'P&L (₹)':<15} {'File Size':<15}")
    print(f"   {'-'*60}")
    
    for day in data['daily_summaries']:
        pnl_sign = "+" if day['pnl'] >= 0 else ""
        print(f"   {day['date']:<15} {day['positions']:<10} "
              f"{pnl_sign}{day['pnl']:>12,.2f}   {day['file_size_kb']:>8.2f} KB")
    
    return data['daily_summaries']


def test_5_get_day_data(date_str):
    """Test 5: Get data for a specific day"""
    print_header(f"TEST 5: Get Day Data ({date_str})")
    
    response = requests.get(f"{API_BASE}/api/v1/backtest/day/{USER_ID}/{STRATEGY_ID}/{date_str}")
    
    if response.status_code != 200:
        print(f"❌ Failed to get day data: {response.status_code}")
        print(f"   {response.text}")
        return None
    
    data = response.json()
    
    # Check compression
    content_length = len(response.content)
    content_encoding = response.headers.get('Content-Encoding', 'none')
    
    print(f"✅ Day data retrieved successfully!\n")
    print(f"Transfer Info:")
    print(f"   Encoding: {content_encoding}")
    print(f"   Transfer Size: {content_length / 1024:.2f} KB")
    print(f"   Decompressed Size: {len(json.dumps(data)) / 1024:.2f} KB")
    
    print(f"\nDay Summary ({date_str}):")
    summary = data['summary']
    print(f"   Total Positions: {summary['total_positions']}")
    print(f"   Closed Positions: {summary['closed_positions']}")
    print(f"   Total P&L: ₹{summary['total_pnl']:,.2f}")
    print(f"   Win Rate: {summary['win_rate']:.2f}%")
    print(f"   Winning Trades: {summary['winning_trades']}")
    print(f"   Losing Trades: {summary['losing_trades']}")
    
    print(f"\nPositions Table:")
    print(f"   {'#':<5} {'Pos ID':<12} {'Num':<5} {'Strike':<8} {'Type':<4} "
          f"{'Entry ₹':<10} {'Exit ₹':<10} {'P&L ₹':<12} {'Status':<8}")
    print(f"   {'-'*85}")
    
    for i, pos in enumerate(data['positions'][:10], 1):  # Show first 10
        pnl = pos.get('pnl', 0)
        pnl_sign = "+" if pnl >= 0 else ""
        exit_price = pos.get('exit_price', 0)
        
        print(f"   {i:<5} {pos['position_id'][:12]:<12} {pos['position_num']:<5} "
              f"{pos['strike']:<8} {pos['option_type']:<4} "
              f"{pos['entry_price']:>9.2f} {exit_price:>9.2f} "
              f"{pnl_sign}{pnl:>10.2f}   {pos['status']:<8}")
    
    if len(data['positions']) > 10:
        print(f"   ... and {len(data['positions']) - 10} more positions")
    
    # Show diagnostic data sample
    if data['positions'] and data['positions'][0].get('diagnostic_data'):
        print(f"\nDiagnostic Data (First Position):")
        diag = data['positions'][0]['diagnostic_data']
        
        print(f"   Conditions Evaluated: {len(diag.get('conditions_evaluated', []))}")
        
        if diag.get('conditions_evaluated'):
            print(f"\n   Sample Conditions:")
            for i, cond in enumerate(diag['conditions_evaluated'][:3], 1):
                result_icon = "✅" if cond.get('result') else "❌"
                print(f"      {i}. {result_icon} {cond.get('lhs_value')} "
                      f"{cond.get('operator')} {cond.get('rhs_value')} "
                      f"[{cond.get('condition_type')}]")
        
        if diag.get('candle_data'):
            print(f"\n   Candle Data Available: {list(diag['candle_data'].keys())}")
    
    return data


def test_6_position_details(day_data):
    """Test 6: Show detailed position analysis"""
    print_header("TEST 6: Detailed Position Analysis")
    
    if not day_data or not day_data.get('positions'):
        print("No positions available for analysis")
        return
    
    # Pick first position
    pos = day_data['positions'][0]
    
    print(f"Position Details:")
    print(f"   Position ID: {pos['position_id']}")
    print(f"   Position Number: {pos['position_num']}")
    print(f"   Re-Entry Number: {pos['re_entry_num']}")
    print(f"   Symbol: {pos['symbol']}")
    print(f"   Strike: {pos['strike']} {pos['option_type']}")
    
    print(f"\nEntry:")
    print(f"   Time: {pos['entry_time']}")
    print(f"   Price: ₹{pos['entry_price']}")
    print(f"   NIFTY Spot: {pos['nifty_spot_at_entry']}")
    print(f"   Quantity: {pos['quantity']}")
    
    print(f"\nExit:")
    print(f"   Time: {pos.get('exit_time', 'N/A')}")
    print(f"   Price: ₹{pos.get('exit_price', 0)}")
    print(f"   NIFTY Spot: {pos.get('nifty_spot_at_exit', 0)}")
    print(f"   Reason: {pos.get('exit_reason', 'N/A')}")
    
    print(f"\nP&L:")
    pnl = pos.get('pnl', 0)
    pnl_sign = "+" if pnl >= 0 else ""
    print(f"   Amount: {pnl_sign}₹{pnl:,.2f}")
    
    # Show condition preview
    if pos.get('condition_preview'):
        print(f"\nEntry Condition:")
        print(f"   {pos['condition_preview']}")
    
    if pos.get('exit_condition_preview'):
        print(f"\nExit Condition:")
        print(f"   {pos['exit_condition_preview']}")
    
    # Show diagnostic breakdown
    if pos.get('diagnostic_data'):
        print(f"\nEntry Condition Breakdown:")
        diag = pos['diagnostic_data']
        for i, cond in enumerate(diag.get('conditions_evaluated', []), 1):
            result_icon = "✅ PASS" if cond.get('result') else "❌ FAIL"
            print(f"   {i}. {result_icon}")
            print(f"      LHS: {cond.get('lhs_value')} ({cond.get('lhs_expression', {}).get('type', 'N/A')})")
            print(f"      Operator: {cond.get('operator')}")
            print(f"      RHS: {cond.get('rhs_value')} ({cond.get('rhs_expression', {}).get('type', 'N/A')})")
            print(f"      Type: {cond.get('condition_type')}")
    
    # Show node variables
    if pos.get('node_variables'):
        print(f"\nNode Variables:")
        for key, value in pos['node_variables'].items():
            print(f"   {key}: {value}")


def test_7_cleanup():
    """Test 7: Optional - Clear data"""
    print_header("TEST 7: Cleanup (Optional)")
    
    print("This will delete all backtest data for this strategy.")
    choice = input("Do you want to clear the data? (yes/no): ").strip().lower()
    
    if choice != 'yes':
        print("Skipped cleanup")
        return
    
    response = requests.delete(f"{API_BASE}/api/v1/backtest/clear/{USER_ID}/{STRATEGY_ID}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Data cleared successfully!")
        print(f"   Deleted Files: {data['deleted_files']}")
        print(f"   Freed Space: {data['freed_space_mb']} MB")
    else:
        print(f"\n❌ Failed to clear data: {response.status_code}")
        print(f"   {response.text}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  📊 Backtest API Test Script")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"   API URL: {API_BASE}")
    print(f"   User ID: {USER_ID}")
    print(f"   Strategy ID: {STRATEGY_ID}")
    
    # Test 1: Check server
    if not test_1_check_server():
        return
    
    input("\n▶️  Press Enter to start backtest...")
    
    # Test 2: Start backtest
    job_id = test_2_start_backtest()
    if not job_id:
        return
    
    input("\n▶️  Press Enter to monitor progress...")
    
    # Test 3: Monitor progress
    test_3_monitor_progress(job_id)
    
    input("\n▶️  Press Enter to get metadata...")
    
    # Test 4: Get metadata
    daily_summaries = test_4_get_metadata()
    if not daily_summaries:
        return
    
    input("\n▶️  Press Enter to get day data...")
    
    # Test 5: Get first day data
    first_date = daily_summaries[0]['date']
    day_data = test_5_get_day_data(first_date)
    
    if day_data:
        input("\n▶️  Press Enter to see position details...")
        
        # Test 6: Show position details
        test_6_position_details(day_data)
    
    # Test 7: Optional cleanup
    input("\n▶️  Press Enter for cleanup options...")
    test_7_cleanup()
    
    print_header("✅ All Tests Completed!")
    print("\n💡 Next Steps:")
    print("   1. Check the files in: backtest_data/user_123/")
    print("   2. Open http://localhost:8000/docs for API documentation")
    print("   3. Build UI to consume these endpoints")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
