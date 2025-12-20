"""
Backtest Runner with Storage Integration
Runs backtest and saves results to file storage
"""
import os
import sys
from datetime import date, datetime, timedelta
from typing import Dict, Any, List
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from show_dashboard_data import run_dashboard_backtest, dashboard_data
from src.storage.backtest_storage import get_storage
from src.utils.market_calendar import get_trading_days_in_month, validate_backtest_date


def serialize_datetime(obj):
    """Recursively convert datetime objects to ISO format strings"""
    from datetime import datetime, date, time, timedelta
    
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return str(obj.total_seconds())
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj


def run_and_save_backtest(
    user_id: str,
    strategy_id: str,
    start_date: date,
    end_date: date,
    progress_callback=None
) -> Dict[str, Any]:
    """
    Run backtest for date range and save to storage
    
    Args:
        user_id: User ID
        strategy_id: Strategy ID
        start_date: Start date
        end_date: End date
        progress_callback: Optional callback(current_date, total_days, completed_days)
    
    Returns:
        Metadata dictionary
    """
    storage = get_storage()
    
    # Clear existing data
    storage.clear_strategy_data(user_id, strategy_id)
    
    # Get all trading days in range
    trading_days = []
    current = start_date
    while current <= end_date:
        if validate_backtest_date(current):
            trading_days.append(current)
        current += timedelta(days=1)
    
    total_days = len(trading_days)
    completed_days = 0
    
    # Initialize metadata
    metadata = {
        "strategy_id": strategy_id,
        "strategy_name": "Strategy",  # Will be updated
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_days": total_days,
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=12)).isoformat(),
        "overall_summary": {
            "total_positions": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "total_winning_trades": 0,
            "total_losing_trades": 0
        },
        "daily_summaries": []
    }
    
    storage.save_metadata(user_id, strategy_id, metadata)
    
    # Overall counters
    overall_positions = 0
    overall_pnl = 0
    overall_winning = 0
    overall_losing = 0
    
    # Run backtest for each day
    for backtest_date in trading_days:
        try:
            # Clear dashboard data
            dashboard_data['positions'] = []
            dashboard_data['summary'] = {}
            
            # Run backtest for this day
            run_dashboard_backtest(strategy_id, backtest_date, debug_mode=None)
            
            # Get strategy name from first run
            if completed_days == 0 and dashboard_data.get('positions'):
                # Extract strategy name if available
                pass
            
            # Prepare day data
            positions = dashboard_data['positions']
            summary = dashboard_data['summary']
            
            print(f"\n🔍 Processing {len(positions)} positions for {backtest_date}")
            
            # Assign position numbers (unique per position_id)
            position_numbers = {}
            next_pos_num = 1
            
            for pos in positions:
                pos_id = pos['position_id']
                
                # Assign position number if new
                if pos_id not in position_numbers:
                    position_numbers[pos_id] = next_pos_num
                    next_pos_num += 1
                
                # Add position_num field
                pos['position_num'] = position_numbers[pos_id]
            
            print(f"🔧 Calling serialize_datetime()...")
            # Serialize all datetime objects before saving
            try:
                day_data = serialize_datetime({
                    "date": backtest_date.strftime('%d-%m-%Y'),
                    "summary": summary,
                    "positions": positions
                })
                print(f"✅ serialize_datetime() completed")
            except Exception as e:
                print(f"❌ serialize_datetime() failed: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Debug: Check if any datetime objects remain
            import json
            from datetime import datetime as dt, date as d
            def find_datetime_objects(obj, path=""):
                """Recursively find datetime objects in nested structures"""
                if isinstance(obj, (dt, d)):
                    print(f"  Found datetime at {path}: {obj} (type: {type(obj).__name__})")
                    return True
                elif isinstance(obj, dict):
                    found = False
                    for key, value in obj.items():
                        if find_datetime_objects(value, f"{path}.{key}" if path else key):
                            found = True
                    return found
                elif isinstance(obj, list):
                    found = False
                    for i, item in enumerate(obj):
                        if find_datetime_objects(item, f"{path}[{i}]"):
                            found = True
                    return found
                return False
            
            try:
                json.dumps(day_data)
                print(f"✅ Day data for {backtest_date} serialized successfully")
            except Exception as e:
                print(f"❌ Serialization check failed: {e}")
                print(f"Searching for datetime objects...")
                find_datetime_objects(day_data, "day_data")
            
            # Save day data
            storage.save_day_data(
                user_id=user_id,
                strategy_id=strategy_id,
                date=backtest_date.strftime('%d-%m-%Y'),
                day_data=day_data
            )
            
            # Update overall counters
            overall_positions += summary.get('total_positions', 0)
            overall_pnl += summary.get('total_pnl', 0)
            overall_winning += summary.get('winning_trades', 0)
            overall_losing += summary.get('losing_trades', 0)
            
            # Add to daily summaries
            file_size = storage.get_file_size(
                user_id, 
                strategy_id, 
                backtest_date.strftime('%d-%m-%Y')
            )
            
            metadata['daily_summaries'].append({
                "date": backtest_date.strftime('%d-%m-%Y'),
                "positions": summary.get('total_positions', 0),
                "pnl": summary.get('total_pnl', 0),
                "has_data": True,
                "file_size_kb": round(file_size / 1024, 2)
            })
            
            completed_days += 1
            
            # Call progress callback
            if progress_callback:
                progress_callback(backtest_date, total_days, completed_days)
            
            # Update metadata with progress
            metadata['status'] = 'running'
            metadata['overall_summary'] = {
                "total_positions": overall_positions,
                "total_pnl": round(overall_pnl, 2),
                "win_rate": round(overall_winning / (overall_winning + overall_losing) * 100, 2) if (overall_winning + overall_losing) > 0 else 0,
                "total_winning_trades": overall_winning,
                "total_losing_trades": overall_losing
            }
            storage.save_metadata(user_id, strategy_id, metadata)
            
        except Exception as e:
            print(f"Error processing {backtest_date}: {e}")
            # Continue with next day
    
    # Mark as completed
    metadata['status'] = 'completed'
    metadata['completed_at'] = datetime.now().isoformat()
    storage.save_metadata(user_id, strategy_id, metadata)
    
    return metadata


def run_single_day_backtest(
    user_id: str,
    strategy_id: str,
    backtest_date: date
) -> Dict[str, Any]:
    """
    Run backtest for a single day
    
    Args:
        user_id: User ID
        strategy_id: Strategy ID
        backtest_date: Date to backtest
    
    Returns:
        Day data dictionary
    """
    # Clear dashboard data
    dashboard_data['positions'] = []
    dashboard_data['summary'] = {}
    
    # Run backtest
    run_dashboard_backtest(strategy_id, backtest_date, debug_mode=None)
    
    # Prepare day data
    positions = dashboard_data['positions']
    summary = dashboard_data['summary']
    
    # Assign position numbers
    position_numbers = {}
    next_pos_num = 1
    
    for pos in positions:
        pos_id = pos['position_id']
        if pos_id not in position_numbers:
            position_numbers[pos_id] = next_pos_num
            next_pos_num += 1
        pos['position_num'] = position_numbers[pos_id]
    
    # Serialize all datetime objects
    day_data = serialize_datetime({
        "date": backtest_date.strftime('%d-%m-%Y'),
        "summary": summary,
        "positions": positions
    })
    
    return day_data
