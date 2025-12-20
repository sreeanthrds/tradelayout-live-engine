"""
Market Calendar - NSE Trading Days and Holidays
"""
from datetime import date, datetime
from typing import List, Set

# NSE Holidays 2024
NSE_HOLIDAYS_2024 = {
    date(2024, 1, 26),  # Republic Day
    date(2024, 3, 8),   # Mahashivratri
    date(2024, 3, 25),  # Holi
    date(2024, 3, 29),  # Good Friday
    date(2024, 4, 11),  # Id-Ul-Fitr
    date(2024, 4, 17),  # Ram Navami
    date(2024, 4, 21),  # Mahavir Jayanti
    date(2024, 5, 1),   # Maharashtra Day
    date(2024, 5, 23),  # Buddha Pournima
    date(2024, 6, 17),  # Bakri Id
    date(2024, 7, 17),  # Muharram
    date(2024, 8, 15),  # Independence Day
    date(2024, 9, 16),  # Milad-un-Nabi
    date(2024, 10, 2),  # Gandhi Jayanti / Mahatma Gandhi Jayanti
    date(2024, 10, 12), # Dussehra
    date(2024, 11, 1),  # Diwali (Laxmi Pujan)
    date(2024, 11, 15), # Guru Nanak Jayanti
    date(2024, 12, 25), # Christmas
}

# NSE Holidays 2025 (for future)
NSE_HOLIDAYS_2025 = {
    date(2025, 1, 26),  # Republic Day
    date(2025, 3, 14),  # Holi
    date(2025, 3, 31),  # Id-Ul-Fitr (Ramadan Eid)
    date(2025, 4, 10),  # Mahavir Jayanti
    date(2025, 4, 14),  # Dr. Ambedkar Jayanti
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Maharashtra Day
    date(2025, 6, 7),   # Bakri Id
    date(2025, 8, 15),  # Independence Day
    date(2025, 8, 27),  # Ganesh Chaturthi
    date(2025, 10, 2),  # Gandhi Jayanti
    date(2025, 10, 21), # Dussehra
    date(2025, 11, 5),  # Diwali (Laxmi Pujan)
    date(2025, 11, 24), # Guru Nanak Jayanti
    date(2025, 12, 25), # Christmas
}

ALL_HOLIDAYS = NSE_HOLIDAYS_2024 | NSE_HOLIDAYS_2025


def is_trading_day(check_date: date) -> bool:
    """
    Check if a given date is a trading day (not weekend or holiday).
    
    Args:
        check_date: Date to check
    
    Returns:
        True if trading day, False if weekend or holiday
    """
    # Check if weekend (Saturday=5, Sunday=6)
    if check_date.weekday() >= 5:
        return False
    
    # Check if holiday
    if check_date in ALL_HOLIDAYS:
        return False
    
    return True


def is_weekend(check_date: date) -> bool:
    """Check if date is weekend."""
    return check_date.weekday() >= 5


def is_holiday(check_date: date) -> bool:
    """Check if date is a market holiday."""
    return check_date in ALL_HOLIDAYS


def get_holiday_name(check_date: date) -> str:
    """Get holiday name if the date is a holiday."""
    holiday_names = {
        date(2024, 1, 26): "Republic Day",
        date(2024, 3, 8): "Mahashivratri",
        date(2024, 3, 25): "Holi",
        date(2024, 3, 29): "Good Friday",
        date(2024, 4, 11): "Id-Ul-Fitr",
        date(2024, 4, 17): "Ram Navami",
        date(2024, 4, 21): "Mahavir Jayanti",
        date(2024, 5, 1): "Maharashtra Day",
        date(2024, 5, 23): "Buddha Pournima",
        date(2024, 6, 17): "Bakri Id",
        date(2024, 7, 17): "Muharram",
        date(2024, 8, 15): "Independence Day",
        date(2024, 9, 16): "Milad-un-Nabi",
        date(2024, 10, 2): "Gandhi Jayanti",
        date(2024, 10, 12): "Dussehra",
        date(2024, 11, 1): "Diwali",
        date(2024, 11, 15): "Guru Nanak Jayanti",
        date(2024, 12, 25): "Christmas",
        # 2025
        date(2025, 1, 26): "Republic Day",
        date(2025, 3, 14): "Holi",
        date(2025, 3, 31): "Id-Ul-Fitr",
        date(2025, 4, 10): "Mahavir Jayanti",
        date(2025, 4, 14): "Dr. Ambedkar Jayanti",
        date(2025, 4, 18): "Good Friday",
        date(2025, 5, 1): "Maharashtra Day",
        date(2025, 6, 7): "Bakri Id",
        date(2025, 8, 15): "Independence Day",
        date(2025, 8, 27): "Ganesh Chaturthi",
        date(2025, 10, 2): "Gandhi Jayanti",
        date(2025, 10, 21): "Dussehra",
        date(2025, 11, 5): "Diwali",
        date(2025, 11, 24): "Guru Nanak Jayanti",
        date(2025, 12, 25): "Christmas",
    }
    return holiday_names.get(check_date, "Unknown Holiday")


def get_trading_days_in_month(year: int, month: int) -> List[date]:
    """
    Get all trading days in a given month.
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
    
    Returns:
        List of trading days (excludes weekends and holidays)
    """
    from datetime import timedelta
    
    # Get first and last day of month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    trading_days = []
    current_date = start_date
    
    while current_date < end_date:
        if is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)
    
    return trading_days


def validate_backtest_date(check_date: date) -> tuple[bool, str]:
    """
    Validate if a date is suitable for backtesting.
    
    Args:
        check_date: Date to validate
    
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    if is_weekend(check_date):
        day_name = check_date.strftime('%A')
        return False, f"Weekend ({day_name}) - Market closed"
    
    if is_holiday(check_date):
        holiday_name = get_holiday_name(check_date)
        return False, f"Market Holiday ({holiday_name})"
    
    return True, ""
