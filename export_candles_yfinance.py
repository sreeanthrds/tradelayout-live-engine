"""
Export 1-minute candles with RSI(14) to CSV using yfinance
Loads historical candles + Oct 29, 2024 candles
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

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
    """Load candles from yfinance and calculate RSI"""
    
    # Map symbols to Yahoo Finance tickers
    ticker_map = {
        'NIFTY': '^NSEI',
        'BANKNIFTY': '^NSEBANK'
    }
    
    yf_ticker = ticker_map.get(symbol, symbol)
    
    print(f"📊 Loading candles from Yahoo Finance...")
    print(f"   Symbol: {symbol} (Yahoo: {yf_ticker})")
    print(f"   Target Date: {target_date}")
    
    # Calculate date range
    target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    
    # Get 5 days of data to ensure we have 500+ candles
    start_date = target_dt - timedelta(days=10)
    end_date = target_dt + timedelta(days=1)
    
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    
    try:
        # Download 1-minute data
        ticker = yf.Ticker(yf_ticker)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval='1m',
            actions=False
        )
        
        if df.empty:
            print(f"❌ No data found for {yf_ticker}")
            return None
        
        print(f"✅ Loaded {len(df)} candles")
        
        # Reset index to make timestamp a column
        df = df.reset_index()
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Convert to IST (UTC+5:30)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
        
        # Calculate RSI(14)
        print(f"\n📊 Calculating RSI(14)...")
        df['rsi_14'] = calculate_rsi(df['close'], period=14)
        
        # Round values
        df['open'] = df['open'].round(2)
        df['high'] = df['high'].round(2)
        df['low'] = df['low'].round(2)
        df['close'] = df['close'].round(2)
        df['rsi_14'] = df['rsi_14'].round(2)
        
        # Add date and time columns
        df['date'] = df['timestamp'].dt.date
        df['time'] = df['timestamp'].dt.time
        
        # Reorder columns
        df = df[['timestamp', 'date', 'time', 'open', 'high', 'low', 'close', 'volume', 'rsi_14']]
        
        # Filter to only include market hours (9:15 AM to 3:30 PM IST)
        df = df[
            (df['timestamp'].dt.hour >= 9) & 
            (
                (df['timestamp'].dt.hour < 15) | 
                ((df['timestamp'].dt.hour == 15) & (df['timestamp'].dt.minute <= 30))
            )
        ]
        
        # Keep last 500 + target date candles
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        target_candles = df[df['date'] == target_date_obj]
        before_candles = df[df['date'] < target_date_obj].tail(500)
        
        # Combine
        df = pd.concat([before_candles, target_candles], ignore_index=True)
        
        print(f"✅ Filtered to {len(df)} candles (500 historical + {len(target_candles)} on {target_date})")
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        print(f"\n✅ Exported to: {output_file}")
        
        # Show statistics
        print(f"\n📊 Sample data (last 10 rows):")
        print(df[['timestamp', 'open', 'high', 'low', 'close', 'rsi_14']].tail(10).to_string(index=False))
        
        print(f"\n📈 RSI Statistics:")
        rsi_data = df['rsi_14'].dropna()
        if len(rsi_data) > 0:
            print(f"   Min: {rsi_data.min():.2f}")
            print(f"   Max: {rsi_data.max():.2f}")
            print(f"   Mean: {rsi_data.mean():.2f}")
        
        # Count candles per date
        print(f"\n📅 Candles per date:")
        candles_per_date = df.groupby('date').size()
        for d, count in candles_per_date.items():
            print(f"   {d}: {count} candles")
        
        return df
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return None


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
