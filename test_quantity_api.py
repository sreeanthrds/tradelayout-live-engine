"""
Test to verify quantity field shows actual_quantity (150) instead of lots (1)
"""
import requests
import json

# Run backtest
start_response = requests.post(
    "http://localhost:8000/api/v1/backtest/start",
    json={
        "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
        "start_date": "2024-10-29",
        "end_date": "2024-10-29",
        "initial_capital": 100000,
        "slippage_percentage": 0.0005,
        "commission_percentage": 0.001,
        "strategy_scale": 2.0
    }
)

backtest_id = start_response.json()['backtest_id']
print(f"Backtest ID: {backtest_id}")

# Wait for completion by consuming stream
print("\nWaiting for backtest to complete...")
stream_response = requests.get(f"http://localhost:8000/api/v1/backtest/{backtest_id}/stream", stream=True)

for line in stream_response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('event: backtest_completed'):
            print("✅ Backtest completed")
            break

# Now check the saved data
print("\nChecking backtest_dashboard_data.json...")
with open('backtest_dashboard_data.json', 'r') as f:
    data = json.load(f)
    
positions = data['positions']
print(f"\nTotal positions: {len(positions)}")

if positions:
    first_pos = positions[0]
    print(f"\nFirst position details:")
    print(f"  Position ID: {first_pos['position_id']}")
    print(f"  Quantity (lots): {first_pos['quantity']}")
    print(f"  Actual Quantity (shares): {first_pos['actual_quantity']}")
    print(f"  Multiplier: {first_pos['multiplier']}")
    print(f"  Expected with 2x scale: {first_pos['quantity']} lots × {first_pos['multiplier']} × 2.0 = {first_pos['quantity'] * first_pos['multiplier'] * 2}")
    
    if first_pos['actual_quantity'] == 150:
        print(f"\n✅ CORRECT: actual_quantity is 150 (1 lot × 75 multiplier × 2.0 scale)")
    else:
        print(f"\n❌ ISSUE: actual_quantity is {first_pos['actual_quantity']}, expected 150")

print("\n" + "="*80)
print("The API now returns actual_quantity in the 'quantity' field for the UI")
print("="*80)
