"""
Test script for backtesting API endpoint
"""
import requests
import json
import time

# API endpoint
API_URL = "http://localhost:8000/api/v1/backtest/start"

# Test payload
payload = {
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "end_date": "2024-10-29",
    "initial_capital": 100000,
    "slippage_percentage": 0.0005,
    "commission_percentage": 0.001,
    "strategy_scale": 2.0  # Test with 2x scaling
}

print("=" * 80)
print("TESTING BACKTESTING API")
print("=" * 80)
print(f"\nEndpoint: {API_URL}")
print(f"\nPayload:")
print(json.dumps(payload, indent=2))
print("\n" + "=" * 80)

try:
    # Send POST request
    print("\n🚀 Sending request...")
    response = requests.post(API_URL, json=payload, timeout=300)
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Request successful!")
        result = response.json()
        print(f"\nResponse:")
        print(json.dumps(result, indent=2))
        
        # Check if we got a backtest_id
        if 'backtest_id' in result:
            print(f"\n✅ Backtest ID: {result['backtest_id']}")
            print(f"📊 Total Days: {result.get('total_days', 'N/A')}")
            print(f"🔗 Stream URL: {result.get('stream_url', 'N/A')}")
    else:
        print(f"❌ Request failed!")
        print(f"\nResponse:")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: API server is not running!")
    print("   Start the server with: python backtest_api_server.py")
except requests.exceptions.Timeout:
    print("\n❌ Request timed out after 5 minutes")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
