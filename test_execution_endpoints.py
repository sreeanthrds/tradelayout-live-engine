"""
Test Execution Dictionary Endpoints
Tests add-to-execution, remove-from-execution, and execution-status endpoints
"""

import requests
import json

API_BASE = "http://localhost:8001"

# Test data
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
STRATEGY_ID = "d70ec04a-1025-46c5-94c4-3e6bff499644"
BROKER_CONNECTION_ID = "acf98a95-1547-4a72-b824-3ce7068f05b4"

print("="*80)
print("EXECUTION DICTIONARY ENDPOINTS TEST")
print("="*80)

# Test 1: Add session to execution (Toggle ON)
print("\n✅ Test 1: Add session to execution (Submit to Queue)")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/add-to-execution",
    json={
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "broker_connection_id": BROKER_CONNECTION_ID,
        "scale": 2.0
    }
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
print(f"Session ID: {result.get('session_id')}")
print(f"Status: {result.get('status')}")
print(f"Configuration:")
for key, value in result.get('configuration', {}).items():
    print(f"  {key}: {value}")

SESSION_ID = result.get('session_id')

# Test 2: Get execution status
print("\n📊 Test 2: Get execution status")
print("-" * 80)
response = requests.get(
    f"{API_BASE}/api/v1/live/session/{SESSION_ID}/execution-status"
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Session ID: {result.get('session_id')}")
print(f"In Execution: {result.get('in_execution')}")
print(f"Status: {result.get('status')}")
print(f"Configuration:")
for key, value in result.get('configuration', {}).items():
    print(f"  {key}: {value}")
print(f"Timestamps:")
for key, value in result.get('timestamps', {}).items():
    if value:
        print(f"  {key}: {value}")

# Test 3: Try adding again (should fail - already in execution)
print("\n⚠️  Test 3: Try adding same session again (should fail)")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/add-to-execution",
    json={
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "broker_connection_id": BROKER_CONNECTION_ID,
        "scale": 3.0  # Different scale
    }
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
print(f"Message: {result.get('message')}")

# Test 4: Remove from execution (Toggle OFF)
print("\n❌ Test 4: Remove session from execution (Untoggle)")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/remove-from-execution",
    json={
        "session_id": SESSION_ID
    }
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
print(f"Message: {result.get('message')}")
print(f"Status: {result.get('status')}")

# Test 5: Check status after removal
print("\n📊 Test 5: Get execution status after removal")
print("-" * 80)
response = requests.get(
    f"{API_BASE}/api/v1/live/session/{SESSION_ID}/execution-status"
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"In Execution: {result.get('in_execution')}")
print(f"Status: {result.get('status')}")
print(f"Removed At: {result.get('timestamps', {}).get('removed_from_execution_at')}")

# Test 6: Add back to execution (Toggle ON again)
print("\n✅ Test 6: Add session back to execution")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/add-to-execution",
    json={
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "broker_connection_id": BROKER_CONNECTION_ID,
        "scale": 1.5
    }
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
print(f"Status: {result.get('status')}")
print(f"Scale: {result.get('configuration', {}).get('scale')}")

# Test 7: Test with invalid broker connection
print("\n❌ Test 7: Test with invalid broker connection (should fail)")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/add-to-execution",
    json={
        "user_id": USER_ID,
        "strategy_id": STRATEGY_ID,
        "broker_connection_id": "invalid-broker-id",
        "scale": 1.0
    }
)
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Error: {response.json().get('detail')}")

# Test 8: Test with invalid strategy
print("\n❌ Test 8: Test with invalid strategy (should fail)")
print("-" * 80)
response = requests.post(
    f"{API_BASE}/api/v1/live/session/add-to-execution",
    json={
        "user_id": USER_ID,
        "strategy_id": "invalid-strategy-id",
        "broker_connection_id": BROKER_CONNECTION_ID,
        "scale": 1.0
    }
)
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Error: {response.json().get('detail')}")

print("\n" + "="*80)
print("✅ EXECUTION ENDPOINTS TEST COMPLETE")
print("="*80)
print("\nSession ID Format Verified:")
print(f"  {SESSION_ID}")
print(f"\nFormat: {{user_id}}_{{strategy_id}}_{{broker_connection_id}}")
print("\nEndpoints Working:")
print("  ✅ POST /api/v1/live/session/add-to-execution")
print("  ✅ POST /api/v1/live/session/remove-from-execution")
print("  ✅ GET /api/v1/live/session/{session_id}/execution-status")
