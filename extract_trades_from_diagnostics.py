#!/usr/bin/env python3
"""
Position-centric trade extraction with multi-exit support and qty simulation.

Key features:
- Trades keyed by (position_id, re_entry_num)
- Multiple exits per position with qty simulation
- Handles partial exits, over-qty, already-closed positions
- Independent entry/exit flows (not dependent on execution tree structure)
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from collections import defaultdict


def load_diagnostics(filepath: str = 'diagnostics_export.json') -> Dict:
    """Load diagnostics JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def _format_price(value) -> str:
    """Format price/amount to exactly 2 decimal places."""
    if value is None:
        return None
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return value


def _extract_exit_reason(node_name: str) -> str:
    """Extract exit reason from node name."""
    if 'SL' in node_name or 'Stop Loss' in node_name:
        return 'SL'
    elif 'Target' in node_name:
        return 'Target'
    elif 'TSL' in node_name or 'Trailing' in node_name:
        return 'TSL'
    elif 'Time' in node_name:
        return 'Time'
    else:
        return 'Other'


def build_signal_chain(events_history: Dict, exec_id: str, max_depth: int = 50, limit_to_immediate: bool = True) -> List[str]:
    """
    Build signal chain by following parent_execution_id backward.
    
    Returns list of execution_ids for signal nodes in CHRONOLOGICAL order (oldest to newest).
    Full node details can be fetched from diagnostics_export.json using these IDs.
    
    Args:
        events_history: Dict of all events
        exec_id: Starting execution ID (Entry or Exit node)
        max_depth: Maximum traversal depth
        limit_to_immediate: If True, only include signals until hitting an Entry/Exit/Start node
                           If False, traverse all the way to Start (full history)
    
    Note: max_depth set to 50 to handle deep re-entry chains (8+ re-entries)
    """
    chain = []
    current_id = exec_id
    depth = 0
    
    while current_id and current_id in events_history and depth < max_depth:
        event = events_history[current_id]
        parent_id = event.get('parent_execution_id')
        
        if parent_id and parent_id in events_history:
            parent_event = events_history[parent_id]
            node_type = parent_event.get('node_type', '')
            
            # Add parent execution_id if it's a signal/condition/start node
            if any(keyword in node_type for keyword in ['Signal', 'Condition', 'Start']):
                chain.append(parent_id)
            
            # If limiting to immediate flow, stop when we hit Entry/Exit/Start (action nodes)
            if limit_to_immediate:
                # Stop if parent is an action node (Entry/Exit) or Start
                if 'EntryNode' in node_type or 'ExitNode' in node_type or 'StartNode' in node_type:
                    break
            
            current_id = parent_id
            depth += 1
        else:
            break
    
    # Reverse to get chronological order (oldest first)
    return list(reversed(chain))


def build_position_index(events_history: Dict) -> Dict[Tuple[str, int], Dict]:
    """
    Build position index keyed by (position_id, re_entry_num).
    
    Returns:
        {
            ("entry-2-pos1", 0): {
                'entry_event': {...},
                'entry_exec_id': "...",
                'entry_qty': 1,
                'exit_events': [(timestamp, exec_id, event), ...]
            }
        }
    """
    position_index = defaultdict(lambda: {
        'entry_event': None,
        'entry_exec_id': None,
        'entry_qty': 0,
        'exit_events': []
    })
    
    # First pass: collect entries and exits
    for exec_id, event in events_history.items():
        node_type = event.get('node_type')
        
        if node_type == 'EntryNode':
            # Extract position info from entry
            position = event.get('position', {})
            position_id = position.get('position_id')
            # CRITICAL: re_entry_num is in entry_config, not position!
            re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
            
            if position_id:
                key = (position_id, re_entry_num)
                position_index[key]['entry_event'] = event
                position_index[key]['entry_exec_id'] = exec_id
                position_index[key]['entry_qty'] = position.get('actual_quantity', position.get('quantity', 1))  # Use actual_quantity (new) or fallback to quantity (old)
        
        elif node_type == 'ExitNode':
            # Extract position info from exit
            position = event.get('position', {})
            position_id = position.get('position_id')
            re_entry_num = position.get('re_entry_num', 0)
            
            # Fallback to action.target_position_id if position block missing
            if not position_id:
                position_id = event.get('action', {}).get('target_position_id')
            
            if position_id is not None:
                key = (position_id, re_entry_num)
                timestamp = event.get('timestamp')
                position_index[key]['exit_events'].append((timestamp, exec_id, event))
        
        elif node_type == 'SquareOffNode':
            # Square-off closes multiple positions at once
            # Extract list of closed positions from diagnostics
            closed_positions = event.get('closed_positions', [])
            timestamp = event.get('timestamp')
            
            for pos_info in closed_positions:
                position_id = pos_info.get('position_id')
                re_entry_num = pos_info.get('re_entry_num', 0)
                
                if position_id:
                    key = (position_id, re_entry_num)
                    # Add square-off as an exit event for this position
                    position_index[key]['exit_events'].append((timestamp, exec_id, event))
    
    # Sort exit events by timestamp for each position
    for key in position_index:
        position_index[key]['exit_events'].sort(key=lambda x: x[0])
    
    return dict(position_index)


def build_trade_for_position(
    trade_key: Tuple[str, int],
    trade_state: Dict,
    events_history: Dict
) -> Dict[str, Any]:
    """
    Build complete trade for a (position_id, re_entry_num) with:
    - entry_flow
    - exit_flows[] (with qty simulation)
    - position_summary
    """
    position_id, re_entry_num = trade_key
    entry_event = trade_state['entry_event']
    entry_exec_id = trade_state['entry_exec_id']
    entry_qty = trade_state['entry_qty']
    exit_events = trade_state['exit_events']
    
    if not entry_event:
        return None
    
    # Build signal chain (just IDs)
    signal_chain_ids = build_signal_chain(events_history, entry_exec_id)
    
    # Determine immediate trigger (for quick UI display)
    immediate_trigger = None
    if re_entry_num == 0:
        # Initial entry - triggered by entry signal
        if signal_chain_ids:
            immediate_trigger = {
                'type': 'initial_entry',
                'entry_signal_id': signal_chain_ids[0] if len(signal_chain_ids) > 0 else None
            }
    else:
        # Re-entry - triggered by re-entry signal after previous exit
        if len(signal_chain_ids) >= 2:
            immediate_trigger = {
                'type': 're_entry',
                're_entry_signal_id': signal_chain_ids[0],  # Most recent = re-entry signal
                'previous_exit_signal_id': signal_chain_ids[1],  # Before that = exit signal
                'previous_entry_num': re_entry_num - 1
            }
    
    # Build entry flow
    action = entry_event.get('action', {})
    entry_flow = {
        'execution_id': entry_exec_id,
        'node_id': entry_event['node_id'],
        'node_name': entry_event['node_name'],
        'timestamp': entry_event['timestamp'],
        'side': action.get('side'),
        'quantity': action.get('actual_quantity', action.get('quantity', entry_qty)),  # Use actual_quantity or fallback
        'price': _format_price(action.get('price')),
        'order_id': action.get('order_id'),
        'signal_chain_ids': signal_chain_ids,
        'immediate_trigger': immediate_trigger
    }
    
    # Simulate qty through exits
    remaining_qty = entry_qty
    exit_flows = []
    
    for timestamp, exit_exec_id, exit_event in exit_events:
        # Determine requested qty (default to all)
        exit_result = exit_event.get('exit_result', {})
        action = exit_event.get('action', {})
        
        # Try to get requested qty from action or result (use actual_quantity)
        position_details = action.get('position_details', {})
        requested_qty = position_details.get('actual_quantity', position_details.get('quantity', remaining_qty))
        if requested_qty is None:
            requested_qty = remaining_qty
        
        # Calculate actual closed qty
        closed_qty = min(requested_qty, remaining_qty)
        effective = closed_qty > 0
        
        # Get PNL (only if effective)
        if effective:
            pnl_raw = exit_result.get('pnl', 0)
            # Scale PNL if partial exit
            if closed_qty < requested_qty and requested_qty > 0:
                pnl_raw = pnl_raw * (closed_qty / requested_qty)
            pnl = _format_price(pnl_raw)
        else:
            pnl = "0.00"
        
        # Determine reason
        if not effective:
            reason = "position_already_closed_by_other_exit"
        else:
            reason = _extract_exit_reason(exit_event.get('node_name', ''))
        
        # Add note if requested > available
        note = None
        if requested_qty > remaining_qty and remaining_qty > 0:
            note = f"Requested {requested_qty}, but only {remaining_qty} available; closed {closed_qty}"
        elif closed_qty < entry_qty and effective:
            note = f"Partial exit: {closed_qty}/{entry_qty}"
        
        # Build exit flow
        exit_flow = {
            'execution_id': exit_exec_id,
            'node_id': exit_event['node_id'],
            'node_name': exit_event['node_name'],
            'timestamp': timestamp,
            'requested_qty': requested_qty,
            'closed_qty': closed_qty,
            'remaining_after': remaining_qty - closed_qty,
            'effective': effective,
            'exit_price': _format_price(exit_result.get('exit_price')),
            'pnl': pnl,
            'reason': reason,
            'signal_chain_ids': build_signal_chain(events_history, exit_exec_id)
        }
        
        if note:
            exit_flow['note'] = note
        
        exit_flows.append(exit_flow)
        
        # Update remaining qty
        remaining_qty -= closed_qty
    
    # Calculate position summary
    net_closed_qty = entry_qty - remaining_qty
    total_pnl = sum(float(ef['pnl']) for ef in exit_flows if ef['effective'])
    status = 'closed' if remaining_qty == 0 else 'open'
    
    # Calculate duration (entry to last effective exit)
    duration_minutes = None
    if exit_flows:
        last_effective_exit = next((ef for ef in reversed(exit_flows) if ef['effective']), None)
        if last_effective_exit:
            entry_time = datetime.fromisoformat(entry_flow['timestamp'])
            exit_time = datetime.fromisoformat(last_effective_exit['timestamp'])
            duration_minutes = round((exit_time - entry_time).total_seconds() / 60, 2)
    
    position_summary = {
        'entry_qty': entry_qty,
        'net_closed_qty': net_closed_qty,
        'remaining_qty': remaining_qty,
        'total_pnl': _format_price(total_pnl),
        'status': status,
        'duration_minutes': duration_minutes
    }
    
    # Build complete trade
    trade = {
        'position_id': position_id,
        're_entry_num': re_entry_num,
        'symbol': entry_event.get('action', {}).get('symbol', ''),
        'entry_flow': entry_flow,
        'exit_flows': exit_flows,
        'position_summary': position_summary
    }
    
    return trade


def get_all_trades(diagnostics: Dict) -> List[Dict[str, Any]]:
    """
    Extract all trades from diagnostics.
    
    Returns list of trades, one per (position_id, re_entry_num).
    """
    events_history = diagnostics.get('events_history', {})
    
    # Build position index
    position_index = build_position_index(events_history)
    
    print(f"📊 Found {len(position_index)} unique positions (including re-entries)")
    
    # Build trade for each position
    trades = []
    for trade_key, trade_state in position_index.items():
        trade = build_trade_for_position(trade_key, trade_state, events_history)
        if trade:
            trades.append(trade)
    
    # Sort by entry timestamp
    trades.sort(key=lambda t: t['entry_flow']['timestamp'])
    
    return trades


def get_daily_summary(trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate trades by day.
    
    Returns:
        Dict[date, summary_dict]
    """
    daily_trades = defaultdict(list)
    
    # Group trades by date
    for trade in trades:
        date = trade['entry_flow']['timestamp'].split(' ')[0]
        daily_trades[date].append(trade)
    
    # Calculate summary for each day
    daily_summary = {}
    for date, day_trades in daily_trades.items():
        closed_trades = [t for t in day_trades if t['position_summary']['status'] == 'closed']
        open_trades = [t for t in day_trades if t['position_summary']['status'] == 'open']
        
        # Sum P&L from position summaries
        total_pnl = sum(float(t['position_summary']['total_pnl']) for t in closed_trades)
        winners = [t for t in closed_trades if float(t['position_summary']['total_pnl']) >= 0]
        losers = [t for t in closed_trades if float(t['position_summary']['total_pnl']) < 0]
        
        daily_summary[date] = {
            'date': date,
            'total_trades': len(day_trades),
            'closed_trades': len(closed_trades),
            'open_trades': len(open_trades),
            'total_pnl': _format_price(total_pnl),
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'win_rate': round(len(winners) / len(closed_trades) * 100, 2) if closed_trades else 0,
            'avg_pnl_per_trade': _format_price(total_pnl / len(closed_trades)) if closed_trades else "0.00",
            'trades': day_trades
        }
    
    return daily_summary


def print_trade_summary(trade: Dict[str, Any]):
    """Print formatted trade summary."""
    print(f"\n{'='*100}")
    print(f"Position: {trade['position_id']} | Re-entry #{trade['re_entry_num']}")
    print(f"Symbol: {trade['symbol']}")
    print(f"{'='*100}")
    
    # Entry flow
    entry = trade['entry_flow']
    print(f"\n📥 ENTRY FLOW")
    print(f"   Node: {entry['node_name']} ({entry['node_id']})")
    print(f"   Time: {entry['timestamp']}")
    print(f"   Action: {entry['side']} {entry['quantity']} @ ₹{entry['price']}")
    
    if entry.get('signal_chain_ids'):
        print(f"   Signal Chain: {len(entry['signal_chain_ids'])} execution IDs")
        print(f"      (Full details in diagnostics_export.json)")
    
    # Exit flows
    print(f"\n📤 EXIT FLOWS ({len(trade['exit_flows'])} exits)")
    for i, exit_flow in enumerate(trade['exit_flows'], 1):
        status_icon = "✅" if exit_flow['effective'] else "❌"
        print(f"\n   {status_icon} Exit #{i}: {exit_flow['node_name']} ({exit_flow['node_id']})")
        print(f"      Time: {exit_flow['timestamp']}")
        print(f"      Requested: {exit_flow['requested_qty']} | Closed: {exit_flow['closed_qty']} | Remaining: {exit_flow['remaining_after']}")
        if exit_flow['effective']:
            print(f"      Exit @ ₹{exit_flow['exit_price']} | P&L: ₹{exit_flow['pnl']}")
        print(f"      Reason: {exit_flow['reason']}")
        if exit_flow.get('note'):
            print(f"      Note: {exit_flow['note']}")
        
        if exit_flow.get('signal_chain_ids'):
            print(f"      Signal Chain: {len(exit_flow['signal_chain_ids'])} execution IDs")
    
    # Position summary
    summary = trade['position_summary']
    print(f"\n💰 POSITION SUMMARY")
    print(f"   Status: {summary['status'].upper()}")
    print(f"   Entry Qty: {summary['entry_qty']} | Closed: {summary['net_closed_qty']} | Remaining: {summary['remaining_qty']}")
    print(f"   Total P&L: ₹{summary['total_pnl']}")
    if summary['duration_minutes']:
        print(f"   Duration: {summary['duration_minutes']} minutes")


def print_daily_summary(date: str, summary: Dict[str, Any]):
    """Print daily summary."""
    print(f"\n{'='*100}")
    print(f"📅 DATE: {date}")
    print(f"{'='*100}")
    print(f"Total Trades: {summary['total_trades']} | Closed: {summary['closed_trades']} | Open: {summary['open_trades']}")
    print(f"P&L: ₹{summary['total_pnl']} | Winners: {summary['winning_trades']} | Losers: {summary['losing_trades']} | Win Rate: {summary['win_rate']:.1f}%")
    print(f"Avg P&L per Trade: ₹{summary['avg_pnl_per_trade']}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*100)
    print("POSITION-CENTRIC TRADE EXTRACTION (Multi-Exit, Qty-Aware)")
    print("="*100)
    
    # Load diagnostics
    diagnostics = load_diagnostics()
    
    # Extract all trades
    print("\n📊 Extracting trades...")
    trades = get_all_trades(diagnostics)
    print(f"✅ Found {len(trades)} trades")
    
    # Get daily summary
    print("\n📅 Calculating daily summaries...")
    daily_summary = get_daily_summary(trades)
    print(f"✅ {len(daily_summary)} days")
    
    # Print daily summaries
    print("\n" + "="*100)
    print("DAILY SUMMARIES")
    print("="*100)
    for date in sorted(daily_summary.keys()):
        print_daily_summary(date, daily_summary[date])
    
    # Print first 3 detailed trades
    print("\n" + "="*100)
    print("DETAILED TRADE EXAMPLES (First 3 trades)")
    print("="*100)
    for trade in trades[:3]:
        print_trade_summary(trade)
    
    # Export to JSON
    output = {
        'summary': {
            'total_trades': len(trades),
            'closed_trades': len([t for t in trades if t['position_summary']['status'] == 'closed']),
            'open_trades': len([t for t in trades if t['position_summary']['status'] == 'open']),
        },
        'daily_summary': daily_summary,
        'trades': trades
    }
    
    with open('trades_summary.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print("\n" + "="*100)
    print("✅ Trades exported to: trades_summary.json")
    print("="*100)
    print("\n🎯 KEY FEATURES:")
    print("   • Position-centric: keyed by (position_id, re_entry_num)")
    print("   • Multi-exit support: handles multiple exits per position")
    print("   • Qty simulation: partial exits, over-qty, already-closed")
    print("   • Independent flows: entry/exit flows not dependent on tree structure")
    print("="*100)
