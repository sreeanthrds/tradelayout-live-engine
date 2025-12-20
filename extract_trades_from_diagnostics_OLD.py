#!/usr/bin/env python3
"""
Extract trades and summaries from execution-chain-based diagnostics.

This script shows how to:
1. Parse the new diagnostics structure
2. Build complete transaction chains for each trade
3. Calculate trade summaries
4. Aggregate by day
"""

import json
from datetime import datetime
from typing import Dict, List, Any
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


def build_trade_from_exit(events_history: Dict, exit_exec_id: str, exit_event: Dict) -> Dict[str, Any]:
    """
    Build a complete trade by traversing backward from exit event.
    
    This is MUCH more efficient:
    - Start from exit (completed trade)
    - Traverse backward using parent_execution_id (O(1) per link)
    - No searching through arrays!
    
    Args:
        events_history: Dict[execution_id, event_dict]
        exit_exec_id: Exit execution ID
        exit_event: Exit event dict
        
    Returns:
        Trade dict with complete chain
    """
    # Step 1: Get exit signal (parent of exit) - O(1)
    exit_signal = None
    exit_signal_id = exit_event.get('parent_execution_id')
    if exit_signal_id and exit_signal_id in events_history:
        exit_signal = events_history[exit_signal_id]
    
    # Step 2: Get entry (parent of exit signal) - O(1)
    entry_event = None
    entry_exec_id = None
    if exit_signal:
        entry_exec_id = exit_signal.get('parent_execution_id')
        if entry_exec_id and entry_exec_id in events_history:
            entry_event = events_history[entry_exec_id]
    
    if not entry_event:
        # Fallback: try to find entry by position_id (shouldn't happen if chain is correct)
        position_id = exit_event.get('action', {}).get('target_position_id')
        for exec_id, event in events_history.items():
            if (event['node_type'] == 'EntryNode' and 
                event.get('position', {}).get('position_id') == position_id):
                entry_event = event
                entry_exec_id = exec_id
                break
    
    if not entry_event:
        return None
    
    # Step 3: Get entry signal (parent of entry) - O(1)
    entry_signal = None
    entry_signal_id = entry_event.get('parent_execution_id')
    if entry_signal_id and entry_signal_id in events_history:
        entry_signal = events_history[entry_signal_id]
    
    # Get position_id
    position_id = exit_event.get('action', {}).get('target_position_id') or entry_event.get('position', {}).get('position_id')
    
    # Step 4: Build trade summary
    trade = {
        'position_id': position_id,
        'symbol': entry_event.get('action', {}).get('symbol', ''),
        're_entry_num': entry_event.get('entry_config', {}).get('re_entry_num', 0),
        
        # Entry phase
        'entry_signal': {
            'execution_id': entry_signal['execution_id'] if entry_signal else None,
            'node_id': entry_signal['node_id'] if entry_signal else None,
            'node_name': entry_signal['node_name'] if entry_signal else None,
            'timestamp': entry_signal['timestamp'] if entry_signal else None,
        } if entry_signal else None,
        
        'entry': {
            'execution_id': entry_exec_id,
            'node_id': entry_event['node_id'],
            'node_name': entry_event['node_name'],
            'timestamp': entry_event['timestamp'],
            'side': entry_event.get('action', {}).get('side'),
            'quantity': entry_event.get('action', {}).get('quantity'),
            'price': _format_price(entry_event.get('action', {}).get('price')),
            'order_id': entry_event.get('action', {}).get('order_id'),
        },
        
        # Exit phase (if closed)
        'exit_signal': {
            'execution_id': exit_signal['execution_id'] if exit_signal else None,
            'node_id': exit_signal['node_id'] if exit_signal else None,
            'node_name': exit_signal['node_name'] if exit_signal else None,
            'timestamp': exit_signal['timestamp'] if exit_signal else None,
            'exit_reason': _extract_exit_reason(exit_signal['node_name']) if exit_signal else None,
        } if exit_signal else None,
        
        'exit': {
            'execution_id': exit_exec_id,
            'node_id': exit_event['node_id'],
            'node_name': exit_event['node_name'],
            'timestamp': exit_event['timestamp'],
            'exit_price': _format_price(exit_event.get('exit_result', {}).get('exit_price')),
            'pnl': _format_price(exit_event.get('exit_result', {}).get('pnl')),
            'positions_closed': exit_event.get('exit_result', {}).get('positions_closed'),
        } if exit_event else None,
        
        # Trade status
        'status': 'closed' if exit_event else 'open',
    }
    
    # Calculate trade metrics if closed
    if exit_event and entry_event:
        entry_time = datetime.fromisoformat(entry_event['timestamp'])
        exit_time = datetime.fromisoformat(exit_event['timestamp'])
        duration = (exit_time - entry_time).total_seconds() / 60  # minutes
        
        pnl_value = exit_event.get('exit_result', {}).get('pnl', 0)
        trade['metrics'] = {
            'duration_minutes': round(duration, 2),
            'pnl': _format_price(pnl_value),
            'is_winner': float(pnl_value) >= 0,
            'entry_price': _format_price(entry_event.get('action', {}).get('price')),
            'exit_price': _format_price(exit_event.get('exit_result', {}).get('exit_price')),
        }
    
    return trade


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


def get_all_trades(diagnostics: Dict) -> List[Dict[str, Any]]:
    """
    Extract all trades from diagnostics by traversing backward from exits.
    
    EFFICIENT APPROACH:
    1. Find all exit events (completed trades only)
    2. For each exit, traverse backward through parent_execution_id chain
    3. O(1) lookups, no searching!
    
    Returns:
        List of trade dicts sorted by entry time
    """
    events_history = diagnostics.get('events_history', {})
    
    # Step 1: Find all exit events (completed trades)
    exit_events = []
    for exec_id, event in events_history.items():
        if event['node_type'] == 'ExitNode':
            exit_events.append((exec_id, event))
    
    # Step 2: Build trade for each exit by traversing backward
    trades = []
    for exit_exec_id, exit_event in exit_events:
        trade = build_trade_from_exit(events_history, exit_exec_id, exit_event)
        if trade:
            trades.append(trade)
    
    # Step 3: Sort by entry time
    trades.sort(key=lambda t: t['entry']['timestamp'])
    
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
        date = trade['entry']['timestamp'].split(' ')[0]  # Get date part
        daily_trades[date].append(trade)
    
    # Calculate summary for each day
    daily_summary = {}
    for date, day_trades in daily_trades.items():
        closed_trades = [t for t in day_trades if t['status'] == 'closed']
        open_trades = [t for t in day_trades if t['status'] == 'open']
        
        # Sum P&L (convert from formatted string back to float for calculation)
        total_pnl = sum(float(t['metrics']['pnl']) for t in closed_trades if t.get('metrics'))
        winners = [t for t in closed_trades if t.get('metrics', {}).get('is_winner')]
        losers = [t for t in closed_trades if not t.get('metrics', {}).get('is_winner')]
        
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
            'trades': day_trades  # Include detailed trades
        }
    
    return daily_summary


def print_trade_summary(trade: Dict[str, Any]):
    """Print a formatted trade summary."""
    print(f"\n{'='*80}")
    print(f"Position: {trade['position_id']} | Re-entry #{trade['re_entry_num']}")
    print(f"Symbol: {trade['symbol']}")
    print(f"{'='*80}")
    
    # Entry signal
    if trade['entry_signal']:
        print(f"\n🟢 Entry Signal: {trade['entry_signal']['node_name']}")
        print(f"   Time: {trade['entry_signal']['timestamp']}")
    
    # Entry
    print(f"\n📥 Entry: {trade['entry']['node_name']}")
    print(f"   Time: {trade['entry']['timestamp']}")
    print(f"   {trade['entry']['side']} {trade['entry']['quantity']} @ ₹{trade['entry']['price']}")
    
    # Exit signal
    if trade['exit_signal']:
        print(f"\n🔔 Exit Signal: {trade['exit_signal']['node_name']} ({trade['exit_signal']['exit_reason']})")
        print(f"   Time: {trade['exit_signal']['timestamp']}")
    
    # Exit
    if trade['exit']:
        print(f"\n📤 Exit: {trade['exit']['node_name']}")
        print(f"   Time: {trade['exit']['timestamp']}")
        print(f"   Exit @ ₹{trade['exit']['exit_price']}")
        
        # Metrics
        if trade.get('metrics'):
            pnl = trade['metrics']['pnl']
            status = "✅ PROFIT" if float(pnl) >= 0 else "❌ LOSS"
            print(f"\n💰 Result: {status}")
            print(f"   P&L: ₹{pnl}")
            print(f"   Duration: {trade['metrics']['duration_minutes']:.1f} minutes")
    else:
        print(f"\n⏳ Status: OPEN (Position not closed)")


def print_daily_summary(date: str, summary: Dict[str, Any]):
    """Print daily summary."""
    print(f"\n{'='*100}")
    print(f"📅 DATE: {date}")
    print(f"{'='*100}")
    print(f"Total Trades: {summary['total_trades']} | ", end='')
    print(f"Closed: {summary['closed_trades']} | ", end='')
    print(f"Open: {summary['open_trades']}")
    print(f"P&L: ₹{summary['total_pnl']} | ", end='')
    print(f"Winners: {summary['winning_trades']} | ", end='')
    print(f"Losers: {summary['losing_trades']} | ", end='')
    print(f"Win Rate: {summary['win_rate']:.1f}%")
    print(f"Avg P&L per Trade: ₹{summary['avg_pnl_per_trade']}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*100)
    print("EXTRACTING TRADES FROM EXECUTION-CHAIN DIAGNOSTICS")
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
            'closed_trades': len([t for t in trades if t['status'] == 'closed']),
            'open_trades': len([t for t in trades if t['status'] == 'open']),
        },
        'daily_summary': daily_summary,
        'trades': trades
    }
    
    with open('trades_summary.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    
    print("\n" + "="*100)
    print("✅ Trades exported to: trades_summary.json")
    print("="*100)
