"""Analyze why only 4 positions instead of 11"""
import pandas as pd

# Load candle data
print("Loading data...")
df = pd.read_csv('candles_rsi_NIFTY_2024-10-29.csv')

# First check what columns we have
print("\nAvailable columns:")
print(df.columns.tolist())
print("\nFirst few rows:")
print(df.head())

# Convert columns to numeric (using actual column names)
for col in df.columns:
    if col != 'timestamp':
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Filter for after 09:17
df_after_917 = df[df['timestamp'] >= '2024-10-29 09:17:00'].copy()

print("=" * 100)
print("🔍 ANALYZING ENTRY-CONDITION-2 (Bearish/CE)")
print("=" * 100)
print("\nConditions:")
print("  1. Time > 09:17")
print("  2. Previous[RSI] > 70")
print("  3. LTP < Previous[Low]")

# Determine RSI column name (could be 'rsi', 'RSI', 'rsi_14', etc.)
rsi_col = None
for col in df.columns:
    if 'rsi' in col.lower():
        rsi_col = col
        break

if rsi_col:
    print(f"\n✅ Found RSI column: {rsi_col}")
    
    # Check how many times RSI > 70 after 09:17
    rsi_above_70 = df_after_917[df_after_917[rsi_col] > 70]
    print(f"✅ After 09:17: {len(df_after_917)} candles")
    print(f"✅ RSI > 70: {len(rsi_above_70)} times")
    
    # Find low columns
    low_col = 'low' if 'low' in df.columns else 'Low'
    ltp_col = 'ltp' if 'ltp' in df.columns else 'close'
    
    # Check how many times price < prev_low when RSI > 70
    rsi_above_70['prev_low'] = rsi_above_70[low_col].shift(1)
    both_conditions = rsi_above_70[rsi_above_70[ltp_col] < rsi_above_70['prev_low']]
    print(f"✅ RSI > 70 AND LTP < Prev Low: {len(both_conditions)} times")
    
    if len(both_conditions) > 0:
        print("\n" + "=" * 100)
        print("📊 TIMES WHEN ALL 3 CONDITIONS MET:")
        print("=" * 100)
        print(both_conditions[['timestamp', ltp_col, 'prev_low', rsi_col]].head(20).to_string(index=False))
else:
    print("❌ No RSI column found!")

if rsi_col:
    print("\n" + "=" * 100)
    print("📈 RSI DISTRIBUTION AFTER 09:17")
    print("=" * 100)
    print(f"RSI > 70: {len(df_after_917[df_after_917[rsi_col] > 70])} times")
    print(f"RSI 60-70: {len(df_after_917[(df_after_917[rsi_col] >= 60) & (df_after_917[rsi_col] <= 70)])} times")
    print(f"RSI 50-60: {len(df_after_917[(df_after_917[rsi_col] >= 50) & (df_after_917[rsi_col] <= 60)])} times")
    print(f"RSI 40-50: {len(df_after_917[(df_after_917[rsi_col] >= 40) & (df_after_917[rsi_col] <= 50)])} times")
    print(f"RSI 30-40: {len(df_after_917[(df_after_917[rsi_col] >= 30) & (df_after_917[rsi_col] <= 40)])} times")
    print(f"RSI < 30: {len(df_after_917[df_after_917[rsi_col] < 30])} times")

    print("\n" + "=" * 100)
    print("💡 CONCLUSION")
    print("=" * 100)
    if len(both_conditions) == 4:
        print("✅ BACKTEST IS CORRECT!")
        print(f"   The entry conditions were met exactly {len(both_conditions)} times.")
        print("   The strategy is working as configured.")
    elif len(both_conditions) == 11:
        print("❌ BACKTEST BUG!")
        print(f"   Conditions met {len(both_conditions)} times but only 4 positions created.")
    else:
        print(f"⚠️  Conditions met {len(both_conditions)} times")
        print(f"   Expected: 11 positions")
        print(f"   Actual: 4 positions")
        print("   Need to investigate further...")
