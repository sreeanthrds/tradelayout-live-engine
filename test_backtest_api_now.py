#!/usr/bin/env python3
"""
Test backtest API endpoint - Final verification
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
TEST_DATE = "2024-10-29"

print("="*80)
print("🧪 BACKTEST API TEST")
print("="*80)
print(f"Endpoint: {API_BASE}/api/v1/backtest")
print(f"Strategy: {STRATEGY_ID}")
print(f"Date: {TEST_DATE}")
print("="*80)
print()

start_time = time.time()

try:
    print("📤 Calling backtest API...")
    response = requests.post(
        f"{API_BASE}/api/v1/backtest",
        json={
            "strategy_id": STRATEGY_ID,
            "start_date": TEST_DATE,
            "end_date": TEST_DATE,
            "mode": "backtesting",
            "include_diagnostics": False  # Faster without diagnostics
        },
        timeout=300  # 5 minutes timeout
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"✅ API Response received in {elapsed:.1f}s")
        print()
        print("="*80)
        print("📊 BACKTEST RESULTS")
        print("="*80)
        
        if data.get('results'):
            result = data['results'][0]
            positions = result.get('positions', [])
            summary = result.get('summary', {})
            
            print(f"\n📅 Date: {result.get('date')}")
            print(f"\n📈 Summary:")
            print(f"   Total Positions: {len(positions)}")
            print(f"   Total P&L: ₹{summary.get('total_pnl', 0):.2f}")
            print(f"   Winning Trades: {summary.get('winning_trades', 0)}")
            print(f"   Losing Trades: {summary.get('losing_trades', 0)}")
            print(f"   Win Rate: {summary.get('win_rate', 0):.2f}%")
            
            if len(positions) > 0:
                print(f"\n📋 First 3 Positions:")
                for i, pos in enumerate(positions[:3], 1):
                    print(f"\n   {i}. Position {pos.get('position_id', 'N/A')}")
                    print(f"      Entry: {pos.get('entry_timestamp', 'N/A')} @ ₹{pos.get('entry_price', 0):.2f}")
                    print(f"      Exit: {pos.get('exit_timestamp', 'N/A')} @ ₹{pos.get('exit_price', 0):.2f}")
                    print(f"      P&L: ₹{pos.get('pnl', 0):.2f}")
                    print(f"      Symbol: {pos.get('symbol', 'N/A')}")
                
                print(f"\n{'='*80}")
                print(f"✅ SUCCESS: Backtest is fully working!")
                print(f"   Created {len(positions)} positions in {elapsed:.1f}s")
                print(f"{'='*80}")
            else:
                print(f"\n⚠️  WARNING: No positions created")
        else:
            print("❌ No results in response")
            print(json.dumps(data, indent=2)[:800])
    else:
        print(f"❌ API Error: {response.status_code}")
        print(response.text[:800])
        
except requests.exceptions.Timeout:
    elapsed = time.time() - start_time
    print(f"⚠️  Request timed out after {elapsed:.1f}s")
    print("\nNote: Backtest may still be running on server.")
    print("Check backtest_dashboard_data.json for results.")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
