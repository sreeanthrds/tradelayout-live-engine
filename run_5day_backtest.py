#!/usr/bin/env python3
"""
Run 5-day backtest and collect all trades
"""
import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.centralized_backtest_engine import CentralizedBacktestEngine
from src.backtesting.backtest_config import BacktestConfig
from datetime import date, datetime
from src.core.gps import GlobalPositionStore

from datetime import datetime, timedelta

# Generate all days in October 2024
start_date = datetime(2024, 10, 1)
end_date = datetime(2024, 10, 31)
dates = []
current = start_date
while current <= end_date:
    dates.append(current.strftime('%Y-%m-%d'))
    current += timedelta(days=1)

for backtest_date_str in dates:
    print(f"\n{'='*80}")
    print(f"RUNNING BACKTEST FOR {backtest_date_str}")
    print(f"{'='*80}")
    
    # Dashboard data structure
    dashboard_data = {
        'strategy_id': '4a7a1a31-e209-4b23-891a-3899fb8e4c28',
        'backtest_date': backtest_date_str,
        'positions': [],
        'summary': {}
    }
    
    # Track all operations
    orig_add = GlobalPositionStore.add_position
    orig_close = GlobalPositionStore.close_position
    
    def track_add(self, pos_id, entry_data, tick_time=None):
        """Track position entry with all details"""
        symbol = entry_data.get('symbol', 'N/A')
        
        # Extract strike and option type
        strike, opt_type, expiry = 'N/A', 'N/A', 'N/A'
        if ':OPT:' in symbol:
            parts = symbol.split(':')
            if len(parts) >= 5:
                expiry = parts[1]
                strike = parts[3]
                opt_type = parts[4]
        
        # Get NIFTY spot price
        ltp_store = entry_data.get('ltp_store', {})
        nifty_spot = 0
        if 'NIFTY' in ltp_store:
            nifty_data = ltp_store['NIFTY']
            if isinstance(nifty_data, dict):
                nifty_spot = nifty_data.get('ltp', 0)
            else:
                nifty_spot = nifty_data
        
        # Build position record
        position_record = {
            'position_id': pos_id,
            'entry_node_id': entry_data.get('node_id', 'N/A'),
            'entry_time': entry_data.get('entry_time', 'N/A'),
            'entry_timestamp': entry_data.get('entry_time', 'N/A').split('T')[1] if 'T' in str(entry_data.get('entry_time', '')) else 'N/A',
            'instrument': entry_data.get('instrument', 'N/A'),
            'symbol': symbol,
            'strike': strike,
            'option_type': opt_type,
            'expiry': expiry,
            'entry_price': entry_data.get('entry_price', 0),
            'quantity': entry_data.get('quantity', 0),
            'lot_size': entry_data.get('lot_size', 1),
            'lots': entry_data.get('quantity', 0) / entry_data.get('lot_size', 1),
            'side': entry_data.get('side', 'N/A'),
            'order_type': entry_data.get('order_type', 'N/A'),
            'order_id': entry_data.get('order_id', 'N/A'),
            're_entry_num': entry_data.get('reEntryNum', 0),
            'nifty_spot_at_entry': nifty_spot,
            'exchange': entry_data.get('exchange', 'N/A'),
            'product_type': entry_data.get('product_type', 'intraday'),
            'status': 'OPEN'
        }
        
        dashboard_data['positions'].append(position_record)
        return orig_add(self, pos_id, entry_data, tick_time)
    
    def track_close(self, pos_id, exit_data, tick_time=None):
        """Track position exit with all details"""
        # Find the OPEN position record with this ID (handles re-entries)
        position_record = None
        for pos in dashboard_data['positions']:
            if pos['position_id'] == pos_id and pos['status'] == 'OPEN':
                position_record = pos
                break
        
        if position_record:
            entry_price = position_record['entry_price']
            exit_price = exit_data.get('price', 0)
            quantity = position_record['quantity']
            
            # Calculate P&L
            pnl = (exit_price - entry_price) * quantity
            pnl_percentage = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            
            # Calculate duration
            entry_time_str = position_record['entry_time']
            exit_time_str = exit_data.get('exit_time', 'N/A')
            
            duration_seconds = 0
            duration_minutes = 0
            if entry_time_str != 'N/A' and exit_time_str != 'N/A':
                try:
                    entry_dt = datetime.fromisoformat(entry_time_str) if isinstance(entry_time_str, str) else entry_time_str
                    exit_dt = datetime.fromisoformat(exit_time_str) if isinstance(exit_time_str, str) else exit_time_str
                    duration = exit_dt - entry_dt
                    duration_seconds = duration.total_seconds()
                    duration_minutes = duration_seconds / 60
                except:
                    pass
            
            # Update position record
            position_record.update({
                'status': 'CLOSED',
                'exit_node_id': exit_data.get('node_id', 'N/A'),
                'exit_time': exit_time_str,
                'exit_timestamp': exit_time_str.split('T')[1] if 'T' in str(exit_time_str) else 'N/A',
                'exit_price': exit_price,
                'exit_reason': exit_data.get('reason', 'N/A'),
                'duration_seconds': duration_seconds,
                'duration_minutes': duration_minutes,
                'pnl': round(pnl, 2),
                'pnl_percentage': round(pnl_percentage, 2)
            })
        
        return orig_close(self, pos_id, exit_data, tick_time)
    
    # Monkey patch GPS methods
    GlobalPositionStore.add_position = track_add
    GlobalPositionStore.close_position = track_close
    
    # Create config
    config = BacktestConfig(
        strategy_ids=['4a7a1a31-e209-4b23-891a-3899fb8e4c28'],
        backtest_date=datetime.strptime(backtest_date_str, '%Y-%m-%d'),
        debug_mode=None
    )
    
    # Run backtest
    engine = CentralizedBacktestEngine(config)
    results = engine.run()
    
    # Calculate summary
    closed_positions = [p for p in dashboard_data['positions'] if p['status'] == 'CLOSED']
    open_positions = [p for p in dashboard_data['positions'] if p['status'] == 'OPEN']
    
    total_pnl = sum(p['pnl'] for p in closed_positions)
    winning_trades = len([p for p in closed_positions if p['pnl'] > 0])
    losing_trades = len([p for p in closed_positions if p['pnl'] < 0])
    breakeven_trades = len([p for p in closed_positions if p['pnl'] == 0])
    
    win_rate = (winning_trades / len(closed_positions) * 100) if closed_positions else 0
    
    avg_win = sum(p['pnl'] for p in closed_positions if p['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(p['pnl'] for p in closed_positions if p['pnl'] < 0) / losing_trades if losing_trades > 0 else 0
    
    avg_duration = sum(p['duration_minutes'] for p in closed_positions) / len(closed_positions) if closed_positions else 0
    
    largest_win = max((p['pnl'] for p in closed_positions), default=0)
    largest_loss = min((p['pnl'] for p in closed_positions), default=0)
    
    re_entries = sum(1 for p in dashboard_data['positions'] if p['re_entry_num'] > 0)
    
    summary = {
        'total_positions': len(dashboard_data['positions']),
        'closed_positions': len(closed_positions),
        'open_positions': len(open_positions),
        'total_pnl': round(total_pnl, 2),
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'breakeven_trades': breakeven_trades,
        'win_rate': round(win_rate, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'avg_duration_minutes': round(avg_duration, 2),
        'largest_win': round(largest_win, 2),
        'largest_loss': round(largest_loss, 2),
        're_entries': re_entries
    }
    
    dashboard_data['summary'] = summary
    
    # Save to date-specific JSON file
    output_file = f'backtest_dashboard_data_{backtest_date_str}.json'
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"\n✅ Saved: {output_file}")
    print(f"   Positions: {len(dashboard_data['positions'])}")
    print(f"   Total P&L: ₹{summary['total_pnl']}")
    
    # Restore original methods
    GlobalPositionStore.add_position = orig_add
    GlobalPositionStore.close_position = orig_close

print(f"\n{'='*80}")
print("✅ ALL 5 DAYS COMPLETED")
print(f"{'='*80}")
