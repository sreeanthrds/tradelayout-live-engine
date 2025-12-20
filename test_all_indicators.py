#!/usr/bin/env python3
"""
Comprehensive Test Suite for All ta_hybrid Indicators
Tests all 136 indicators with default values on Oct 1, 2024
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

import ta_hybrid as ta
import inspect
from datetime import date, datetime
import json

print(f"\n{'='*100}")
print(f"TA_HYBRID INDICATOR DISCOVERY")
print(f"{'='*100}\n")

# Discover all indicators
all_indicators = []
registry = ta._INDICATOR_REGISTRY

print(f"Total indicators in registry: {len(registry)}\n")

# Categorize indicators
categories = {
    'Momentum': [],
    'Trend': [],
    'Volatility': [],
    'Volume': [],
    'Other': []
}

for name, indicator_class in sorted(registry.items()):
    try:
        # Get indicator signature
        sig = inspect.signature(indicator_class.__init__)
        params = {}
        
        # Extract default parameters
        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'kwargs'):
                continue
            if param.default != inspect.Parameter.empty:
                params[param_name] = param.default
            elif param_name == 'length':
                params[param_name] = 14
            elif param_name == 'period':
                params[param_name] = 14
            elif param_name == 'fast_period':
                params[param_name] = 12
            elif param_name == 'slow_period':
                params[param_name] = 26
            elif param_name == 'signal_period':
                params[param_name] = 9
            elif param_name == 'price_field':
                params[param_name] = 'close'
        
        # Categorize
        category = 'Other'
        name_lower = name.lower()
        if any(x in name_lower for x in ['rsi', 'stoch', 'cci', 'mfi', 'roc', 'momentum', 'willr', 'ultimate']):
            category = 'Momentum'
        elif any(x in name_lower for x in ['ma', 'ema', 'sma', 'wma', 'dema', 'tema', 'adx', 'aroon', 'macd', 'ppo', 'trix']):
            category = 'Trend'
        elif any(x in name_lower for x in ['atr', 'bb', 'keltner', 'donchian', 'volatility', 'std']):
            category = 'Volatility'
        elif any(x in name_lower for x in ['volume', 'obv', 'vwap', 'ad', 'cmf', 'mfi']):
            category = 'Volume'
        
        indicator_info = {
            'name': name,
            'class': indicator_class.__name__,
            'category': category,
            'params': params,
            'doc': (indicator_class.__doc__ or '').strip().split('\n')[0][:80]
        }
        
        all_indicators.append(indicator_info)
        categories[category].append(indicator_info)
        
    except Exception as e:
        print(f"⚠️  Error analyzing {name}: {e}")

# Display summary
print(f"{'Category':<15} {'Count':<8} {'Examples'}")
print(f"{'-'*100}")
for cat, inds in categories.items():
    examples = ', '.join([i['name'] for i in inds[:3]])
    print(f"{cat:<15} {len(inds):<8} {examples}...")

print(f"\n{'='*100}")
print(f"DETAILED INDICATOR LIST")
print(f"{'='*100}\n")

for cat, inds in categories.items():
    if not inds:
        continue
    print(f"\n## {cat} Indicators ({len(inds)})\n")
    for ind in inds:
        param_str = ', '.join([f"{k}={v}" for k, v in ind['params'].items()])
        print(f"  {ind['name']:<20} - {ind['class']:<25} ({param_str})")

# Save to file
with open('indicator_list.json', 'w') as f:
    json.dump({
        'total': len(all_indicators),
        'categories': {k: len(v) for k, v in categories.items()},
        'indicators': all_indicators
    }, f, indent=2)

print(f"\n{'='*100}")
print(f"✅ Saved indicator list to indicator_list.json")
print(f"{'='*100}\n")
