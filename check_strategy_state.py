#!/usr/bin/env python3
"""
Check strategy state from cache
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.global_instances import get_instance_manager
import json

instance_id = "admin_tester_user_2yfjTGEKjL7XkklQyBaMP6SN2Lc_5708424d-5962-4629-978c-05b3a174e104"

print('='*80)
print('🔍 CHECKING STRATEGY STATE')
print('='*80)

instance_manager = get_instance_manager()
cache = instance_manager.get_or_create_cache('admin_tester')

# Check strategy_states key
if hasattr(cache, 'cache'):
    strategy_states = cache.cache.get('strategy_states', {})
    
    print(f"\nTotal strategies in cache: {len(strategy_states)}")
    
    if instance_id in strategy_states:
        state = strategy_states[instance_id]
        print(f"\n✅ Strategy state found for: {instance_id}")
        print(f"\nState keys: {list(state.keys())}")
        
        # Check for GPS reference
        if 'gps' in state:
            gps = state['gps']
            print(f"\n📍 GPS found in strategy state")
            
            # Check if GPS has positions method
            if hasattr(gps, 'positions'):
                positions = gps.positions
                print(f"   Total positions: {len(positions)}")
                
                for pos_id, pos_data in positions.items():
                    status = pos_data.get('status', 'unknown')
                    status_icon = '✅' if status == 'closed' else '⏳'
                    print(f"\n{status_icon} Position: {pos_id}")
                    print(f"   Symbol: {pos_data.get('symbol')}")
                    print(f"   Side: {pos_data.get('side')}")
                    print(f"   Entry Price: ₹{pos_data.get('entry_price', 0):.2f}")
                    print(f"   Quantity: {pos_data.get('actual_quantity', 0)}")
                    
                    if status == 'closed':
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
                        print(f"   P&L: {pnl_icon} ₹{pnl:.2f}")
            else:
                print(f"   GPS type: {type(gps)}")
                print(f"   GPS attributes: {dir(gps)}")
        
        # Check for positions directly in state
        if 'positions' in state:
            print(f"\n📦 Positions found directly in state: {len(state['positions'])}")
            
        # Check context for GPS
        if 'context' in state:
            context = state['context']
            if 'gps' in context:
                print(f"\n📍 GPS found in context")
                gps = context['gps']
                if hasattr(gps, 'positions'):
                    positions = gps.positions
                    print(f"   Total positions: {len(positions)}")
                    
                    closed_count = sum(1 for p in positions.values() if p.get('status') == 'closed')
                    open_count = sum(1 for p in positions.values() if p.get('status') != 'closed')
                    
                    print(f"   Closed: {closed_count}")
                    print(f"   Open: {open_count}")
                    
                    if positions:
                        print("\n" + "="*80)
                        print("📝 ALL POSITIONS")
                        print("="*80)
                        
                        total_pnl = 0
                        for pos_id, pos_data in positions.items():
                            status = pos_data.get('status', 'unknown')
                            status_icon = '✅' if status == 'closed' else '⏳'
                            
                            print(f"\n{status_icon} Position: {pos_id}")
                            print(f"   Symbol: {pos_data.get('symbol')}")
                            print(f"   Side: {pos_data.get('side')}")
                            print(f"   Entry Price: ₹{pos_data.get('entry_price', 0):.2f}")
                            print(f"   Quantity: {pos_data.get('actual_quantity', 0)}")
                            print(f"   Entry Time: {pos_data.get('entry_time')}")
                            
                            if status == 'closed':
                                exit_price = pos_data.get('exit_price', 0)
                                entry_price = pos_data.get('entry_price', 0)
                                qty = pos_data.get('actual_quantity', 0)
                                side = pos_data.get('side', 'BUY')
                                
                                if side.upper() == 'BUY':
                                    pnl = (exit_price - entry_price) * qty
                                else:
                                    pnl = (entry_price - exit_price) * qty
                                
                                total_pnl += pnl
                                pnl_icon = '🟢' if pnl >= 0 else '🔴'
                                print(f"   Exit Price: ₹{exit_price:.2f}")
                                print(f"   Exit Time: {pos_data.get('exit_time')}")
                                print(f"   P&L: {pnl_icon} ₹{pnl:.2f}")
                                print(f"   Exit Reason: {pos_data.get('exit_reason', 'N/A')}")
                        
                        print("\n" + "="*80)
                        print("📊 SUMMARY")
                        print("="*80)
                        print(f"\nTotal Positions: {len(positions)}")
                        print(f"Closed: {closed_count}")
                        print(f"Open: {open_count}")
                        pnl_icon = '🟢' if total_pnl >= 0 else '🔴'
                        print(f"Total P&L: {pnl_icon} ₹{total_pnl:.2f}")
                        print(f"\n{'='*80}")
    else:
        print(f"\n❌ No state found for instance: {instance_id}")
        print(f"\nAvailable strategies:")
        for sid in strategy_states.keys():
            print(f"   - {sid}")
else:
    print("❌ Cache is not DictCache")

print("\n" + "="*80)
