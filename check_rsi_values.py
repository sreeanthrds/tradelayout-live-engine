#!/usr/bin/env python3
"""
Check actual RSI values on Oct 1st to see if condition RSI > 70 is ever met
"""
import os
import sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ['SUPABASE_URL'] = 'https://oonepfqgzpdssfzvokgk.supabase.co'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vbmVwZnFnenBkc3NmenZva2drIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MDE5OTkxNCwiZXhwIjoyMDY1Nzc1OTE0fQ.qmUNhAh3oVhPW2lcAkw7E2Z19MenEIoWCBXCR9Hq6Kg'

from src.backtesting.data_manager import DataManager
from src.backtesting.backtest_config import BacktestConfig
from datetime import datetime, date

# Get historical data with indicators
config = BacktestConfig(
    strategy_ids=['64c2c932-0e0b-462a-9a36-7cda4371d102'],
    backtest_date=date(2024, 10, 1),
    debug_mode=None
)

# Fetch strategy
from supabase import create_client
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
result = supabase.table('strategies').select('*').eq('id', '64c2c932-0e0b-462a-9a36-7cda4371d102').execute()
strategy_data = result.data[0]

# Initialize DataManager
data_manager = DataManager(
    strategy_id='64c2c932-0e0b-462a-9a36-7cda4371d102',
    strategy_data=strategy_data,
    backtest_date=datetime(2024, 10, 1),
    subscriber_id='test_rsi'
)

# Initialize from historical data
data_manager.initialize_from_historical_data()

# Get candles with indicators
candles_1m = data_manager.get_candles('NIFTY:1m')

print(f"\n{'='*120}")
print(f"RSI VALUES ON OCT 1ST 2024 - CHECKING FOR RSI > 70")
print(f"{'='*120}\n")

print(f"Total candles with indicators: {len(candles_1m)}\n")

# Convert to DataFrame for easier analysis
df = pd.DataFrame(candles_1m)

# Check if RSI indicator exists
if 'indicators' in df.columns and len(df) > 0:
    # Extract RSI values
    rsi_values = []
    for idx, row in df.iterrows():
        indicators = row.get('indicators', {})
        rsi = indicators.get('rsi_1764539168968', None)
        timestamp = row.get('timestamp', 'N/A')
        close = row.get('close', 0)
        low = row.get('low', 0)
        high = row.get('high', 0)
        
        rsi_values.append({
            'timestamp': timestamp,
            'close': close,
            'low': low,
            'high': high,
            'rsi': rsi
        })
    
    rsi_df = pd.DataFrame(rsi_values)
    
    # Show times when RSI > 70
    high_rsi = rsi_df[rsi_df['rsi'] > 70]
    
    if len(high_rsi) > 0:
        print(f"✅ Found {len(high_rsi)} candles where RSI > 70:\n")
        print(f"{'Time':<10} {'Close':<10} {'Low':<10} {'High':<10} {'RSI':<10}")
        print(f"{'-'*60}")
        for idx, row in high_rsi.iterrows():
            ts = str(row['timestamp']).split(' ')[1] if ' ' in str(row['timestamp']) else str(row['timestamp'])
            print(f"{ts:<10} {row['close']:<10.2f} {row['low']:<10.2f} {row['high']:<10.2f} {row['rsi']:<10.2f}")
    else:
        print(f"❌ NO candles found where RSI > 70")
        print(f"\nMax RSI value: {rsi_df['rsi'].max():.2f}")
        print(f"Min RSI value: {rsi_df['rsi'].min():.2f}")
        print(f"Average RSI: {rsi_df['rsi'].mean():.2f}")
    
    # Show candles around 09:18
    print(f"\n{'='*120}")
    print(f"CANDLES AROUND 09:18 (Expected Entry Time)")
    print(f"{'='*120}\n")
    
    morning_candles = rsi_df[rsi_df['timestamp'].astype(str).str.contains('09:1')]
    
    if len(morning_candles) > 0:
        print(f"{'Time':<12} {'Close':<10} {'Low':<10} {'High':<10} {'RSI':<10} {'RSI>70':<8}")
        print(f"{'-'*70}")
        for idx, row in morning_candles.iterrows():
            ts = str(row['timestamp']).split(' ')[1] if ' ' in str(row['timestamp']) else str(row['timestamp'])
            rsi_check = '✅ YES' if row['rsi'] > 70 else '❌ No'
            print(f"{ts:<12} {row['close']:<10.2f} {row['low']:<10.2f} {row['high']:<10.2f} {row['rsi']:<10.2f} {rsi_check:<8}")
    
    # Check specific entry condition at 09:18
    candle_0918 = rsi_df[rsi_df['timestamp'].astype(str).str.contains('09:18')]
    if len(candle_0918) > 0:
        print(f"\n{'='*120}")
        print(f"SPECIFIC CHECK AT 09:18")
        print(f"{'='*120}")
        row_918 = candle_0918.iloc[0]
        
        # Get previous candle (09:17)
        idx_918 = candle_0918.index[0]
        if idx_918 > 0:
            row_917 = rsi_df.iloc[idx_918 - 1]
            
            print(f"\nPrevious Candle (09:17):")
            print(f"  Low: {row_917['low']:.2f}")
            print(f"  RSI: {row_917['rsi']:.2f}")
            
            print(f"\nCurrent Candle (09:18):")
            print(f"  Close: {row_918['close']:.2f}")
            print(f"  RSI: {row_918['rsi']:.2f}")
            
            print(f"\nCondition Checks:")
            print(f"  RSI(offset=-1) > 70: {row_917['rsi']:.2f} > 70 = {row_917['rsi'] > 70}")
            print(f"  LTP < Low(offset=-1): Need live LTP data")
            
else:
    print(f"❌ No indicator data found in candles")

print(f"\n{'='*120}\n")
