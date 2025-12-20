"""
Test STEP 1: GPS position_num tracking
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.core.gps import GlobalPositionStore

def test_position_num_tracking():
    """Test position_num auto-increment"""
    print("\n" + "="*80)
    print("TEST 1: Position Number Auto-Increment")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id = "entry-3-pos1"
    
    # First entry
    entry_data_1 = {
        'node_id': 'entry-3',
        'price': 241.65,
        'quantity': 50,
        'symbol': 'NIFTY25050CE',
        'reEntryNum': 0
    }
    
    gps.add_position(position_id, entry_data_1)
    
    pos1 = gps.get_position(position_id)
    print(f"\n✅ Position 1 created:")
    print(f"   position_id: {pos1['position_id']}")
    print(f"   position_num: {pos1['position_num']}")
    print(f"   reEntryNum: {pos1['reEntryNum']}")
    print(f"   status: {pos1['status']}")
    
    assert pos1['position_num'] == 1, "First position should have position_num = 1"
    assert gps.get_latest_position_num(position_id) == 1, "Latest position_num should be 1"
    assert gps.has_open_position(position_id) == True, "Should have open position"
    
    print(f"\n✅ Assertions passed for position 1")


def test_block_concurrent_positions():
    """Test that second position is blocked while first is open"""
    print("\n" + "="*80)
    print("TEST 2: Block Concurrent Positions")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id = "entry-3-pos1"
    
    # First entry
    entry_data_1 = {'node_id': 'entry-3', 'price': 241.65, 'quantity': 50}
    gps.add_position(position_id, entry_data_1)
    
    print(f"\n✅ Position 1 created (status: open)")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    
    # Try to create second position while first is open
    entry_data_2 = {'node_id': 'entry-3', 'price': 235.40, 'quantity': 50}
    
    try:
        gps.add_position(position_id, entry_data_2)
        print(f"\n❌ FAILED: Should have blocked second position!")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"\n✅ Correctly blocked second position:")
        print(f"   Error: {str(e)}")
        assert "already has an open transaction" in str(e)


def test_sequential_positions():
    """Test sequential positions after closing"""
    print("\n" + "="*80)
    print("TEST 3: Sequential Positions After Close")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id = "entry-3-pos1"
    
    # Position 1: Open → Close
    entry_data_1 = {'node_id': 'entry-3', 'price': 241.65, 'quantity': 50, 'reEntryNum': 0}
    gps.add_position(position_id, entry_data_1)
    
    print(f"\n✅ Position 1 created:")
    print(f"   position_num: {gps.get_position(position_id)['position_num']}")
    print(f"   status: open")
    
    # Close position 1
    exit_data_1 = {'price': 185.30, 'reason': 'EOD'}
    gps.close_position(position_id, exit_data_1)
    
    print(f"\n✅ Position 1 closed:")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    
    # Position 2: Open
    entry_data_2 = {'node_id': 'entry-3', 'price': 235.40, 'quantity': 50, 'reEntryNum': 1}
    gps.add_position(position_id, entry_data_2)
    
    pos2 = gps.get_position(position_id)
    print(f"\n✅ Position 2 created:")
    print(f"   position_num: {pos2['position_num']}")
    print(f"   reEntryNum: {pos2['reEntryNum']}")
    print(f"   status: open")
    
    assert pos2['position_num'] == 2, "Second position should have position_num = 2"
    assert gps.get_latest_position_num(position_id) == 2, "Latest position_num should be 2"
    assert gps.has_open_position(position_id) == True, "Should have open position"
    
    # Close position 2
    exit_data_2 = {'price': 220.50, 'reason': 'Target'}
    gps.close_position(position_id, exit_data_2)
    
    print(f"\n✅ Position 2 closed:")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    
    # Position 3: Open
    entry_data_3 = {'node_id': 'entry-3', 'price': 228.90, 'quantity': 50, 'reEntryNum': 2}
    gps.add_position(position_id, entry_data_3)
    
    pos3 = gps.get_position(position_id)
    print(f"\n✅ Position 3 created:")
    print(f"   position_num: {pos3['position_num']}")
    print(f"   reEntryNum: {pos3['reEntryNum']}")
    
    assert pos3['position_num'] == 3, "Third position should have position_num = 3"
    assert gps.get_latest_position_num(position_id) == 3, "Latest position_num should be 3"
    
    print(f"\n✅ All assertions passed for sequential positions")


def test_reset_day():
    """Test that position counters reset on new day"""
    print("\n" + "="*80)
    print("TEST 4: Reset Day Clears Counters")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id = "entry-3-pos1"
    
    # Day 1: Create 2 positions
    entry_1 = {'node_id': 'entry-3', 'price': 241.65, 'quantity': 50}
    gps.add_position(position_id, entry_1)
    gps.close_position(position_id, {'price': 185.30})
    
    entry_2 = {'node_id': 'entry-3', 'price': 235.40, 'quantity': 50}
    gps.add_position(position_id, entry_2)
    
    print(f"\n✅ Day 1 - Position 2 created:")
    print(f"   position_num: {gps.get_position(position_id)['position_num']}")
    print(f"   latest_position_num: {gps.get_latest_position_num(position_id)}")
    
    assert gps.get_position(position_id)['position_num'] == 2
    
    # Reset day
    gps.reset_day(datetime.now())
    
    print(f"\n✅ Day reset:")
    print(f"   position_counters: {gps.position_counters}")
    print(f"   latest_position_num: {gps.get_latest_position_num(position_id)}")
    
    assert gps.position_counters == {}, "Counters should be reset"
    assert gps.get_latest_position_num(position_id) == 0, "Latest should be 0 after reset"
    
    # Day 2: Position numbering starts from 1 again
    gps.close_position(position_id, {'price': 220.50})  # Close day 1 position
    
    entry_3 = {'node_id': 'entry-3', 'price': 228.90, 'quantity': 50}
    gps.add_position(position_id, entry_3)
    
    pos_day2 = gps.get_position(position_id)
    print(f"\n✅ Day 2 - Position created:")
    print(f"   position_num: {pos_day2['position_num']}")
    
    assert pos_day2['position_num'] == 1, "Day 2 should start from position_num = 1"
    
    print(f"\n✅ Day reset test passed")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  STEP 1: GPS position_num Tracking Tests")
    print("="*80)
    
    try:
        test_position_num_tracking()
        test_block_concurrent_positions()
        test_sequential_positions()
        test_reset_day()
        
        print("\n" + "="*80)
        print("  ✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nSTEP 1 is working correctly. Ready for STEP 2!")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
