#!/usr/bin/env python3
"""
Format all price/amount values in diagnostics_export.json to exactly 2 decimal places.
"""

import json


def format_price(value):
    """Format price/amount to exactly 2 decimal places."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return value
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return value


def format_event(event):
    """Format all price fields in an event."""
    # Format action prices (entry/exit orders)
    if 'action' in event and event['action']:
        action = event['action']
        if 'price' in action:
            action['price'] = format_price(action['price'])
        if 'position_details' in action:
            pos = action['position_details']
            if 'entry_price' in pos:
                pos['entry_price'] = format_price(pos['entry_price'])
            if 'current_price' in pos:
                pos['current_price'] = format_price(pos['current_price'])
    
    # Format exit result
    if 'exit_result' in event and event['exit_result']:
        result = event['exit_result']
        if 'exit_price' in result:
            result['exit_price'] = format_price(result['exit_price'])
        if 'pnl' in result:
            result['pnl'] = format_price(result['pnl'])
    
    # Format position data
    if 'position' in event and event['position']:
        pos = event['position']
        if 'entry_price' in pos:
            pos['entry_price'] = format_price(pos['entry_price'])
        if 'current_price' in pos:
            pos['current_price'] = format_price(pos['current_price'])
    
    return event


def main():
    print("="*100)
    print("FORMATTING DIAGNOSTICS PRICES TO 2 DECIMALS")
    print("="*100)
    
    # Load diagnostics
    with open('diagnostics_export.json', 'r') as f:
        data = json.load(f)
    
    print(f"\n✅ Loaded diagnostics_export.json")
    print(f"   Events: {len(data['events_history'])}")
    
    # Format all events
    count = 0
    for exec_id, event in data['events_history'].items():
        format_event(event)
        count += 1
    
    print(f"✅ Formatted {count} events")
    
    # Save formatted diagnostics
    with open('diagnostics_export.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved formatted diagnostics_export.json")
    
    print("\n" + "="*100)
    print("✅ COMPLETE - All prices formatted to 2 decimals (e.g., 100.00, 45.50, 34.05)")
    print("="*100)


if __name__ == "__main__":
    main()
