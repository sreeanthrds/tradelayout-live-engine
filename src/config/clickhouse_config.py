#!/usr/bin/env python3
"""
ClickHouse Configuration for Live Trading Engine
"""

import os
from typing import Dict, Any


class ClickHouseConfig:
    """ClickHouse database configuration."""
    
    # Connection settings - Using localhost
    HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    USER = os.getenv('CLICKHOUSE_USER', 'default')
    PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    SECURE = os.getenv('CLICKHOUSE_SECURE', 'false').lower() == 'true'
    DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'tradelayout')
    
    # Table settings
    TABLE_NAME = os.getenv('CLICKHOUSE_TABLE', 'nse_ticks_stocks')
    
    # Query settings
    BATCH_SIZE = int(os.getenv('CLICKHOUSE_BATCH_SIZE', '10000'))
    QUERY_TIMEOUT = int(os.getenv('CLICKHOUSE_QUERY_TIMEOUT', '300'))  # seconds
    
    # Timezone configuration
    # BACKUP_SHIFTED: For Dec 6 backup (data stored with +5:30 hour shift)
    # IST: For live trading data (correct timezone)
    DATA_TIMEZONE = os.getenv('CLICKHOUSE_DATA_TIMEZONE', 'IST')
    
    # Market hours for different data sources
    # BACKUP_SHIFTED: IST times + 5:30 hours
    #   09:15:00 + 5:30 = 14:45:00
    #   15:30:00 + 5:30 = 21:00:00
    MARKET_OPEN_TIME_BACKUP = '14:45:00'
    MARKET_CLOSE_TIME_BACKUP = '21:00:00'
    
    # IST: Correct market hours for live trading
    MARKET_OPEN_TIME_IST = '09:15:00'
    MARKET_CLOSE_TIME_IST = '15:30:00'
    
    @classmethod
    def get_market_hours(cls) -> tuple:
        """Get market hours based on configured timezone."""
        if cls.DATA_TIMEZONE == 'BACKUP_SHIFTED':
            return (cls.MARKET_OPEN_TIME_BACKUP, cls.MARKET_CLOSE_TIME_BACKUP)
        else:
            return (cls.MARKET_OPEN_TIME_IST, cls.MARKET_CLOSE_TIME_IST)
    
    @classmethod
    def get_connection_config(cls) -> Dict[str, Any]:
        """Get ClickHouse connection configuration."""
        return {
            'host': cls.HOST,
            'user': cls.USER,
            'password': cls.PASSWORD,
            'secure': cls.SECURE,
            'database': cls.DATABASE
        }
    
    @classmethod
    def get_table_config(cls) -> Dict[str, Any]:
        """Get ClickHouse table configuration."""
        return {
            'table': cls.TABLE_NAME,
            'batch_size': cls.BATCH_SIZE,
            'query_timeout': cls.QUERY_TIMEOUT
        }
    
    @classmethod
    def get_market_hours_config(cls) -> Dict[str, str]:
        """Get market hours configuration."""
        return {
            'open_time': cls.MARKET_OPEN_TIME,
            'close_time': cls.MARKET_CLOSE_TIME
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate ClickHouse configuration."""
        required_fields = ['HOST', 'USER', 'PASSWORD', 'TABLE_NAME']
        
        for field in required_fields:
            if not getattr(cls, field):
                print(f"Error: Missing required ClickHouse configuration: {field}")
                return False
        
        return True


# Default configuration instance
clickhouse_config = ClickHouseConfig() 