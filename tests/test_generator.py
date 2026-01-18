"""
Tests for the generator module.

This module tests the DocumentationGenerator functionality including
HTML and Markdown generation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from robotframework_docgen.parser import RobotFrameworkDocParser, LibraryInfo, KeywordInfo
from robotframework_docgen.generator import DocumentationGenerator


@pytest.fixture
def sample_library_info():
    """Create a sample LibraryInfo for testing."""
    keywords = [
        KeywordInfo(
            name="Test Keyword",
            description="A test keyword",
            example="",
            parameters=[("name", "str"), ("age", "int")],
            return_type="str",
            line_number=10,
            parameter_enums={}
        )
    ]
    
    return LibraryInfo(
        name="TestLibrary",
        version="1.0.0",
        scope="TEST",
        description="A test library",
        keywords=keywords
    )


@pytest.fixture
def library_with_enum():
    """Create a library info with Enum parameters."""
    keywords = [
        KeywordInfo(
            name="Enum Keyword",
            description="Keyword with Enum",
            example="",
            parameters=[("status", "StatusEnum"), ("value", "MyEnum")],
            return_type="None",
            line_number=10,
            parameter_enums={
                "status": {
                    "type_name": "StatusEnum",
                    "members": [
                        {"name": "ACTIVE", "value": "active"},
                        {"name": "INACTIVE", "value": "inactive"}
                    ]
                },
                "value": {
                    "type_name": "MyEnum",
                    "members": [
                        {"name": "ValueA", "value": 123},
                        {"name": "ValueB", "value": 456}
                    ],
                    "default": "ValueA"
                }
            }
        )
    ]
    
    return LibraryInfo(
        name="EnumLibrary",
        version="1.0.0",
        scope="TEST",
        description="Library with Enum",
        keywords=keywords
    )


class TestHTMLGeneration:
    """Test HTML generation."""
    
    def test_generate_html_basic(self, sample_library_info):
        """Test basic HTML generation."""
        generator = DocumentationGenerator(sample_library_info)
        html = generator.generate_html()
        
        assert html is not None
        assert len(html) > 0
        assert "<html" in html.lower() or "<!doctype" in html.lower()
        assert "TestLibrary" in html
        assert "Test Keyword" in html
    
    def test_html_includes_library_metadata(self, sample_library_info):
        """Test that HTML includes library metadata."""
        generator = DocumentationGenerator(sample_library_info)
        html = generator.generate_html()
        
        assert "1.0.0" in html  # Version
        assert "TEST" in html  # Scope
    
    def test_html_includes_keyword_parameters(self, sample_library_info):
        """Test that HTML includes keyword parameters."""
        generator = DocumentationGenerator(sample_library_info)
        html = generator.generate_html()
        
        assert "name" in html
        assert "age" in html
        assert "str" in html or "int" in html
    
    def test_html_includes_enum_info(self, library_with_enum):
        """Test that HTML includes Enum information."""
        generator = DocumentationGenerator(library_with_enum)
        html = generator.generate_html()
        
        assert "StatusEnum" in html or "status" in html.lower()
        assert "Allowed values" in html or "allowed values" in html.lower()
        assert "ACTIVE" in html
        assert "INACTIVE" in html
    
    def test_html_includes_enum_default(self, library_with_enum):
        """Test that HTML includes Enum default value."""
        generator = DocumentationGenerator(library_with_enum)
        html = generator.generate_html()
        
        # Check for default value
        enum_info = library_with_enum.keywords[0].parameter_enums['value']
        if 'default' in enum_info:
            assert enum_info['default'] in html
    
    def test_html_template_placeholders(self, sample_library_info):
        """Test that all template placeholders are replaced."""
        generator = DocumentationGenerator(sample_library_info)
        html = generator.generate_html()
        
        # Should not contain any unreplaced placeholders
        assert "{{LIBRARY_NAME}}" not in html
        assert "{{VERSION}}" not in html
        assert "{{KEYWORD_LIST}}" not in html


class TestMarkdownGeneration:
    """Test Markdown generation."""
    
    def test_generate_markdown_basic(self, sample_library_info):
        """Test basic Markdown generation."""
        generator = DocumentationGenerator(sample_library_info)
        markdown = generator.generate_markdown()
        
        assert markdown is not None
        assert len(markdown) > 0
        assert "# TestLibrary" in markdown
        assert "## Keywords" in markdown
        assert "### Test Keyword" in markdown
    
    def test_markdown_includes_parameters(self, sample_library_info):
        """Test that Markdown includes parameters."""
        generator = DocumentationGenerator(sample_library_info)
        markdown = generator.generate_markdown()
        
        assert "**Parameters:**" in markdown
        assert "`name`" in markdown
        assert "`age`" in markdown
    
    def test_markdown_includes_enum_info(self, library_with_enum):
        """Test that Markdown includes Enum information."""
        generator = DocumentationGenerator(library_with_enum)
        markdown = generator.generate_markdown()
        
        assert "Allowed values" in markdown
        assert "ACTIVE" in markdown
        assert "INACTIVE" in markdown
        assert "ValueA" in markdown
        assert "ValueB" in markdown
    
    def test_markdown_includes_enum_default(self, library_with_enum):
        """Test that Markdown includes Enum default value."""
        generator = DocumentationGenerator(library_with_enum)
        markdown = generator.generate_markdown()
        
        enum_info = library_with_enum.keywords[0].parameter_enums['value']
        if 'default' in enum_info:
            assert enum_info['default'] in markdown
    
    def test_markdown_includes_return_type(self, sample_library_info):
        """Test that Markdown includes return type."""
        generator = DocumentationGenerator(sample_library_info)
        markdown = generator.generate_markdown()
        
        assert "**Returns:**" in markdown
        assert "`str`" in markdown


class TestGeneratorConfig:
    """Test generator configuration."""
    
    def test_custom_library_name(self, sample_library_info):
        """Test custom library name from config."""
        config = {"name": "CustomName"}
        generator = DocumentationGenerator(sample_library_info, config=config)
        
        assert generator.library_name == "CustomName"
    
    def test_fallback_to_class_name(self, sample_library_info):
        """Test fallback to class name when config name not provided."""
        generator = DocumentationGenerator(sample_library_info)
        
        assert generator.library_name == "TestLibrary"
    
    def test_metadata_in_html(self, sample_library_info):
        """Test that metadata from config appears in HTML."""
        config = {
            "author": "Test Author",
            "maintainer": "Test Maintainer",
            "license": "MIT"
        }
        generator = DocumentationGenerator(sample_library_info, config=config)
        html = generator.generate_html()
        
        assert "Test Author" in html or "Author" in html
        assert "Test Maintainer" in html or "Maintainer" in html


class TestGeneratorEdgeCases:
    """Test edge cases in generator."""
    
    def test_empty_keywords(self):
        """Test generation with no keywords."""
        library_info = LibraryInfo(
            name="EmptyLibrary",
            version="1.0.0",
            scope="TEST",
            description="Empty library",
            keywords=[]
        )
        
        generator = DocumentationGenerator(library_info)
        html = generator.generate_html()
        markdown = generator.generate_markdown()
        
        assert html is not None
        assert markdown is not None
        assert "EmptyLibrary" in html
        assert "EmptyLibrary" in markdown
    
    def test_keyword_without_parameters(self):
        """Test keyword without parameters."""
        keywords = [
            KeywordInfo(
                name="No Params",
                description="No parameters",
                example="",
                parameters=[],
                return_type="None",
                line_number=10,
                parameter_enums={}
            )
        ]
        
        library_info = LibraryInfo(
            name="TestLibrary",
            version="1.0.0",
            scope="TEST",
            description="Test",
            keywords=keywords
        )
        
        generator = DocumentationGenerator(library_info)
        html = generator.generate_html()
        markdown = generator.generate_markdown()
        
        assert "No Params" in html
        assert "No Params" in markdown
    
    def test_keyword_without_description(self):
        """Test keyword without description."""
        keywords = [
            KeywordInfo(
                name="No Desc",
                description="",
                example="",
                parameters=[("x", "int")],
                return_type="None",
                line_number=10,
                parameter_enums={}
            )
        ]
        
        library_info = LibraryInfo(
            name="TestLibrary",
            version="1.0.0",
            scope="TEST",
            description="Test",
            keywords=keywords
        )
        
        generator = DocumentationGenerator(library_info)
        html = generator.generate_html()
        markdown = generator.generate_markdown()
        
        assert "No Desc" in html
        assert "No Desc" in markdown
