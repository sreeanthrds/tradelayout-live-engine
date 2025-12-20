#!/usr/bin/env python3
"""
Test SSE-based backtest API
"""
import requests
import json
import sys

def test_start_backtest():
    """Test the /api/v1/backtest/start endpoint"""
    print("="*80)
    print("Testing POST /api/v1/backtest/start")
    print("="*80)
    
    url = "http://localhost:8000/api/v1/backtest/start"
    payload = {
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-24",
        "end_date": "2024-10-26",  # Just 3 days for quick test
        "initial_capital": 100000
    }
    
    print(f"\nRequest: POST {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload)
    
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        result = response.json()
        backtest_id = result['backtest_id']
        print(f"\n✅ Backtest started successfully!")
        print(f"Backtest ID: {backtest_id}")
        print(f"Stream URL: {result['stream_url']}")
        return backtest_id
    else:
        print(f"\n❌ Failed to start backtest")
        return None

def test_stream_backtest(backtest_id):
    """Test the SSE stream endpoint"""
    print("\n" + "="*80)
    print("Testing GET /api/v1/backtest/{id}/stream (SSE)")
    print("="*80)
    
    url = f"http://localhost:8000/api/v1/backtest/{backtest_id}/stream"
    print(f"\nConnecting to: {url}")
    print("Note: This will stream events in real-time...\n")
    
    # Use requests with stream=True for SSE
    response = requests.get(url, stream=True, timeout=120)
    
    if response.status_code == 200:
        print("✅ Connected to SSE stream\n")
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # SSE format: "event: day_started\ndata: {...}\n\n"
                if line_str.startswith('event:'):
                    event_type = line_str.split(':', 1)[1].strip()
                    print(f"\n📡 Event: {event_type}")
                
                elif line_str.startswith('data:'):
                    data_str = line_str.split(':', 1)[1].strip()
                    try:
                        data = json.loads(data_str)
                        print(f"   Data: {json.dumps(data, indent=6)}")
                    except json.JSONDecodeError:
                        print(f"   Data: {data_str}")
                
                # Check for completion
                if 'backtest_completed' in line_str:
                    print("\n✅ Backtest completed!")
                    break
        
        return True
    else:
        print(f"❌ Failed to connect to stream: {response.status_code}")
        return False

def test_download_day(backtest_id, date):
    """Test downloading a specific day's data"""
    print("\n" + "="*80)
    print(f"Testing GET /api/v1/backtest/{{id}}/day/{date}")
    print("="*80)
    
    url = f"http://localhost:8000/api/v1/backtest/{backtest_id}/day/{date}"
    print(f"\nRequest: GET {url}")
    
    response = requests.get(url)
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        # Save to file
        filename = f"backtest_{date}.zip"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Downloaded: {filename} ({len(response.content)} bytes)")
        
        # Show what's in the ZIP
        import zipfile
        with zipfile.ZipFile(filename, 'r') as zf:
            print(f"\nZIP Contents:")
            for info in zf.infolist():
                print(f"   - {info.filename} ({info.file_size} bytes, compressed: {info.compress_size} bytes)")
        
        return True
    else:
        print(f"❌ Failed to download: {response.text}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 SSE API Test Suite")
    print("="*80)
    print("\n⚠️  Make sure the server is running: python backtest_api_server.py")
    input("Press Enter to continue...")
    
    # Test 1: Start backtest
    backtest_id = test_start_backtest()
    if not backtest_id:
        print("\n❌ Cannot proceed without backtest_id")
        return 1
    
    # Test 2: Stream progress
    success = test_stream_backtest(backtest_id)
    if not success:
        print("\n❌ Stream test failed")
        return 1
    
    # Test 3: Download day details
    test_date = "2024-10-24"
    success = test_download_day(backtest_id, test_date)
    if not success:
        print("\n❌ Download test failed")
        return 1
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
