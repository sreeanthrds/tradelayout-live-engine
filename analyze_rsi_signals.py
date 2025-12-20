#!/usr/bin/env python3
"""
Reusable script to analyze RSI + Price Breakout signals
Usage: python analyze_rsi_signals.py [date] [csv_file]
Example: python analyze_rsi_signals.py 2024-10-29 candles_rsi_NIFTY_2024-10-29.csv
"""
import pandas as pd
import sys
from datetime import datetime

def analyze_rsi_signals(csv_file, target_date_str='2024-10-29'):
    """
    Analyze RSI + Price breakout signals for a specific date
    
    Args:
        csv_file: Path to CSV file with candles and RSI data
        target_date_str: Date to analyze in YYYY-MM-DD format
        
    Returns:
        tuple: (bullish_signals_df, bearish_signals_df)
    """
    # Read CSV
    df = pd.read_csv(csv_file)
    df.columns = df.columns.str.strip()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert numeric columns to float
    numeric_cols = ['prev_rsi', 'prev_high', 'prev_low', 'rsi_14', 'high', 'low', 'close', 'open']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Filter only target date
    target_date = pd.to_datetime(target_date_str).date()
    target_df = df[df['timestamp'].dt.date == target_date].copy()
    
    if len(target_df) == 0:
        print(f"❌ No data found for {target_date_str}")
        return None, None
    
    # Bullish signals: prev_rsi < 30 AND current_high > prev_high
    bullish_signals = target_df[
        (target_df['prev_rsi'].notna()) &
        (target_df['prev_high'].notna()) &
        (target_df['prev_rsi'] < 30) & 
        (target_df['high'] > target_df['prev_high'])
    ].copy()
    
    # Bearish signals: prev_rsi > 70 AND current_low < prev_low
    bearish_signals = target_df[
        (target_df['prev_rsi'].notna()) &
        (target_df['prev_low'].notna()) &
        (target_df['prev_rsi'] > 70) & 
        (target_df['low'] < target_df['prev_low'])
    ].copy()
    
    return bullish_signals, bearish_signals


def print_signals(bullish_signals, bearish_signals, target_date_str):
    """Print signal analysis"""
    print("=" * 80)
    print(f"📊 RSI + Price Breakout Signal Analysis")
    print(f"📅 Date: {target_date_str}")
    print("=" * 80)
    
    # Bullish signals
    print(f"\n🟢 BULLISH SIGNALS: prev_rsi < 30 AND current_high > prev_high")
    print("-" * 80)
    
    if len(bullish_signals) > 0:
        print(f"Found {len(bullish_signals)} bullish signal(s):\n")
        for idx, row in bullish_signals.iterrows():
            print(f"⏰ {row['timestamp'].strftime('%H:%M:%S')}")
            print(f"   Prev RSI: {row['prev_rsi']:.2f} (< 30 ✓)")
            print(f"   Current High: {row['high']:.2f} > Prev High: {row['prev_high']:.2f} ✓")
            print(f"   Current Close: {row['close']:.2f}")
            print(f"   Current RSI: {row['rsi_14']:.2f}")
            print()
    else:
        print("❌ No bullish signals found\n")
    
    # Bearish signals
    print(f"🔴 BEARISH SIGNALS: prev_rsi > 70 AND current_low < prev_low")
    print("-" * 80)
    
    if len(bearish_signals) > 0:
        print(f"Found {len(bearish_signals)} bearish signal(s):\n")
        for idx, row in bearish_signals.iterrows():
            print(f"⏰ {row['timestamp'].strftime('%H:%M:%S')}")
            print(f"   Prev RSI: {row['prev_rsi']:.2f} (> 70 ✓)")
            print(f"   Current Low: {row['low']:.2f} < Prev Low: {row['prev_low']:.2f} ✓")
            print(f"   Current Close: {row['close']:.2f}")
            print(f"   Current RSI: {row['rsi_14']:.2f}")
            print()
    else:
        print("❌ No bearish signals found\n")
    
    # Summary
    print("📈 SUMMARY")
    print("=" * 80)
    print(f"Bullish Signals: {len(bullish_signals)}")
    print(f"Bearish Signals: {len(bearish_signals)}")
    print(f"Total Signals: {len(bullish_signals) + len(bearish_signals)}")
    print("=" * 80)


def export_signals(bullish_signals, bearish_signals, output_file):
    """Export signals to CSV"""
    if len(bullish_signals) > 0 or len(bearish_signals) > 0:
        bullish_signals['signal_type'] = 'BULLISH'
        bearish_signals['signal_type'] = 'BEARISH'
        
        all_signals = pd.concat([bullish_signals, bearish_signals], ignore_index=True)
        all_signals = all_signals.sort_values('timestamp')
        
        all_signals.to_csv(output_file, index=False)
        print(f"\n✅ Signals exported to: {output_file}")
        return True
    return False


if __name__ == "__main__":
    # Parse command line arguments
    csv_file = 'candles_rsi_NIFTY_2024-10-29.csv'
    target_date = '2024-10-29'
    
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    if len(sys.argv) > 2:
        csv_file = sys.argv[2]
    
    print(f"\n📁 Reading: {csv_file}")
    print(f"📅 Target Date: {target_date}\n")
    
    # Analyze signals
    bullish_signals, bearish_signals = analyze_rsi_signals(csv_file, target_date)
    
    if bullish_signals is not None:
        # Print results
        print_signals(bullish_signals, bearish_signals, target_date)
        
        # Export to CSV
        output_file = f'rsi_signals_{target_date}.csv'
        export_signals(bullish_signals, bearish_signals, output_file)
