#!/usr/bin/env python3
"""
Corrected Entry Signal Analysis
Entry-3 and Entry-4 both use RSI < 30 (oversold), but different price actions
"""
import pandas as pd
import json

def analyze_entry_signals(csv_file='candles_rsi_NIFTY_2024-10-29.csv', target_date='2024-10-29'):
    """Analyze entry signals with corrected logic"""
    
    # Read CSV
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert numeric columns
    for col in ['prev_rsi', 'prev_high', 'prev_low', 'rsi_14', 'high', 'low', 'close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter target date
    target_date = pd.to_datetime(target_date).date()
    df = df[df['timestamp'].dt.date == target_date].copy()
    
    # Entry-3 (CE): prev_rsi < 30 AND high > prev_high (bullish breakout from oversold)
    entry3_signals = df[
        (df['prev_rsi'].notna()) &
        (df['prev_high'].notna()) &
        (df['prev_rsi'] < 30) & 
        (df['high'] > df['prev_high'])
    ].copy()
    entry3_signals['signal_type'] = 'ENTRY-3 (CE)'
    
    # Entry-4 (PE): prev_rsi < 30 AND low < prev_low (bearish breakdown from oversold)
    entry4_signals = df[
        (df['prev_rsi'].notna()) &
        (df['prev_low'].notna()) &
        (df['prev_rsi'] < 30) & 
        (df['low'] < df['prev_low'])
    ].copy()
    entry4_signals['signal_type'] = 'ENTRY-4 (PE)'
    
    return entry3_signals, entry4_signals


def compare_with_actual_positions(entry3_signals, entry4_signals):
    """Compare signals with actual backtest positions"""
    
    print("=" * 100)
    print("✅ CORRECTED ENTRY SIGNAL ANALYSIS - Oct 29, 2024")
    print("=" * 100)
    
    print("\n📋 STRATEGY LOGIC:")
    print("-" * 100)
    print("Both entries use RSI < 30 (OVERSOLD ZONE), but different price actions:")
    print()
    print("🟢 Entry-3 (CE): prev_rsi < 30 AND high > prev_high")
    print("   → Bullish breakout from oversold → BUY CALL")
    print()
    print("🔴 Entry-4 (PE): prev_rsi < 30 AND low < prev_low")
    print("   → Bearish breakdown from oversold → BUY PUT")
    
    print("\n" + "=" * 100)
    print(f"🟢 ENTRY-3 (CE) SIGNALS: {len(entry3_signals)}")
    print("-" * 100)
    
    for _, row in entry3_signals.iterrows():
        print(f"⏰ {row['timestamp'].strftime('%H:%M:%S')}")
        print(f"   Prev RSI: {row['prev_rsi']:.2f} → Current RSI: {row['rsi_14']:.2f}")
        print(f"   High: {row['high']:.2f} > Prev High: {row['prev_high']:.2f} ✓")
        print(f"   Close: {row['close']:.2f}")
        print()
    
    print("\n" + "=" * 100)
    print(f"🔴 ENTRY-4 (PE) SIGNALS: {len(entry4_signals)}")
    print("-" * 100)
    
    for _, row in entry4_signals.iterrows():
        print(f"⏰ {row['timestamp'].strftime('%H:%M:%S')}")
        print(f"   Prev RSI: {row['prev_rsi']:.2f} → Current RSI: {row['rsi_14']:.2f}")
        print(f"   Low: {row['low']:.2f} < Prev Low: {row['prev_low']:.2f} ✓")
        print(f"   Close: {row['close']:.2f}")
        print()
    
    # Load actual positions
    try:
        with open('backtest_dashboard_data_2024-10-29.json', 'r') as f:
            data = json.load(f)
        
        positions = data.get('positions', [])
        entry3_positions = [p for p in positions if p.get('entry_node_id') == 'entry-3']
        entry4_positions = [p for p in positions if p.get('entry_node_id') == 'entry-4']
        
        print("\n" + "=" * 100)
        print("📊 SIGNALS vs ACTUAL POSITIONS:")
        print("-" * 100)
        
        print(f"\n🟢 Entry-3 (CE):")
        print(f"   Signals Found: {len(entry3_signals)}")
        print(f"   Positions Created: {len(entry3_positions)}")
        for pos in entry3_positions:
            entry_time = pos.get('entry_time', '').split('T')[1] if 'T' in pos.get('entry_time', '') else ''
            re_entry = f" (re-entry {pos.get('re_entry_num', 0)})" if pos.get('re_entry_num', 0) > 0 else ""
            print(f"     • {entry_time}{re_entry}")
        
        print(f"\n🔴 Entry-4 (PE):")
        print(f"   Signals Found: {len(entry4_signals)}")
        print(f"   Positions Created: {len(entry4_positions)}")
        for pos in entry4_positions:
            entry_time = pos.get('entry_time', '').split('T')[1] if 'T' in pos.get('entry_time', '') else ''
            re_entry = f" (re-entry {pos.get('re_entry_num', 0)})" if pos.get('re_entry_num', 0) > 0 else ""
            print(f"     • {entry_time}{re_entry}")
        
        print(f"\n📈 TOTAL:")
        print(f"   Total Signals: {len(entry3_signals) + len(entry4_signals)}")
        print(f"   Total Positions: {len(positions)}")
        
        gap = (len(entry3_signals) + len(entry4_signals)) - len(positions)
        if gap == 0:
            print(f"\n   ✅ Signals match position count!")
        else:
            print(f"\n   Gap: {gap} (some signals didn't create positions or re-entries used different logic)")
        
    except FileNotFoundError:
        print("\n❌ backtest_dashboard_data_2024-10-29.json not found")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    entry3_signals, entry4_signals = analyze_entry_signals()
    compare_with_actual_positions(entry3_signals, entry4_signals)
