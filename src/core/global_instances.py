"""
Global instance manager for multi-strategy execution.

Manages singleton instances for:
- Production queue: Shared cache/data/tick processor for all users
- Admin/Tester queue: Isolated instances for testing

Designed for easy migration to distributed environment (Redis).

Author: UniTrader Team
Created: 2024-12-19
"""

from typing import Optional, Dict, Any
from src.core.cache_manager import CacheManager
from src.backtesting.data_manager import DataManager
from src.core.centralized_tick_processor import CentralizedTickProcessor
from src.utils.logger import log_info, log_warning


class GlobalInstanceManager:
    """
    Manage global singleton instances for multi-strategy execution.
    
    Two instance types:
    1. production: Shared across all users (scheduled at 09:13 AM)
    2. admin_tester: Isolated for testing (manual trigger)
    """
    
    def __init__(self):
        """Initialize instance storage."""
        self._instances: Dict[str, Dict[str, Any]] = {
            'production': {
                'cache': None,
                'data_manager': None,
                'tick_processor': None,
                'strategy_subscription_manager': None
            },
            'admin_tester': {
                'cache': None,
                'data_manager': None,
                'tick_processor': None,
                'strategy_subscription_manager': None
            }
        }
        
        log_info("🌐 GlobalInstanceManager initialized")
    
    def get_or_create_cache(self, instance_type: str = 'production') -> CacheManager:
        """
        Get or create CacheManager singleton.
        
        Args:
            instance_type: 'production' or 'admin_tester'
            
        Returns:
            CacheManager instance
        """
        if self._instances[instance_type]['cache'] is None:
            log_info(f"📦 Creating new CacheManager for {instance_type}")
            self._instances[instance_type]['cache'] = CacheManager()
        return self._instances[instance_type]['cache']
    
    def get_or_create_data_manager(
        self, 
        instance_type: str = 'production',
        broker_name: str = 'clickhouse'
    ) -> DataManager:
        """
        Get or create DataManager singleton.
        
        Args:
            instance_type: 'production' or 'admin_tester'
            broker_name: Broker name for data source
            
        Returns:
            DataManager instance
        """
        if self._instances[instance_type]['data_manager'] is None:
            cache = self.get_or_create_cache(instance_type)
            log_info(f"📊 Creating new DataManager for {instance_type}")
            self._instances[instance_type]['data_manager'] = DataManager(
                cache=cache,
                broker_name=broker_name
            )
        return self._instances[instance_type]['data_manager']
    
    def get_or_create_tick_processor(
        self,
        instance_type: str = 'production',
        thread_safe: bool = False
    ) -> CentralizedTickProcessor:
        """
        Get or create CentralizedTickProcessor singleton.
        
        Args:
            instance_type: 'production' or 'admin_tester'
            thread_safe: Enable thread safety for live trading
            
        Returns:
            CentralizedTickProcessor instance
        """
        if self._instances[instance_type]['tick_processor'] is None:
            cache = self.get_or_create_cache(instance_type)
            data_manager = self.get_or_create_data_manager(instance_type)
            log_info(f"⚙️ Creating new CentralizedTickProcessor for {instance_type}")
            self._instances[instance_type]['tick_processor'] = CentralizedTickProcessor(
                cache_manager=cache,
                data_manager=data_manager,
                thread_safe=thread_safe
            )
        return self._instances[instance_type]['tick_processor']
    
    def get_or_create_strategy_subscription_manager(
        self,
        instance_type: str = 'production'
    ):
        """
        Get or create StrategySubscriptionManager singleton.
        
        Args:
            instance_type: 'production' or 'admin_tester'
            
        Returns:
            StrategySubscriptionManager instance
        """
        if self._instances[instance_type]['strategy_subscription_manager'] is None:
            from src.core.strategy_subscription_manager import StrategySubscriptionManager
            
            cache = self.get_or_create_cache(instance_type)
            tick_processor = self.get_or_create_tick_processor(instance_type)
            
            log_info(f"🎯 Creating new StrategySubscriptionManager for {instance_type}")
            self._instances[instance_type]['strategy_subscription_manager'] = StrategySubscriptionManager(
                cache_manager=cache,
                indicator_manager=tick_processor.indicator_manager,
                option_manager=tick_processor.option_manager
            )
        return self._instances[instance_type]['strategy_subscription_manager']
    
    def clear_instance(self, instance_type: str = 'admin_tester'):
        """
        Clear instance (for testing cleanup).
        
        Only allowed for admin_tester, not production.
        
        Args:
            instance_type: Must be 'admin_tester'
        """
        if instance_type == 'production':
            log_warning("⚠️ Cannot clear production instance!")
            return
        
        log_info(f"🧹 Clearing {instance_type} instance")
        self._instances[instance_type] = {
            'cache': None,
            'data_manager': None,
            'tick_processor': None,
            'strategy_subscription_manager': None
        }
    
    def get_instance_info(self, instance_type: str = 'production') -> Dict[str, bool]:
        """
        Get information about instance state.
        
        Args:
            instance_type: 'production' or 'admin_tester'
            
        Returns:
            Dict with instance creation status
        """
        return {
            'cache_created': self._instances[instance_type]['cache'] is not None,
            'data_manager_created': self._instances[instance_type]['data_manager'] is not None,
            'tick_processor_created': self._instances[instance_type]['tick_processor'] is not None,
            'strategy_subscription_manager_created': self._instances[instance_type]['strategy_subscription_manager'] is not None
        }


# Global singleton instance manager
_global_instance_manager = GlobalInstanceManager()


# Convenience functions
def get_instance_manager() -> GlobalInstanceManager:
    """Get global instance manager."""
    return _global_instance_manager
