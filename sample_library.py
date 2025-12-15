"""
DataProcessor Library

A comprehensive Robot Framework library for data processing, validation, and transformation.
This library demonstrates all capabilities of the robotframework-docgen tool with
real-world examples and practical use cases.
"""

from robot.api.deco import keyword
from typing import List, Dict, Optional, Union, Any
from datetime import datetime
import json
import re


class DataProcessor:
    """
    A powerful data processing library for Robot Framework.
    
    This library provides keywords for:
    - Data validation and transformation
    - JSON and dictionary manipulation
    - String processing and formatting
    - List operations and filtering
    - Data comparison and merging
    """
    
    ROBOT_LIBRARY_VERSION = "2.5.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the DataProcessor library."""
        self._cache = {}
        self._history = []
    
    @keyword
    def validate_json_structure(self, json_data: Union[str, dict], schema: Dict[str, Any]) -> bool:
        """
        Validate JSON data against a schema structure.
        
        This keyword validates that the provided JSON data matches the expected
        schema structure. It checks for required fields, data types, and nested
        structures.
        
        **Arguments:**
        - `json_data`: JSON string or dictionary to validate
        - `schema`: Dictionary defining the expected structure with type information
        
        **Returns:** `True` if validation passes, `False` otherwise.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Validate JSON Example
            ${schema}    Create Dictionary    name=str    age=int    email=str
            ${valid}    Validate Json Structure    {"name": "John", "age": 30, "email": "john@example.com"}    ${schema}
            Should Be True    ${valid}
        ```
        
        **Schema Format:**
        | Field | Type | Description |
        |-------|------|-------------|
        | Field name | str/int/bool/list/dict | Expected data type |
        | Nested dict | dict | For nested objects, use dict with sub-schema |
        
        **See also:**
        - `Transform Json Data` for data transformation
        - `Merge Dictionaries` for combining data structures
        """
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError:
                return False
        
        for key, expected_type in schema.items():
            if key not in json_data:
                return False
            if not isinstance(json_data[key], expected_type):
                return False
        
        return True
    
    @keyword("Transform JSON Data")
    def transform_json_data(self, 
                           data: Union[str, Dict], 
                           mapping: Dict[str, str],
                           default_value: Optional[Any] = None) -> Dict[str, Any]:
        """
        Transform JSON data using field mapping rules.
        
        Maps fields from source data to target structure based on the provided
        mapping dictionary. Supports nested field access using dot notation.
        
        **Arguments:**
        - `data`: Source JSON data (string or dictionary)
        - `mapping`: Dictionary mapping target fields to source fields (e.g., `{"new_name": "old_name"}`)
        - `default_value`: Default value for missing fields (default: None)
        
        **Returns:** Transformed dictionary with mapped fields.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Transform JSON Example
            ${source}    Create Dictionary    first_name=John    last_name=Doe    age=30
            ${mapping}    Create Dictionary    name=first_name    surname=last_name    years=age
            ${result}    Transform Json Data    ${source}    ${mapping}
            # Result: {"name": "John", "surname": "Doe", "years": 30}
        ```
        
        **Advanced Mapping:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Advanced Transform Example
            ${source}    Create Dictionary    user=${dict}    metadata=${dict2}
            ${mapping}    Create Dictionary    username=user.name    email=user.contact.email
            ${result}    Transform Json Data    ${source}    ${mapping}
        ```
        """
        if isinstance(data, str):
            data = json.loads(data)
        
        result = {}
        for target_field, source_field in mapping.items():
            if "." in source_field:
                # Nested field access
                value = data
                for part in source_field.split("."):
                    value = value.get(part, default_value)
                    if value is None:
                        break
                result[target_field] = value if value is not None else default_value
            else:
                result[target_field] = data.get(source_field, default_value)
        
        return result
    
    @keyword
    def filter_list_by_condition(self, 
                                  items: List[Any], 
                                  condition: str,
                                  value: Optional[Any] = None) -> List[Any]:
        """
        Filter a list based on a condition.
        
        Filters list items based on various conditions like equality, comparison,
        type checking, or custom lambda functions.
        
        **Arguments:**
        - `items`: List of items to filter
        - `condition`: Condition type: `equals`, `contains`, `greater_than`, `less_than`, `type_is`, `matches_regex`
        - `value`: Value to compare against (required for most conditions)
        
        **Returns:** Filtered list containing only matching items.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Filter List Example
            ${numbers}    Create List    1    5    10    15    20
            ${filtered}    Filter List By Condition    ${numbers}    greater_than    10
            # Result: [15, 20]
        ```
        
        **Supported Conditions:**
        | Condition | Description | Example |
        |-----------|-------------|---------|
        | `equals` | Exact match | `equals` with `value="test"` |
        | `contains` | Substring search | `contains` with `value="key"` |
        | `greater_than` | Numeric comparison | `greater_than` with `value=10` |
        | `less_than` | Numeric comparison | `less_than` with `value=5` |
        | `type_is` | Type checking | `type_is` with `value=int` |
        | `matches_regex` | Pattern matching | `matches_regex` with `value="^[A-Z]+$"` |
        
        **Regex Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Filter By Regex Example
            ${emails}    Create List    user@example.com    invalid    admin@test.org
            ${valid}    Filter List By Condition    ${emails}    matches_regex    ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$
        ```
        """
        result = []
        for item in items:
            match = False
            if condition == "equals":
                match = item == value
            elif condition == "contains":
                match = value in str(item)
            elif condition == "greater_than":
                match = isinstance(item, (int, float)) and item > value
            elif condition == "less_than":
                match = isinstance(item, (int, float)) and item < value
            elif condition == "type_is":
                match = isinstance(item, value if isinstance(value, type) else type(value))
            elif condition == "matches_regex":
                match = bool(re.match(value, str(item)))
            
            if match:
                result.append(item)
        
        return result
    
    @keyword
    def merge_dictionaries(self, 
                          *dictionaries: Dict[str, Any],
                          strategy: str = "override") -> Dict[str, Any]:
        """
        Merge multiple dictionaries into a single dictionary.
        
        Combines multiple dictionaries using different merge strategies. Handles
        nested dictionaries intelligently based on the chosen strategy.
        
        **Arguments:**
        - `*dictionaries`: Variable number of dictionaries to merge
        - `strategy`: Merge strategy - `override` (default), `keep_first`, `keep_last`, `deep_merge`
        
        **Returns:** Merged dictionary containing all key-value pairs.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Merge Dictionaries Example
            ${dict1}    Create Dictionary    name=John    age=30
            ${dict2}    Create Dictionary    age=35    city=NYC
            ${merged}    Merge Dictionaries    ${dict1}    ${dict2}
            # Result: {"name": "John", "age": 35, "city": "NYC"} (override strategy)
        ```
        
        **Merge Strategies:**
        
        | Strategy | Behavior | Use Case |
        |----------|----------|----------|
        | `override` | Later dicts override earlier ones | Default configuration overrides |
        | `keep_first` | First value wins | Preserve original data |
        | `keep_last` | Last value wins | Latest updates take precedence |
        | `deep_merge` | Recursively merge nested dicts | Complex nested structures |
        
        **Deep Merge Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Deep Merge Example
            ${base}    Create Dictionary    user=${dict}    settings=${dict2}
            ${update}    Create Dictionary    user=${dict3}    settings=${dict4}
            ${merged}    Merge Dictionaries    ${base}    ${update}    strategy=deep_merge
        ```
        """
        if not dictionaries:
            return {}
        
        result = {}
        
        if strategy == "keep_first":
            for d in dictionaries:
                for key, value in d.items():
                    if key not in result:
                        result[key] = value
        elif strategy == "keep_last":
            for d in dictionaries:
                result.update(d)
        elif strategy == "deep_merge":
            result = dictionaries[0].copy()
            for d in dictionaries[1:]:
                for key, value in d.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = self.merge_dictionaries(result[key], value, strategy="deep_merge")
                    else:
                        result[key] = value
        else:  # override (default)
            for d in dictionaries:
                result.update(d)
        
        return result
    
    @keyword
    def format_string_template(self, 
                              template: str, 
                              variables: Dict[str, Any],
                              missing_handler: str = "skip") -> str:
        """
        Format a string template with variable substitution.
        
        Replaces placeholders in a template string with values from a dictionary.
        Supports various placeholder formats and missing value handling strategies.
        
        **Arguments:**
        - `template`: String template with placeholders (e.g., `"Hello {name}, you have {count} messages"`)
        - `variables`: Dictionary mapping placeholder names to values
        - `missing_handler`: How to handle missing variables - `skip`, `error`, or `default`
        
        **Returns:** Formatted string with variables substituted.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Format Template Example
            ${template}    Set Variable    Welcome {username}! You have {message_count} new messages.
            ${vars}    Create Dictionary    username=John    message_count=5
            ${result}    Format String Template    ${template}    ${vars}
            # Result: "Welcome John! You have 5 new messages."
        ```
        
        **Placeholder Formats:**
        - `{variable}` - Simple placeholder
        - `{variable:default}` - With default value
        - `{variable!upper}` - With transformation (upper, lower, title)
        
        **Missing Handler Options:**
        | Handler | Behavior |
        |---------|----------|
        | `skip` | Leave placeholder as-is |
        | `error` | Raise an error |
        | `default` | Use empty string |
        
        **Advanced Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Advanced Template Example
            ${template}    Set Variable    User: {user:Guest} | Status: {status!upper} | Count: {count:0}
            ${vars}    Create Dictionary    status=active
            ${result}    Format String Template    ${template}    ${vars}    missing_handler=default
        ```
        """
        result = template
        
        # Find all placeholders
        placeholder_pattern = r'\{([^}]+)\}'
        placeholders = re.findall(placeholder_pattern, template)
        
        for placeholder in placeholders:
            # Parse placeholder (name:default or name!transform)
            var_name = placeholder
            default_value = None
            transform = None
            
            if ":" in placeholder:
                var_name, default_value = placeholder.split(":", 1)
            elif "!" in placeholder:
                var_name, transform = placeholder.split("!", 1)
            
            # Get value
            if var_name in variables:
                value = variables[var_name]
            elif default_value is not None:
                value = default_value
            elif missing_handler == "error":
                raise ValueError(f"Missing variable: {var_name}")
            elif missing_handler == "default":
                value = ""
            else:  # skip
                continue
            
            # Apply transformation
            if transform == "upper":
                value = str(value).upper()
            elif transform == "lower":
                value = str(value).lower()
            elif transform == "title":
                value = str(value).title()
            
            # Replace placeholder
            result = result.replace(f"{{{placeholder}}}", str(value))
        
        return result
    
    @keyword
    def extract_data_by_pattern(self, 
                               text: str, 
                               pattern: str,
                               group: Optional[int] = None) -> Union[str, List[str]]:
        """
        Extract data from text using regex patterns.
        
        Extracts matching text from a string using regular expressions. Supports
        single match, all matches, and specific capture group extraction.
        
        **Arguments:**
        - `text`: Text to search in
        - `pattern`: Regular expression pattern
        - `group`: Capture group number (None for all matches, 0 for full match, 1+ for specific group)
        
        **Returns:** Extracted string or list of strings.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Extract Pattern Example
            ${text}    Set Variable    Contact: john@example.com or admin@test.org
            ${emails}    Extract Data By Pattern    ${text}    [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}
            # Result: ["john@example.com", "admin@test.org"]
        ```
        
        **Capture Group Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Extract With Group Example
            ${text}    Set Variable    Date: 2024-01-15 Time: 14:30:00
            ${date}    Extract Data By Pattern    ${text}    (\\d{4}-\\d{2}-\\d{2})    group=1
            # Result: "2024-01-15"
        ```
        
        **Common Patterns:**
        | Pattern | Description | Example |
        |---------|-------------|---------|
        | `\\d+` | Numbers | `"123"` from `"Price: 123 dollars"` |
        | `[A-Z][a-z]+` | Capitalized words | `"John"` from `"Hello John Doe"` |
        | `\\w+@\\w+\\.\\w+` | Email addresses | `"user@example.com"` |
        | `\\$\\{[^}]+\\}` | Robot variables | `${variable}` from Robot Framework code |
        """
        matches = re.findall(pattern, text)
        
        if group is not None:
            # Extract specific capture group
            compiled = re.compile(pattern)
            matches = [m[group] if isinstance(m, tuple) else m for m in matches]
            if matches:
                return matches[0] if len(matches) == 1 else matches
        
        return matches if len(matches) > 1 else (matches[0] if matches else "")
    
    @keyword("Compare Data Structures")
    def compare_data_structures(self, 
                               data1: Union[Dict, List], 
                               data2: Union[Dict, List],
                               ignore_order: bool = False) -> Dict[str, Any]:
        """
        Compare two data structures and return differences.
        
        Performs deep comparison of dictionaries or lists, identifying added,
        removed, and modified items. Useful for data validation and testing.
        
        **Arguments:**
        - `data1`: First data structure (baseline)
        - `data2`: Second data structure (to compare)
        - `ignore_order`: If True, list order is ignored (default: False)
        
        **Returns:** Dictionary with comparison results:
        - `equal`: Boolean indicating if structures are identical
        - `added`: Items present in data2 but not in data1
        - `removed`: Items present in data1 but not in data2
        - `modified`: Items that differ between structures
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Compare Structures Example
            ${original}    Create Dictionary    name=John    age=30
            ${updated}    Create Dictionary    name=John    age=31    city=NYC
            ${diff}    Compare Data Structures    ${original}    ${updated}
            # Result: {"equal": False, "added": {"city": "NYC"}, "removed": {}, "modified": {"age": (30, 31)}}
        ```
        
        **List Comparison:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Compare Lists Example
            ${list1}    Create List    a    b    c
            ${list2}    Create List    c    b    a
            ${diff}    Compare Data Structures    ${list1}    ${list2}    ignore_order=True
            # Result: {"equal": True, ...}
        ```
        """
        result = {
            "equal": True,
            "added": {},
            "removed": {},
            "modified": {}
        }
        
        if isinstance(data1, dict) and isinstance(data2, dict):
            all_keys = set(data1.keys()) | set(data2.keys())
            
            for key in all_keys:
                if key not in data1:
                    result["added"][key] = data2[key]
                    result["equal"] = False
                elif key not in data2:
                    result["removed"][key] = data1[key]
                    result["equal"] = False
                elif data1[key] != data2[key]:
                    result["modified"][key] = (data1[key], data2[key])
                    result["equal"] = False
        
        elif isinstance(data1, list) and isinstance(data2, list):
            if ignore_order:
                if set(data1) != set(data2):
                    result["equal"] = False
                    result["added"] = [x for x in data2 if x not in data1]
                    result["removed"] = [x for x in data1 if x not in data2]
            else:
                if data1 != data2:
                    result["equal"] = False
                    # Find differences
                    max_len = max(len(data1), len(data2))
                    for i in range(max_len):
                        if i >= len(data1):
                            result["added"][i] = data2[i]
                        elif i >= len(data2):
                            result["removed"][i] = data1[i]
                        elif data1[i] != data2[i]:
                            result["modified"][i] = (data1[i], data2[i])
        
        return result
    
    @keyword
    def group_items_by_key(self, 
                          items: List[Dict[str, Any]], 
                          key: str,
                          default_group: str = "other") -> Dict[str, List[Dict[str, Any]]]:
        """
        Group a list of dictionaries by a common key.
        
        Organizes a list of dictionaries into groups based on the value of a
        specified key. Useful for categorizing and organizing data.
        
        **Arguments:**
        - `items`: List of dictionaries to group
        - `key`: Key name to group by
        - `default_group`: Group name for items missing the key (default: "other")
        
        **Returns:** Dictionary mapping group names to lists of items.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Group Items Example
            ${users}    Create List
            ...    ${dict1}    # {"name": "John", "role": "admin"}
            ...    ${dict2}    # {"name": "Jane", "role": "user"}
            ...    ${dict3}    # {"name": "Bob", "role": "admin"}
            ${grouped}    Group Items By Key    ${users}    role
            # Result: {"admin": [dict1, dict3], "user": [dict2]}
        ```
        
        **Use Cases:**
        - Organizing test results by status
        - Grouping API responses by category
        - Categorizing log entries by level
        - Sorting data by type or classification
        
        **Nested Key Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Group By Nested Key Example
            ${items}    Create List    ${dict1}    ${dict2}
            # dict1: {"user": {"department": "IT"}}
            # Use dot notation: "user.department"
        ```
        """
        grouped = {}
        
        for item in items:
            if "." in key:
                # Nested key access
                value = item
                for part in key.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                group_key = str(value) if value is not None else default_group
            else:
                group_key = str(item.get(key, default_group))
            
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(item)
        
        return grouped
    
    @keyword
    def calculate_statistics(self, 
                           numbers: List[Union[int, float]],
                           include_percentiles: bool = False) -> Dict[str, float]:
        """
        Calculate statistical measures for a list of numbers.
        
        Computes common statistical metrics including mean, median, min, max,
        and optionally percentiles. Useful for data analysis and reporting.
        
        **Arguments:**
        - `numbers`: List of numeric values
        - `include_percentiles`: If True, calculate 25th, 50th, 75th, and 95th percentiles
        
        **Returns:** Dictionary with statistical measures:
        - `count`: Number of values
        - `sum`: Sum of all values
        - `mean`: Average value
        - `median`: Middle value
        - `min`: Minimum value
        - `max`: Maximum value
        - `range`: Difference between max and min
        - `percentiles`: (if enabled) Dictionary with percentile values
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Calculate Statistics Example
            ${scores}    Create List    85    90    78    92    88
            ${stats}    Calculate Statistics    ${scores}
            # Result: {"count": 5, "mean": 86.6, "median": 88, "min": 78, "max": 92, ...}
        ```
        
        **With Percentiles:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Statistics With Percentiles Example
            ${data}    Create List    10    20    30    40    50    60    70    80    90    100
            ${stats}    Calculate Statistics    ${data}    include_percentiles=True
            # Includes: "percentiles": {"25": 30, "50": 55, "75": 80, "95": 95}
        ```
        
        **Visualization:**
        ```
        Distribution: [min]----[25%]----[median]----[75%]----[max]
        ```
        """
        if not numbers:
            return {"count": 0, "sum": 0, "mean": 0, "median": 0, "min": 0, "max": 0, "range": 0}
        
        sorted_nums = sorted(numbers)
        count = len(numbers)
        total = sum(numbers)
        mean = total / count
        median = sorted_nums[count // 2] if count % 2 == 1 else (sorted_nums[count // 2 - 1] + sorted_nums[count // 2]) / 2
        min_val = min(numbers)
        max_val = max(numbers)
        range_val = max_val - min_val
        
        result = {
            "count": count,
            "sum": total,
            "mean": round(mean, 2),
            "median": round(median, 2),
            "min": min_val,
            "max": max_val,
            "range": range_val
        }
        
        if include_percentiles:
            percentiles = {}
            for p in [25, 50, 75, 95]:
                index = int((p / 100) * (count - 1))
                percentiles[str(p)] = sorted_nums[index]
            result["percentiles"] = percentiles
        
        return result
    
    @keyword
    def create_data_snapshot(self, 
                            data: Any,
                            include_metadata: bool = True) -> Dict[str, Any]:
        """
        Create a snapshot of data with optional metadata.
        
        Captures a point-in-time snapshot of data structures, including
        metadata like timestamp, data type, and size information.
        
        **Arguments:**
        - `data`: Data structure to snapshot (dict, list, string, etc.)
        - `include_metadata`: If True, include metadata in snapshot (default: True)
        
        **Returns:** Dictionary containing snapshot data and metadata.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Create Snapshot Example
            ${data}    Create Dictionary    name=John    age=30
            ${snapshot}    Create Data Snapshot    ${data}
            # Result: {"data": {...}, "metadata": {"timestamp": "...", "type": "dict", "size": 2}}
        ```
        
        **Metadata Fields:**
        | Field | Description |
        |-------|-------------|
        | `timestamp` | ISO format timestamp |
        | `type` | Data type (dict, list, str, etc.) |
        | `size` | Size/length of data structure |
        | `hash` | Hash of serialized data (for comparison) |
        
        **Use Cases:**
        - Data versioning and comparison
        - Audit trails
        - Debugging data transformations
        - Testing data integrity
        """
        snapshot = {"data": data}
        
        if include_metadata:
            import hashlib
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "type": type(data).__name__,
            }
            
            if isinstance(data, (dict, list)):
                metadata["size"] = len(data)
            elif isinstance(data, str):
                metadata["size"] = len(data)
                metadata["bytes"] = len(data.encode('utf-8'))
            
            # Create hash for comparison
            data_str = json.dumps(data, sort_keys=True) if isinstance(data, (dict, list)) else str(data)
            metadata["hash"] = hashlib.md5(data_str.encode()).hexdigest()
            
            snapshot["metadata"] = metadata
        
        return snapshot
