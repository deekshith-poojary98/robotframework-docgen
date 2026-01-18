"""
Pytest configuration and shared fixtures.

This module provides shared fixtures and configuration for all tests.
"""
import pytest
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
