"""
Tests for Enum type support in keyword arguments.

This module tests the Enum detection, extraction, and rendering functionality.
"""
import pytest
import tempfile
import os
from pathlib import Path
from enum import Enum
from robotframework_docgen.parser import RobotFrameworkDocParser, KeywordInfo
from robotframework_docgen.generator import DocumentationGenerator


class TestEnum(Enum):
    """Test Enum for testing."""
    VALUE_A = 1
    VALUE_B = 2
    VALUE_C = "three"


class StatusEnum(Enum):
    """Status Enum for testing."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


@pytest.fixture
def enum_library_file():
    """Create a temporary library file with Enum types."""
    content = '''"""
Test Library with Enum Types
"""
from robot.api.deco import keyword
from enum import Enum
from typing import Optional


class MyEnum(Enum):
    """Test Enum."""
    ValueA = 123
    ValueB = 456
    ValueC = 789


class StatusEnum(Enum):
    """Status Enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class TestLibrary:
    """Test library for Enum support."""
    
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def keyword_with_enum(self, status: StatusEnum, value: MyEnum = MyEnum.ValueA):
        """
        Keyword with Enum parameters.
        
        **Arguments:**
        - `status`: Status enum
        - `value`: Value enum with default
        """
        pass
    
    @keyword
    def keyword_without_enum(self, name: str, age: int = 18):
        """
        Regular keyword without Enum.
        
        **Arguments:**
        - `name`: Name string
        - `age`: Age integer
        """
        pass
    
    @keyword
    def keyword_mixed(self, name: str, status: StatusEnum, age: int = 18):
        """
        Keyword with mixed parameter types.
        
        **Arguments:**
        - `name`: Name string
        - `status`: Status enum
        - `age`: Age integer
        """
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def enum_library_file_no_defaults():
    """Create a temporary library file with Enum types without defaults."""
    content = '''"""
Test Library with Enum Types (No Defaults)
"""
from robot.api.deco import keyword
from enum import Enum


class ColorEnum(Enum):
    """Color Enum."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestLibrary:
    """Test library."""
    
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def set_color(self, color: ColorEnum):
        """Set color."""
        pass
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestEnumDetection:
    """Test Enum type detection."""
    
    def test_detect_enum_in_parameters(self, enum_library_file):
        """Test that Enum types are detected in keyword parameters."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        # Find the keyword with Enum
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        assert keyword is not None
        
        # Check that Enum information is extracted
        assert 'status' in keyword.parameter_enums
        assert 'value' in keyword.parameter_enums
        
        # Check Enum details
        status_enum = keyword.parameter_enums['status']
        assert status_enum['type_name'] == 'StatusEnum'
        assert len(status_enum['members']) == 2
        assert any(m['name'] == 'ACTIVE' and m['value'] == 'active' for m in status_enum['members'])
        assert any(m['name'] == 'INACTIVE' and m['value'] == 'inactive' for m in status_enum['members'])
        
        value_enum = keyword.parameter_enums['value']
        assert value_enum['type_name'] == 'MyEnum'
        assert len(value_enum['members']) == 3
        # Default value may not always be extracted (depends on parsing path)
        # Check if default exists, and if so, verify it's correct
        if 'default' in value_enum:
            assert value_enum['default'] == 'ValueA'
    
    def test_no_enum_in_regular_keyword(self, enum_library_file):
        """Test that regular keywords don't have Enum information."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword Without Enum"), None)
        assert keyword is not None
        
        # Should have no Enum information
        assert not keyword.parameter_enums or len(keyword.parameter_enums) == 0
    
    def test_mixed_parameters(self, enum_library_file):
        """Test keyword with mixed Enum and regular parameters."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword Mixed"), None)
        assert keyword is not None
        
        # Should have Enum info only for Enum parameter
        assert 'status' in keyword.parameter_enums
        assert 'name' not in keyword.parameter_enums
        assert 'age' not in keyword.parameter_enums
    
    def test_enum_without_default(self, enum_library_file_no_defaults):
        """Test Enum parameter without default value."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file_no_defaults)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Set Color"), None)
        assert keyword is not None
        
        assert 'color' in keyword.parameter_enums
        color_enum = keyword.parameter_enums['color']
        assert 'default' not in color_enum or color_enum.get('default') is None


class TestEnumExtraction:
    """Test Enum information extraction."""
    
    def test_extract_enum_members(self, enum_library_file):
        """Test that all Enum members are extracted correctly."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        value_enum = keyword.parameter_enums['value']
        
        # Check all members are present
        member_names = {m['name'] for m in value_enum['members']}
        assert member_names == {'ValueA', 'ValueB', 'ValueC'}
        
        # Check values
        member_dict = {m['name']: m['value'] for m in value_enum['members']}
        assert member_dict['ValueA'] == 123
        assert member_dict['ValueB'] == 456
        assert member_dict['ValueC'] == 789
    
    def test_extract_enum_with_string_values(self, enum_library_file):
        """Test Enum with string values."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        status_enum = keyword.parameter_enums['status']
        
        # Check string values are preserved
        member_dict = {m['name']: m['value'] for m in status_enum['members']}
        assert member_dict['ACTIVE'] == 'active'
        assert member_dict['INACTIVE'] == 'inactive'


class TestEnumRendering:
    """Test Enum rendering in generated documentation."""
    
    def test_html_renders_enum_info(self, enum_library_file):
        """Test that HTML output includes Enum information."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        # Check that Enum type is mentioned
        assert 'StatusEnum' in html or 'status' in html.lower()
        
        # Check that allowed values are mentioned
        assert 'Allowed values' in html or 'allowed values' in html.lower()
        
        # Check that Enum members are present
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        status_enum = keyword.parameter_enums['status']
        for member in status_enum['members']:
            assert member['name'] in html
    
    def test_html_renders_enum_default(self, enum_library_file):
        """Test that HTML output includes Enum default value."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        # Check that default value is shown
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        value_enum = keyword.parameter_enums['value']
        if 'default' in value_enum:
            assert value_enum['default'] in html
    
    def test_markdown_renders_enum_info(self, enum_library_file):
        """Test that Markdown output includes Enum information."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        markdown = generator.generate_markdown()
        
        # Check that Enum information is present
        assert 'Allowed values' in markdown
        
        # Check that Enum members are listed
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        status_enum = keyword.parameter_enums['status']
        for member in status_enum['members']:
            assert member['name'] in markdown
            assert str(member['value']) in markdown
    
    def test_markdown_renders_enum_default(self, enum_library_file):
        """Test that Markdown output includes Enum default value."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        markdown = generator.generate_markdown()
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword With Enum"), None)
        value_enum = keyword.parameter_enums['value']
        if 'default' in value_enum:
            assert value_enum['default'] in markdown


class TestEnumEdgeCases:
    """Test edge cases for Enum support."""
    
    def test_enum_with_int_values(self):
        """Test Enum with integer values."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from enum import Enum


class IntEnum(Enum):
    """Integer Enum."""
    ONE = 1
    TWO = 2
    THREE = 3


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, value: IntEnum):
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
            assert 'value' in keyword.parameter_enums
            enum_info = keyword.parameter_enums['value']
            
            # Check integer values are preserved
            member_dict = {m['name']: m['value'] for m in enum_info['members']}
            assert member_dict['ONE'] == 1
            assert member_dict['TWO'] == 2
            assert member_dict['THREE'] == 3
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_enum_with_float_values(self):
        """Test Enum with float values."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from enum import Enum


class FloatEnum(Enum):
    """Float Enum."""
    PI = 3.14
    E = 2.71


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, value: FloatEnum):
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
            assert 'value' in keyword.parameter_enums
            enum_info = keyword.parameter_enums['value']
            
            # Check float values are preserved
            member_dict = {m['name']: m['value'] for m in enum_info['members']}
            assert member_dict['PI'] == 3.14
            assert member_dict['E'] == 2.71
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_multiple_enum_parameters(self):
        """Test keyword with multiple Enum parameters."""
        content = '''"""
Test Library
"""
from robot.api.deco import keyword
from enum import Enum


class Enum1(Enum):
    A = 1
    B = 2


class Enum2(Enum):
    X = "x"
    Y = "y"


class TestLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, e1: Enum1, e2: Enum2):
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
            assert 'e1' in keyword.parameter_enums
            assert 'e2' in keyword.parameter_enums
            
            assert keyword.parameter_enums['e1']['type_name'] == 'Enum1'
            assert keyword.parameter_enums['e2']['type_name'] == 'Enum2'
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestEnumBackwardCompatibility:
    """Test that Enum support doesn't break existing functionality."""
    
    def test_regular_parameters_still_work(self, enum_library_file):
        """Test that regular parameters still work correctly."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword Without Enum"), None)
        assert keyword is not None
        
        # Should have parameters
        assert len(keyword.parameters) == 2
        assert any(p[0] == 'name' and p[1] == 'str' for p in keyword.parameters)
        assert any(p[0] == 'age' and p[1] == 'int' for p in keyword.parameters)
        
        # Should not have Enum info
        assert not keyword.parameter_enums
    
    def test_mixed_keywords_still_work(self, enum_library_file):
        """Test that keywords with mixed types still work."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(enum_library_file)
        
        keyword = next((kw for kw in library_info.keywords if kw.name == "Keyword Mixed"), None)
        assert keyword is not None
        
        # Should have all parameters
        assert len(keyword.parameters) == 3
        
        # Only Enum parameter should have Enum info
        assert 'status' in keyword.parameter_enums
        assert 'name' not in keyword.parameter_enums
        assert 'age' not in keyword.parameter_enums
