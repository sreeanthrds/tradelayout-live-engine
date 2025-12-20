"""
Filter NIFTY candles for RSI + Price breakout signals
1. Previous RSI < 30 AND Current High > Previous High (Bullish)
2. Previous RSI > 70 AND Current Low < Previous Low (Bearish)
"""
import pandas as pd

# Read CSV
df = pd.read_csv('candles_rsi_NIFTY_2024-10-29.csv')
df.columns = df.columns.str.strip()

# Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Convert numeric columns to float (handle string values)
df['prev_rsi'] = pd.to_numeric(df['prev_rsi'], errors='coerce')
df['prev_high'] = pd.to_numeric(df['prev_high'], errors='coerce')
df['prev_low'] = pd.to_numeric(df['prev_low'], errors='coerce')
df['rsi_14'] = pd.to_numeric(df['rsi_14'], errors='coerce')
df['high'] = pd.to_numeric(df['high'], errors='coerce')
df['low'] = pd.to_numeric(df['low'], errors='coerce')
df['close'] = pd.to_numeric(df['close'], errors='coerce')

print("=" * 80)
print("📊 RSI + Price Breakout Signal Filter")
print("=" * 80)

# Filter only Oct 29, 2024 data
target_date = pd.to_datetime('2024-10-29').date()
oct29_df = df[df['timestamp'].dt.date == target_date].copy()

print(f"\n📅 Analyzing only Oct 29, 2024: {len(oct29_df)} candles")
print(f"   Time range: {oct29_df['timestamp'].min().strftime('%H:%M')} to {oct29_df['timestamp'].max().strftime('%H:%M')}")

# Filter 1: Previous RSI < 30 AND Current High > Previous High (BULLISH)
print("\n🟢 BULLISH SIGNALS: prev_rsi < 30 AND current_high > prev_high")
print("-" * 80)

bullish_signals = oct29_df[
    (oct29_df['prev_rsi'].notna()) &
    (oct29_df['prev_high'].notna()) &
    (oct29_df['prev_rsi'] < 30) & 
    (oct29_df['high'] > oct29_df['prev_high'])
].copy()

if len(bullish_signals) > 0:
    print(f"Found {len(bullish_signals)} bullish signals:\n")
    for idx, row in bullish_signals.iterrows():
        print(f"⏰ {row['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Prev RSI: {row['prev_rsi']:.2f} (< 30 ✓)")
        print(f"   Current High: {row['high']:.2f} > Prev High: {row['prev_high']:.2f} ✓")
        print(f"   Current Close: {row['close']:.2f}")
        print(f"   Current RSI: {row['rsi_14']:.2f}")
        print()
else:
    print("❌ No bullish signals found")

# Filter 2: Previous RSI > 70 AND Current Low < Previous Low (BEARISH)
print("\n🔴 BEARISH SIGNALS: prev_rsi > 70 AND current_low < prev_low")
print("-" * 80)

bearish_signals = oct29_df[
    (oct29_df['prev_rsi'].notna()) &
    (oct29_df['prev_low'].notna()) &
    (oct29_df['prev_rsi'] > 70) & 
    (oct29_df['low'] < oct29_df['prev_low'])
].copy()

if len(bearish_signals) > 0:
    print(f"Found {len(bearish_signals)} bearish signals:\n")
    for idx, row in bearish_signals.iterrows():
        print(f"⏰ {row['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Prev RSI: {row['prev_rsi']:.2f} (> 70 ✓)")
        print(f"   Current Low: {row['low']:.2f} < Prev Low: {row['prev_low']:.2f} ✓")
        print(f"   Current Close: {row['close']:.2f}")
        print(f"   Current RSI: {row['rsi_14']:.2f}")
        print()
else:
    print("❌ No bearish signals found")

# Summary
print("\n📈 SUMMARY")
print("=" * 80)
print(f"Date: Oct 29, 2024")
print(f"Total Candles Analyzed: {len(oct29_df)}")
print(f"Bullish Signals: {len(bullish_signals)}")
print(f"Bearish Signals: {len(bearish_signals)}")
print(f"Total Signals: {len(bullish_signals) + len(bearish_signals)}")

# Export to CSV
if len(bullish_signals) > 0 or len(bearish_signals) > 0:
    # Combine signals with signal type
    bullish_signals['signal_type'] = 'BULLISH'
    bearish_signals['signal_type'] = 'BEARISH'
    
    all_signals = pd.concat([bullish_signals, bearish_signals], ignore_index=True)
    all_signals = all_signals.sort_values('timestamp')
    
    output_file = 'rsi_breakout_signals_2024-10-29.csv'
    all_signals.to_csv(output_file, index=False)
    print(f"\n✅ Signals exported to: {output_file}")

print("=" * 80)
