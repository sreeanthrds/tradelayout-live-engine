"""
Live State Formatter

Extracts relevant data from context for live simulation monitoring.
No duplication - just reads what's already in context and formats for UI.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def format_live_state(context: Dict[str, Any], node_registry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and format context data for UI consumption.
    
    Reads from existing context without duplication:
    - node_states (filtered to active/pending only)
    - candle_df_dict (latest 2 candles per timeframe)
    - ltp_store (all current prices)
    - gps (open positions with unrealized PNL)
    - current_timestamp
    
    Args:
        context: Execution context with all strategy state
        node_registry: Dictionary of node_id -> node instance
        
    Returns:
        Dictionary with formatted state ready for JSON serialization
    """
    
    # 1. Extract active/pending nodes
    active_nodes = _extract_active_nodes(context, node_registry)
    
    # 2. Extract latest candles (current + previous only)
    latest_candles = _extract_latest_candles(context)
    
    # 3. Extract LTP store (entire store - it's small)
    ltp_store = context.get('ltp_store', {})
    
    # 4. Extract open positions with unrealized PNL
    open_positions, total_unrealized_pnl = _extract_open_positions(context, ltp_store)
    
    # 5. Get current timestamp
    current_timestamp = context.get('current_timestamp')
    
    # 6. Calculate progress (if available)
    stats = _calculate_stats(context)
    
    return {
        'timestamp': current_timestamp.isoformat() if current_timestamp and hasattr(current_timestamp, 'isoformat') else str(current_timestamp),
        'active_nodes': active_nodes,
        'latest_candles': latest_candles,
        'ltp_store': ltp_store,
        'open_positions': open_positions,
        'total_unrealized_pnl': total_unrealized_pnl,
        'stats': stats
    }


def _extract_active_nodes(context: Dict[str, Any], node_registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract nodes that are currently ACTIVE or PENDING.
    Inactive nodes are skipped to reduce payload size.
    Includes both state data and node configuration (e.g., explicit conditions).
    """
    active_nodes = []
    node_states = context.get('node_states', {})
    
    for node_id, state in node_states.items():
        status = state.get('status', 'Inactive')
        
        # Only include active or pending nodes
        if status in ['Active', 'Pending']:
            node = node_registry.get(node_id)
            
            node_info = {
                'node_id': node_id,
                'node_type': node.type if node else 'Unknown',
                'node_name': node.name if node else node_id,
                'status': status,
                'visited': state.get('visited', False),
                're_entry_num': state.get('reEntryNum', 0)
            }
            
            # Add node-specific state data if available
            # (e.g., condition results, order status, etc.)
            if 'diagnostic_data' in state:
                node_info['diagnostic_data'] = state.get('diagnostic_data')
            
            if 'condition_result' in state:
                node_info['condition_result'] = state.get('condition_result')
            
            if 'order_status' in state:
                node_info['order_status'] = state.get('order_status')
            
            # Extract explicit conditions from node object (for signal nodes)
            if node:
                node_type = node.type if hasattr(node, 'type') else type(node).__name__
                
                # For ReEntrySignalNode and EntrySignalNode - include explicit conditions
                if node_type in ['ReEntrySignalNode', 'EntrySignalNode']:
                    if hasattr(node, 'conditions') and node.conditions:
                        node_info['explicit_conditions'] = node.conditions
                
                # For ReEntrySignalNode - include implicit check states from diagnostic data
                if node_type == 'ReEntrySignalNode':
                    # Extract implicit condition states if available in diagnostic_data
                    diagnostic = state.get('diagnostic_data', {})
                    if diagnostic:
                        implicit_checks = {}
                        # These are typically logged/stored by the node during execution
                        if 'has_open_position' in diagnostic:
                            implicit_checks['has_open_position'] = diagnostic['has_open_position']
                        if 'target_node_active' in diagnostic:
                            implicit_checks['target_node_active'] = diagnostic['target_node_active']
                        if 'max_entries_reached' in diagnostic:
                            implicit_checks['max_entries_reached'] = diagnostic['max_entries_reached']
                        
                        if implicit_checks:
                            node_info['implicit_checks'] = implicit_checks
            
            active_nodes.append(node_info)
    
    return active_nodes


def _extract_latest_candles(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract current and previous candle for each timeframe.
    Reduces payload size by sending only 2 candles instead of 20.
    """
    latest_candles = {}
    candle_df_dict = context.get('candle_df_dict', {})
    
    for symbol, timeframes in candle_df_dict.items():
        latest_candles[symbol] = {}
        
        # Handle both dict and list formats
        if isinstance(timeframes, dict):
            items = timeframes.items()
        elif isinstance(timeframes, list):
            # If timeframes is a list, treat as single timeframe with default name
            items = [('default', timeframes)]
        else:
            continue
        
        for timeframe, candles in items:
            if isinstance(candles, list) and len(candles) >= 2:
                # Get last 2 candles (current and previous)
                current = candles[-1]
                previous = candles[-2]
                
                # Convert to dict if needed
                if not isinstance(current, dict):
                    current = current if isinstance(current, dict) else {}
                if not isinstance(previous, dict):
                    previous = previous if isinstance(previous, dict) else {}
                
                latest_candles[symbol][timeframe] = {
                    'current': current,
                    'previous': previous
                }
    
    return latest_candles


def _extract_open_positions(context: Dict[str, Any], ltp_store: Dict[str, Any]) -> tuple:
    """
    Extract open positions and calculate unrealized PNL.
    
    Returns:
        Tuple of (open_positions_list, total_unrealized_pnl)
    """
    open_positions = []
    total_unrealized_pnl = 0.0
    
    gps = context.get('gps')
    if not gps:
        return open_positions, total_unrealized_pnl
    
    # Handle both dict and list formats for gps.positions
    positions_dict = {}
    if isinstance(gps.positions, dict):
        positions_dict = gps.positions
    elif isinstance(gps.positions, list):
        # If it's a list, treat as positions without node grouping
        positions_dict = {'all': gps.positions}
    else:
        return open_positions, total_unrealized_pnl
    
    # Iterate through all node positions
    for node_id, positions in positions_dict.items():
        for pos in positions:
            if pos.get('status') == 'OPEN':
                # Extract position details
                position_id = pos.get('position_id')
                symbol = pos.get('symbol')
                side = pos.get('side', 'buy')
                actual_quantity = pos.get('actual_quantity', 0)  # Actual traded quantity for P&L
                quantity = pos.get('quantity', 0)  # Number of lots/stocks
                multiplier = pos.get('multiplier', 1)  # Lot size
                entry_price = pos.get('entry_price', 0)
                entry_time = pos.get('entry_time')
                
                # Get current LTP for this symbol
                current_ltp = 0
                if symbol and symbol in ltp_store:
                    ltp_data = ltp_store.get(symbol, {})
                    current_ltp = ltp_data.get('ltp', 0)
                
                # Calculate unrealized PNL using actual_quantity
                unrealized_pnl = 0.0
                if current_ltp > 0 and entry_price > 0 and actual_quantity > 0:
                    if side == 'buy':
                        unrealized_pnl = (current_ltp - entry_price) * actual_quantity
                    else:  # sell
                        unrealized_pnl = (entry_price - current_ltp) * actual_quantity
                
                total_unrealized_pnl += unrealized_pnl
                
                # Format position data
                position_data = {
                    'position_id': position_id,
                    'node_id': node_id,
                    'symbol': symbol,
                    'side': side,
                    'actual_quantity': actual_quantity,  # Actual traded quantity (for display and P&L)
                    'quantity': quantity,  # Number of lots/stocks
                    'multiplier': multiplier,  # Lot size
                    'entry_price': entry_price,
                    'entry_time': entry_time.isoformat() if hasattr(entry_time, 'isoformat') else str(entry_time),
                    'current_ltp': current_ltp,
                    'unrealized_pnl': unrealized_pnl
                }
                
                open_positions.append(position_data)
    
    return open_positions, total_unrealized_pnl


def _calculate_stats(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate simulation statistics.
    """
    stats = {
        'ticks_processed': context.get('ticks_processed', 0),
        'total_ticks': context.get('total_ticks', 0),
        'progress_percentage': 0.0
    }
    
    # Calculate progress
    if stats['total_ticks'] > 0:
        stats['progress_percentage'] = (stats['ticks_processed'] / stats['total_ticks']) * 100
    
    # Add GPS statistics if available
    gps = context.get('gps')
    if gps:
        total_positions = 0
        closed_positions = 0
        
        for positions in gps.positions.values():
            for pos in positions:
                total_positions += 1
                if pos.get('status') == 'CLOSED':
                    closed_positions += 1
        
        stats['total_positions'] = total_positions
        stats['closed_positions'] = closed_positions
        stats['open_positions'] = total_positions - closed_positions
    
    return stats
