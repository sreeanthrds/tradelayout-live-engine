#!/usr/bin/env python3
"""
Test that diagnostics fail loudly instead of silently.

This script intentionally breaks diagnostics in various ways
to verify that errors are caught and reported clearly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.node_diagnostics import NodeDiagnostics


def test_missing_node_id():
    """Test that missing node.id raises AttributeError."""
    print("\n" + "="*80)
    print("TEST 1: Missing node.id attribute")
    print("="*80)
    
    diagnostics = NodeDiagnostics()
    
    # Create fake node without 'id' attribute
    class FakeNode:
        pass
    
    fake_node = FakeNode()
    context = {
        'node_events_history': {},
        'node_current_state': {},
        'tick_count': 1
    }
    
    try:
        diagnostics.record_event(
            node=fake_node,
            context=context,
            event_type='test_event'
        )
        print("❌ FAIL: Should have raised AttributeError!")
        return False
    except AttributeError as e:
        print(f"✅ PASS: Raised AttributeError as expected: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Raised wrong exception: {type(e).__name__}: {e}")
        return False


def test_missing_context_keys():
    """Test that missing context keys raise KeyError."""
    print("\n" + "="*80)
    print("TEST 2: Missing context keys (node_events_history)")
    print("="*80)
    
    diagnostics = NodeDiagnostics()
    
    # Create node with id
    class FakeNode:
        def __init__(self):
            self.id = 'test-node'
    
    fake_node = FakeNode()
    
    # Context missing 'node_events_history'
    context = {
        'tick_count': 1
    }
    
    try:
        diagnostics.record_event(
            node=fake_node,
            context=context,
            event_type='test_event'
        )
        print("❌ FAIL: Should have raised KeyError!")
        return False
    except KeyError as e:
        print(f"✅ PASS: Raised KeyError as expected: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Raised wrong exception: {type(e).__name__}: {e}")
        return False


def test_update_current_state_missing_keys():
    """Test that update_current_state fails loud when context is missing keys."""
    print("\n" + "="*80)
    print("TEST 3: update_current_state with missing context keys")
    print("="*80)
    
    diagnostics = NodeDiagnostics()
    
    class FakeNode:
        def __init__(self):
            self.id = 'test-node'
    
    fake_node = FakeNode()
    
    # Context missing 'node_current_state'
    context = {
        'tick_count': 1
    }
    
    try:
        diagnostics.update_current_state(
            node=fake_node,
            context=context,
            status='active'
        )
        print("❌ FAIL: Should have raised KeyError!")
        return False
    except KeyError as e:
        print(f"✅ PASS: Raised KeyError as expected: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Raised wrong exception: {type(e).__name__}: {e}")
        return False


def test_clear_state_missing_node_id():
    """Test that clear_current_state fails loud when node has no id."""
    print("\n" + "="*80)
    print("TEST 4: clear_current_state with node missing 'id'")
    print("="*80)
    
    diagnostics = NodeDiagnostics()
    
    class FakeNode:
        pass
    
    fake_node = FakeNode()
    context = {
        'node_current_state': {}
    }
    
    try:
        diagnostics.clear_current_state(
            node=fake_node,
            context=context
        )
        print("❌ FAIL: Should have raised AttributeError!")
        return False
    except AttributeError as e:
        print(f"✅ PASS: Raised AttributeError as expected: {e}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Raised wrong exception: {type(e).__name__}: {e}")
        return False


def test_valid_operation():
    """Test that valid operations still work correctly."""
    print("\n" + "="*80)
    print("TEST 5: Valid operation (should succeed)")
    print("="*80)
    
    diagnostics = NodeDiagnostics()
    
    class FakeNode:
        def __init__(self):
            self.id = 'test-node'
            self.type = 'TestNode'
    
    fake_node = FakeNode()
    context = {
        'node_events_history': {},
        'node_current_state': {},
        'tick_count': 1,
        'current_timestamp': None,
        'node_status': {}
    }
    
    try:
        diagnostics.record_event(
            node=fake_node,
            context=context,
            event_type='test_event',
            evaluation_data={'test': 'data'}
        )
        
        # Check that event was recorded
        if 'test-node' in context['node_events_history']:
            events = list(context['node_events_history']['test-node'])
            if len(events) == 1:
                print(f"✅ PASS: Event recorded successfully: {events[0]['event_type']}")
                return True
            else:
                print(f"❌ FAIL: Wrong number of events: {len(events)}")
                return False
        else:
            print("❌ FAIL: No events recorded!")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("🧪 DIAGNOSTICS FAIL-LOUD TEST SUITE")
    print("="*80)
    print("\nThese tests verify that diagnostics fail loudly (with clear errors)")
    print("instead of failing silently when something is wrong.\n")
    
    results = []
    
    results.append(("Missing node.id", test_missing_node_id()))
    results.append(("Missing context keys (record_event)", test_missing_context_keys()))
    results.append(("Missing context keys (update_current_state)", test_update_current_state_missing_keys()))
    results.append(("Missing node.id (clear_current_state)", test_clear_state_missing_node_id()))
    results.append(("Valid operation", test_valid_operation()))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Diagnostics fail loudly as expected!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed - Diagnostics may fail silently!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
