"""
HTTPClient Library

A Robot Framework library for HTTP operations and web API interactions.
Provides keywords for making HTTP requests, handling responses, and API testing.
"""

from robot.api.deco import keyword
from typing import Dict, Optional, Any
import json


class HTTPClient:
    """
    HTTP client library for Robot Framework.
    
    This library provides keywords for:
    - Making HTTP requests (GET, POST, PUT, DELETE)
    - Handling HTTP responses
    - Working with JSON APIs
    - Managing headers and authentication
    - Response validation
    """
    
    ROBOT_LIBRARY_VERSION = "2.0.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the HTTPClient library."""
        self._session_headers = {}
        self._last_response = None
    
    @keyword
    def http_get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform HTTP GET request.
        
        **Arguments:**
        - `url`: Target URL
        - `headers`: Optional dictionary of HTTP headers
        
        **Returns:** Response dictionary with status, headers, and body
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        HTTP GET Example
            ${response}    Http Get    https://api.example.com/users
            Should Be Equal As Integers    ${response}[status]    200
        ```
        """
        # Simulated implementation for demo
        return {
            "status": 200,
            "headers": headers or {},
            "body": {"message": "GET request successful", "url": url}
        }
    
    @keyword
    def http_post(self, url: str, data: Optional[Dict[str, Any]] = None, 
                  headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform HTTP POST request.
        
        **Arguments:**
        - `url`: Target URL
        - `data`: Request body data (dictionary)
        - `headers`: Optional dictionary of HTTP headers
        
        **Returns:** Response dictionary with status, headers, and body
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        HTTP POST Example
            ${data}    Create Dictionary    name=John    email=john@example.com
            ${response}    Http Post    https://api.example.com/users    ${data}
            Response Should Be Success    ${response}
        ```
        """
        # Simulated implementation for demo
        return {
            "status": 201,
            "headers": headers or {},
            "body": {"message": "POST request successful", "data": data or {}}
        }
    
    @keyword
    def http_put(self, url: str, data: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform HTTP PUT request.
        
        **Arguments:**
        - `url`: Target URL
        - `data`: Request body data (dictionary)
        - `headers`: Optional dictionary of HTTP headers
        
        **Returns:** Response dictionary with status, headers, and body
        """
        # Simulated implementation for demo
        return {
            "status": 200,
            "headers": headers or {},
            "body": {"message": "PUT request successful", "data": data or {}}
        }
    
    @keyword
    def http_delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform HTTP DELETE request.
        
        **Arguments:**
        - `url`: Target URL
        - `headers`: Optional dictionary of HTTP headers
        
        **Returns:** Response dictionary with status, headers, and body
        """
        # Simulated implementation for demo
        return {
            "status": 204,
            "headers": headers or {},
            "body": {"message": "DELETE request successful"}
        }
    
    @keyword
    def set_header(self, name: str, value: str) -> None:
        """
        Set a default header for all subsequent requests.
        
        **Arguments:**
        - `name`: Header name
        - `value`: Header value
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        Set Header Example
            Set Header    Authorization    Bearer token123
            Set Header    Content-Type    application/json
            ${response}    Http Get    https://api.example.com/data
        ```
        """
        self._session_headers[name] = value
    
    @keyword
    def clear_headers(self) -> None:
        """
        Clear all default headers.
        """
        self._session_headers.clear()
    
    @keyword
    def get_response_status(self, response: Dict[str, Any]) -> int:
        """
        Extract HTTP status code from response.
        
        **Arguments:**
        - `response`: Response dictionary from HTTP request
        
        **Returns:** HTTP status code
        """
        return response.get("status", 0)
    
    @keyword
    def get_response_body(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract response body from HTTP response.
        
        **Arguments:**
        - `response`: Response dictionary from HTTP request
        
        **Returns:** Response body as dictionary
        """
        return response.get("body", {})
    
    @keyword
    def response_should_be_success(self, response: Dict[str, Any]) -> None:
        """
        Verify that HTTP response status is success (2xx).
        
        **Arguments:**
        - `response`: Response dictionary from HTTP request
        
        **Raises:** AssertionError if status is not 2xx
        """
        status = response.get("status", 0)
        if not (200 <= status < 300):
            raise AssertionError(f"Expected success status, got {status}")
    
    @keyword
    def parse_json_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON response body.
        
        **Arguments:**
        - `response`: Response dictionary from HTTP request
        
        **Returns:** Parsed JSON as dictionary
        """
        body = response.get("body", {})
        if isinstance(body, str):
            return json.loads(body)
        return body
    
    @keyword
    def build_query_string(self, params: Dict[str, Any]) -> str:
        """
        Build URL query string from parameters.
        
        **Arguments:**
        - `params`: Dictionary of query parameters
        
        **Returns:** Query string (e.g., "key1=value1&key2=value2")
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        Build Query String Example
            ${params}    Create Dictionary    page=1    limit=10
            ${query}    Build Query String    ${params}
            Should Be Equal    ${query}    page=1&limit=10
        ```
        """
        return "&".join([f"{k}={v}" for k, v in params.items()])
    
    @keyword
    def set_basic_auth(self, username: str, password: str) -> None:
        """
        Set Basic Authentication header.
        
        **Arguments:**
        - `username`: Username for authentication
        - `password`: Password for authentication
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        Set Basic Auth Example
            Set Basic Auth    admin    secret123
            ${response}    Http Get    https://api.example.com/protected
        ```
        """
        import base64
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self.set_header("Authorization", f"Basic {encoded}")
    
    @keyword
    def set_bearer_token(self, token: str) -> None:
        """
        Set Bearer token authentication header.
        
        **Arguments:**
        - `token`: Bearer token string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    HTTPClient
        
        
        *** Test Cases ***
        Set Bearer Token Example
            Set Bearer Token    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
            ${response}    Http Get    https://api.example.com/data
        ```
        """
        self.set_header("Authorization", f"Bearer {token}")

