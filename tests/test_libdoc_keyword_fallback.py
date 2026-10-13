"""Regression tests for libraries whose keywords are absent from the AST map.

Robot Framework exposes every public method as a keyword unless
ROBOT_AUTO_KEYWORDS is false. Those methods are not decorated, so they never
enter the AST keyword map. Referencing an uninitialized parameter_defaults
dict used to abort LibraryDocumentation parsing and drop the keywords.
"""

from pathlib import Path

from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.parser import RobotFrameworkDocParser


def _write(path: Path, source: str) -> str:
    path.write_text(source)
    return str(path)


def test_undecorated_keywords_are_documented(tmp_path):
    """A class library with no @keyword decorators must keep Libdoc's keywords."""
    path = _write(
        tmp_path / "exactmatch.py",
        '''
class exactmatch:
    """Example library."""

    def hello(self, name):
        """Greet someone by name."""
        return name

    def open_browser(self, url, headless=False):
        """Open a browser at the given URL."""
        return url

    def current_time(self) -> str:
        """Return the current time."""
        return "now"
''',
    )

    library = RobotFrameworkDocParser().parse_file(path)
    keywords = {kw.name: kw for kw in library.keywords}

    assert set(keywords) == {"Hello", "Open Browser", "Current Time"}
    assert keywords["Current Time"].parameters == []
    assert keywords["Current Time"].return_type == "str"
    assert keywords["Hello"].parameters == [("name", "")]
    assert keywords["Open Browser"].parameters[0] == ("url", "")
    assert keywords["Open Browser"].parameter_defaults["headless"] == "False"
    assert "Greet someone" in keywords["Hello"].description

    html = DocumentationGenerator(library, RobotFrameworkDocParser()).generate_html()
    assert "Hello" in html
    assert "Open Browser" in html
    assert "headless" in html
    assert 'arg-type">Any</span>' not in html


def test_camel_case_keyword_keeps_robot_framework_name(tmp_path):
    """CamelCase methods must be documented under Robot Framework's keyword name."""
    path = _write(
        tmp_path / "camelib.py",
        '''
from robot.api.deco import keyword
from enum import Enum


class Mode(Enum):
    FAST = "fast"
    SLOW = "slow"


class camelib:
    @keyword
    def openBrowser(self, url: str, mode: Mode = Mode.FAST) -> str:
        """Open a browser."""
        return url
''',
    )

    library = RobotFrameworkDocParser().parse_file(path)
    assert len(library.keywords) == 1
    keyword = library.keywords[0]
    assert keyword.name == "Open Browser"
    assert keyword.parameters[0] == ("url", "str")
    assert "mode" in dict(keyword.parameters)
    assert keyword.parameter_enums["mode"]["members"]
    assert keyword.return_type == "str"


def test_acronym_keyword_name_matches_libdoc(tmp_path):
    """Names like parse_JSON must not abort parsing of the rest of the library."""
    path = _write(
        tmp_path / "jsonlib.py",
        '''
from robot.api.deco import keyword


class jsonlib:
    @keyword
    def parse_JSON(self, text: str) -> dict:
        """Parse a JSON document."""
        return {}

    @keyword
    def simple_keyword(self, name: str):
        """A normal keyword."""
        return name
''',
    )

    library = RobotFrameworkDocParser().parse_file(path)
    names = {kw.name for kw in library.keywords}
    assert names == {"Parse JSON", "Simple Keyword"}
    parsed = next(kw for kw in library.keywords if kw.name == "Parse JSON")
    assert parsed.parameters == [("text", "str")]
    assert parsed.return_type == "dict"
