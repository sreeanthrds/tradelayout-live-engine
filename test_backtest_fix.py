#!/usr/bin/env python3
"""
Test backtest API after reverting unified engine changes
"""

import requests
import json

API_BASE = "http://localhost:8000"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
TEST_DATE = "2024-10-29"

print("="*80)
print("🧪 TESTING BACKTEST API")
print("="*80)
print(f"Strategy: {STRATEGY_ID}")
print(f"Date: {TEST_DATE}")
print()

try:
    print("📤 Calling /api/v1/backtest...")
    response = requests.post(
        f"{API_BASE}/api/v1/backtest",
        json={
            "strategy_id": STRATEGY_ID,
            "start_date": TEST_DATE,
            "end_date": TEST_DATE,
            "mode": "backtesting",
            "include_diagnostics": False  # Skip diagnostics for faster test
        },
        timeout=180  # 3 minutes
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Backtest API successful!\n")
        
        if data.get('results'):
            result = data['results'][0]
            positions = result.get('positions', [])
            summary = result.get('summary', {})
            
            print(f"📊 Results:")
            print(f"   Date: {result.get('date')}")
            print(f"   Total Positions: {len(positions)}")
            print(f"   Total P&L: {summary.get('total_pnl', 0)}")
            print(f"   Winning: {summary.get('winning_trades', 0)}")
            print(f"   Losing: {summary.get('losing_trades', 0)}")
            
            if len(positions) > 0:
                print(f"\n✅ SUCCESS: Backtest is working! Created {len(positions)} positions")
            else:
                print(f"\n⚠️  WARNING: No positions created")
        else:
            print("❌ No results in response")
            print(json.dumps(data, indent=2)[:500])
    else:
        print(f"❌ API Error: {response.status_code}")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("❌ Request timed out")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
