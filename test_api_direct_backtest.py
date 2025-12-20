#!/usr/bin/env python3
"""
Test Unified Engine via Direct Backtest API
Tests the unified engine through the simpler /api/v1/backtest endpoint

Run this test:
1. Start API server: python backtest_api_server.py (already running)
2. Run test: python test_api_direct_backtest.py

Expected: 9 positions created (matches baseline)
"""

import requests
import json

API_BASE = "http://localhost:8000"

print("="*80)
print("🧪 DIRECT BACKTEST API TEST - Unified Engine")
print("="*80)
print()
print("Strategy: 5708424d-5962-4629-978c-05b3a174e104")
print("Date: October 29, 2024")
print("Endpoint: /api/v1/backtest")
print()
print("="*80)
print()

strategy_id = "5708424d-5962-4629-978c-05b3a174e104"
test_date = "2024-10-29"

try:
    print("🚀 Calling backtest API...")
    response = requests.post(
        f"{API_BASE}/api/v1/backtest",
        json={
            "strategy_id": strategy_id,
            "start_date": test_date,
            "end_date": test_date,
            "mode": "backtesting",
            "include_diagnostics": True
        },
        timeout=120  # 2 minutes timeout
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ API request successful!")
        print(f"\n{'='*80}")
        print(f"📊 BACKTEST RESULTS")
        print(f"{'='*80}\n")
        
        if 'results' in data and len(data['results']) > 0:
            daily_result = data['results'][0]
            positions = daily_result.get('positions', [])
            
            print(f"📊 Position Summary:")
            print(f"   Date: {daily_result['date']}")
            print(f"   Total Positions: {len(positions)}")
            
            if len(positions) == 9:
                print(f"\n✅ SUCCESS: Created 9 positions (matches baseline!)")
            else:
                print(f"\n⚠️  WARNING: Expected 9 positions, got {len(positions)}")
            
            # Show position details
            if len(positions) > 0:
                print(f"\n📋 Position Details:")
                for i, pos in enumerate(positions[:10], 1):
                    status = pos.get('status', 'UNKNOWN')
                    entry = pos.get('entry_price', 0)
                    exit_price = pos.get('exit_price', 'OPEN')
                    pnl = pos.get('pnl', 0)
                    print(f"\n   {i}. Position ID: {pos.get('position_id', 'N/A')}")
                    print(f"      Action: {pos.get('side', 'N/A')} {pos.get('symbol', 'N/A')}")
                    print(f"      Entry: {entry} → Exit: {exit_price}")
                    print(f"      Status: {status}, P&L: {pnl}")
            
            # Show summary
            if 'summary' in daily_result:
                summary = daily_result['summary']
                print(f"\n📈 Summary:")
                print(f"   Total P&L: {summary.get('total_pnl', 0)}")
                print(f"   Winning Trades: {summary.get('winning_trades', 0)}")
                print(f"   Losing Trades: {summary.get('losing_trades', 0)}")
        else:
            print(f"❌ No results in response")
            print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ API request failed: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.Timeout:
    print(f"❌ Request timed out (>120s)")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}\n")
