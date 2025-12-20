"""
Test script to check the stream endpoint response
"""
import requests
import json

# Backtest ID from the previous API call
backtest_id = "5708424d-5962-4629-978c-05b3a174e104_2024-10-29_2024-10-29"
stream_url = f"http://localhost:8000/api/v1/backtest/{backtest_id}/stream"

print("=" * 80)
print("TESTING STREAM ENDPOINT")
print("=" * 80)
print(f"\nStream URL: {stream_url}")
print("\n" + "=" * 80)

try:
    print("\n🚀 Fetching stream data...")
    response = requests.get(stream_url, timeout=60)
    
    print(f"\n📊 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Request successful!")
        
        # Parse streaming response (each line is a JSON object)
        lines = response.text.strip().split('\n')
        print(f"\n📝 Received {len(lines)} events")
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                try:
                    event = json.loads(line)
                    event_type = event.get('event', 'unknown')
                    
                    if event_type == 'complete':
                        print(f"\n✅ Event {i}: {event_type}")
                        result = event.get('result', {})
                        positions = result.get('positions', [])
                        print(f"   Total Positions: {len(positions)}")
                        
                        if positions:
                            print(f"\n📊 Position Data Sample (first position):")
                            print(json.dumps(positions[0], indent=2))
                        else:
                            print("   ⚠️ NO POSITIONS FOUND!")
                            print(f"\n   Full result:")
                            print(json.dumps(result, indent=2))
                    elif event_type == 'progress':
                        date = event.get('date', 'N/A')
                        positions = event.get('positions', 0)
                        print(f"   Event {i}: {event_type} - Date: {date}, Positions: {positions}")
                    elif event_type == 'error':
                        print(f"\n❌ Event {i}: ERROR")
                        print(f"   Message: {event.get('message', 'Unknown error')}")
                        print(f"   Details: {event.get('details', {})}")
                    else:
                        print(f"   Event {i}: {event_type}")
                        
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ Failed to parse event {i}: {e}")
                    print(f"   Raw: {line[:100]}...")
    else:
        print(f"❌ Request failed!")
        print(f"\nResponse:")
        print(response.text[:1000])
        
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: API server is not running!")
    print("   Start the server with: python backtest_api_server.py")
except requests.exceptions.Timeout:
    print("\n❌ Request timed out")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
