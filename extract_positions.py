#!/usr/bin/env python3
"""
Extract full diagnostics + position information from backtest.
No code changes - only reading from context.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from run_quick_backtest import run_backtest

def extract_full_results():
    """Run backtest and extract diagnostics + positions."""
    print("="*80)
    print("RUNNING BACKTEST TO EXTRACT DIAGNOSTICS + POSITIONS")
    print("="*80)
    
    # Run backtest
    engine = run_backtest()
    
    # Extract diagnostics from strategy_state (no code changes!)
    active_strategies = engine.centralized_processor.strategy_manager.active_strategies
    
    if not active_strategies:
        print("❌ No active strategies found!")
        return None
    
    # Get first strategy
    strategy_state = list(active_strategies.values())[0]
    
    # Extract diagnostics
    diagnostics = strategy_state.get('diagnostics')
    if not diagnostics:
        print("❌ No diagnostics found!")
        return None
    
    # Build complete export
    full_export = {
        "metadata": {
            "strategy_id": strategy_state['strategy_id'],
            "instance_id": strategy_state['instance_id'],
            "user_id": strategy_state['user_id'],
            "account_id": strategy_state['account_id']
        },
        "diagnostics": {
            "events_history": diagnostics.get_all_events({
                'node_events_history': strategy_state.get('node_events_history', {})
            }),
            "current_state": diagnostics.get_all_current_states({
                'node_current_state': strategy_state.get('node_current_state', {})
            })
        },
        "positions": {
            "all_positions": strategy_state.get('positions', {}),
            "position_count": len(strategy_state.get('positions', {}))
        },
        "gps": None,  # Will extract from context_manager
        "node_states": strategy_state.get('node_states', {}),
        "strategy_config": strategy_state['config']
    }
    
    # Extract GPS (Global Position Store) from context_manager
    context_manager = strategy_state.get('context_manager')
    if context_manager and hasattr(context_manager, 'gps'):
        gps = context_manager.gps
        full_export['gps'] = {
            "all_positions": gps.get_all_positions(),
            "position_summary": {
                "total_positions": len(gps.get_all_positions()),
                "open_positions": len([p for p in gps.get_all_positions().values() if p.get('status') == 'open']),
                "closed_positions": len([p for p in gps.get_all_positions().values() if p.get('status') == 'closed'])
            }
        }
    
    # Save to file
    output_file = "full_diagnostics_and_positions.json"
    with open(output_file, 'w') as f:
        json.dump(full_export, f, indent=2, default=str)
    
    print(f"\n✅ Full export saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total nodes with events: {len(full_export['diagnostics']['events_history'])}")
    print(f"Nodes in current state: {len(full_export['diagnostics']['current_state'])}")
    print(f"Strategy positions: {full_export['positions']['position_count']}")
    
    if full_export['gps']:
        print(f"GPS total positions: {full_export['gps']['position_summary']['total_positions']}")
        print(f"  - Open: {full_export['gps']['position_summary']['open_positions']}")
        print(f"  - Closed: {full_export['gps']['position_summary']['closed_positions']}")
    
    return full_export

if __name__ == '__main__':
    result = extract_full_results()
    
    if result:
        print("\n" + "="*80)
        print("✅ EXTRACTION COMPLETE!")
        print("="*80)
        print("\nFiles created:")
        print("  1. full_diagnostics_and_positions.json - Complete export")
        print("  2. diagnostics_export.json - Diagnostics only (from view_diagnostics.py)")
    else:
        print("\n❌ Extraction failed!")
        sys.exit(1)
