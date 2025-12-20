"""
Complete API test with detailed logging
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

print("=" * 80)
print("FULL API FLOW TEST")
print("=" * 80)

# Step 1: Start backtest
print("\n📤 Step 1: Starting backtest...")
payload = {
    "strategy_id": "5708424d-5962-4629-978c-05b3a174e104",
    "start_date": "2024-10-29",
    "end_date": "2024-10-29",
    "initial_capital": 100000,
    "slippage_percentage": 0.0005,
    "commission_percentage": 0.001,
    "strategy_scale": 2.0
}

start_response = requests.post(f"{API_BASE}/api/v1/backtest/start", json=payload)
print(f"   Status: {start_response.status_code}")
start_data = start_response.json()
print(f"   Backtest ID: {start_data.get('backtest_id')}")

backtest_id = start_data.get('backtest_id')

# Step 2: Stream the results
print(f"\n📥 Step 2: Streaming results for {backtest_id}...")
stream_url = f"{API_BASE}/api/v1/backtest/{backtest_id}/stream"

response = requests.get(stream_url, stream=True, timeout=120)
print(f"   Stream status: {response.status_code}")

events = []
for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data_str = line_str[6:]  # Remove 'data: ' prefix
            try:
                event_data = json.loads(data_str)
                events.append(event_data)
            except:
                pass

print(f"\n📊 Step 3: Analyzing {len(events)} events...")

for i, event in enumerate(events, 1):
    event_type = 'unknown'
    
    # Determine event type
    if 'date' in event and 'day_number' in event:
        if 'summary' in event:
            event_type = 'day_completed'
        else:
            event_type = 'day_started'
    elif 'backtest_id' in event and 'overall_summary' in event:
        event_type = 'backtest_completed'
    
    print(f"\n   Event {i}: {event_type}")
    
    if event_type == 'day_started':
        print(f"      Date: {event.get('date')}")
        print(f"      Day: {event.get('day_number')}/{event.get('total_days')}")
    
    elif event_type == 'day_completed':
        print(f"      Date: {event.get('date')}")
        summary = event.get('summary', {})
        print(f"      Total Trades: {summary.get('total_trades')}")
        print(f"      Total P&L: ₹{summary.get('total_pnl')}")
        print(f"      Winning Trades: {summary.get('winning_trades')}")
        print(f"      Losing Trades: {summary.get('losing_trades')}")
        print(f"      Win Rate: {summary.get('win_rate')}%")
        
        # Check if we have detail data
        has_detail = event.get('has_detail_data', False)
        print(f"      Has Detail Data: {has_detail}")
        
        if has_detail:
            detail_url = f"{API_BASE}/api/v1/backtest/{backtest_id}/details/{event.get('date')}"
            print(f"\n   📋 Fetching detail data from: {detail_url}")
            detail_response = requests.get(detail_url)
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                positions = detail_data.get('positions', [])
                print(f"      ✅ Retrieved {len(positions)} positions from details")
                
                if len(positions) > 0:
                    print(f"\n      📊 First position sample:")
                    pos = positions[0]
                    print(f"         Position ID: {pos.get('position_id')}")
                    print(f"         Entry Node: {pos.get('entry_node_id')}")
                    print(f"         Quantity: {pos.get('quantity')} (lots)")
                    print(f"         Actual Quantity: {pos.get('actual_quantity')} (shares)")
                    print(f"         Multiplier: {pos.get('multiplier')}")
                    print(f"         Entry Price: ₹{pos.get('entry_price')}")
                    print(f"         Exit Price: ₹{pos.get('exit_price')}")
                    print(f"         P&L: ₹{pos.get('pnl')}")
                else:
                    print(f"      ⚠️ NO POSITIONS in detail data!")
            else:
                print(f"      ❌ Failed to fetch details: {detail_response.status_code}")
    
    elif event_type == 'backtest_completed':
        print(f"      ✅ Backtest Complete!")
        overall = event.get('overall_summary', {})
        print(f"      Total Days: {overall.get('total_days')}")
        print(f"      Total Trades: {overall.get('total_trades')}")
        print(f"      Total P&L: ₹{overall.get('total_pnl')}")
        print(f"      Win Rate: {overall.get('win_rate')}%")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
