"""
Test Client for File-Based Backtest API
Demonstrates complete workflow
"""
import requests
import time
import json
from datetime import date

# Configuration
API_BASE_URL = "http://localhost:8000"
USER_ID = "user_123"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def test_run_backtest():
    """Test: Start a backtest"""
    print_section("1. Starting Backtest")
    
    payload = {
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "start_date": "2024-10-01",
        "end_date": "2024-10-05"  # 5 days for quick test
    }
    
    response = requests.post(f"{API_BASE_URL}/api/v1/backtest/run", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Backtest started successfully")
        print(f"   Job ID: {data['job_id']}")
        print(f"   Status: {data['status']}")
        return data['job_id']
    else:
        print(f"❌ Failed to start backtest: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_check_status(job_id):
    """Test: Check job status"""
    print_section("2. Checking Job Status")
    
    while True:
        response = requests.get(f"{API_BASE_URL}/api/v1/backtest/status/{job_id}")
        
        if response.status_code == 200:
            data = response.json()
            status = data['status']
            
            print(f"Status: {status}")
            
            if data.get('progress'):
                progress = data['progress']
                print(f"Progress: {progress['completed_days']}/{progress['total_days']} days ({progress['percentage']}%)")
                print(f"Current date: {progress['current_date']}")
            
            if status == 'completed':
                print(f"✅ Backtest completed!")
                break
            elif status == 'failed':
                print(f"❌ Backtest failed!")
                print(f"   Error: {data.get('error')}")
                break
            else:
                print(f"⏳ Waiting... (status: {status})")
                time.sleep(2)
        else:
            print(f"❌ Failed to check status: {response.status_code}")
            break


def test_get_metadata():
    """Test: Get backtest metadata"""
    print_section("3. Getting Backtest Metadata")
    
    response = requests.get(f"{API_BASE_URL}/api/v1/backtest/metadata/{USER_ID}/{STRATEGY_ID}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Metadata retrieved")
        print(f"\n   Strategy ID: {data['strategy_id']}")
        print(f"   Date Range: {data['start_date']} to {data['end_date']}")
        print(f"   Total Days: {data['total_days']}")
        print(f"   Status: {data['status']}")
        print(f"\n   Overall Summary:")
        summary = data['overall_summary']
        print(f"      Total Positions: {summary['total_positions']}")
        print(f"      Total P&L: ₹{summary['total_pnl']:,.2f}")
        print(f"      Win Rate: {summary['win_rate']:.2f}%")
        print(f"      Winning Trades: {summary['total_winning_trades']}")
        print(f"      Losing Trades: {summary['total_losing_trades']}")
        
        print(f"\n   Daily Summaries:")
        for day in data['daily_summaries']:
            print(f"      {day['date']}: {day['positions']} positions, P&L: ₹{day['pnl']:,.2f}, File: {day['file_size_kb']} KB")
        
        return data['daily_summaries']
    else:
        print(f"❌ Failed to get metadata: {response.status_code}")
        return []


def test_get_day_data(date_str):
    """Test: Get day data"""
    print_section(f"4. Getting Day Data for {date_str}")
    
    response = requests.get(f"{API_BASE_URL}/api/v1/backtest/day/{USER_ID}/{STRATEGY_ID}/{date_str}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Day data retrieved (auto-decompressed by browser)")
        
        # Check response headers for compression
        content_encoding = response.headers.get('Content-Encoding', 'none')
        content_length = len(response.content)
        print(f"   Transfer encoding: {content_encoding}")
        print(f"   Transfer size: {content_length / 1024:.2f} KB")
        
        print(f"\n   Date: {data['date']}")
        print(f"   Summary:")
        summary = data['summary']
        print(f"      Total Positions: {summary['total_positions']}")
        print(f"      Closed Positions: {summary['closed_positions']}")
        print(f"      Total P&L: ₹{summary['total_pnl']:,.2f}")
        print(f"      Win Rate: {summary['win_rate']:.2f}%")
        
        print(f"\n   Positions:")
        for i, pos in enumerate(data['positions'][:3], 1):  # Show first 3
            print(f"      {i}. Position {pos['position_id']} (#{pos['position_num']})")
            print(f"         Symbol: {pos['symbol']}")
            print(f"         Entry: ₹{pos['entry_price']} @ {pos['entry_time']}")
            print(f"         Exit: ₹{pos.get('exit_price', 'N/A')} @ {pos.get('exit_time', 'N/A')}")
            print(f"         P&L: ₹{pos.get('pnl', 0):,.2f}")
            print(f"         Status: {pos['status']}")
            print(f"         Has diagnostics: {bool(pos.get('diagnostic_data'))}")
        
        if len(data['positions']) > 3:
            print(f"      ... and {len(data['positions']) - 3} more positions")
        
        # Show diagnostic data structure for first position
        if data['positions'] and data['positions'][0].get('diagnostic_data'):
            print(f"\n   Diagnostic Data Structure (first position):")
            diag = data['positions'][0]['diagnostic_data']
            print(f"      Conditions evaluated: {len(diag.get('conditions_evaluated', []))}")
            if diag.get('conditions_evaluated'):
                cond = diag['conditions_evaluated'][0]
                print(f"      Sample condition:")
                print(f"         LHS: {cond.get('lhs_value')}")
                print(f"         Operator: {cond.get('operator')}")
                print(f"         RHS: {cond.get('rhs_value')}")
                print(f"         Result: {cond.get('result')}")
                print(f"         Type: {cond.get('condition_type')}")
        
        return data
    else:
        print(f"❌ Failed to get day data: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_clear_data():
    """Test: Clear strategy data"""
    print_section("5. Clearing Strategy Data (Optional)")
    
    response = input("\nDo you want to clear all data? (yes/no): ")
    if response.lower() != 'yes':
        print("Skipped clearing data")
        return
    
    response = requests.delete(f"{API_BASE_URL}/api/v1/backtest/clear/{USER_ID}/{STRATEGY_ID}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Data cleared successfully")
        print(f"   Deleted files: {data['deleted_files']}")
        print(f"   Freed space: {data['freed_space_mb']} MB")
    else:
        print(f"❌ Failed to clear data: {response.status_code}")


def main():
    """Run all tests"""
    print("="*80)
    print("  File-Based Backtest API Test Client")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  API URL: {API_BASE_URL}")
    print(f"  User ID: {USER_ID}")
    print(f"  Strategy ID: {STRATEGY_ID}")
    
    try:
        # Step 1: Start backtest
        job_id = test_run_backtest()
        if not job_id:
            return
        
        # Step 2: Monitor progress
        test_check_status(job_id)
        
        # Step 3: Get metadata
        daily_summaries = test_get_metadata()
        
        # Step 4: Get day data (first day)
        if daily_summaries:
            first_date = daily_summaries[0]['date']
            test_get_day_data(first_date)
        
        # Step 5: Optional cleanup
        test_clear_data()
        
        print_section("✅ All Tests Completed")
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to API server at {API_BASE_URL}")
        print(f"   Make sure the server is running: python backtest_file_api_server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
