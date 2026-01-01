"""
StringUtils Library

A comprehensive Robot Framework library for string manipulation, validation, and formatting.
Provides powerful keywords for text processing, pattern matching, and data transformation.
"""

from robot.api.deco import keyword
from typing import List, Optional, Dict, Any
import re
import hashlib
import base64


class StringUtils:
    """
    String utilities library for Robot Framework.
    
    This library provides comprehensive string operations including:
    - String manipulation and transformation
    - Pattern matching and validation
    - Encoding and hashing
    - Text formatting and templating
    - Data extraction and parsing
    """
    
    ROBOT_LIBRARY_VERSION = "2.1.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the StringUtils library."""
        self._cache = {}
    
    @keyword
    def capitalize_words(self, text: str) -> str:
        """
        Capitalize the first letter of each word in a string.
        
        **Arguments:**
        - `text`: Input string to capitalize
        
        **Returns:** String with each word capitalized
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Capitalize Text Example
            ${result}    Capitalize Words    hello world
            Should Be Equal    ${result}    Hello World
        ```
        """
        return text.title()
    
    @keyword
    def remove_whitespace(self, text: str, mode: str = "all") -> str:
        """
        Remove whitespace from a string.
        
        **Arguments:**
        - `text`: Input string
        - `mode`: Removal mode - "all" (remove all), "leading" (remove leading), 
                  "trailing" (remove trailing), "both" (remove both ends)
        
        **Returns:** String with whitespace removed
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Remove Whitespace Example
            ${result}    Remove Whitespace    "  hello world  "    mode=both
            Should Be Equal    ${result}    hello world
        ```
        """
        if mode == "all":
            return re.sub(r'\s+', '', text)
        elif mode == "leading":
            return text.lstrip()
        elif mode == "trailing":
            return text.rstrip()
        elif mode == "both":
            return text.strip()
        return text
    
    @keyword
    def extract_numbers(self, text: str) -> List[int]:
        """
        Extract all numbers from a string.
        
        **Arguments:**
        - `text`: Input string containing numbers
        
        **Returns:** List of extracted integers
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Extract Numbers Example
            ${numbers}    Extract Numbers    Price: $99.99, Quantity: 5
            Should Contain    ${numbers}    ${99}
            Should Contain    ${numbers}    ${5}
        ```
        """
        return [int(match) for match in re.findall(r'\d+', text)]
    
    @keyword
    def extract_emails(self, text: str) -> List[str]:
        """
        Extract all email addresses from a string.
        
        **Arguments:**
        - `text`: Input string containing email addresses
        
        **Returns:** List of extracted email addresses
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Extract Emails Example
            ${emails}    Extract Emails    Contact: john@example.com or jane@test.org
            Should Contain    ${emails}    john@example.com
            Should Contain    ${emails}    jane@test.org
        ```
        """
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, text)
    
    @keyword
    def validate_url(self, url: str) -> bool:
        """
        Validate if a string is a valid URL.
        
        **Arguments:**
        - `url`: URL string to validate
        
        **Returns:** True if valid URL, False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Validate URL Example
            ${valid}    Validate Url    https://example.com
            Should Be True    ${valid}
        ```
        """
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
        return bool(re.match(pattern, url))
    
    @keyword
    def mask_sensitive_data(self, text: str, visible_chars: int = 4) -> str:
        """
        Mask sensitive data, showing only first few characters.
        
        **Arguments:**
        - `text`: Text to mask
        - `visible_chars`: Number of characters to keep visible (default: 4)
        
        **Returns:** Masked string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Mask Sensitive Data Example
            ${masked}    Mask Sensitive Data    secret12345    visible_chars=3
            Should Start With    ${masked}    sec
            Should Contain    ${masked}    *
        ```
        """
        if len(text) <= visible_chars:
            return '*' * len(text)
        return text[:visible_chars] + '*' * (len(text) - visible_chars)
    
    @keyword
    def hash_string(self, text: str, algorithm: str = "sha256") -> str:
        """
        Generate hash of a string.
        
        **Arguments:**
        - `text`: Text to hash
        - `algorithm`: Hash algorithm - "md5", "sha1", "sha256" (default)
        
        **Returns:** Hexadecimal hash string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Hash String Example
            ${hash}    Hash String    password123    algorithm=sha256
            Should Not Be Empty    ${hash}
            Length Should Be    ${hash}    ${64}
        ```
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode('utf-8'))
        return hash_obj.hexdigest()
    
    @keyword
    def encode_base64(self, text: str) -> str:
        """
        Encode string to Base64.
        
        **Arguments:**
        - `text`: Text to encode
        
        **Returns:** Base64 encoded string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Encode Base64 Example
            ${encoded}    Encode Base64    Hello World
            Should Not Be Empty    ${encoded}
        ```
        """
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
    
    @keyword
    def decode_base64(self, encoded_text: str) -> str:
        """
        Decode Base64 string.
        
        **Arguments:**
        - `encoded_text`: Base64 encoded string
        
        **Returns:** Decoded string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Decode Base64 Example
            ${decoded}    Decode Base64    SGVsbG8gV29ybGQ=
            Should Be Equal    ${decoded}    Hello World
        ```
        """
        return base64.b64decode(encoded_text).decode('utf-8')
    
    @keyword
    def replace_pattern(self, text: str, pattern: str, replacement: str, 
                       case_sensitive: bool = True) -> str:
        """
        Replace text matching a regex pattern.
        
        **Arguments:**
        - `text`: Input text
        - `pattern`: Regular expression pattern
        - `replacement`: Replacement string
        - `case_sensitive`: Whether pattern matching is case sensitive (default: True)
        
        **Returns:** Text with replacements applied
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Replace Pattern Example
            ${result}    Replace Pattern    Hello 123 World    \\d+    NUMBER
            Should Be Equal    ${result}    Hello NUMBER World
        ```
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        return re.sub(pattern, replacement, text, flags=flags)
    
    @keyword
    def split_string(self, text: str, separator: str = None, max_split: int = -1) -> List[str]:
        """
        Split string into a list.
        
        **Arguments:**
        - `text`: Text to split
        - `separator`: Separator string (default: whitespace)
        - `max_split`: Maximum number of splits (default: -1 for unlimited)
        
        **Returns:** List of strings
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Split String Example
            ${parts}    Split String    apple,banana,cherry    separator=,
            Should Contain    ${parts}    apple
            Should Contain    ${parts}    banana
            Should Contain    ${parts}    cherry
        ```
        """
        if separator is None:
            return text.split(maxsplit=max_split if max_split >= 0 else None)
        return text.split(separator, maxsplit=max_split if max_split >= 0 else None)
    
    @keyword
    def join_strings(self, strings: List[str], separator: str = " ") -> str:
        """
        Join list of strings with a separator.
        
        **Arguments:**
        - `strings`: List of strings to join
        - `separator`: Separator string (default: space)
        
        **Returns:** Joined string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Join Strings Example
            @{items}    Create List    apple    banana    cherry
            ${result}    Join Strings    ${items}    separator=,
            Should Be Equal    ${result}    apple,banana,cherry
        ```
        """
        return separator.join(strings)
    
    @keyword
    def format_template(self, template: str, **kwargs: Any) -> str:
        """
        Format a string template with variables.
        
        **Arguments:**
        - `template`: Template string with {variable} placeholders
        - `**kwargs`: Variable name-value pairs
        
        **Returns:** Formatted string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Format Template Example
            ${result}    Format Template    Hello {name}, you are {age} years old
            ...    name=John    age=30
            Should Be Equal    ${result}    Hello John, you are 30 years old
        ```
        """
        return template.format(**kwargs)
    
    @keyword
    def count_occurrences(self, text: str, substring: str, case_sensitive: bool = True) -> int:
        """
        Count occurrences of a substring in text.
        
        **Arguments:**
        - `text`: Text to search in
        - `substring`: Substring to count
        - `case_sensitive`: Whether search is case sensitive (default: True)
        
        **Returns:** Number of occurrences
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Count Occurrences Example
            ${count}    Count Occurrences    hello hello world    hello
            Should Be Equal As Integers    ${count}    ${2}
        ```
        """
        if not case_sensitive:
            text = text.lower()
            substring = substring.lower()
        return text.count(substring)
    
    @keyword
    def truncate_string(self, text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate string to maximum length.
        
        **Arguments:**
        - `text`: Text to truncate
        - `max_length`: Maximum length
        - `suffix`: Suffix to append if truncated (default: "...")
        
        **Returns:** Truncated string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Truncate String Example
            ${result}    Truncate String    This is a very long text    10
            Should Be Equal    ${result}    This is a...
        ```
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @keyword
    def pad_string(self, text: str, width: int, padding: str = " ", 
                  align: str = "left") -> str:
        """
        Pad string to specified width.
        
        **Arguments:**
        - `text`: Text to pad
        - `width`: Target width
        - `padding`: Padding character (default: space)
        - `align`: Alignment - "left", "right", or "center" (default: left)
        
        **Returns:** Padded string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Pad String Example
            ${result}    Pad String    hello    10    align=right
            Should Be Equal    ${result}    ${SPACE * 5}hello
        ```
        """
        if align == "left":
            return text.ljust(width, padding)
        elif align == "right":
            return text.rjust(width, padding)
        elif align == "center":
            return text.center(width, padding)
        return text
    
    @keyword
    def reverse_string(self, text: str) -> str:
        """
        Reverse a string.
        
        **Arguments:**
        - `text`: Text to reverse
        
        **Returns:** Reversed string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Reverse String Example
            ${result}    Reverse String    hello
            Should Be Equal    ${result}    olleh
        ```
        """
        return text[::-1]
    
    @keyword
    def remove_duplicates(self, text: str, separator: str = " ") -> str:
        """
        Remove duplicate words/parts from a string.
        
        **Arguments:**
        - `text`: Text to process
        - `separator`: Separator to split by (default: space)
        
        **Returns:** String with duplicates removed
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Remove Duplicates Example
            ${result}    Remove Duplicates    apple banana apple cherry
            Should Be Equal    ${result}    apple banana cherry
        ```
        """
        parts = text.split(separator)
        seen = set()
        unique_parts = []
        for part in parts:
            if part not in seen:
                seen.add(part)
                unique_parts.append(part)
        return separator.join(unique_parts)
    
    @keyword
    def validate_phone_number(self, phone: str, country: str = "US") -> bool:
        """
        Validate phone number format.
        
        **Arguments:**
        - `phone`: Phone number string
        - `country`: Country code for validation (default: US)
        
        **Returns:** True if valid format, False otherwise
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Validate Phone Number Example
            ${valid}    Validate Phone Number    +1-555-123-4567
            Should Be True    ${valid}
        ```
        """
        # Simplified validation - remove non-digits and check length
        digits = re.sub(r'\D', '', phone)
        if country == "US":
            return len(digits) == 10 or (len(digits) == 11 and digits[0] == '1')
        return len(digits) >= 10
    
    @keyword
    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse JSON object from text.
        
        **Arguments:**
        - `text`: Text containing JSON
        
        **Returns:** Parsed JSON dictionary or None if not found
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Extract JSON From Text Example
            ${json}    Extract Json From Text    Data: {"name": "John", "age": 30}
            Should Be Equal    ${json}[name]    John
            Should Be Equal As Integers    ${json}[age]    ${30}
        ```
        """
        import json
        # Try to find JSON object in text
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
    
    @keyword
    def generate_random_string(self, length: int = 10, 
                              include_uppercase: bool = True,
                              include_lowercase: bool = True,
                              include_digits: bool = True,
                              include_special: bool = False) -> str:
        """
        Generate a random string.
        
        **Arguments:**
        - `length`: Length of string (default: 10)
        - `include_uppercase`: Include uppercase letters (default: True)
        - `include_lowercase`: Include lowercase letters (default: True)
        - `include_digits`: Include digits (default: True)
        - `include_special`: Include special characters (default: False)
        
        **Returns:** Random string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    StringUtils
        
        *** Test Cases ***
        Generate Random String Example
            ${random}    Generate Random String    length=16    include_special=True
            Length Should Be    ${random}    ${16}
            Should Match Regexp    ${random}    .+
        ```
        """
        import random
        import string
        
        chars = ""
        if include_uppercase:
            chars += string.ascii_uppercase
        if include_lowercase:
            chars += string.ascii_lowercase
        if include_digits:
            chars += string.digits
        if include_special:
            chars += "!@#$%^&*"
        
        if not chars:
            chars = string.ascii_letters + string.digits
        
        return ''.join(random.choice(chars) for _ in range(length))
