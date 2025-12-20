#!/usr/bin/env python3
"""Convert diagnostics_export.json to SESSION_SUMMARY.json.

Reads ONLY from diagnostics (no GPS/context needed) and creates trade summary.
This makes diagnostics the single source of truth for both events and summaries.

SESSION_SUMMARY.json is used for both backtesting and live trading to provide
a unified format for displaying positions, P&L, and summary statistics.
"""

import json
import os
from datetime import datetime, date
from typing import Dict, List, Any, Optional


def load_diagnostics(filepath: str) -> Dict[str, Any]:
    """Load diagnostics_export.json."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_entry_events(events_history: Dict[str, List[Dict]]) -> List[Dict]:
    """Extract all entry events from events_history."""
    entries = []
    
    for node_id, events in events_history.items():
        if node_id.startswith('entry-') and not node_id.startswith('entry-condition'):
            for event in events:
                if event.get('position'):
                    entries.append({
                        'node_id': node_id,
                        'event': event
                    })
    
    return entries


def extract_exit_events(events_history: Dict[str, List[Dict]]) -> List[Dict]:
    """Extract all exit events from events_history."""
    exits = []
    
    for node_id, events in events_history.items():
        if node_id.startswith('exit-') and not node_id.startswith('exit-condition'):
            for event in events:
                if event.get('exit_result'):
                    exits.append({
                        'node_id': node_id,
                        'event': event
                    })
    
    return exits


def match_entry_exit(entries: List[Dict], exits: List[Dict]) -> List[Dict]:
    """Match entries with exits by position_id and create trade summary."""
    trades = []
    
    # Create exit lookup by position_id
    exit_by_position = {}
    for exit_info in exits:
        event = exit_info['event']
        action = event.get('action', {})
        target_pos_id = action.get('target_position_id')
        if target_pos_id:
            exit_by_position[target_pos_id] = exit_info
    
    # Match entries with exits
    for entry_info in entries:
        entry_event = entry_info['event']
        position = entry_event.get('position', {})
        position_id = position.get('position_id')
        
        if not position_id:
            continue
        
        entry_config = entry_event.get('entry_config', {})
        
        # Find matching exit
        exit_info = exit_by_position.get(position_id)
        
        if exit_info:
            exit_event = exit_info['event']
            exit_result = exit_event.get('exit_result', {})
            
            trade = {
                'position_id': position_id,
                'symbol': position.get('symbol'),
                'side': position.get('side'),
                'quantity': position.get('quantity'),
                'entry_price': position.get('entry_price'),
                'exit_price': exit_result.get('exit_price'),
                'entry_time': position.get('entry_time'),
                'exit_time': exit_result.get('exit_time'),
                'pnl': exit_result.get('pnl'),
                'pnl_percent': round((exit_result.get('pnl', 0) / (position.get('entry_price', 1) * position.get('quantity', 1))) * 100, 2) if exit_result.get('pnl') else None,
                're_entry_num': entry_config.get('re_entry_num'),
                'position_num': entry_config.get('position_num'),
                'entry_node': entry_info['node_id'],
                'exit_node': exit_info['node_id'],
            }
        else:
            # Open position (no exit yet)
            trade = {
                'position_id': position_id,
                'symbol': position.get('symbol'),
                'side': position.get('side'),
                'quantity': position.get('quantity'),
                'entry_price': position.get('entry_price'),
                'exit_price': None,
                'entry_time': position.get('entry_time'),
                'exit_time': None,
                'pnl': None,
                'pnl_percent': None,
                're_entry_num': entry_config.get('re_entry_num'),
                'position_num': entry_config.get('position_num'),
                'entry_node': entry_info['node_id'],
                'exit_node': None,
            }
        
        trades.append(trade)
    
    # Sort by entry_time
    trades.sort(key=lambda t: t.get('entry_time', ''))
    
    # Add position_number (1-indexed)
    for idx, trade in enumerate(trades, start=1):
        trade['position_number'] = idx
    
    return trades


def calculate_summary(trades: List[Dict], events_history: Dict, current_state: Dict) -> Dict:
    """Calculate summary statistics."""
    closed_trades = [t for t in trades if t.get('pnl') is not None]
    open_trades = [t for t in trades if t.get('pnl') is None]
    
    total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
    winning = [t for t in closed_trades if t.get('pnl', 0) > 0]
    losing = [t for t in closed_trades if t.get('pnl', 0) < 0]
    
    win_rate = (len(winning) / len(closed_trades) * 100) if closed_trades else 0
    
    return {
        'total_positions': len(trades),
        'closed_positions': len(closed_trades),
        'open_positions': len(open_trades),
        'total_pnl': round(total_pnl, 2),
        'win_rate_percent': round(win_rate, 1),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'nodes_with_events': len(events_history),
        'active_nodes_remaining': len(current_state),
    }


def extract_session_date(trades: List[Dict]) -> Optional[str]:
    """Extract session date from first trade entry time."""
    if not trades:
        return None
    
    first_trade = trades[0]
    entry_time = first_trade.get('entry_time')
    
    if entry_time:
        # Parse datetime and extract date
        try:
            if isinstance(entry_time, str):
                # Handle ISO format with timezone
                dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                return dt.date().isoformat()
        except:
            pass
    
    return None


def convert(input_file: str, output_file: str, strategy_id: str = None, session_type: str = 'backtest'):
    """Main conversion function."""
    print(f"📖 Loading diagnostics from: {input_file}")
    diagnostics = load_diagnostics(input_file)
    
    events_history = diagnostics.get('events_history', {})
    current_state = diagnostics.get('current_state', {})
    
    print(f"📊 Extracting entry/exit events...")
    entries = extract_entry_events(events_history)
    exits = extract_exit_events(events_history)
    
    print(f"   Found {len(entries)} entries, {len(exits)} exits")
    
    print(f"🔗 Matching entries with exits...")
    trades = match_entry_exit(entries, exits)
    
    print(f"📈 Calculating summary...")
    summary = calculate_summary(trades, events_history, current_state)
    
    # Extract session date from trades
    session_date = extract_session_date(trades)
    
    # Determine session status
    session_status = 'completed' if summary['open_positions'] == 0 else 'in_progress'
    
    result = {
        'metadata': {
            'session_date': session_date,
            'strategy_id': strategy_id,
            'session_type': session_type,
            'session_status': session_status,
            'last_updated': datetime.now().isoformat(),
            'generated_from': 'diagnostics_export.json'
        },
        'summary': summary,
        'positions': trades,
    }
    
    print(f"💾 Writing results to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✅ Conversion complete!")
    print(f"   Session Date: {session_date}")
    print(f"   Session Status: {session_status}")
    print(f"   Total Positions: {summary['total_positions']}")
    print(f"   Open Positions: {summary['open_positions']}")
    print(f"   Total P&L: ₹{summary['total_pnl']}")
    print(f"   Win Rate: {summary['win_rate_percent']}%")


if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'diagnostics_export.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'SESSION_SUMMARY.json'
    strategy_id = sys.argv[3] if len(sys.argv) > 3 else None
    session_type = sys.argv[4] if len(sys.argv) > 4 else 'backtest'
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)
    
    convert(input_file, output_file, strategy_id, session_type)
