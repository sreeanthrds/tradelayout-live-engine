"""
Data Availability Checker
==========================

Verifies that sufficient OHLC data exists in ClickHouse before running backtests.
Prevents failed backtests due to missing data.
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict
import clickhouse_connect

logger = logging.getLogger(__name__)


class DataAvailabilityChecker:
    """
    Check if OHLC data is available for backtest dates.
    
    Queries the OHLC tables to ensure data exists before running backtests.
    """
    
    def __init__(self, clickhouse_client):
        """
        Initialize data availability checker.
        
        Args:
            clickhouse_client: ClickHouse client instance
        """
        self.client = clickhouse_client
        logger.info("🔍 Data Availability Checker initialized")
    
    def check_date_availability(
        self,
        backtest_date: datetime,
        symbols: List[str],
        timeframe: str = '1d'
    ) -> Dict[str, any]:
        """
        Check if data is available for the requested backtest date.
        
        Args:
            backtest_date: Date to backtest
            symbols: List of symbols to check
            timeframe: Timeframe to check (default: '1d' for daily data)
        
        Returns:
            Dictionary with:
            - 'available': bool - Whether data is available
            - 'reason': str - Reason if not available
            - 'first_available': datetime - First date with data
            - 'last_available': datetime - Last date with data
            - 'missing_symbols': List[str] - Symbols with missing data
        """
        try:
            backtest_date_str = backtest_date.strftime('%Y-%m-%d')
            
            # Check overall date range in database (1d data doesn't have timeframe column)
            range_query = f"""
                SELECT 
                    min(toDate(timestamp)) as first_date,
                    max(toDate(timestamp)) as last_date
                FROM nse_ohlcv_indices
            """
            
            range_result = self.client.query(range_query)
            
            if not range_result or range_result.row_count == 0:
                logger.error("❌ No OHLC data found in database")
                return {
                    'available': False,
                    'reason': f'No OHLC data found in nse_ohlcv_indices table for timeframe {timeframe}',
                    'first_available': None,
                    'last_available': None,
                    'missing_symbols': symbols
                }
            
            first_available, last_available = range_result.first_row
            
            # Convert to date for comparison
            if isinstance(first_available, datetime):
                first_available_date = first_available.date()
            else:
                first_available_date = first_available
            
            if isinstance(last_available, datetime):
                last_available_date = last_available.date()
            else:
                last_available_date = last_available
            
            backtest_date_only = backtest_date.date() if isinstance(backtest_date, datetime) else backtest_date
            
            logger.info(f"📅 Database date range: {first_available_date} to {last_available_date}")
            logger.info(f"📅 Requested backtest date: {backtest_date_only}")
            
            # Check if backtest date is within range
            if backtest_date_only < first_available_date:
                logger.warning(f"⚠️  Backtest date {backtest_date_only} is before first available date {first_available_date}")
                return {
                    'available': False,
                    'reason': f'Backtest date {backtest_date_only} is before first available date {first_available_date}',
                    'first_available': first_available,
                    'last_available': last_available,
                    'missing_symbols': []
                }
            
            if backtest_date_only > last_available_date:
                logger.warning(f"⚠️  Backtest date {backtest_date_only} is after last available date {last_available_date}")
                return {
                    'available': False,
                    'reason': f'Backtest date {backtest_date_only} is beyond last available date {last_available_date}',
                    'first_available': first_available,
                    'last_available': last_available,
                    'missing_symbols': []
                }
            
            # Check specific symbols on the requested date (use 'ticker' column)
            missing_symbols = []
            for symbol in symbols:
                symbol_query = f"""
                    SELECT count(*) as candle_count
                    FROM nse_ohlcv_indices
                    WHERE ticker = '{symbol}'
                      AND toDate(timestamp) = '{backtest_date_str}'
                """
                
                symbol_result = self.client.query(symbol_query)
                
                if symbol_result and symbol_result.row_count > 0:
                    candle_count = symbol_result.first_row[0]
                    if candle_count == 0:
                        logger.warning(f"⚠️  No data for {symbol} on {backtest_date_str}")
                        missing_symbols.append(symbol)
                    else:
                        logger.info(f"✅ {symbol}: {candle_count} candles on {backtest_date_str}")
                else:
                    missing_symbols.append(symbol)
            
            if missing_symbols:
                logger.warning(f"⚠️  Missing data for symbols: {missing_symbols} on {backtest_date_str}")
                return {
                    'available': False,
                    'reason': f'Missing data for symbols: {", ".join(missing_symbols)} on {backtest_date_str}',
                    'first_available': first_available,
                    'last_available': last_available,
                    'missing_symbols': missing_symbols
                }
            
            logger.info(f"✅ All data available for {backtest_date_str}")
            return {
                'available': True,
                'reason': 'Data available',
                'first_available': first_available,
                'last_available': last_available,
                'missing_symbols': []
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking data availability: {e}")
            return {
                'available': False,
                'reason': f'Error checking availability: {str(e)}',
                'first_available': None,
                'last_available': None,
                'missing_symbols': symbols
            }
    
    def get_available_date_range(self, symbols: List[str], timeframe: str = '1d') -> Dict:
        """
        Get the available date range for specific symbols.
        
        Args:
            symbols: List of symbols to check
            timeframe: Timeframe to check (default: '1d')
        
        Returns:
            Dictionary with date range information
        """
        try:
            symbols_str = "', '".join(symbols)
            query = f"""
                SELECT 
                    ticker,
                    min(toDate(timestamp)) as first_date,
                    max(toDate(timestamp)) as last_date,
                    count(DISTINCT toDate(timestamp)) as total_candles
                FROM nse_ohlcv_indices
                WHERE ticker IN ('{symbols_str}')
                GROUP BY ticker
                ORDER BY ticker
            """
            
            result = self.client.query(query)
            
            if not result or result.row_count == 0:
                return {}
            
            date_ranges = {}
            for row in result.result_rows:
                symbol, first_date, last_date, total_candles = row
                date_ranges[symbol] = {
                    'first_date': first_date,
                    'last_date': last_date,
                    'total_candles': total_candles
                }
            
            return date_ranges
            
        except Exception as e:
            logger.error(f"❌ Error getting date ranges: {e}")
            return {}
