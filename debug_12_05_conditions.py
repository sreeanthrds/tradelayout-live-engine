#!/usr/bin/env python3
"""
Debug exactly why conditions fail at 12:05
"""
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"\n{'='*100}")
print(f"DEBUG 12:05 CONDITIONS")
print(f"{'='*100}\n")

# Load CSV
csv_path = '/Users/sreenathreddy/Downloads/UniTrader-project/backtesting_project/tradelayout-engine/candles_rsi_NIFTY_2024-10-29.csv'
df = pd.read_csv(csv_path)
df.columns = df.columns.str.strip()
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Get 12:04 and 12:05 candles
candle_12_04 = df[df['timestamp'] == '2024-10-29 12:04:00'].iloc[0]
candle_12_05 = df[df['timestamp'] == '2024-10-29 12:05:00'].iloc[0]

print("re-entry-signal-4 conditions:")
print("  1. RSI > 70 (previous candle)")
print("  2. LTP < Low[-1]")
print()

print(f"At 12:05:00:")
print(f"  Current candle close (acts as LTP): {candle_12_05['close']}")
print(f"  Previous candle (12:04):")
print(f"    RSI: {candle_12_04['rsi_14']}")
print(f"    Low: {candle_12_04['low']}")
print()

prev_rsi = candle_12_04['rsi_14']
current_close = candle_12_05['close']
prev_low = candle_12_04['low']

condition_1 = prev_rsi > 70
condition_2 = current_close < prev_low

print(f"Condition 1 (RSI > 70): {prev_rsi:.2f} > 70 = {condition_1} {'✓' if condition_1 else '✗'}")
print(f"Condition 2 (LTP < Low[-1]): {current_close:.2f} < {prev_low:.2f} = {condition_2} {'✓' if condition_2 else '✗'}")
print()
print(f"BOTH conditions met: {condition_1 and condition_2} {'✓✓✓' if (condition_1 and condition_2) else '✗✗✗'}")

print(f"\n{'='*100}\n")
