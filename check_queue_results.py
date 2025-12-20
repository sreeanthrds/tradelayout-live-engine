#!/usr/bin/env python3
"""
Check queue execution results - retrieve positions from GPS
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.global_instances import get_instance_manager
import json

# Instance ID for the strategy that just ran
instance_id = "admin_tester_user_2yfjTGEKjL7XkklQyBaMP6SN2Lc_5708424d-5962-4629-978c-05b3a174e104"

print('='*80)
print('📊 QUEUE EXECUTION RESULTS')
print('='*80)
print(f"\nInstance ID: {instance_id}\n")

# Get instance manager
instance_manager = get_instance_manager()

# Get cache for admin_tester queue
cache = instance_manager.get_or_create_cache('admin_tester')

# Get strategy subscription
subscription = cache.get_strategy_subscription(instance_id)
if subscription:
    print("✅ Strategy subscription found:")
    print(f"   User: {subscription.get('user_id')}")
    print(f"   Strategy: {subscription.get('strategy_id')}")
    print(f"   Status: {subscription.get('status')}")
    print(f"   Scale: {subscription.get('scale')}")
else:
    print("❌ No strategy subscription found")

# Try to get positions from GPS
try:
    # GPS stores positions per strategy instance
    gps_key = f"gps:{instance_id}"
    
    # Check if cache has GPS data
    if hasattr(cache, 'cache'):
        # DictCache - direct access
        gps_data = cache.cache.get(gps_key)
        if gps_data:
            print(f"\n✅ GPS data found in cache:")
            print(f"   Total positions: {len(gps_data.get('positions', {}))}")
            
            positions = gps_data.get('positions', {})
            closed_count = sum(1 for p in positions.values() if p.get('status') == 'closed')
            open_count = sum(1 for p in positions.values() if p.get('status') != 'closed')
            
            print(f"   Closed: {closed_count}")
            print(f"   Open: {open_count}")
            
            if positions:
                print("\n" + "="*80)
                print("📝 POSITIONS DETAIL")
                print("="*80)
                
                for pos_id, pos_data in positions.items():
                    status_icon = '✅' if pos_data.get('status') == 'closed' else '⏳'
                    print(f"\n{status_icon} Position: {pos_id}")
                    print(f"   Symbol: {pos_data.get('symbol')}")
                    print(f"   Side: {pos_data.get('side')}")
                    print(f"   Entry Price: ₹{pos_data.get('entry_price', 0):.2f}")
                    print(f"   Quantity: {pos_data.get('actual_quantity', 0)}")
                    print(f"   Entry Time: {pos_data.get('entry_time')}")
                    
                    if pos_data.get('status') == 'closed':
                        exit_price = pos_data.get('exit_price', 0)
                        entry_price = pos_data.get('entry_price', 0)
                        qty = pos_data.get('actual_quantity', 0)
                        side = pos_data.get('side', 'BUY')
                        
                        if side.upper() == 'BUY':
                            pnl = (exit_price - entry_price) * qty
                        else:
                            pnl = (entry_price - exit_price) * qty
                        
                        pnl_icon = '🟢' if pnl >= 0 else '🔴'
                        print(f"   Exit Price: ₹{exit_price:.2f}")
                        print(f"   Exit Time: {pos_data.get('exit_time')}")
                        print(f"   P&L: {pnl_icon} ₹{pnl:.2f}")
                
                # Calculate total P&L
                total_pnl = 0
                for pos_data in positions.values():
                    if pos_data.get('status') == 'closed':
                        exit_price = pos_data.get('exit_price', 0)
                        entry_price = pos_data.get('entry_price', 0)
                        qty = pos_data.get('actual_quantity', 0)
                        side = pos_data.get('side', 'BUY')
                        
                        if side.upper() == 'BUY':
                            pnl = (exit_price - entry_price) * qty
                        else:
                            pnl = (entry_price - exit_price) * qty
                        
                        total_pnl += pnl
                
                print("\n" + "="*80)
                print("📊 SUMMARY")
                print("="*80)
                print(f"\nTotal Positions: {len(positions)}")
                print(f"Closed: {closed_count}")
                print(f"Open: {open_count}")
                pnl_icon = '🟢' if total_pnl >= 0 else '🔴'
                print(f"Total P&L: {pnl_icon} ₹{total_pnl:.2f}")
        else:
            print(f"\n⚠️ No GPS data found for key: {gps_key}")
            print("\nAvailable cache keys:")
            for key in list(cache.cache.keys())[:20]:
                print(f"   - {key}")
    else:
        print("\n⚠️ Cache type not recognized (not DictCache)")
        
except Exception as e:
    print(f"\n❌ Error retrieving GPS data: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
