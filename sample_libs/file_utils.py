"""
FileUtils Library

A Robot Framework library for file and directory operations.
Provides keywords for file manipulation, reading, writing, and directory management.
"""

from robot.api.deco import keyword
from pathlib import Path
from typing import List, Optional
import os
import shutil
import json


class FileUtils:
    """
    File and directory utilities for Robot Framework.
    
    This library provides comprehensive file system operations including:
    - File reading and writing
    - Directory creation and management
    - File copying and moving
    - Path manipulation
    - File existence checks
    """
    
    ROBOT_LIBRARY_VERSION = "1.2.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    def __init__(self):
        """Initialize the FileUtils library."""
        self._temp_files = []
    
    @keyword
    def read_file_content(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        Read entire content of a file.
        
        **Arguments:**
        - `file_path`: Path to the file to read
        - `encoding`: File encoding (default: utf-8)
        
        **Returns:** File content as string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Read File Example
            ${content}    Read File Content    /path/to/file.txt
            Should Not Be Empty    ${content}
        ```
        """
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    
    @keyword
    def write_file_content(self, file_path: str, content: str, encoding: str = "utf-8") -> None:
        """
        Write content to a file.
        
        Creates the file if it doesn't exist, overwrites if it does.
        
        **Arguments:**
        - `file_path`: Path where to write the file
        - `content`: Content to write
        - `encoding`: File encoding (default: utf-8)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Write File Example
            Write File Content    output.txt    Hello World
            File Should Exist    output.txt
        ```
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
    
    @keyword
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        **Arguments:**
        - `file_path`: Path to check
        
        **Returns:** True if file exists, False otherwise
        """
        return Path(file_path).is_file()
    
    @keyword
    def directory_exists(self, dir_path: str) -> bool:
        """
        Check if a directory exists.
        
        **Arguments:**
        - `dir_path`: Directory path to check
        
        **Returns:** True if directory exists, False otherwise
        """
        return Path(dir_path).is_dir()
    
    @keyword
    def create_directory(self, dir_path: str, parents: bool = True) -> None:
        """
        Create a directory.
        
        **Arguments:**
        - `dir_path`: Directory path to create
        - `parents`: Create parent directories if needed (default: True)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Create Directory Example
            Create Directory    /path/to/new/directory
            Directory Should Exist    /path/to/new/directory
        ```
        """
        Path(dir_path).mkdir(parents=parents, exist_ok=True)
    
    @keyword
    def copy_file(self, source: str, destination: str) -> None:
        """
        Copy a file from source to destination.
        
        **Arguments:**
        - `source`: Source file path
        - `destination`: Destination file path
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Copy File Example
            Copy File    source.txt    backup/source.txt
            File Should Exist    backup/source.txt
        ```
        """
        shutil.copy2(source, destination)
    
    @keyword
    def move_file(self, source: str, destination: str) -> None:
        """
        Move a file from source to destination.
        
        **Arguments:**
        - `source`: Source file path
        - `destination`: Destination file path
        """
        shutil.move(source, destination)
    
    @keyword
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file.
        
        **Arguments:**
        - `file_path`: Path to file to delete
        
        **Raises:** FileNotFoundError if file doesn't exist
        """
        Path(file_path).unlink()
    
    @keyword
    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """
        List all files in a directory.
        
        **Arguments:**
        - `directory`: Directory path to list
        - `pattern`: Optional glob pattern to filter files (e.g., "*.txt")
        
        **Returns:** List of file paths
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        List Files Example
            ${files}    List Files    /path/to/dir    *.txt
            Should Not Be Empty    ${files}
        ```
        """
        path = Path(directory)
        if pattern:
            return [str(f) for f in path.glob(pattern) if f.is_file()]
        return [str(f) for f in path.iterdir() if f.is_file()]
    
    @keyword
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        **Arguments:**
        - `file_path`: Path to file
        
        **Returns:** File size in bytes
        """
        return Path(file_path).stat().st_size
    
    @keyword
    def read_json_file(self, file_path: str) -> dict:
        """
        Read and parse a JSON file.
        
        **Arguments:**
        - `file_path`: Path to JSON file
        
        **Returns:** Parsed JSON as dictionary
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Read JSON File Example
            ${data}    Read Json File    config.json
            Should Be Equal    ${data}[key]    value
        ```
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @keyword
    def write_json_file(self, file_path: str, data: dict, indent: int = 2) -> None:
        """
        Write data to a JSON file.
        
        **Arguments:**
        - `file_path`: Path where to write JSON file
        - `data`: Dictionary to write as JSON
        - `indent`: JSON indentation (default: 2)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Write JSON File Example
            ${config}    Create Dictionary    key=value    name=test
            Write Json File    config.json    ${config}
            File Should Exist    config.json
        ```
        """
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
    
    @keyword
    def get_file_extension(self, file_path: str) -> str:
        """
        Get file extension.
        
        **Arguments:**
        - `file_path`: File path
        
        **Returns:** File extension (without dot)
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Get File Extension Example
            ${ext}    Get File Extension    document.pdf
            Should Be Equal    ${ext}    pdf
        ```
        """
        return Path(file_path).suffix.lstrip(".")
    
    @keyword
    def join_paths(self, *paths: str) -> str:
        """
        Join multiple path components.
        
        **Arguments:**
        - `*paths`: Variable number of path components
        
        **Returns:** Joined path string
        
        **Example:**
        ```robot
        *** Settings ***
        Library    FileUtils
        
        *** Test Cases ***
        Join Paths Example
            ${path}    Join Paths    /home    user    documents    file.txt
            Should Be Equal    ${path}    /home/user/documents/file.txt
        ```
        """
        return str(Path(*paths))

