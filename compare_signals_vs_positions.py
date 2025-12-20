#!/usr/bin/env python3
"""
Compare RSI Signals vs Actual Backtest Positions
"""
import pandas as pd
import json

def load_backtest_positions(json_file='backtest_dashboard_data_2024-10-29.json'):
    """Load positions from backtest dashboard"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    positions = data.get('positions', [])
    
    # Convert to DataFrame for easier analysis
    pos_data = []
    for pos in positions:
        entry_time = pos.get('entry_time', '')
        if 'T' in entry_time:
            entry_time = pd.to_datetime(entry_time)
        
        pos_data.append({
            'entry_node': pos.get('entry_node_id'),
            'entry_time': entry_time,
            'symbol': pos.get('symbol', ''),
            'option_type': pos.get('option_type', ''),
            'side': pos.get('side', ''),
            're_entry_num': pos.get('re_entry_num', 0),
            'entry_price': pos.get('entry_price', 0),
            'exit_price': pos.get('exit_price', 0),
            'pnl': pos.get('pnl', 0)
        })
    
    return pd.DataFrame(pos_data)


def analyze_rsi_signals(csv_file='candles_rsi_NIFTY_2024-10-29.csv', target_date='2024-10-29'):
    """Load RSI signals from candle data"""
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert numeric columns
    for col in ['prev_rsi', 'prev_high', 'prev_low', 'rsi_14', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter target date
    target_date = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target_date]
    
    # Bullish signals
    bullish = df[
        (df['prev_rsi'].notna()) &
        (df['prev_high'].notna()) &
        (df['prev_rsi'] < 30) & 
        (df['high'] > df['prev_high'])
    ].copy()
    
    # Bearish signals
    bearish = df[
        (df['prev_rsi'].notna()) &
        (df['prev_low'].notna()) &
        (df['prev_rsi'] > 70) & 
        (df['low'] < df['prev_low'])
    ].copy()
    
    return bullish, bearish


def compare_signals_and_positions():
    """Main comparison function"""
    print("=" * 80)
    print("📊 RSI Signals vs Actual Backtest Positions - Oct 29, 2024")
    print("=" * 80)
    
    # Load backtest positions
    positions_df = load_backtest_positions()
    
    # Load RSI signals
    bullish_signals, bearish_signals = analyze_rsi_signals()
    
    # Summary
    print("\n📈 EXPECTED (Based on Strategy Config):")
    print("-" * 80)
    print("  entry-3 (CE): Max 9 entries")
    print("  entry-4 (PE): Max 10 entries")
    print("  TOTAL EXPECTED: Up to 19 positions")
    
    print("\n📊 RSI SIGNALS FOUND:")
    print("-" * 80)
    print(f"  🟢 Bullish (RSI<30 + breakout): {len(bullish_signals)} signals")
    if len(bullish_signals) > 0:
        for _, sig in bullish_signals.iterrows():
            print(f"     • {sig['timestamp'].strftime('%H:%M:%S')} - RSI: {sig['prev_rsi']:.1f} → {sig['rsi_14']:.1f}")
    
    print(f"\n  🔴 Bearish (RSI>70 + breakdown): {len(bearish_signals)} signals")
    if len(bearish_signals) > 0:
        for _, sig in bearish_signals.iterrows():
            print(f"     • {sig['timestamp'].strftime('%H:%M:%S')} - RSI: {sig['prev_rsi']:.1f} → {sig['rsi_14']:.1f}")
    
    print("\n🎯 ACTUAL POSITIONS CREATED:")
    print("-" * 80)
    
    # Group by entry node
    for node_id in positions_df['entry_node'].unique():
        node_positions = positions_df[positions_df['entry_node'] == node_id]
        print(f"\n  {node_id}: {len(node_positions)} positions")
        
        for _, pos in node_positions.iterrows():
            entry_time = pos['entry_time']
            if hasattr(entry_time, 'strftime'):
                entry_time_str = entry_time.strftime('%H:%M:%S')
            else:
                entry_time_str = str(entry_time)
            
            re_entry = f" (re-entry {pos['re_entry_num']})" if pos['re_entry_num'] > 0 else ""
            pnl_str = f"{pos['pnl']:+.2f}" if pd.notna(pos['pnl']) else "N/A"
            print(f"     • {entry_time_str} - {pos['option_type']} {pos['side']}{re_entry} | P&L: ₹{pnl_str}")
    
    print(f"\n  TOTAL ACTUAL: {len(positions_df)} positions")
    
    # Analysis
    print("\n🔍 ANALYSIS:")
    print("=" * 80)
    
    total_signals = len(bullish_signals) + len(bearish_signals)
    gap = total_signals - len(positions_df)
    
    print(f"RSI Signals Found: {total_signals}")
    print(f"Positions Created: {len(positions_df)}")
    print(f"Gap: {gap} signals did NOT create positions")
    
    print("\n❓ Possible Reasons for Gap:")
    print("-" * 80)
    print("1. ⏰ Time filters: Entries may stop after certain time")
    print("2. 🔢 Re-entry limits: Max entries per node reached")
    print("3. 📊 Additional conditions: Other filters beyond RSI")
    print("4. 💼 Position limits: Max open positions restriction")
    print("5. 🎯 Strategy state: Strategy may have terminated early")
    
    # Check if signals aligned with position times
    print("\n✅ Signal-Position Time Matching:")
    print("-" * 80)
    
    for _, pos in positions_df.iterrows():
        pos_time = pos['entry_time']
        if hasattr(pos_time, 'floor'):
            pos_time = pos_time.floor('min')  # Round to minute
            
            # Check bullish signals
            for _, sig in bullish_signals.iterrows():
                sig_time = sig['timestamp'].floor('min')
                if sig_time == pos_time:
                    print(f"  ✓ {pos['entry_node']} at {pos_time.strftime('%H:%M')} matched bullish signal")
            
            # Check bearish signals  
            for _, sig in bearish_signals.iterrows():
                sig_time = sig['timestamp'].floor('min')
                if sig_time == pos_time:
                    print(f"  ✓ {pos['entry_node']} at {pos_time.strftime('%H:%M')} matched bearish signal")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    compare_signals_and_positions()
