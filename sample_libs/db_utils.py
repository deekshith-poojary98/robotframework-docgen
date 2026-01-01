"""
DBUtils Library

A Robot Framework library for database operations.
Provides keywords for database queries, data manipulation, and connection management.
"""

from robot.api.deco import keyword
from typing import List, Dict, Optional, Any
from datetime import datetime


class DBUtils:
    """
    Database utilities library for Robot Framework.
    
    This library provides keywords for:
    - Database connection management
    - Executing SQL queries
    - Data insertion and updates
    - Query result handling
    - Transaction management
    """
    
    ROBOT_LIBRARY_VERSION = "1.5.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the DBUtils library."""
        self._connection = None
        self._transactions = []
    
    @keyword
    def connect_to_database(self, host: str, database: str, 
                           username: str, password: str, 
                           port: int = 5432) -> None:
        """
        Connect to a database.
        
        **Arguments:**
        - `host`: Database host address
        - `database`: Database name
        - `username`: Database username
        - `password`: Database password
        - `port`: Database port (default: 5432)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Connect To Database Example
            Connect To Database    localhost    mydb    admin    secret123
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated connection for demo
        self._connection = {
            "host": host,
            "database": database,
            "username": username,
            "port": port
        }
    
    @keyword
    def disconnect_from_database(self) -> None:
        """
        Disconnect from the database.
        """
        self._connection = None
    
    @keyword
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        **Arguments:**
        - `query`: SQL SELECT query string
        - `params`: Optional list of query parameters
        
        **Returns:** List of dictionaries representing rows
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Execute Query Example
            Connect To Database    localhost    mydb    admin    secret123
            ${results}    Execute Query    SELECT * FROM users WHERE age > ?    ${[25]}
            Should Not Be Empty    ${results}
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated query results for demo
        return [
            {"id": 1, "name": "John", "age": 30},
            {"id": 2, "name": "Jane", "age": 28}
        ]
    
    @keyword
    def execute_non_query(self, query: str, params: Optional[List[Any]] = None) -> int:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE).
        
        **Arguments:**
        - `query`: SQL query string
        - `params`: Optional list of query parameters
        
        **Returns:** Number of affected rows
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Execute Non Query Example
            Connect To Database    localhost    mydb    admin    secret123
            ${count}    Execute Non Query    UPDATE users SET status = ? WHERE id = ?
            ...    ${['active', 1]}
            Should Be Equal As Integers    ${count}    ${1}
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated result for demo
        return 1
    
    @keyword
    def insert_record(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a record into a table.
        
        **Arguments:**
        - `table`: Table name
        - `data`: Dictionary of column names and values
        
        **Returns:** ID of inserted record
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Insert Record Example
            Connect To Database    localhost    mydb    admin    secret123
            ${record}    Create Dictionary    name=John    email=john@example.com    age=30
            ${id}    Insert Record    users    ${record}
            Should Not Be Empty    ${id}
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated insert for demo
        return 123
    
    @keyword
    def update_record(self, table: str, data: Dict[str, Any], 
                     where_clause: str, params: Optional[List[Any]] = None) -> int:
        """
        Update records in a table.
        
        **Arguments:**
        - `table`: Table name
        - `data`: Dictionary of column names and new values
        - `where_clause`: WHERE clause (without WHERE keyword)
        - `params`: Optional list of parameters for WHERE clause
        
        **Returns:** Number of affected rows
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Update Record Example
            Connect To Database    localhost    mydb    admin    secret123
            ${data}    Create Dictionary    status=active    updated_at=${timestamp}
            ${count}    Update Record    users    ${data}    id = ?    ${[1]}
            Should Be Equal As Integers    ${count}    ${1}
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated update for demo
        return 1
    
    @keyword
    def delete_record(self, table: str, where_clause: str, 
                     params: Optional[List[Any]] = None) -> int:
        """
        Delete records from a table.
        
        **Arguments:**
        - `table`: Table name
        - `where_clause`: WHERE clause (without WHERE keyword)
        - `params`: Optional list of parameters for WHERE clause
        
        **Returns:** Number of deleted rows
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Delete Record Example
            Connect To Database    localhost    mydb    admin    secret123
            ${count}    Delete Record    users    id = ?    ${[1]}
            Should Be Equal As Integers    ${count}    ${1}
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated delete for demo
        return 1
    
    @keyword
    def get_table_count(self, table: str, where_clause: Optional[str] = None,
                       params: Optional[List[Any]] = None) -> int:
        """
        Get count of records in a table.
        
        **Arguments:**
        - `table`: Table name
        - `where_clause`: Optional WHERE clause (without WHERE keyword)
        - `params`: Optional list of parameters for WHERE clause
        
        **Returns:** Record count
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Get Table Count Example
            Connect To Database    localhost    mydb    admin    secret123
            ${count}    Get Table Count    users    status = ?    ${['active']}
            Should Be True    ${count} > 0
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated count for demo
        return 42
    
    @keyword
    def begin_transaction(self) -> None:
        """
        Begin a database transaction.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Transaction Example
            Connect To Database    localhost    mydb    admin    secret123
            Begin Transaction
            Insert Record    users    ${data1}
            Insert Record    users    ${data2}
            Commit Transaction
            [Teardown]    Disconnect From Database
        ```
        """
        self._transactions.append({"started": datetime.now()})
    
    @keyword
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if self._transactions:
            self._transactions.pop()
    
    @keyword
    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if self._transactions:
            self._transactions.pop()
    
    @keyword
    def query_single_row(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a query and return a single row.
        
        **Arguments:**
        - `query`: SQL SELECT query string
        - `params`: Optional list of query parameters
        
        **Returns:** Dictionary representing a single row
        
        **Raises:** ValueError if no rows or multiple rows found
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Query Single Row Example
            Connect To Database    localhost    mydb    admin    secret123
            ${user}    Query Single Row    SELECT * FROM users WHERE id = ?    ${[1]}
            Should Be Equal    ${user}[name]    John
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated single row result for demo
        return {"id": 1, "name": "John", "email": "john@example.com"}
    
    @keyword
    def query_single_value(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a query and return a single value.
        
        **Arguments:**
        - `query`: SQL SELECT query string (should return one column)
        - `params`: Optional list of query parameters
        
        **Returns:** Single value from query result
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DBUtils
        
        *** Test Cases ***
        Query Single Value Example
            Connect To Database    localhost    mydb    admin    secret123
            ${count}    Query Single Value    SELECT COUNT(*) FROM users
            Should Be True    ${count} >= 0
            [Teardown]    Disconnect From Database
        ```
        """
        # Simulated single value result for demo
        return 42

