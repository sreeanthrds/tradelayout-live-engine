"""
Test: Position ID Independence
Demonstrates that position_num belongs to position_id
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.core.gps import GlobalPositionStore


def test_same_position_id_sequential():
    """
    Test: Same position_id → Sequential position_num (1, 2, 3, ...)
    """
    print("\n" + "="*80)
    print("TEST 1: Same Position ID → Sequential position_num")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id = "entry-3-pos1"  # SAME position_id for all
    
    print(f"\nPosition ID: {position_id}")
    print(f"{'='*60}")
    
    # Position 1
    entry1 = {'node_id': 'entry-3', 'price': 241.65, 'quantity': 50}
    gps.add_position(position_id, entry1)
    pos1 = gps.get_position(position_id)
    print(f"\n✅ Position 1 created:")
    print(f"   position_id: {pos1['position_id']}")
    print(f"   position_num: {pos1['position_num']}")
    print(f"   status: {pos1['status']}")
    
    # Close position 1
    gps.close_position(position_id, {'price': 185.30})
    print(f"\n✅ Position 1 closed")
    
    # Position 2 (SAME position_id)
    entry2 = {'node_id': 'entry-3', 'price': 235.40, 'quantity': 50}
    gps.add_position(position_id, entry2)
    pos2 = gps.get_position(position_id)
    print(f"\n✅ Position 2 created:")
    print(f"   position_id: {pos2['position_id']}")
    print(f"   position_num: {pos2['position_num']}")
    print(f"   status: {pos2['status']}")
    
    # Close position 2
    gps.close_position(position_id, {'price': 220.50})
    print(f"\n✅ Position 2 closed")
    
    # Position 3 (SAME position_id)
    entry3 = {'node_id': 'entry-3', 'price': 228.90, 'quantity': 50}
    gps.add_position(position_id, entry3)
    pos3 = gps.get_position(position_id)
    print(f"\n✅ Position 3 created:")
    print(f"   position_id: {pos3['position_id']}")
    print(f"   position_num: {pos3['position_num']}")
    print(f"   status: {pos3['status']}")
    
    # Verify all belong to SAME position_id by checking transactions
    final_pos = gps.get_position(position_id)
    transactions = final_pos.get('transactions', [])
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"   All positions share position_id: '{position_id}'")
    print(f"   Total transactions: {len(transactions)}")
    for i, txn in enumerate(transactions, 1):
        print(f"   Transaction {i}: position_num = {txn['position_num']}, status = {txn['status']}")
    print(f"   Sequential numbering: 1 → 2 → 3 ✅")
    
    assert len(transactions) == 3
    assert transactions[0]['position_num'] == 1
    assert transactions[1]['position_num'] == 2
    assert transactions[2]['position_num'] == 3
    assert all(txn['position_id'] == position_id for txn in transactions)
    
    print(f"\n✅ VERIFIED: Same position_id → Sequential position_num")


def test_different_position_ids_independent():
    """
    Test: Different position_ids → Independent counters
    """
    print("\n" + "="*80)
    print("TEST 2: Different Position IDs → Independent Counters")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    position_id_A = "entry-3-pos1"  # Position ID A
    position_id_B = "entry-5-pos1"  # Position ID B (different entry node)
    
    print(f"\nTwo Different Position IDs:")
    print(f"   Position ID A: {position_id_A}")
    print(f"   Position ID B: {position_id_B}")
    print(f"{'='*60}")
    
    # Position A1
    entry_a1 = {'node_id': 'entry-3', 'price': 241.65, 'quantity': 50}
    gps.add_position(position_id_A, entry_a1)
    pos_a1 = gps.get_position(position_id_A)
    print(f"\n✅ Position A1 created:")
    print(f"   position_id: {pos_a1['position_id']}")
    print(f"   position_num: {pos_a1['position_num']}")
    
    # Position B1 (different position_id)
    entry_b1 = {'node_id': 'entry-5', 'price': 150.30, 'quantity': 50}
    gps.add_position(position_id_B, entry_b1)
    pos_b1 = gps.get_position(position_id_B)
    print(f"\n✅ Position B1 created:")
    print(f"   position_id: {pos_b1['position_id']}")
    print(f"   position_num: {pos_b1['position_num']}")
    
    # Close both
    gps.close_position(position_id_A, {'price': 185.30})
    gps.close_position(position_id_B, {'price': 145.20})
    
    # Position A2 (same as A)
    entry_a2 = {'node_id': 'entry-3', 'price': 235.40, 'quantity': 50}
    gps.add_position(position_id_A, entry_a2)
    pos_a2 = gps.get_position(position_id_A)
    print(f"\n✅ Position A2 created:")
    print(f"   position_id: {pos_a2['position_id']}")
    print(f"   position_num: {pos_a2['position_num']}")
    
    # Position B2 (same as B)
    entry_b2 = {'node_id': 'entry-5', 'price': 148.90, 'quantity': 50}
    gps.add_position(position_id_B, entry_b2)
    pos_b2 = gps.get_position(position_id_B)
    print(f"\n✅ Position B2 created:")
    print(f"   position_id: {pos_b2['position_id']}")
    print(f"   position_num: {pos_b2['position_num']}")
    
    # Verify independence by checking transactions
    final_pos_a = gps.get_position(position_id_A)
    final_pos_b = gps.get_position(position_id_B)
    
    txns_a = final_pos_a.get('transactions', [])
    txns_b = final_pos_b.get('transactions', [])
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"   Position A: ID = '{position_id_A}'")
    print(f"      Transactions: {len(txns_a)}")
    for i, txn in enumerate(txns_a, 1):
        print(f"      A{i}: position_num = {txn['position_num']}")
    
    print(f"\n   Position B: ID = '{position_id_B}'")
    print(f"      Transactions: {len(txns_b)}")
    for i, txn in enumerate(txns_b, 1):
        print(f"      B{i}: position_num = {txn['position_num']}")
    
    print(f"\n   ✅ INDEPENDENT: Each position_id has its own counter!")
    
    assert len(txns_a) == 2
    assert len(txns_b) == 2
    assert txns_a[0]['position_num'] == 1  # A counter: 1
    assert txns_a[1]['position_num'] == 2  # A counter: 2
    assert txns_b[0]['position_num'] == 1  # B counter: 1 (independent)
    assert txns_b[1]['position_num'] == 2  # B counter: 2 (independent)
    assert final_pos_a['position_id'] != final_pos_b['position_id']
    
    print(f"\n✅ VERIFIED: Different position_ids → Independent counters")


def test_visual_representation():
    """
    Visual representation of position_id and position_num relationship
    """
    print("\n" + "="*80)
    print("TEST 3: Visual Representation")
    print("="*80)
    
    gps = GlobalPositionStore()
    gps.set_current_tick_time(datetime.now())
    
    # Create multiple positions across different position_ids
    positions_data = [
        ("entry-3-pos1", "entry-3", 241.65),
        ("entry-3-pos1", "entry-3", 235.40),  # Re-entry
        ("entry-5-pos1", "entry-5", 150.30),
        ("entry-3-pos1", "entry-3", 228.90),  # Another re-entry
        ("entry-5-pos1", "entry-5", 148.90),  # Re-entry
    ]
    
    print("\n" + "="*80)
    print("Creating Positions:")
    print("="*80)
    
    results = []
    for pos_id, node_id, price in positions_data:
        # Close previous if exists
        if gps.has_open_position(pos_id):
            gps.close_position(pos_id, {'price': price - 10})
        
        # Create new
        entry = {'node_id': node_id, 'price': price, 'quantity': 50}
        gps.add_position(pos_id, entry)
        pos = gps.get_position(pos_id)
        
        results.append({
            'position_id': pos['position_id'],
            'position_num': pos['position_num'],
            'node_id': node_id,
            'price': price
        })
        
        print(f"   Created: position_id='{pos_id}', position_num={pos['position_num']}, price={price}")
    
    # Show final structure
    print("\n" + "="*80)
    print("Final Structure:")
    print("="*80)
    
    print(f"\n📊 Position ID: 'entry-3-pos1'")
    print(f"   ├─ position_num: 1 (first entry)")
    print(f"   ├─ position_num: 2 (re-entry 1)")
    print(f"   └─ position_num: 3 (re-entry 2)")
    
    print(f"\n📊 Position ID: 'entry-5-pos1'")
    print(f"   ├─ position_num: 1 (first entry)")
    print(f"   └─ position_num: 2 (re-entry 1)")
    
    print(f"\n{'='*80}")
    print(f"Key Concept:")
    print(f"{'='*80}")
    print(f"   • position_id = Entry node identifier (constant)")
    print(f"   • position_num = Sequential number per position_id (1, 2, 3, ...)")
    print(f"   • Different position_ids → Independent counters")
    print(f"   • Same position_id → Sequential numbering")
    
    # Verify counters
    assert gps.get_latest_position_num("entry-3-pos1") == 3
    assert gps.get_latest_position_num("entry-5-pos1") == 2
    
    print(f"\n✅ VERIFIED: Concept is correctly implemented")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  Position ID Independence Tests")
    print("="*80)
    
    try:
        test_same_position_id_sequential()
        test_different_position_ids_independent()
        test_visual_representation()
        
        print("\n" + "="*80)
        print("  ✅ ALL TESTS PASSED!")
        print("="*80)
        
        print("\n" + "="*80)
        print("Summary:")
        print("="*80)
        print("✅ Same position_id → position_num increments (1, 2, 3, ...)")
        print("✅ Different position_ids → Independent counters")
        print("✅ Each position_id tracks its own sequence")
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
