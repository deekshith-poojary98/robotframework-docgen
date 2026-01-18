"""
Integration tests for the full documentation generation pipeline.

This module tests the complete workflow from parsing to generation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from robotframework_docgen.parser import RobotFrameworkDocParser
from robotframework_docgen.generator import DocumentationGenerator


@pytest.fixture
def complete_library_file():
    """Create a complete library file with various features."""
    content = '''"""
Complete Test Library

This library demonstrates all features of robotframework-docgen.
"""
from robot.api.deco import keyword
from enum import Enum
from typing import Optional, List, Dict, Any, Union


class StatusEnum(Enum):
    """Status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class PriorityEnum(Enum):
    """Priority enumeration."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class CompleteLibrary:
    """Complete test library."""
    
    ROBOT_LIBRARY_VERSION = "2.0.0"
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    
    @keyword
    def process_data(self, data: Dict[str, Any], status: StatusEnum = StatusEnum.ACTIVE) -> Dict:
        """
        Process data with status.
        
        **Arguments:**
        - `data`: Data dictionary
        - `status`: Status enum (default: ACTIVE)
        
        **Returns:** Processed data dictionary
        """
        return {}
    
    @keyword("Set Priority")
    def set_priority(self, priority: PriorityEnum, description: Optional[str] = None):
        """
        Set priority level.
        
        **Arguments:**
        - `priority`: Priority enum (LOW, MEDIUM, HIGH, CRITICAL)
        - `description`: Optional description
        """
        pass
    
    @keyword
    def filter_items(self, items: List[str], status: StatusEnum) -> List[str]:
        """
        Filter items by status.
        
        **Arguments:**
        - `items`: List of items
        - `status`: Status to filter by
        
        **Returns:** Filtered list
        """
        return []
    
    @keyword
    def simple_keyword(self, name: str, age: int = 18) -> str:
        """
        Simple keyword without Enum.
        
        **Arguments:**
        - `name`: Name string
        - `age`: Age integer
        
        **Returns:** Formatted string
        """
        return f"{name}: {age}"
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestFullPipeline:
    """Test the complete documentation generation pipeline."""
    
    def test_parse_and_generate_html(self, complete_library_file):
        """Test parsing and HTML generation."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        assert library_info is not None
        assert len(library_info.keywords) > 0
        
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        assert html is not None
        assert len(html) > 0
        assert "CompleteLibrary" in html or "Complete" in html
    
    def test_parse_and_generate_markdown(self, complete_library_file):
        """Test parsing and Markdown generation."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        markdown = generator.generate_markdown()
        
        assert markdown is not None
        assert len(markdown) > 0
        assert "#" in markdown  # Should have headers
    
    def test_enum_integration(self, complete_library_file):
        """Test Enum integration in full pipeline."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        # Find keyword with Enum
        keyword = next((kw for kw in library_info.keywords if 'process' in kw.name.lower()), None)
        assert keyword is not None
        
        # Check Enum is detected
        assert 'status' in keyword.parameter_enums
        
        # Generate HTML and check Enum is rendered
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        assert "StatusEnum" in html or "status" in html.lower()
        assert "ACTIVE" in html
        assert "INACTIVE" in html
    
    def test_multiple_enums_integration(self, complete_library_file):
        """Test multiple Enum types in one library."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        # Check both Enum types are detected
        status_keyword = next((kw for kw in library_info.keywords if 'process' in kw.name.lower()), None)
        priority_keyword = next((kw for kw in library_info.keywords if 'priority' in kw.name.lower()), None)
        
        assert status_keyword is not None
        assert priority_keyword is not None
        
        assert 'status' in status_keyword.parameter_enums
        assert 'priority' in priority_keyword.parameter_enums
        
        # Generate and verify both are rendered
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        assert "StatusEnum" in html or "status" in html.lower()
        assert "PriorityEnum" in html or "priority" in html.lower()
    
    def test_mixed_keywords_integration(self, complete_library_file):
        """Test library with both Enum and non-Enum keywords."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        # Should have keywords with and without Enum
        enum_keywords = [kw for kw in library_info.keywords if kw.parameter_enums]
        non_enum_keywords = [kw for kw in library_info.keywords if not kw.parameter_enums]
        
        assert len(enum_keywords) > 0
        assert len(non_enum_keywords) > 0
        
        # Generate and verify both types render correctly
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        markdown = generator.generate_markdown()
        
        # Both should be present
        for kw in library_info.keywords:
            assert kw.name in html or kw.name.replace(" ", "") in html
            assert kw.name in markdown or kw.name.replace(" ", "") in markdown


class TestFileOutput:
    """Test file output functionality."""
    
    def test_write_html_file(self, complete_library_file):
        """Test writing HTML to file."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        html = generator.generate_html()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html)
            temp_path = f.name
        
        try:
            # Verify file was written
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Verify content
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "CompleteLibrary" in content or "Complete" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_write_markdown_file(self, complete_library_file):
        """Test writing Markdown to file."""
        parser = RobotFrameworkDocParser()
        library_info = parser.parse_file(complete_library_file)
        
        generator = DocumentationGenerator(library_info, parser)
        markdown = generator.generate_markdown()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown)
            temp_path = f.name
        
        try:
            # Verify file was written
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0
            
            # Verify content
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "#" in content  # Should have headers
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestBackwardCompatibility:
    """Test backward compatibility with existing libraries."""
    
    def test_library_without_enums(self):
        """Test library without any Enum types."""
        content = '''"""
Library without Enums
"""
from robot.api.deco import keyword


class SimpleLibrary:
    ROBOT_LIBRARY_VERSION = "1.0.0"
    ROBOT_LIBRARY_SCOPE = "TEST"
    
    @keyword
    def test_keyword(self, name: str, age: int):
        """Test keyword."""
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            parser = RobotFrameworkDocParser()
            library_info = parser.parse_file(temp_path)
            
            # Should parse successfully
            assert library_info is not None
            assert len(library_info.keywords) > 0
            
            # Should have no Enum info
            for kw in library_info.keywords:
                assert not kw.parameter_enums or len(kw.parameter_enums) == 0
            
            # Should generate successfully
            generator = DocumentationGenerator(library_info, parser)
            html = generator.generate_html()
            markdown = generator.generate_markdown()
            
            assert html is not None
            assert markdown is not None
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
