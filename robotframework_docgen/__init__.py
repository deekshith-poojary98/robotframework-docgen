"""
Robot Framework Documentation Generator

A powerful documentation generator for Robot Framework libraries that extracts
keywords, arguments, and docstrings to create professional, well-formatted HTML
and Markdown documentation with advanced markdown support and syntax highlighting.
"""

from robotframework_docgen._meta import __author__, __email__, __version__
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
    "__version__",
    "__author__",
    "__email__",
]
