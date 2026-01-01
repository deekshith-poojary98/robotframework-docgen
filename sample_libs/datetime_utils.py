"""
DateTimeUtils Library

A Robot Framework library for date and time operations.
Provides keywords for date parsing, formatting, calculations, and timezone handling.
"""

from robot.api.deco import keyword
from typing import Optional
from datetime import datetime, timedelta
import calendar


class DateTimeUtils:
    """
    Date and time utilities library for Robot Framework.
    
    This library provides comprehensive date/time operations including:
    - Date parsing and formatting
    - Date arithmetic and calculations
    - Timezone conversions
    - Date comparisons
    - Timestamp operations
    """
    
    ROBOT_LIBRARY_VERSION = "1.3.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the DateTimeUtils library."""
        self._default_format = "%Y-%m-%d %H:%M:%S"
    
    @keyword
    def get_current_datetime(self, format: Optional[str] = None) -> str:
        """
        Get current date and time.
        
        **Arguments:**
        - `format`: Optional datetime format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Current datetime as formatted string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Current DateTime Example
            ${now}    Get Current Datetime
            Should Not Be Empty    ${now}
            ${custom}    Get Current Datetime    format=%Y-%m-%d
            Should Match Regexp    ${custom}    \\d{4}-\\d{2}-\\d{2}
        ```
        """
        fmt = format or self._default_format
        return datetime.now().strftime(fmt)
    
    @keyword
    def parse_datetime(self, date_string: str, format: Optional[str] = None) -> datetime:
        """
        Parse a date string into datetime object.
        
        **Arguments:**
        - `date_string`: Date string to parse
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Datetime object
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Parse DateTime Example
            ${dt}    Parse Datetime    2024-01-15 10:30:00
            Should Not Be None    ${dt}
        ```
        """
        fmt = format or self._default_format
        return datetime.strptime(date_string, fmt)
    
    @keyword
    def format_datetime(self, dt: datetime, format: str = None) -> str:
        """
        Format a datetime object to string.
        
        **Arguments:**
        - `dt`: Datetime object to format
        - `format`: Format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Formatted datetime string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Format DateTime Example
            ${dt}    Parse Datetime    2024-01-15 10:30:00
            ${formatted}    Format Datetime    ${dt}    format=%d/%m/%Y
            Should Be Equal    ${formatted}    15/01/2024
        ```
        """
        fmt = format or self._default_format
        return dt.strftime(fmt)
    
    @keyword
    def add_days(self, date_string: str, days: int, format: Optional[str] = None) -> str:
        """
        Add days to a date.
        
        **Arguments:**
        - `date_string`: Base date string
        - `days`: Number of days to add (can be negative)
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** New date as formatted string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Add Days Example
            ${future}    Add Days    2024-01-15 10:30:00    days=7
            ${past}    Add Days    2024-01-15 10:30:00    days=-3
            Should Not Be Equal    ${future}    ${past}
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        new_dt = dt + timedelta(days=days)
        return new_dt.strftime(fmt)
    
    @keyword
    def add_hours(self, date_string: str, hours: int, format: Optional[str] = None) -> str:
        """
        Add hours to a datetime.
        
        **Arguments:**
        - `date_string`: Base datetime string
        - `hours`: Number of hours to add (can be negative)
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** New datetime as formatted string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Add Hours Example
            ${later}    Add Hours    2024-01-15 10:30:00    hours=5
            Should Not Be Equal    ${later}    2024-01-15 10:30:00
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        new_dt = dt + timedelta(hours=hours)
        return new_dt.strftime(fmt)
    
    @keyword
    def add_minutes(self, date_string: str, minutes: int, format: Optional[str] = None) -> str:
        """
        Add minutes to a datetime.
        
        **Arguments:**
        - `date_string`: Base datetime string
        - `minutes`: Number of minutes to add (can be negative)
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** New datetime as formatted string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Add Minutes Example
            ${later}    Add Minutes    2024-01-15 10:30:00    minutes=30
            Should Not Be Equal    ${later}    2024-01-15 10:30:00
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        new_dt = dt + timedelta(minutes=minutes)
        return new_dt.strftime(fmt)
    
    @keyword
    def get_date_difference(self, date1: str, date2: str, 
                           unit: str = "days", format: Optional[str] = None) -> int:
        """
        Calculate difference between two dates.
        
        **Arguments:**
        - `date1`: First date string
        - `date2`: Second date string
        - `unit`: Unit of difference - "days", "hours", "minutes", "seconds" (default: days)
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Difference as integer
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Date Difference Example
            ${diff}    Get Date Difference    2024-01-15    2024-01-20    unit=days
            Should Be Equal As Integers    ${diff}    ${5}
        ```
        """
        fmt = format or self._default_format
        dt1 = datetime.strptime(date1, fmt)
        dt2 = datetime.strptime(date2, fmt)
        delta = abs(dt2 - dt1)
        
        if unit == "days":
            return delta.days
        elif unit == "hours":
            return int(delta.total_seconds() / 3600)
        elif unit == "minutes":
            return int(delta.total_seconds() / 60)
        elif unit == "seconds":
            return int(delta.total_seconds())
        return delta.days
    
    @keyword
    def is_date_before(self, date1: str, date2: str, format: Optional[str] = None) -> bool:
        """
        Check if first date is before second date.
        
        **Arguments:**
        - `date1`: First date string
        - `date2`: Second date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** True if date1 is before date2, False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Is Date Before Example
            ${result}    Is Date Before    2024-01-15    2024-01-20
            Should Be True    ${result}
        ```
        """
        fmt = format or self._default_format
        dt1 = datetime.strptime(date1, fmt)
        dt2 = datetime.strptime(date2, fmt)
        return dt1 < dt2
    
    @keyword
    def is_date_after(self, date1: str, date2: str, format: Optional[str] = None) -> bool:
        """
        Check if first date is after second date.
        
        **Arguments:**
        - `date1`: First date string
        - `date2`: Second date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** True if date1 is after date2, False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Is Date After Example
            ${result}    Is Date After    2024-01-20    2024-01-15
            Should Be True    ${result}
        ```
        """
        fmt = format or self._default_format
        dt1 = datetime.strptime(date1, fmt)
        dt2 = datetime.strptime(date2, fmt)
        return dt1 > dt2
    
    @keyword
    def get_timestamp(self) -> float:
        """
        Get current Unix timestamp.
        
        **Returns:** Unix timestamp as float
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Timestamp Example
            ${ts}    Get Timestamp
            Should Be True    ${ts} > 0
        ```
        """
        return datetime.now().timestamp()
    
    @keyword
    def timestamp_to_datetime(self, timestamp: float, format: Optional[str] = None) -> str:
        """
        Convert Unix timestamp to datetime string.
        
        **Arguments:**
        - `timestamp`: Unix timestamp
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Datetime string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Timestamp To DateTime Example
            ${ts}    Get Timestamp
            ${dt}    Timestamp To Datetime    ${ts}
            Should Not Be Empty    ${dt}
        ```
        """
        fmt = format or self._default_format
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(fmt)
    
    @keyword
    def datetime_to_timestamp(self, date_string: str, format: Optional[str] = None) -> float:
        """
        Convert datetime string to Unix timestamp.
        
        **Arguments:**
        - `date_string`: Datetime string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Unix timestamp as float
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        DateTime To Timestamp Example
            ${ts}    DateTime To Timestamp    2024-01-15 10:30:00
            Should Be True    ${ts} > 0
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        return dt.timestamp()
    
    @keyword
    def get_day_of_week(self, date_string: str, format: Optional[str] = None) -> str:
        """
        Get day of week name for a date.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Day name (Monday, Tuesday, etc.)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Day Of Week Example
            ${day}    Get Day Of Week    2024-01-15
            Should Be Equal    ${day}    Monday
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        return calendar.day_name[dt.weekday()]
    
    @keyword
    def get_month_name(self, date_string: str, format: Optional[str] = None) -> str:
        """
        Get month name for a date.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Month name (January, February, etc.)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Month Name Example
            ${month}    Get Month Name    2024-01-15
            Should Be Equal    ${month}    January
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        return calendar.month_name[dt.month]
    
    @keyword
    def is_weekend(self, date_string: str, format: Optional[str] = None) -> bool:
        """
        Check if a date falls on weekend.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** True if weekend (Saturday or Sunday), False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Is Weekend Example
            ${result}    Is Weekend    2024-01-13
            Should Be True    ${result}
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        return dt.weekday() >= 5
    
    @keyword
    def is_weekday(self, date_string: str, format: Optional[str] = None) -> bool:
        """
        Check if a date falls on weekday.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** True if weekday (Monday-Friday), False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Is Weekday Example
            ${result}    Is Weekday    2024-01-15
            Should Be True    ${result}
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        return dt.weekday() < 5
    
    @keyword
    def get_start_of_day(self, date_string: str, format: Optional[str] = None) -> str:
        """
        Get start of day (00:00:00) for a date.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Datetime string with time set to 00:00:00
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Start Of Day Example
            ${start}    Get Start Of Day    2024-01-15 14:30:00
            Should End With    ${start}    00:00:00
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_dt.strftime(fmt)
    
    @keyword
    def get_end_of_day(self, date_string: str, format: Optional[str] = None) -> str:
        """
        Get end of day (23:59:59) for a date.
        
        **Arguments:**
        - `date_string`: Date string
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Datetime string with time set to 23:59:59
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get End Of Day Example
            ${end}    Get End Of Day    2024-01-15 14:30:00
            Should End With    ${end}    23:59:59
        ```
        """
        fmt = format or self._default_format
        dt = datetime.strptime(date_string, fmt)
        end_dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return end_dt.strftime(fmt)
    
    @keyword
    def get_age(self, birth_date: str, reference_date: Optional[str] = None,
                format: Optional[str] = None) -> int:
        """
        Calculate age from birth date.
        
        **Arguments:**
        - `birth_date`: Birth date string
        - `reference_date`: Optional reference date (default: current date)
        - `format`: Optional format string (default: YYYY-MM-DD HH:MM:SS)
        
        **Returns:** Age in years
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DateTimeUtils
        
        *** Test Cases ***
        Get Age Example
            ${age}    Get Age    1990-01-15    reference_date=2024-01-15
            Should Be Equal As Integers    ${age}    ${34}
        ```
        """
        fmt = format or self._default_format
        birth_dt = datetime.strptime(birth_date, fmt)
        if reference_date:
            ref_dt = datetime.strptime(reference_date, fmt)
        else:
            ref_dt = datetime.now()
        
        age = ref_dt.year - birth_dt.year
        if (ref_dt.month, ref_dt.day) < (birth_dt.month, birth_dt.day):
            age -= 1
        return age

