"""
Sample Library with Enum Types

This library demonstrates Enum type support in Robot Framework keywords.
It showcases various Enum patterns including:
- Enum with default values
- Enum with different value types (int, str, float)
- Multiple Enum parameters
- Mixed Enum and regular parameters
"""
from robot.api.deco import keyword
from enum import Enum
from typing import Optional, List


class LogLevel(Enum):
    """Logging level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Status(Enum):
    """Status enumeration with integer values."""
    PENDING = 1
    ACTIVE = 2
    COMPLETED = 3
    CANCELLED = 4
    FAILED = 5


class Priority(Enum):
    """Priority enumeration."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class Color(Enum):
    """Color enumeration with string values."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    YELLOW = "yellow"
    PURPLE = "purple"


class TemperatureUnit(Enum):
    """Temperature unit enumeration."""
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"
    KELVIN = "kelvin"


class EnumLibrary:
    """Sample library demonstrating Enum type usage.
    
    This library demonstrates Enum type support in Robot Framework keywords.
    It showcases various Enum patterns including:
    - Enum with default values
    - Enum with different value types (int, str, float)
    - Multiple Enum parameters
    - Mixed Enum and regular parameters
    """
    
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def set_log_level(self, level: LogLevel = LogLevel.INFO):
        """
        Set the logging level.
        
        **Arguments:**
        - `level`: Log level (default: INFO)
        
        **Returns:** None
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            Set Log Level    ${LogLevel.INFO}
            Set Log Level    level=ERROR
        ```
        """
        print(f"Setting log level to: {level.value}")
        return level.value
    
    @keyword("Process With Status")
    def process_with_status(self, 
                           item: str, 
                           status: Status = Status.PENDING,
                           priority: Priority = Priority.MEDIUM) -> dict:
        """
        Process an item with status and priority.
        
        **Arguments:**
        - `item`: Item name or identifier
        - `status`: Processing status (default: PENDING)
        - `priority`: Processing priority (default: MEDIUM)
        
        **Returns:** Dictionary with processing result
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${result}    Process With Status    item-123    status=ACTIVE    priority=HIGH
        ```
        """
        return {
            "item": item,
            "status": status.name,
            "status_value": status.value,
            "priority": priority.name,
            "priority_value": priority.value
        }
    
    @keyword
    def filter_by_status(self, 
                        items: List[str], 
                        status: Status) -> List[str]:
        """
        Filter items by status.
        
        **Arguments:**
        - `items`: List of item identifiers
        - `status`: Status to filter by
        
        **Returns:** Filtered list of items matching the status
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${items}    Create List    item1    item2    item3
            ${filtered}    Filter By Status    ${items}    ${Status.ACTIVE}
        ```
        """
        # Simulate filtering logic
        return [item for item in items if item]
    
    @keyword
    def set_color(self, color: Color, intensity: Optional[int] = None):
        """
        Set a color with optional intensity.
        
        **Arguments:**
        - `color`: Color to set
        - `intensity`: Optional intensity value (0-100)
        
        **Returns:** None
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            Set Color    ${Color.RED}    intensity=75
            Set Color    color=GREEN
        ```
        """
        intensity_str = f" at {intensity}%" if intensity else ""
        print(f"Setting color to {color.value}{intensity_str}")
    
    @keyword("Convert Temperature")
    def convert_temperature(self, 
                           value: float, 
                           from_unit: TemperatureUnit,
                           to_unit: TemperatureUnit = TemperatureUnit.CELSIUS) -> float:
        """
        Convert temperature between units.
        
        **Arguments:**
        - `value`: Temperature value
        - `from_unit`: Source temperature unit
        - `to_unit`: Target temperature unit (default: CELSIUS)
        
        **Returns:** Converted temperature value
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${celsius}    Convert Temperature    32    ${TemperatureUnit.FAHRENHEIT}    ${TemperatureUnit.CELSIUS}
        ```
        """
        # Simplified conversion logic
        if from_unit == to_unit:
            return value
        
        # Convert to Celsius first
        if from_unit == TemperatureUnit.FAHRENHEIT:
            celsius = (value - 32) * 5 / 9
        elif from_unit == TemperatureUnit.KELVIN:
            celsius = value - 273.15
        else:
            celsius = value
        
        # Convert from Celsius to target
        if to_unit == TemperatureUnit.FAHRENHEIT:
            return celsius * 9 / 5 + 32
        elif to_unit == TemperatureUnit.KELVIN:
            return celsius + 273.15
        else:
            return celsius
    
    @keyword
    def get_status_info(self, status: Status) -> dict:
        """
        Get information about a status.
        
        **Arguments:**
        - `status`: Status to get information for
        
        **Returns:** Dictionary with status information
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${info}    Get Status Info    ${Status.ACTIVE}
        ```
        """
        status_descriptions = {
            Status.PENDING: "Item is waiting to be processed",
            Status.ACTIVE: "Item is currently being processed",
            Status.COMPLETED: "Item processing has been completed",
            Status.CANCELLED: "Item processing was cancelled",
            Status.FAILED: "Item processing failed"
        }
        
        return {
            "name": status.name,
            "value": status.value,
            "description": status_descriptions.get(status, "Unknown status")
        }
    
    @keyword
    def create_task(self, 
                   name: str,
                   priority: Priority = Priority.MEDIUM,
                   status: Status = Status.PENDING) -> dict:
        """
        Create a new task with priority and status.
        
        **Arguments:**
        - `name`: Task name
        - `priority`: Task priority (default: MEDIUM)
        - `status`: Initial status (default: PENDING)
        
        **Returns:** Dictionary with task information
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${task}    Create Task    Important Task    priority=HIGH    status=PENDING
        ```
        """
        return {
            "name": name,
            "priority": priority.name,
            "priority_value": priority.value,
            "status": status.name,
            "status_value": status.value
        }
    
    @keyword
    def log_message(self, 
                   message: str,
                   level: LogLevel = LogLevel.INFO,
                   color: Optional[Color] = None):
        """
        Log a message with specified level and optional color.
        
        **Arguments:**
        - `message`: Message to log
        - `level`: Log level (default: INFO)
        - `color`: Optional color for display
        
        **Returns:** None
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            Log Message    This is an error    level=ERROR    color=RED
            Log Message    Information message
        ```
        """
        color_str = f" [{color.value}]" if color else ""
        print(f"[{level.value.upper()}]{color_str} {message}")
    
    @keyword
    def get_all_statuses(self) -> List[str]:
        """
        Get all available status values.
        
        **Returns:** List of all status names
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${statuses}    Get All Statuses
            Should Contain    ${statuses}    ACTIVE
        ```
        """
        return [status.name for status in Status]
    
    @keyword
    def get_all_priorities(self) -> List[str]:
        """
        Get all available priority values.
        
        **Returns:** List of all priority names
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${priorities}    Get All Priorities
            Should Contain    ${priorities}    HIGH
        ```
        """
        return [priority.name for priority in Priority]
    
    @keyword
    def validate_status(self, status: Status) -> bool:
        """
        Validate if a status is valid.
        
        **Arguments:**
        - `status`: Status to validate
        
        **Returns:** True if status is valid, False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${valid}    Validate Status    ${Status.ACTIVE}
            Should Be True    ${valid}
        ```
        """
        return status in Status
    
    @keyword
    def get_status_by_value(self, value: int) -> Optional[Status]:
        """
        Get status enum by its integer value.
        
        **Arguments:**
        - `value`: Status integer value
        
        **Returns:** Status enum if found, None otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    EnumLibrary


        *** Test Cases ***
        Example Test
            ${status}    Get Status By Value    2
            Should Be Equal    ${status.name}    ACTIVE
        ```
        """
        for status in Status:
            if status.value == value:
                return status
        return None
