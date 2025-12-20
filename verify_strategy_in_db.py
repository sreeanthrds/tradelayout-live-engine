"""
Quick verification script to check if RSI condition exists in database
"""

import os
import json
from supabase import create_client

# Set credentials
os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

print("=" * 100)
print("🔍 VERIFYING STRATEGY IN DATABASE")
print("=" * 100)

strategy_id = "5708424d-5962-4629-978c-05b3a174e104"

# Query database
response = supabase.table("strategies").select("*").eq("id", strategy_id).execute()

if not response.data:
    print("❌ Strategy not found!")
    exit(1)

db_strategy = response.data[0]

print(f"\n✅ Found strategy: {db_strategy.get('name')}")
print(f"Updated at: {db_strategy.get('updated_at')}")
print(f"Version: {db_strategy.get('version', 'N/A')}")

# Get the strategy config
config = db_strategy.get('strategy') or db_strategy.get('config')

if isinstance(config, str):
    config = json.loads(config)

# Convert to string for searching
config_str = json.dumps(config, indent=2)

print("\n" + "=" * 100)
print("🔍 CHECKING FOR RSI CONDITION")
print("=" * 100)

# Check for any RSI reference
rsi_indicators = []
if 'rsi_' in config_str:
    print("✅ Found RSI indicator references!")
    
    # Extract all RSI indicator names
    import re
    rsi_matches = re.findall(r'"rsi_\d+"', config_str)
    rsi_indicators = list(set(rsi_matches))
    print(f"   RSI indicators found: {', '.join(rsi_indicators)}")
else:
    print("❌ NO RSI indicator references found")

if '"type": "indicator"' in config_str:
    print("✅ Found indicator-type conditions")
else:
    print("❌ NO indicator-type conditions found")

# Check entry-condition-2 specifically
print("\n" + "=" * 100)
print("📌 ENTRY-CONDITION-2 ANALYSIS")
print("=" * 100)

nodes = config.get('nodes', [])
entry_cond_2 = None

for node in nodes:
    if node.get('id') == 'entry-condition-2':
        entry_cond_2 = node
        break

if entry_cond_2:
    data = entry_cond_2.get('data', {})
    conditions = data.get('conditions', [])
    
    if conditions:
        root = conditions[0]
        sub_conditions = root.get('conditions', [])
        
        print(f"Number of conditions: {len(sub_conditions)}")
        print(f"Group logic: {root.get('groupLogic', 'N/A')}")
        print("\nConditions:")
        
        has_rsi = False
        for idx, cond in enumerate(sub_conditions, 1):
            lhs = cond.get('lhs', {})
            rhs = cond.get('rhs', {})
            operator = cond.get('operator', 'N/A')
            
            # Check if this is RSI condition
            if lhs.get('type') == 'indicator':
                has_rsi = True
                indicator_name = lhs.get('name', 'Unknown')
                offset = lhs.get('offset', 0)
                offset_str = "Previous" if offset == -1 else f"[{offset}]"
                
                if rhs.get('type') == 'constant':
                    rhs_val = rhs.get('value', 'N/A')
                    print(f"  {idx}. {offset_str}[{indicator_name}] {operator} {rhs_val} ✅ RSI CONDITION")
            elif lhs.get('type') == 'current_time':
                time_val = rhs.get('timeValue', 'N/A')
                print(f"  {idx}. Current Time {operator} {time_val}")
            elif lhs.get('type') == 'live_data':
                lhs_field = f"TI.{lhs.get('field', 'N/A')}"
                
                if rhs.get('type') == 'market_data':
                    rhs_field = rhs.get('field', 'N/A')
                    rhs_offset = rhs.get('offset', 0)
                    rhs_offset_str = "Previous" if rhs_offset == -1 else f"[{rhs_offset}]"
                    print(f"  {idx}. {lhs_field} {operator} {rhs_offset_str}[TI.{rhs_field}]")
        
        print("\n" + "=" * 100)
        print("📊 SUMMARY")
        print("=" * 100)
        
        if has_rsi:
            print("✅ RSI CONDITION EXISTS in database!")
            print("✅ Strategy is correctly configured")
        else:
            print("❌ RSI CONDITION MISSING from database!")
            print("❌ Only time and price conditions found")
            print("\n⚠️  ACTION REQUIRED:")
            print("   1. Open strategy in UI")
            print("   2. Re-add the RSI condition to entry-condition-2")
            print("   3. Save the strategy")
            print("   4. Run this script again to verify")
    else:
        print("❌ No conditions found in entry-condition-2")
else:
    print("❌ entry-condition-2 node not found")

print("\n" + "=" * 100)
