#!/usr/bin/env python3
"""
Simplified Trade Extraction - Industry Standard Format

Generates clean, UI-friendly structure:
- Daily summary at top level
- Each trade as a single row (table format)
- signal_chain_ids for flow visualization
- Minimal nested data

Structure follows industry best practices from:
- Bloomberg Terminal
- TradingView
- Interactive Brokers
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def extract_simplified_trades(diagnostics_file: str = 'diagnostics_export.json') -> Dict[str, Any]:
    """
    Extract trades in simplified format for UI.
    
    Returns:
        {
            "date": "2024-10-29",
            "summary": {
                "total_trades": 9,
                "total_pnl": -834.45,
                "winning_trades": 0,
                "losing_trades": 9,
                "win_rate": 0.0
            },
            "trades": [
                {
                    "trade_id": "entry-3-pos1-r0",
                    "position_id": "entry-3-pos1",
                    "re_entry_num": 0,
                    "symbol": "NIFTY:...",
                    "side": "SELL",
                    "quantity": 1,
                    "entry_price": "262.05",
                    "entry_time": "2024-10-29 11:42:00",
                    "exit_price": "287.80",
                    "exit_time": "2024-10-29 12:04:00",
                    "pnl": "-25.75",
                    "pnl_percent": "-9.82",
                    "duration_minutes": 22,
                    "status": "closed",
                    
                    # For flow visualization - IDs only
                    "entry_flow_ids": ["exec_start_...", "exec_entry_signal_...", "exec_entry_..."],
                    "exit_flow_ids": ["exec_exit_signal_...", "exec_exit_..."],
                    
                    # Node names for quick display (optional - can be fetched from diagnostics)
                    "entry_trigger": "Entry Signal - Bearish",
                    "exit_reason": "Exit - SL"
                }
            ]
        }
    """
    
    with open(diagnostics_file) as f:
        diagnostics = json.load(f)
    
    events_history = diagnostics.get('events_history', {})
    
    # Build position index
    position_index = defaultdict(lambda: {
        'entry_event': None,
        'entry_exec_id': None,
        'exit_events': []
    })
    
    # Index all entry and exit events
    for exec_id, event in events_history.items():
        node_type = event.get('node_type', '')
        
        if node_type == 'EntryNode':
            position = event.get('position', {})
            position_id = position.get('position_id')
            re_entry_num = event.get('entry_config', {}).get('re_entry_num', 0)
            
            if position_id:
                key = (position_id, re_entry_num)
                position_index[key]['entry_event'] = event
                position_index[key]['entry_exec_id'] = exec_id
        
        elif node_type == 'ExitNode':
            position = event.get('position', {})
            position_id = position.get('position_id')
            re_entry_num = position.get('re_entry_num', 0)
            
            if not position_id:
                position_id = event.get('action', {}).get('target_position_id')
            
            if position_id:
                key = (position_id, re_entry_num)
                timestamp = event.get('timestamp')
                position_index[key]['exit_events'].append((timestamp, exec_id, event))
        
        elif node_type == 'SquareOffNode':
            # Square-off closes multiple positions
            closed_positions = event.get('closed_positions', [])
            timestamp = event.get('timestamp')
            
            for pos_info in closed_positions:
                position_id = pos_info.get('position_id')
                re_entry_num = pos_info.get('re_entry_num', 0)
                
                if position_id:
                    key = (position_id, re_entry_num)
                    position_index[key]['exit_events'].append((timestamp, exec_id, event))
    
    # Build trades list
    trades = []
    total_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    
    for (position_id, re_entry_num), trade_data in sorted(position_index.items()):
        entry_event = trade_data['entry_event']
        entry_exec_id = trade_data['entry_exec_id']
        exit_events = sorted(trade_data['exit_events'], key=lambda x: x[0])
        
        if not entry_event:
            continue
        
        # Extract entry data
        position = entry_event.get('position', {})
        action = entry_event.get('action', {})
        
        entry_price = float(action.get('price', 0))
        entry_qty = int(action.get('quantity', 1))
        entry_time = entry_event.get('timestamp', '')
        symbol = action.get('symbol', position.get('symbol', ''))
        side = action.get('side', position.get('side', '')).upper()
        
        # Build entry flow IDs - traverse from entry node to start
        entry_flow_ids = build_flow_chain(events_history, entry_exec_id)
        
        # Extract exit data (use first exit for primary exit, aggregate P&L)
        exit_price = None
        exit_time = None
        exit_reason = None
        exit_flow_ids = []
        trade_pnl = 0.0
        
        for _, exit_exec_id, exit_event in exit_events:
            node_type = exit_event.get('node_type', '')
            
            # Handle ExitNode vs SquareOffNode differently
            if node_type == 'ExitNode':
                exit_result = exit_event.get('exit_result', {})
                positions_closed = exit_result.get('positions_closed', 0)
                
                if positions_closed > 0:
                    # Use first effective exit for display
                    if exit_price is None:
                        exit_price_str = exit_result.get('exit_price', '0')
                        if isinstance(exit_price_str, str):
                            exit_price = float(exit_price_str.replace(',', ''))
                        else:
                            exit_price = float(exit_price_str)
                        
                        exit_time = exit_event.get('timestamp', '')
                        exit_reason = exit_event.get('node_name', '')
                        exit_flow_ids = build_flow_chain(events_history, exit_exec_id)
                    
                    # Aggregate P&L
                    pnl_value = exit_result.get('pnl', 0)
                    if isinstance(pnl_value, str):
                        pnl_value = float(pnl_value.replace(',', ''))
                    trade_pnl += pnl_value
            
            elif node_type == 'SquareOffNode':
                # Square-off has different structure - data is in closed_positions
                closed_positions_list = exit_event.get('closed_positions', [])
                
                # Find this specific position in the closed_positions list
                for pos_info in closed_positions_list:
                    if pos_info.get('position_id') == position_id and pos_info.get('re_entry_num') == re_entry_num:
                        # Use first effective exit for display
                        if exit_price is None:
                            exit_price = float(pos_info.get('exit_price', 0))
                            exit_time = exit_event.get('timestamp', '')
                            exit_reason = exit_event.get('node_name', '') or 'Square-Off'
                            exit_flow_ids = build_flow_chain(events_history, exit_exec_id)
                        
                        # Calculate P&L for square-off
                        entry_px = float(pos_info.get('entry_price', 0))
                        exit_px = float(pos_info.get('exit_price', 0))
                        qty = int(pos_info.get('quantity', 1))
                        side = pos_info.get('side', 'buy').lower()
                        
                        if side == 'buy':
                            pnl = (exit_px - entry_px) * qty
                        else:  # sell
                            pnl = (entry_px - exit_px) * qty
                        
                        trade_pnl += pnl
                        break
        
        # Calculate duration
        duration_minutes = 0
        if entry_time and exit_time:
            try:
                entry_dt = datetime.fromisoformat(entry_time.replace('+05:30', ''))
                exit_dt = datetime.fromisoformat(exit_time.replace('+05:30', ''))
                duration_minutes = int((exit_dt - entry_dt).total_seconds() / 60)
            except:
                pass
        
        # Calculate P&L percentage
        pnl_percent = 0.0
        if entry_price > 0:
            pnl_percent = (trade_pnl / (entry_price * entry_qty)) * 100
        
        # Status
        status = 'closed' if exit_price else 'open'
        
        # Track stats
        total_pnl += trade_pnl
        if trade_pnl > 0:
            winning_trades += 1
        elif trade_pnl < 0:
            losing_trades += 1
        
        # Get entry trigger name (first signal node in chain)
        entry_trigger = "Unknown"
        if entry_flow_ids:
            # Find first signal/condition node
            for exec_id in entry_flow_ids:
                node = events_history.get(exec_id, {})
                node_type = node.get('node_type', '')
                if 'Signal' in node_type or 'Condition' in node_type:
                    entry_trigger = node.get('node_name', 'Unknown')
                    break
        
        # Build trade object
        trade = {
            "trade_id": f"{position_id}-r{re_entry_num}",
            "position_id": position_id,
            "re_entry_num": re_entry_num,
            "symbol": symbol,
            "side": side,
            "quantity": entry_qty,
            "entry_price": f"{entry_price:.2f}",
            "entry_time": entry_time,
            "exit_price": f"{exit_price:.2f}" if exit_price else None,
            "exit_time": exit_time,
            "pnl": f"{trade_pnl:.2f}",
            "pnl_percent": f"{pnl_percent:.2f}",
            "duration_minutes": duration_minutes,
            "status": status,
            
            # Flow IDs for visualization
            "entry_flow_ids": entry_flow_ids,
            "exit_flow_ids": exit_flow_ids,
            
            # Quick display info
            "entry_trigger": entry_trigger,
            "exit_reason": exit_reason
        }
        
        trades.append(trade)
    
    # Build daily summary
    total_trades = len(trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Extract date from first trade
    date = "unknown"
    if trades:
        first_time = trades[0].get('entry_time', '')
        if first_time:
            try:
                date = first_time.split()[0]  # Get YYYY-MM-DD part
            except:
                pass
    
    result = {
        "date": date,
        "summary": {
            "total_trades": total_trades,
            "total_pnl": f"{total_pnl:.2f}",
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": f"{win_rate:.2f}"
        },
        "trades": trades
    }
    
    return result


def build_flow_chain(events_history: Dict, exec_id: str, max_depth: int = 50) -> List[str]:
    """
    Build flow chain from current node back to start/trigger.
    
    Returns list of execution IDs in CHRONOLOGICAL order (oldest to newest),
    INCLUDING the current node.
    
    This gives the complete path: Start → Signals → Current Node
    """
    chain = [exec_id]  # Include the current node (Entry or Exit)
    current_id = exec_id
    depth = 0
    
    while current_id and current_id in events_history and depth < max_depth:
        event = events_history[current_id]
        parent_id = event.get('parent_execution_id')
        
        if parent_id and parent_id in events_history:
            parent_event = events_history[parent_id]
            node_type = parent_event.get('node_type', '')
            
            # Add ALL parent nodes (signals, conditions, start)
            if any(keyword in node_type for keyword in ['Signal', 'Condition', 'Start', 'Entry', 'Exit']):
                chain.append(parent_id)
            
            current_id = parent_id
            depth += 1
        else:
            break
    
    # Reverse to get chronological order (oldest first)
    return list(reversed(chain))


def main():
    print("="*100)
    print("🔄 EXTRACTING TRADES - SIMPLIFIED FORMAT")
    print("="*100)
    
    try:
        result = extract_simplified_trades()
        
        # Save to file
        output_file = 'trades_daily.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Extracted {result['summary']['total_trades']} trades for {result['date']}")
        print(f"   Total P&L: ₹{result['summary']['total_pnl']}")
        print(f"   Win Rate: {result['summary']['win_rate']}%")
        
        print(f"\n" + "="*100)
        print(f"✅ Saved to: {output_file}")
        print("="*100)
        
        # Show sample trade
        if result['trades']:
            print("\n📋 Sample Trade:")
            trade = result['trades'][0]
            print(json.dumps(trade, indent=2))
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
