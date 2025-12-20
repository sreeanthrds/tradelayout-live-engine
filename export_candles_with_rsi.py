"""
Export 1-minute candles with RSI(14) to CSV
Loads 500 historical candles + Oct 29, 2024 candles
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, date, timedelta
import clickhouse_connect
from src.config.clickhouse_config import ClickHouseConfig

# RSI calculation
def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    deltas = prices.diff()
    gain = deltas.where(deltas > 0, 0)
    loss = -deltas.where(deltas < 0, 0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def load_candles_with_rsi(symbol='NIFTY', target_date='2024-10-29', output_file='candles_with_rsi.csv'):
    """Load candles and calculate RSI"""
    
    print(f"Connecting to ClickHouse...")
    try:
        client = clickhouse_connect.get_client(
            host=ClickHouseConfig.HOST,
            port=8443,
            user=ClickHouseConfig.USER,
            password=ClickHouseConfig.PASSWORD,
            secure=True
        )
        print(f"✅ Connected to ClickHouse")
    except Exception as e:
        print(f"❌ Failed to connect to ClickHouse: {e}")
        return None
    
    # Calculate date range: 500 candles before + target date
    target_dt = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    # Assuming market hours 9:15 AM to 3:30 PM = 375 minutes per day
    # 500 candles = ~2 days of data, so go back 5 days to be safe
    start_date = target_dt - timedelta(days=5)
    end_date = target_dt
    
    print(f"\n📅 Loading candles from {start_date} to {end_date}...")
    print(f"   Symbol: {symbol}")
    
    # Query ClickHouse
    query = f"""
    SELECT 
        timestamp,
        open,
        high,
        low,
        close,
        volume
    FROM tick_data_1m
    WHERE symbol = '{symbol}'
      AND toDate(timestamp) >= '{start_date}'
      AND toDate(timestamp) <= '{end_date}'
    ORDER BY timestamp ASC
    """
    
    try:
        result = client.query(query)
        df = pd.DataFrame(result.result_rows, columns=result.column_names)
        
        if df.empty:
            print(f"❌ No data found for {symbol} between {start_date} and {end_date}")
            return None
        
        print(f"✅ Loaded {len(df)} candles")
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate RSI(14)
        print(f"\n📊 Calculating RSI(14)...")
        df['rsi_14'] = calculate_rsi(df['close'], period=14)
        
        # Round RSI to 2 decimals
        df['rsi_14'] = df['rsi_14'].round(2)
        
        # Format timestamp for better readability
        df['date'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        
        # Reorder columns
        df = df[['timestamp', 'date', 'time', 'open', 'high', 'low', 'close', 'volume', 'rsi_14']]
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        print(f"\n✅ Exported to: {output_file}")
        print(f"   Total rows: {len(df)}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Show sample with RSI
        print(f"\n📊 Sample data (last 10 rows):")
        print(df.tail(10).to_string(index=False))
        
        # Show RSI statistics
        print(f"\n📈 RSI Statistics:")
        print(f"   Min: {df['rsi_14'].min():.2f}")
        print(f"   Max: {df['rsi_14'].max():.2f}")
        print(f"   Mean: {df['rsi_14'].mean():.2f}")
        
        # Count candles per date
        print(f"\n📅 Candles per date:")
        candles_per_date = df.groupby('date').size()
        for d, count in candles_per_date.items():
            print(f"   {d}: {count} candles")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None
    finally:
        client.close()


if __name__ == "__main__":
    # Load NIFTY candles for Oct 29, 2024
    df = load_candles_with_rsi(
        symbol='NIFTY',
        target_date='2024-10-29',
        output_file='nifty_candles_with_rsi_2024-10-29.csv'
    )
    
    if df is not None:
        print(f"\n✅ Success! File saved: nifty_candles_with_rsi_2024-10-29.csv")
    else:
        print(f"\n❌ Failed to export data")
