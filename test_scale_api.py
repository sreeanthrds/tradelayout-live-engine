"""
Test script for session configuration API with scale parameter
"""

import requests
import json

API_BASE = "http://localhost:8001"

# Test data
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
STRATEGY_ID = "d70ec04a-1025-46c5-94c4-3e6bff499644"
BROKER_CONNECTION_ID = "acf98a95-1547-4a72-b824-3ce7068f05b4"

print("="*70)
print("SESSION CONFIGURATION API TEST")
print("="*70)

# Test 1: Configure session with scale=2.0
print("\n📝 Test 1: Configure session with scale=2.0")
response = requests.post(
    f"{API_BASE}/api/v1/live/session/configure",
    json={
        "session_id": "test_scale_session",
        "strategy_id": STRATEGY_ID,
        "broker_connection_id": BROKER_CONNECTION_ID,
        "scale": 2.0
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 2: Get session configuration
print("\n📋 Test 2: Get session configuration")
response = requests.get(
    f"{API_BASE}/api/v1/live/session/test_scale_session/configuration"
)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Test 3: Start SSE session with scale (alternative method)
print("\n🚀 Test 3: Start SSE session with scale in request")
response = requests.post(
    f"{API_BASE}/api/v1/live/session/start-sse",
    json={
        "user_id": USER_ID,
        "sessions": {
            "test_scale_execution": {
                "strategy_id": STRATEGY_ID,
                "broker_connection_id": BROKER_CONNECTION_ID,
                "scale": 3.0
            }
        }
    }
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
if result.get('created_sessions'):
    for session in result['created_sessions']:
        print(f"\n📊 Session Created:")
        print(f"   Session ID: {session.get('session_id')}")
        print(f"   Strategy: {session.get('strategy_id')}")
        print(f"   Scale: {session.get('broker_metadata', {}).get('scale', 'N/A')}")
        print(f"   Status: {session.get('status')}")

# Test 4: List all configurations
print("\n📜 Test 4: List all session configurations")
response = requests.get(
    f"{API_BASE}/api/v1/live/sessions/configurations?user_id={USER_ID}"
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Total configurations: {result.get('total')}")
for config in result.get('configurations', []):
    print(f"\n   Session: {config.get('session_id')}")
    print(f"   Scale: {config.get('scale')}")
    print(f"   Status: {config.get('status')}")

print("\n" + "="*70)
print("✅ API TEST COMPLETE")
print("="*70)
print("\nNote: Scale values are now configurable via API")
print("Scale multiplies: quantity × multiplier × scale")
print("Example: quantity=1, multiplier=50, scale=2.0 → actual_qty=100")
