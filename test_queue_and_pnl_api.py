#!/usr/bin/env python3
"""
Test Queue Toggle and P&L API Integration
Diagnoses issues with:
1. Queue toggle enable/disable
2. Individual strategy P&L display
3. Aggregated P&L across all strategies
"""

import requests
import json

API_BASE = "http://localhost:8000"
USER_ID = "user_2yfjTGEKjL7XkklQyBaMP6SN2Lc"
TEST_STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"

print("="*80)
print("🔍 QUEUE TOGGLE & P&L API DIAGNOSTIC")
print("="*80)
print()

# Test 1: Get user strategies (should show queue toggle)
print("📋 TEST 1: Get User Strategies")
print("-" * 80)
try:
    response = requests.get(f"{API_BASE}/api/live-trading/strategies/{USER_ID}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Response successful")
        print(f"   Total strategies: {data.get('total_strategies', 0)}")
        
        for strategy in data.get('strategies', []):
            print(f"\n   Strategy: {strategy['strategy_name']}")
            print(f"   - ID: {strategy['strategy_id']}")
            print(f"   - Status: {strategy['status']}")
            print(f"   - show_queue_toggle: {strategy.get('show_queue_toggle', 'MISSING')}")
            print(f"   - is_queued: {strategy.get('is_queued', 'MISSING')}")
            
            if not strategy.get('show_queue_toggle'):
                print(f"   ⚠️  ISSUE: show_queue_toggle is False/Missing!")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Get live trading dashboard (should show P&L)
print(f"\n\n📊 TEST 2: Get Live Trading Dashboard")
print("-" * 80)
try:
    response = requests.get(f"{API_BASE}/api/live-trading/dashboard/{USER_ID}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Response successful")
        print(f"   Total sessions: {data.get('total_sessions', 0)}")
        print(f"   Active sessions: {data.get('active_sessions', 0)}")
        
        # Calculate aggregated P&L
        total_realized_pnl = 0
        total_unrealized_pnl = 0
        total_pnl = 0
        
        for session_id, session in data.get('sessions', {}).items():
            strategy_name = session.get('strategy_name', 'Unknown')
            pnl_data = session.get('data', {}).get('gps_data', {}).get('pnl', {})
            
            realized = float(pnl_data.get('realized_pnl', '0'))
            unrealized = float(pnl_data.get('unrealized_pnl', '0'))
            total = float(pnl_data.get('total_pnl', '0'))
            
            total_realized_pnl += realized
            total_unrealized_pnl += unrealized
            total_pnl += total
            
            print(f"\n   Strategy: {strategy_name}")
            print(f"   - Session ID: {session_id}")
            print(f"   - Status: {session.get('status', 'unknown')}")
            print(f"   - show_queue_toggle: {session.get('show_queue_toggle', 'MISSING')}")
            print(f"   - is_queued: {session.get('is_queued', 'MISSING')}")
            print(f"   - P&L:")
            print(f"     • Realized: ₹{realized:.2f}")
            print(f"     • Unrealized: ₹{unrealized:.2f}")
            print(f"     • Total: ₹{total:.2f}")
            
            if pnl_data.get('realized_pnl') == "0.00" and pnl_data.get('unrealized_pnl') == "0.00":
                print(f"   ⚠️  ISSUE: P&L is zero - may not be calculated")
        
        print(f"\n{'='*80}")
        print(f"📈 AGGREGATED P&L (Calculated from all strategies):")
        print(f"   - Total Realized: ₹{total_realized_pnl:.2f}")
        print(f"   - Total Unrealized: ₹{total_unrealized_pnl:.2f}")
        print(f"   - Total P&L: ₹{total_pnl:.2f}")
        print(f"{'='*80}")
        
        if total_pnl == 0:
            print(f"\n⚠️  WARNING: Aggregated P&L is zero - backend may not be calculating P&L")
        
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Check queue status
print(f"\n\n🎯 TEST 3: Check Queue Status")
print("-" * 80)
try:
    response = requests.get(f"{API_BASE}/api/queue/status/admin_tester")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API Response successful")
        print(f"   Queue type: {data.get('queue_type', 'unknown')}")
        print(f"   Total strategies: {data.get('total_strategies', 0)}")
        print(f"   Pending entries: {data.get('pending_entries', 0)}")
        print(f"   Is processing: {data.get('is_processing', False)}")
        
        if data.get('strategies'):
            print(f"\n   Strategies in queue:")
            for strategy in data['strategies']:
                print(f"   - {strategy['strategy_id']}: {strategy.get('strategy_name', 'Unknown')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Test queue submit
print(f"\n\n➕ TEST 4: Test Queue Submit")
print("-" * 80)
try:
    response = requests.post(
        f"{API_BASE}/api/queue/submit",
        params={"user_id": USER_ID, "queue_type": "admin_tester"},
        json=[{
            "strategy_id": TEST_STRATEGY_ID,
            "broker_connection_id": "test_broker",
            "scale": 1.0
        }]
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Queue submit successful")
        print(f"   Queue position: {data.get('queue_position', 'N/A')}")
        print(f"   Total strategies queued: {data.get('total_strategies_queued', 0)}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Summary
print(f"\n\n{'='*80}")
print(f"📝 DIAGNOSTIC SUMMARY")
print(f"{'='*80}")
print(f"""
ISSUES TO CHECK IN FRONTEND:

1. Queue Toggle:
   - Backend provides 'show_queue_toggle' and 'is_queued' flags
   - Check if frontend correctly reads these flags from API response
   - Verify checkbox binding in UI component

2. Individual Strategy P&L:
   - Backend provides P&L in: sessions[session_id].data.gps_data.pnl
   - Structure: {{realized_pnl, unrealized_pnl, total_pnl, closed_trades, open_trades}}
   - Verify frontend reads from correct path

3. Aggregated P&L:
   - Backend DOES NOT provide pre-calculated aggregated P&L
   - Frontend MUST sum P&L from all sessions
   - Calculation: total_pnl = sum(session.data.gps_data.pnl.total_pnl for all sessions)

RECOMMENDED FIXES:

Backend:
- Add aggregated P&L calculation to /api/live-trading/dashboard endpoint
- Return aggregated_pnl in dashboard response

Frontend:
- Verify queue toggle checkbox reads 'show_queue_toggle' flag
- Verify P&L display reads from correct API path
- Implement local aggregation if backend doesn't provide it
""")
print(f"{'='*80}\n")
