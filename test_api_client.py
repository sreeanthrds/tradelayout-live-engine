"""
Test client for Backtest API
Demonstrates how to call the API from UI or other applications
"""

import requests
import json
from datetime import datetime

# API Base URL
API_BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    print("="*80)
    print("Testing Health Check")
    print("="*80)
    
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_single_day_backtest():
    """Test single day backtest"""
    print("="*80)
    print("Testing Single Day Backtest")
    print("="*80)
    
    request_data = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "mode": "backtesting",
        "include_diagnostics": True
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("\nSending request...")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/backtest",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if data['success']:
            result = data['data']
            print(f"\n✅ Backtest completed successfully!")
            print(f"Strategy ID: {result['strategy_id']}")
            print(f"Date Range: {result['date_range']['start']} to {result['date_range']['end']}")
            print(f"Total Days: {result['metadata']['total_days']}")
            
            # Show summary for each day
            for day_result in result['daily_results']:
                print(f"\n📅 Date: {day_result['date']}")
                print(f"   Positions: {day_result['summary']['total_positions']}")
                print(f"   P&L: ₹{day_result['summary']['total_pnl']:.2f}")
                print(f"   Win Rate: {day_result['summary']['win_rate']:.2f}%")
                
                # Show first transaction's diagnostic text
                if day_result['positions']:
                    first_pos = day_result['positions'][0]
                    print(f"\n   Sample Diagnostic Text (Transaction #1):")
                    print("   " + "─"*76)
                    for line in first_pos.get('diagnostic_text', '').split('\n')[:20]:
                        print(f"   {line}")
                    print("   ...")
            
            # Show overall summary
            print(f"\n📊 Overall Summary:")
            overall = result['overall_summary']
            print(f"   Total Positions: {overall['total_positions']}")
            print(f"   Total P&L: ₹{overall['total_pnl']:.2f}")
            print(f"   Win Rate: {overall['overall_win_rate']:.2f}%")
            print(f"   Largest Win: ₹{overall['largest_win']:.2f}")
            print(f"   Largest Loss: ₹{overall['largest_loss']:.2f}")
            
            # Save full response to file
            with open('api_response_sample.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✅ Full response saved to: api_response_sample.json")
        else:
            print(f"❌ Error: {data.get('error')}")
    else:
        print(f"❌ Request failed: {response.text}")
    
    print()

def test_multi_day_backtest():
    """Test multi-day backtest"""
    print("="*80)
    print("Testing Multi-Day Backtest (3 days)")
    print("="*80)
    
    request_data = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "end_date": "2024-10-31",
        "mode": "backtesting",
        "include_diagnostics": False  # Exclude diagnostics for smaller response
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("\nSending request...")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/backtest",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if data['success']:
            result = data['data']
            print(f"\n✅ Multi-day backtest completed!")
            print(f"Days tested: {result['metadata']['total_days']}")
            
            for day_result in result['daily_results']:
                print(f"\n📅 {day_result['date']}: {day_result['summary']['total_positions']} positions, P&L: ₹{day_result['summary']['total_pnl']:.2f}")
            
            print(f"\n📊 Overall: ₹{result['overall_summary']['total_pnl']:.2f} across {result['overall_summary']['total_positions']} positions")
        else:
            print(f"❌ Error: {data.get('error')}")
    else:
        print(f"❌ Request failed: {response.text}")
    
    print()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TradeLayout Backtest API - Test Client")
    print("="*80 + "\n")
    
    print("Make sure the API server is running:")
    print("  python backtest_api_server.py")
    print()
    
    input("Press Enter to start tests...")
    print()
    
    # Run tests
    test_health_check()
    test_single_day_backtest()
    test_multi_day_backtest()
    
    print("="*80)
    print("✅ All tests completed!")
    print("="*80)
