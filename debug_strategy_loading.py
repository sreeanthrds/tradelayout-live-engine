#!/usr/bin/env python3
"""
Debug script to check if strategy is loading indicators correctly
"""

import os
import sys
from datetime import date

# Set environment variables
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.strategy_manager import StrategyManager

print("=" * 100)
print("🔍 DEBUG: STRATEGY LOADING")
print("=" * 100)

strategy_id = "5708424d-5962-4629-978c-05b3a174e104"

print(f"\n📋 Loading strategy: {strategy_id}")

manager = StrategyManager()
strategy = manager.load_strategy(strategy_id=strategy_id)

print(f"\n✅ Strategy loaded: {strategy.strategy_name}")
print(f"   User ID: {strategy.user_id}")

print("\n" + "=" * 100)
print("📊 INSTRUMENT CONFIGS")
print("=" * 100)

print(f"\nTotal instrument configs: {len(strategy.instrument_configs)}")

for key, inst_config in strategy.instrument_configs.items():
    print(f"\n  {key}:")
    print(f"    Symbol: {inst_config.symbol}")
    print(f"    Timeframe: {inst_config.timeframe}")
    print(f"    Indicators: {len(inst_config.indicators)}")
    
    for ind in inst_config.indicators:
        print(f"      - {ind.name}({ind.params}) -> key: {ind.key}")

print("\n" + "=" * 100)
print("🎯 EXPECTED vs ACTUAL")
print("=" * 100)

if len(strategy.instrument_configs) == 0:
    print("\n❌ NO INSTRUMENT CONFIGS FOUND!")
    print("   This is why indicators aren't being registered")
    print("\n🔍 Checking raw strategy data...")
    
    # Try to load raw data
    from supabase import create_client
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    
    response = supabase.table("strategies").select("*").eq("id", strategy_id).execute()
    if response.data:
        import json
        raw_strategy = response.data[0]
        config = raw_strategy.get('strategy') or raw_strategy.get('config')
        
        if isinstance(config, str):
            config = json.loads(config)
        
        # Check for indicator nodes
        indicator_nodes = [n for n in config.get('nodes', []) if n.get('type') == 'indicator']
        print(f"\n   Found {len(indicator_nodes)} indicator nodes in raw data:")
        for node in indicator_nodes:
            print(f"      - {node['id']}: {node.get('data', {})}")

else:
    print(f"\n✅ Found {len(strategy.instrument_configs)} instrument configs")
    total_indicators = sum(len(ic.indicators) for ic in strategy.instrument_configs.values())
    print(f"✅ Total indicators: {total_indicators}")
    
    if total_indicators > 0:
        print("\n✅ Indicators are properly loaded!")
    else:
        print("\n❌ Instrument configs exist but NO indicators!")

print("\n" + "=" * 100)
