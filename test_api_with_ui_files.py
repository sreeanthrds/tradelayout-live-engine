#!/usr/bin/env python3
"""
Test script for Backtest API with UI files generation.

Demonstrates:
1. Running backtest via API
2. Receiving JSON response
3. Accessing generated trades_daily.json
4. Accessing generated diagnostics_export.json
"""

import requests
import json
import time

# API Configuration
API_BASE_URL = "http://localhost:8000"
STRATEGY_ID = "5708424d-5962-4629-978c-05b3a174e104"
TEST_DATE = "2024-10-29"

def test_backtest_endpoint():
    """Test the main backtest endpoint"""
    print("="*80)
    print("🧪 TEST 1: Run Backtest via API")
    print("="*80)
    
    # Request payload
    payload = {
        "strategy_id": STRATEGY_ID,
        "start_date": TEST_DATE,
        "mode": "backtesting",
        "include_diagnostics": True
    }
    
    print(f"\n📤 Sending request to {API_BASE_URL}/api/v1/backtest")
    print(f"   Strategy: {STRATEGY_ID}")
    print(f"   Date: {TEST_DATE}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/backtest",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            print("\n✅ Backtest successful!")
            data = response.json()
            
            # Display summary
            summary = data['data']['overall_summary']
            print(f"\n📊 Summary:")
            print(f"   Total Positions: {summary['total_positions']}")
            print(f"   Total P&L: ₹{summary['total_pnl']:.2f}")
            print(f"   Winning Trades: {summary['total_winning_trades']}")
            print(f"   Losing Trades: {summary['total_losing_trades']}")
            print(f"   Win Rate: {summary['overall_win_rate']:.2f}%")
            
            # Check if UI files were generated
            ui_files_generated = data['data']['metadata'].get('ui_files_generated', False)
            print(f"\n📁 UI Files Generated: {'✅ Yes' if ui_files_generated else '❌ No'}")
            
            return True
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_get_trades_daily():
    """Test getting the trades_daily.json file"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Get trades_daily.json File")
    print("="*80)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/backtest/files/trades_daily",
            timeout=10
        )
        
        if response.status_code == 200:
            print("\n✅ trades_daily.json retrieved successfully!")
            data = response.json()
            
            print(f"\n📊 Trades Data:")
            print(f"   Date: {data.get('date')}")
            print(f"   Total Trades: {data['summary']['total_trades']}")
            print(f"   Total P&L: {data['summary']['total_pnl']}")
            
            # Show first trade details
            if data['trades']:
                first_trade = data['trades'][0]
                print(f"\n   First Trade:")
                print(f"   - Trade ID: {first_trade['trade_id']}")
                print(f"   - Symbol: {first_trade['symbol']}")
                print(f"   - Entry Price: ₹{first_trade['entry_price']}")
                print(f"   - P&L: ₹{first_trade['pnl']}")
            
            return True
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_get_diagnostics_export():
    """Test getting the diagnostics_export.json file"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Get diagnostics_export.json File")
    print("="*80)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/backtest/files/diagnostics_export",
            timeout=10
        )
        
        if response.status_code == 200:
            print("\n✅ diagnostics_export.json retrieved successfully!")
            data = response.json()
            
            print(f"\n📊 Diagnostics Data:")
            print(f"   Total Events: {len(data['events_history'])}")
            
            # Check if current_state is present (it shouldn't be for backtesting)
            has_current_state = 'current_state' in data
            print(f"   Current State Included: {'❌ Yes (WRONG!)' if has_current_state else '✅ No (CORRECT!)'}")
            
            if has_current_state:
                print("\n   ⚠️  WARNING: current_state should NOT be included in backtesting!")
                print("   It's only for live simulation.")
            
            # Show first event
            if data['events_history']:
                first_event_id = list(data['events_history'].keys())[0]
                first_event = data['events_history'][first_event_id]
                print(f"\n   First Event:")
                print(f"   - Execution ID: {first_event_id}")
                print(f"   - Node: {first_event['node_name']}")
                print(f"   - Type: {first_event['node_type']}")
            
            return True
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_api_status():
    """Test the API status endpoint"""
    print("\n" + "="*80)
    print("🧪 TEST 4: API Status Check")
    print("="*80)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/backtest/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ API is ready!")
            print(f"\n   Status: {data['status']}")
            print(f"   Features:")
            for feature, enabled in data['features'].items():
                status = "✅" if enabled else "❌"
                print(f"   - {status} {feature}")
            
            return True
        else:
            print(f"\n❌ API not ready: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("="*80)
    print("🚀 BACKTEST API TEST SUITE")
    print("="*80)
    print(f"\nAPI Base URL: {API_BASE_URL}")
    print(f"Strategy ID: {STRATEGY_ID}")
    print(f"Test Date: {TEST_DATE}")
    
    # Run tests
    results = []
    
    # Test 1: API Status
    results.append(("API Status", test_api_status()))
    time.sleep(1)
    
    # Test 2: Run Backtest
    results.append(("Run Backtest", test_backtest_endpoint()))
    time.sleep(2)  # Wait for file generation
    
    # Test 3: Get trades_daily.json
    results.append(("Get trades_daily.json", test_get_trades_daily()))
    time.sleep(1)
    
    # Test 4: Get diagnostics_export.json
    results.append(("Get diagnostics_export.json", test_get_diagnostics_export()))
    
    # Summary
    print("\n" + "="*80)
    print("📋 TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n🎯 Overall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
    
    print("="*80)
