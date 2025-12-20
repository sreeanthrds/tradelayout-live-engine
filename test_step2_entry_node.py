"""
Test STEP 2: EntryNode maxEntries field
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy.nodes.entry_node import EntryNode


def test_max_entries_default():
    """Test default maxEntries = 1"""
    print("\n" + "="*80)
    print("TEST 1: Default maxEntries = 1")
    print("="*80)
    
    # Create EntryNode without maxEntries in config
    config = {
        'label': 'Entry 1',
        'positions': [
            {
                'id': 'entry-3-pos1',
                'vpi': 'entry-3-pos1',
                'quantity': 1,
                'positionType': 'buy'
            }
        ]
    }
    
    entry_node = EntryNode('entry-3', config)
    
    print(f"\n✅ EntryNode created:")
    print(f"   node_id: {entry_node.id}")
    print(f"   maxEntries: {entry_node.maxEntries}")
    
    assert entry_node.maxEntries == 1, "Default maxEntries should be 1"
    print(f"\n✅ Assertion passed: maxEntries defaults to 1")


def test_max_entries_custom():
    """Test custom maxEntries value"""
    print("\n" + "="*80)
    print("TEST 2: Custom maxEntries = 9")
    print("="*80)
    
    # Create EntryNode with maxEntries = 9
    config = {
        'label': 'Entry 1',
        'maxEntries': 9,  # 1 initial + 8 re-entries
        'positions': [
            {
                'id': 'entry-3-pos1',
                'vpi': 'entry-3-pos1',
                'quantity': 1,
                'positionType': 'buy'
            }
        ]
    }
    
    entry_node = EntryNode('entry-3', config)
    
    print(f"\n✅ EntryNode created:")
    print(f"   node_id: {entry_node.id}")
    print(f"   maxEntries: {entry_node.maxEntries}")
    
    assert entry_node.maxEntries == 9, "Custom maxEntries should be 9"
    print(f"\n✅ Assertion passed: maxEntries set to 9 (1 initial + 8 re-entries)")


def test_get_position_id():
    """Test get_position_id helper method"""
    print("\n" + "="*80)
    print("TEST 3: Get Position ID")
    print("="*80)
    
    # Create EntryNode
    config = {
        'label': 'Entry 1',
        'positions': [
            {
                'id': 'entry-3-pos1',
                'vpi': 'entry-3-pos1',
                'quantity': 1,
                'positionType': 'buy'
            }
        ]
    }
    
    entry_node = EntryNode('entry-3', config)
    
    # Mock context (minimal)
    context = {}
    
    position_id = entry_node.get_position_id(context)
    
    print(f"\n✅ Position ID retrieved:")
    print(f"   position_id: {position_id}")
    
    assert position_id == 'entry-3-pos1', "Should use VPI as position ID"
    print(f"\n✅ Assertion passed: position_id correct")


def test_multiple_entry_nodes():
    """Test multiple entry nodes with different maxEntries"""
    print("\n" + "="*80)
    print("TEST 4: Multiple Entry Nodes")
    print("="*80)
    
    # Entry node 1: No re-entries
    config1 = {
        'label': 'Entry 1',
        'maxEntries': 1,
        'positions': [{'id': 'entry-1-pos1'}]
    }
    entry1 = EntryNode('entry-1', config1)
    
    # Entry node 2: Allow 5 entries
    config2 = {
        'label': 'Entry 2',
        'maxEntries': 5,
        'positions': [{'id': 'entry-2-pos1'}]
    }
    entry2 = EntryNode('entry-2', config2)
    
    # Entry node 3: Allow 10 entries
    config3 = {
        'label': 'Entry 3',
        'maxEntries': 10,
        'positions': [{'id': 'entry-3-pos1'}]
    }
    entry3 = EntryNode('entry-3', config3)
    
    print(f"\n✅ Multiple entry nodes created:")
    print(f"   entry-1: maxEntries = {entry1.maxEntries}")
    print(f"   entry-2: maxEntries = {entry2.maxEntries}")
    print(f"   entry-3: maxEntries = {entry3.maxEntries}")
    
    assert entry1.maxEntries == 1
    assert entry2.maxEntries == 5
    assert entry3.maxEntries == 10
    
    print(f"\n✅ All assertions passed: Each entry node has correct maxEntries")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  STEP 2: EntryNode maxEntries Tests")
    print("="*80)
    
    try:
        test_max_entries_default()
        test_max_entries_custom()
        test_get_position_id()
        test_multiple_entry_nodes()
        
        print("\n" + "="*80)
        print("  ✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nSTEP 2 is working correctly. Ready for STEP 3!")
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
