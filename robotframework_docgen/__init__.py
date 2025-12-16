"""
Robot Framework Documentation Generator

A powerful documentation generator for Robot Framework libraries that extracts
keywords, arguments, and docstrings to create professional, well-formatted HTML
and Markdown documentation with advanced markdown support and syntax highlighting.
"""

__version__ = "1.0.0"
__author__ = "Deekshith Poojary"
__email__ = "deekshithpoojary355@gmail.com"

from robotframework_docgen.parser import (
    RobotFrameworkDocParser,
    KeywordInfo,
    LibraryInfo,
)
from robotframework_docgen.generator import DocumentationGenerator

__all__ = [
    "RobotFrameworkDocParser",
    "DocumentationGenerator",
    "KeywordInfo",
    "LibraryInfo",
]

