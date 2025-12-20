"""
Test STEP 3: ReEntrySignalNode - Explicit first, then Implicit conditions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.core.gps import GlobalPositionStore
from src.utils.context_manager import ContextManager
from strategy.nodes.entry_node import EntryNode
from strategy.nodes.re_entry_signal_node import ReEntrySignalNode


def test_explicit_conditions_first():
    """
    Test: Explicit conditions are evaluated FIRST
    If explicit fail → Stay ACTIVE
    """
    print("\n" + "="*80)
    print("TEST 1: Explicit Conditions Evaluated First")
    print("="*80)
    
    # Create mock EntryNode
    entry_config = {
        'label': 'Entry 1',
        'maxEntries': 3,
        'positions': [{'id': 'entry-3-pos1', 'vpi': 'entry-3-pos1'}]
    }
    entry_node = EntryNode('entry-3', entry_config)
    
    # Create ReEntrySignalNode with failing conditions
    reentry_config = {
        'label': 'Re-Entry 1',
        'conditions': [
            {
                'lhs': {'type': 'number', 'value': 1},
                'operator': '>',
                'rhs': {'type': 'number', 'value': 10}  # 1 > 10 = FALSE
            }
        ]
    }
    reentry_node = ReEntrySignalNode('reentry-1', reentry_config)
    reentry_node.children = ['entry-3']
    
    # Setup context
    context_manager = ContextManager()  # Creates its own GPS
    gps = context_manager.gps  # Use the GPS from context_manager
    gps.set_current_tick_time(datetime.now())
    
    context = {
        'current_timestamp': datetime.now(),
        'context_manager': context_manager,
        'node_instances': {
            'entry-3': entry_node,
            'reentry-1': reentry_node
        },
        'node_states': {}
    }
    
    # Mark reentry node as active
    reentry_node.mark_active(context)
    
    # Execute
    result = reentry_node._execute_node_logic(context)
    
    print(f"\n✅ Test Results:")
    print(f"   signal_emitted: {result.get('signal_emitted')}")
    print(f"   logic_completed: {result.get('logic_completed')}")
    print(f"   reason: {result.get('reason')}")
    
    # Verify: Explicit conditions failed → Stay ACTIVE
    assert result.get('signal_emitted') == False, "Signal should not be emitted"
    assert result.get('logic_completed') == False, "Logic should not complete"
    assert result.get('reason') == 'Explicit conditions not satisfied'
    assert reentry_node.is_active(context) == True, "Should stay ACTIVE"
    
    print(f"\n✅ VERIFIED: Explicit conditions failed → Node stays ACTIVE")


def test_implicit_check_max_entries():
    """
    Test: Implicit Check 1 - position_num < maxEntries
    If position_num >= maxEntries → Mark INACTIVE permanently
    """
    print("\n" + "="*80)
    print("TEST 2: Implicit Check - Max Entries Reached")
    print("="*80)
    
    # Create EntryNode with maxEntries = 2
    entry_config = {
        'label': 'Entry 1',
        'maxEntries': 2,  # Only 2 positions allowed
        'positions': [{'id': 'entry-3-pos1', 'vpi': 'entry-3-pos1'}]
    }
    entry_node = EntryNode('entry-3', entry_config)
    
    # Create ReEntrySignalNode with PASSING explicit conditions
    # We need conditions that PASS so we can test implicit checks
    reentry_config = {
        'label': 'Re-Entry 1',
        'conditions': []  # No conditions = always pass
    }
    reentry_node = ReEntrySignalNode('reentry-1', reentry_config)
    reentry_node.children = ['entry-3']
    
    # Setup GPS with 2 positions already created
    context_manager = ContextManager()  # Creates its own GPS
    gps = context_manager.gps  # Use the GPS from context_manager
    gps.set_current_tick_time(datetime.now())
    
    position_id = 'entry-3-pos1'
    
    # Position 1
    gps.add_position(position_id, {'node_id': 'entry-3', 'price': 100})
    gps.close_position(position_id, {'price': 95})
    
    # Position 2
    gps.add_position(position_id, {'node_id': 'entry-3', 'price': 105})
    gps.close_position(position_id, {'price': 110})
    
    # Debug: Check counter state
    print(f"\n✅ Setup:")
    print(f"   maxEntries: {entry_node.maxEntries}")
    print(f"   latest_position_num: {gps.get_latest_position_num(position_id)}")
    print(f"   counter value: {gps.position_counters.get(position_id, 'NOT SET')}")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    
    context = {
        'current_timestamp': datetime.now(),
        'context_manager': context_manager,
        'node_instances': {
            'entry-3': entry_node,
            'reentry-1': reentry_node
        },
        'node_states': {}
    }
    
    # Mark reentry node as active
    reentry_node.mark_active(context)
    entry_node.mark_inactive(context)  # Entry node inactive
    
    # Execute
    result = reentry_node._execute_node_logic(context)
    
    print(f"\n✅ Debug:")
    print(f"   GPS position_num: {gps.get_latest_position_num(position_id)}")
    print(f"   maxEntries from node: {entry_node.maxEntries}")
    print(f"   Check: {gps.get_latest_position_num(position_id)} >= {entry_node.maxEntries} = {gps.get_latest_position_num(position_id) >= entry_node.maxEntries}")
    
    print(f"\n✅ Test Results:")
    print(f"   signal_emitted: {result.get('signal_emitted')}")
    print(f"   logic_completed: {result.get('logic_completed')}")
    print(f"   reason: {result.get('reason')}")
    print(f"   node_status: {'ACTIVE' if reentry_node.is_active(context) else 'INACTIVE'}")
    
    # Verify: Max entries reached → Mark INACTIVE
    assert result.get('signal_emitted') == False
    assert result.get('logic_completed') == False
    assert 'Max entries reached' in result.get('reason', '')
    assert reentry_node.is_active(context) == False, "Should be marked INACTIVE"
    
    print(f"\n✅ VERIFIED: Max entries reached → Node marked INACTIVE permanently")


def test_implicit_check_open_position():
    """
    Test: Implicit Check 2 - No open position for position_id
    If position open → Skip (visited=True), stay ACTIVE
    """
    print("\n" + "="*80)
    print("TEST 3: Implicit Check - Position Already Open")
    print("="*80)
    
    # Create EntryNode with maxEntries = 3
    entry_config = {
        'label': 'Entry 1',
        'maxEntries': 3,
        'positions': [{'id': 'entry-3-pos1', 'vpi': 'entry-3-pos1'}]
    }
    entry_node = EntryNode('entry-3', entry_config)
    
    # Create ReEntrySignalNode with PASSING explicit conditions
    reentry_config = {
        'label': 'Re-Entry 1',
        'conditions': []  # No conditions = always pass
    }
    reentry_node = ReEntrySignalNode('reentry-1', reentry_config)
    reentry_node.children = ['entry-3']
    
    # Setup GPS with 1 OPEN position
    context_manager = ContextManager()  # Creates its own GPS
    gps = context_manager.gps  # Use the GPS from context_manager
    gps.set_current_tick_time(datetime.now())
    
    position_id = 'entry-3-pos1'
    gps.add_position(position_id, {'node_id': 'entry-3', 'price': 100})  # OPEN
    
    print(f"\n✅ Setup:")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    print(f"   latest_position_num: {gps.get_latest_position_num(position_id)}")
    
    context = {
        'current_timestamp': datetime.now(),
        'context_manager': context_manager,
        'node_instances': {
            'entry-3': entry_node,
            'reentry-1': reentry_node
        },
        'node_states': {}
    }
    
    reentry_node.mark_active(context)
    entry_node.mark_inactive(context)
    
    # Execute
    result = reentry_node._execute_node_logic(context)
    
    print(f"\n✅ Test Results:")
    print(f"   signal_emitted: {result.get('signal_emitted')}")
    print(f"   logic_completed: {result.get('logic_completed')}")
    print(f"   reason: {result.get('reason')}")
    print(f"   node_status: {'ACTIVE' if reentry_node.is_active(context) else 'INACTIVE'}")
    
    # Verify: Position open → Skip but stay ACTIVE
    assert result.get('signal_emitted') == False
    assert result.get('logic_completed') == False
    assert 'Position already open' in result.get('reason', '')
    assert reentry_node.is_active(context) == True, "Should stay ACTIVE"
    
    print(f"\n✅ VERIFIED: Position open → Skipped (visited=True), stays ACTIVE")


def test_implicit_check_entry_node_active():
    """
    Test: Implicit Check 3 - Target EntryNode must be INACTIVE
    If EntryNode ACTIVE → Skip (visited=True), stay ACTIVE
    """
    print("\n" + "="*80)
    print("TEST 4: Implicit Check - Entry Node Still Active")
    print("="*80)
    
    # Create EntryNode
    entry_config = {
        'label': 'Entry 1',
        'maxEntries': 3,
        'positions': [{'id': 'entry-3-pos1', 'vpi': 'entry-3-pos1'}]
    }
    entry_node = EntryNode('entry-3', entry_config)
    
    # Create ReEntrySignalNode with PASSING explicit conditions
    reentry_config = {
        'label': 'Re-Entry 1',
        'conditions': []  # No conditions = always pass
    }
    reentry_node = ReEntrySignalNode('reentry-1', reentry_config)
    reentry_node.children = ['entry-3']
    
    # Setup GPS (no positions)
    context_manager = ContextManager()  # Creates its own GPS
    gps = context_manager.gps  # Use the GPS from context_manager
    gps.set_current_tick_time(datetime.now())
    
    context = {
        'current_timestamp': datetime.now(),
        'context_manager': context_manager,
        'node_instances': {
            'entry-3': entry_node,
            'reentry-1': reentry_node
        },
        'node_states': {}
    }
    
    reentry_node.mark_active(context)
    entry_node.mark_active(context)  # Entry node ACTIVE!
    
    print(f"\n✅ Setup:")
    print(f"   entry_node_active: {entry_node.is_active(context)}")
    
    # Execute
    result = reentry_node._execute_node_logic(context)
    
    print(f"\n✅ Test Results:")
    print(f"   signal_emitted: {result.get('signal_emitted')}")
    print(f"   logic_completed: {result.get('logic_completed')}")
    print(f"   reason: {result.get('reason')}")
    print(f"   node_status: {'ACTIVE' if reentry_node.is_active(context) else 'INACTIVE'}")
    
    # Verify: Entry node ACTIVE → Skip but stay ACTIVE
    assert result.get('signal_emitted') == False
    assert result.get('logic_completed') == False
    assert 'EntryNode still ACTIVE' in result.get('reason', '')
    assert reentry_node.is_active(context) == True, "Should stay ACTIVE"
    
    print(f"\n✅ VERIFIED: Entry node ACTIVE → Skipped (visited=True), stays ACTIVE")


def test_all_conditions_pass():
    """
    Test: All conditions pass → Activate children
    """
    print("\n" + "="*80)
    print("TEST 5: All Conditions Pass → Activate Children")
    print("="*80)
    
    # Create EntryNode
    entry_config = {
        'label': 'Entry 1',
        'maxEntries': 3,
        'positions': [{'id': 'entry-3-pos1', 'vpi': 'entry-3-pos1'}]
    }
    entry_node = EntryNode('entry-3', entry_config)
    
    # Create ReEntrySignalNode with PASSING explicit conditions
    reentry_config = {
        'label': 'Re-Entry 1',
        'conditions': []  # No conditions = always pass
    }
    reentry_node = ReEntrySignalNode('reentry-1', reentry_config)
    reentry_node.children = ['entry-3']
    
    # Setup GPS with 1 closed position
    context_manager = ContextManager()  # Creates its own GPS
    gps = context_manager.gps  # Use the GPS from context_manager
    gps.set_current_tick_time(datetime.now())
    
    position_id = 'entry-3-pos1'
    gps.add_position(position_id, {'node_id': 'entry-3', 'price': 100})
    gps.close_position(position_id, {'price': 110})  # CLOSED
    
    print(f"\n✅ Setup:")
    print(f"   maxEntries: {entry_node.maxEntries}")
    print(f"   latest_position_num: {gps.get_latest_position_num(position_id)}")
    print(f"   has_open_position: {gps.has_open_position(position_id)}")
    print(f"   entry_node_active: False")
    
    context = {
        'current_timestamp': datetime.now(),
        'context_manager': context_manager,
        'node_instances': {
            'entry-3': entry_node,
            'reentry-1': reentry_node
        },
        'node_states': {}
    }
    
    reentry_node.mark_active(context)
    entry_node.mark_inactive(context)  # Entry node INACTIVE
    
    # Execute
    result = reentry_node._execute_node_logic(context)
    
    print(f"\n✅ Test Results:")
    print(f"   signal_emitted: {result.get('signal_emitted')}")
    print(f"   logic_completed: {result.get('logic_completed')}")
    
    # Verify: All pass → Activate children
    assert result.get('signal_emitted') == True, "Signal should be emitted"
    assert result.get('logic_completed') == True, "Logic should complete"
    
    print(f"\n✅ VERIFIED: All conditions passed → Children will be activated")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  STEP 3: ReEntrySignalNode Tests")
    print("="*80)
    
    try:
        test_explicit_conditions_first()
        test_implicit_check_max_entries()
        test_implicit_check_open_position()
        test_implicit_check_entry_node_active()
        test_all_conditions_pass()
        
        print("\n" + "="*80)
        print("  ✅ ALL TESTS PASSED!")
        print("="*80)
        
        print("\n" + "="*80)
        print("Summary:")
        print("="*80)
        print("✅ Explicit conditions evaluated FIRST")
        print("✅ Explicit fail → Stay ACTIVE (keep trying)")
        print("✅ Implicit Check 1: position_num >= maxEntries → INACTIVE")
        print("✅ Implicit Check 2: Position open → Skip (visited=True)")
        print("✅ Implicit Check 3: Entry ACTIVE → Skip (visited=True)")
        print("✅ All pass → Activate children")
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
