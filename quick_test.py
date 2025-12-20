import requests
import time

API_BASE_URL = "http://localhost:8000"
payload = {
    "user_id": "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc",
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "mode": "live",
    "broker_connection_id": "clickhouse",
    "speed_multiplier": 100.0  # Very fast
}

print("Starting simulation...")
response = requests.post(f"{API_BASE_URL}/api/v1/simulation/start", json=payload, timeout=30)
session_id = response.json().get('session_id')
print(f"Session ID: {session_id}")

print("Waiting 10 seconds for errors to appear...")
time.sleep(10)

print("Done - check server logs for traceback")
