from typing import List, Dict, Any
from robot.api.deco import keyword
import time
import json
import os


class SampleLibrary:
    """
    A comprehensive test library for Robot Framework documentation generation.
    This library includes various types of keywords to demonstrate the full
    capabilities of the documentation generator.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.0.0"
    
    def __init__(self):
        """Initialize the test library."""
        self._session_data = {}
        self._counter = 0
    
    @keyword("Open Application")
    def open_application(self, app_path: str, timeout: int = 30) -> str:
        """
        The **Open Application** keyword starts a new application instance.
        
        ## Example
        
        ```robot
        
        *** Settings ***
        Library         TestLibrary
        
        *** Test Cases ***
        Launch App
            ${pid}=    Open Application    C:\\Program Files\\MyApp\\app.exe
            Log        Application started with PID: ${pid}
        ```
        
        ## Notes
        - The application must be a valid executable file
        - Use `Close Application` to properly terminate the application
        """
        # Simulate application launch
        self._counter += 1
        pid = f"PID_{self._counter}_{int(time.time())}"
        self._session_data[pid] = {
            'path': app_path,
            'started_at': time.time(),
            'status': 'running'
        }
        return pid
    
    @keyword("Close Application")
    def close_application(self, pid: str) -> bool:
        """
        The **Close Application** keyword terminates a running application.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Close App
            ${pid}=    Open Application    C:\\MyApp\\app.exe
            ${result}= Close Application    ${pid}
            Should Be True    ${result}
        ```
        """
        if pid in self._session_data:
            self._session_data[pid]['status'] = 'closed'
            return True
        return False
    
    @keyword("Get Process ID")
    def get_process_id(self, app_name: str = "default") -> str:
        """
        The **Get Process ID** keyword retrieves the process ID of a running application.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Get PID
            ${pid}=    Get Process ID    MyApplication
            Log        Process ID: ${pid}
        ```
        """
        return f"PID_{app_name}_{int(time.time())}"
    
    @keyword("Wait for Process Exit")
    def wait_for_process_exit(self, pid: str, timeout: int = 60) -> bool:
        """
        The **Wait for Process Exit** keyword waits for an application to terminate.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Wait for Exit
            ${pid}=    Open Application    C:\\MyApp\\app.exe
            ${result}= Wait for Process Exit    ${pid}    30
            Should Be True    ${result}
        ```
        """
        # Simulate waiting
        time.sleep(0.1)  # Simulate processing time
        return True
    
    @keyword("Connect to Application")
    def connect_to_application(self, host: str = "localhost", port: int = 8080) -> bool:
        """
        The **Connect to Application** keyword establishes a connection to a remote application.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Connect Remote
            ${connected}=    Connect to Application    192.168.1.100    9090
            Should Be True    ${connected}
        ```
        """
        return True
    
    @keyword("Kill Application")
    def kill_application(self, pid: str, force: bool = False) -> bool:
        """
        The **Kill Application** keyword forcefully terminates an application.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Force Kill
            ${pid}=    Open Application    C:\\MyApp\\app.exe
            ${result}= Kill Application    ${pid}    force=True
            Should Be True    ${result}
        ```
        """
        return True
    
    @keyword("Set Application Timeout")
    def set_application_timeout(self, timeout: int) -> None:
        """
        The **Set Application Timeout** keyword configures the default timeout for application operations.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Configure Timeout
            Set Application Timeout    45
            ${pid}=    Open Application    C:\\MyApp\\app.exe
        ```
        """
        self._timeout = timeout
    
    @keyword("Get Application Status")
    def get_application_status(self, pid: str) -> str:
        """
        The **Get Application Status** keyword retrieves the current status of an application.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Check Status
            ${pid}=    Open Application    C:\\MyApp\\app.exe
            ${status}= Get Application Status    ${pid}
            Should Be Equal    ${status}    running
        ```
        """
        if pid in self._session_data:
            return self._session_data[pid]['status']
        return "unknown"
    
    @keyword("List Running Applications")
    def list_running_applications(self) -> List[str]:
        """
        The **List Running Applications** keyword returns a list of all running application PIDs.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        List Apps
            ${pids}=    List Running Applications
            Log Many    ${pids}
        ```
        """
        running_pids = []
        for pid, data in self._session_data.items():
            if data['status'] == 'running':
                running_pids.append(pid)
        return running_pids
    
    @keyword("Save Session Data")
    def save_session_data(self, file_path: str) -> bool:
        """
        The **Save Session Data** keyword saves current session information to a file.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Save Data
            ${pid}=    Open Application    C:\\MyApp\\app.exe
            ${saved}=  Save Session Data    session.json
            Should Be True    ${saved}
        ```
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self._session_data, f, indent=2)
            return True
        except Exception:
            return False
    
    @keyword("Load Session Data")
    def load_session_data(self, file_path: str) -> bool:
        """
        The **Load Session Data** keyword loads session information from a file.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Load Data
            ${loaded}= Load Session Data    session.json
            Should Be True    ${loaded}
        ```
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    self._session_data = json.load(f)
                return True
            return False
        except Exception:
            return False
    
    @keyword("Clear Session Data")
    def clear_session_data(self) -> None:
        """
        The **Clear Session Data** keyword clears all stored session information.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Clear Data
            Clear Session Data
            ${pids}=    List Running Applications
            Should Be Empty    ${pids}
        ```
        """
        self._session_data.clear()
    
    @keyword("Get Session Statistics")
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        The **Get Session Statistics** keyword returns statistics about the current session.
        
        ## Example
        
        ```robot
        *** Settings ***
        Library         TestLibrary

        *** Test Cases ***
        Get Stats
            ${stats}=   Get Session Statistics
            Log         Total applications: ${stats}[total]
            Log         Running: ${stats}[running]
        ```
        """
        total = len(self._session_data)
        running = sum(1 for data in self._session_data.values() if data['status'] == 'running')
        closed = sum(1 for data in self._session_data.values() if data['status'] == 'closed')
        
        return {
            'total': total,
            'running': running,
            'closed': closed,
            'uptime': time.time() - min(data['started_at'] for data in self._session_data.values()) if self._session_data else 0
        }
