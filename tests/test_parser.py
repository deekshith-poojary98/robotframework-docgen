"""
Tests for the parser module.

This module tests the RobotFrameworkDocParser functionality including
library parsing, keyword extraction, and type annotation handling.
"""
import pytest
import tempfile
import os
from pathlib import Path
from robotframework_docgen.parser import RobotFrameworkDocParser, KeywordInfo, LibraryInfo


@pytest.fixture
def simple_library_file():
    """Create a simple library file for testing."""
    content = '''"""
Simple Test Library
"""
from robot.api.deco import keyword
from typing import Optional, List, Dict, Any


class SimpleLibrary:
    """Simple test library."""
    
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def simple_keyword(self, name: str, age: int = 18):
        """
        Simple keyword.
        
        **Arguments:**
        - `name`: Name string
        - `age`: Age integer
        """
        return f"{name} is {age}"
    
    @keyword("Complex Keyword")
    def complex_keyword(self, data: Dict[str, Any], items: Optional[List[str]] = None) -> Dict:
        """
        Complex keyword with complex types.
        
        **Arguments:**
        - `data`: Data dictionary
        - `items`: Optional items list
        """
        return {}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def module_level_library_file():
    """Create a module-level library file for testing."""
    content = '''"""
Module-level library.
"""
from robot.api.deco import keyword


ROBOT_LIBRARY_VERSION = "2.0.0"
ROBOT_LIBRARY_SCOPE = "GLOBAL"


@keyword
def module_keyword(name: str) -> str:
    """
    Module-level keyword.
    
    **Arguments:**
    - `name`: Name string
    """
    return name
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestLibraryParsing:
    """Test library parsing functionality."""
    
    def test_parse_simple_library(self, simple_library_file):
        """Test parsing a simple library."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        assert library_info is not None
        assert library_info.name == "SimpleLibrary"
        assert library_info.version == "1.0.0"
        assert library_info.scope == "TEST"
        assert len(library_info.keywords) > 0
    
    def test_extract_keywords(self, simple_library_file):
        """Test keyword extraction."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        # Should have at least 2 keywords
        assert len(library_info.keywords) >= 2
        
        # Check keyword names
        keyword_names = {kw.name for kw in library_info.keywords}
        assert "Simple Keyword" in keyword_names or "simple_keyword" in keyword_names
        assert "Complex Keyword" in keyword_names
    
    def test_extract_parameters(self, simple_library_file):
        """Test parameter extraction."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        # Find simple keyword
        keyword = next((kw for kw in library_info.keywords if 'simple' in kw.name.lower()), None)
        assert keyword is not None
        
        # Should have parameters
        assert len(keyword.parameters) >= 2
        param_names = {p[0] for p in keyword.parameters}
        assert 'name' in param_names
        assert 'age' in param_names
    
    def test_extract_type_annotations(self, simple_library_file):
        """Test type annotation extraction."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        # Find complex keyword
        keyword = next((kw for kw in library_info.keywords if 'complex' in kw.name.lower()), None)
        assert keyword is not None
        
        # Check type annotations
        param_dict = {p[0]: p[1] for p in keyword.parameters}
        assert 'data' in param_dict
        assert 'Dict' in param_dict['data'] or 'dict' in param_dict['data'].lower()
        assert 'items' in param_dict
    
    def test_extract_return_type(self, simple_library_file):
        """Test return type extraction."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        # Find complex keyword
        keyword = next((kw for kw in library_info.keywords if 'complex' in kw.name.lower()), None)
        assert keyword is not None
        
        # Should have return type
        assert keyword.return_type is not None
        assert keyword.return_type != "None"


class TestTypeAnnotationHandling:
    """Test type annotation handling."""
    
    def test_union_types(self):
        """Test Union type annotations."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from typing import Union


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, value: Union[str, int]):
        """Test keyword."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            
            keyword = library_info.keywords[0]
            param_dict = {p[0]: p[1] for p in keyword.parameters}
            assert 'value' in param_dict
            # Union should be represented somehow
            assert 'str' in param_dict['value'] or 'Union' in param_dict['value']
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_optional_types(self):
        """Test Optional type annotations."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from typing import Optional


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, value: Optional[str] = None):
        """Test keyword."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            
            keyword = library_info.keywords[0]
            param_dict = {p[0]: p[1] for p in keyword.parameters}
            assert 'value' in param_dict
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_generic_types(self):
        """Test generic type annotations (List, Dict)."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from typing import List, Dict


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, items: List[str], data: Dict[str, int]):
        """Test keyword."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            
            keyword = library_info.keywords[0]
            param_dict = {p[0]: p[1] for p in keyword.parameters}
            assert 'items' in param_dict
            assert 'data' in param_dict
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDocstringParsing:
    """Test docstring parsing."""
    
    def test_parse_docstring(self, simple_library_file):
        """Test docstring parsing."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(simple_library_file)
        
        keyword = library_info.keywords[0]
        assert keyword.description is not None
        assert len(keyword.description) > 0
    
    def test_markdown_in_docstring(self):
        """Test markdown processing in docstrings."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self):
        """
        Test keyword with **bold** and *italic*.
        
        - List item 1
        - List item 2
        """
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            
            keyword = library_info.keywords[0]
            # Markdown should be processed
            assert keyword.description is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestErrorHandling:
    """Test error handling."""
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        parser = RobotFrameworkDocParser()
        # Should handle gracefully
        with pytest.raises((FileNotFoundError, Exception)):
            parser.parse_file("nonexistent_file.py")
    
    def test_invalid_python_file(self):
        """Test handling of invalid Python file."""
        content = "This is not valid Python code !!!"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            # Should raise SyntaxError for invalid Python
            with pytest.raises(SyntaxError):
                parser.parse_file(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_file_without_keywords(self):
        """Test handling of file without keywords."""
        content = '''"""
File without keywords.
"""

class RegularClass:
    """Regular class."""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            # Should handle gracefully
            assert library_info is not None
            # May have 0 keywords
            assert isinstance(library_info.keywords, list)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
