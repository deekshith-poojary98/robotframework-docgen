"""Regression tests for library intro Markdown and fenced-code soft-wrapping."""

import re
from pathlib import Path

from robotframework_docgen.cli import generate_single_library
from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.parser import KeywordInfo, LibraryInfo, RobotFrameworkDocParser


def _plain(html: str) -> str:
    """Strip tags so assertions target rendered text, not highlighter spans."""
    return re.sub(r"<[^>]+>", "", html or "")


MARKDOWN_INTRO = '''\
Robot Framework library for deterministic time control.

`TimeTravel` uses [time-machine](https://example.com/time-machine)
to manipulate Python-level time APIs.

This library does **not** change remote services.

Examples:

```robotframework
*** Settings ***
Library    TimeTravel

*** Test Cases ***
OTP Expires After Five Minutes
    Freeze Time       2026-01-01T10:00:00+00:00
    Advance Time      5 minutes
```
'''


def _dynamic_library_source(class_name: str = "DynamicLib") -> str:
    # Triple-quoted class docstring embeds Markdown intro + a fenced RF example.
    return f'''\
class {class_name}:
    """Library intro with **bold** text and a link to [docs](https://example.com).

Also supports:

- item one
- item two

Examples:

```robotframework
*** Test Cases ***
Demo
    Do Thing    value
```
"""
    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "1.2.3"
    ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"

    def get_keyword_names(self):
        return ["Do Thing"]

    def run_keyword(self, name, args, kwargs):
        return None

    def get_keyword_arguments(self, name):
        return ["value"]

    def get_keyword_documentation(self, name):
        if name == "__intro__":
            return self.__class__.__doc__
        return """Do a thing with ``value``.

Examples:

```robotframework
*** Test Cases ***
Demo
    Do Thing    hello
    Do Thing    world
```
"""
'''


class TestJoinSoftWrappedLines:
    def test_joins_soft_wrapped_prose(self):
        parser = RobotFrameworkDocParser()
        joined = parser._join_soft_wrapped_lines(
            "Naive values are interpreted in\n"
            "the timezone configured by Set Timezone.\n"
        )
        assert joined == (
            "Naive values are interpreted in the timezone configured by Set Timezone."
        )

    def test_inserts_blank_line_before_table_after_heading(self):
        parser = RobotFrameworkDocParser()
        joined = parser._join_soft_wrapped_lines(
            "**Schema Format:**\n"
            "| Field | Type |\n"
            "|-------|------|\n"
            "| name | str |\n"
        )
        assert "**Schema Format:**\n\n| Field | Type |" in joined
        assert "| name | str |" in joined
        # Consecutive table rows stay tight (no blank between rows).
        assert "| Field | Type |\n|-------|------|\n| name | str |" in joined

    def test_inserts_blank_line_before_list_after_heading(self):
        parser = RobotFrameworkDocParser()
        joined = parser._join_soft_wrapped_lines(
            "**Arguments:**\n"
            "- `json_data`: payload\n"
            "- `schema`: expected shape\n"
        )
        assert "**Arguments:**\n\n- `json_data`: payload\n- `schema`: expected shape" in joined

    def test_bold_heading_is_not_treated_as_list_marker(self):
        parser = RobotFrameworkDocParser()
        joined = parser._join_soft_wrapped_lines(
            "**See also:**\n"
            "more prose on the next\n"
            "soft-wrapped line.\n"
        )
        assert joined == (
            "**See also:** more prose on the next soft-wrapped line."
        )

    def test_parse_docstring_renders_markdown_tables_and_lists(self):
        parser = RobotFrameworkDocParser()
        html, _ = parser._parse_docstring(
            """\
**Schema Format:**
| Field | Type | Description |
|-------|------|-------------|
| name | str | Expected type |

**Supported Conditions:**
- `equals` — Exact match
- `contains` — Substring search
"""
        )
        assert "<table>" in html
        assert "<th>Field</th>" in html
        assert "<td>name</td>" in html
        assert "<ul>" in html
        assert "<li><code>equals</code>" in html
        assert "| Field |" not in html

    def test_nested_lists_preserve_indent(self):
        parser = RobotFrameworkDocParser()
        # Python-Markdown needs 4-space indent for nesting; soft-wrap must keep it.
        html, _ = parser._parse_docstring(
            """\
- parent
    - child one
    - child two
- sibling
"""
        )
        assert html.count("<ul>") >= 2
        assert "<li>child one</li>" in html
        assert "<li>sibling</li>" in html

    def test_bold_not_eaten_by_code_fixup(self):
        parser = RobotFrameworkDocParser()
        html, _ = parser._parse_docstring(
            "use ``${variable}``, keep *emphasis*, and prefer **strong** labels."
        )
        assert "<strong>strong</strong>" in html
        assert "``strong**" not in html

    def test_underscores_in_image_urls_not_wrapped(self):
        parser = RobotFrameworkDocParser()
        html, _ = parser._parse_docstring(
            "![logo](https://example.com/img/rf_favicon.png)"
        )
        assert 'src="https://example.com/img/rf_favicon.png"' in html
        assert "<code>rf_favicon</code>" not in html

    def test_preserves_fenced_robot_lines_and_indent(self):
        parser = RobotFrameworkDocParser()
        source = """\
Freeze perceived time at ``at``.

Examples:

```robotframework
*** Settings ***
Library    TimeTravel

*** Test Cases ***
Example
    Freeze Time    2026-01-01T10:00:00+00:00
    Freeze Time    2026-01-01T10:00:00
```
"""
        joined = parser._join_soft_wrapped_lines(source)
        assert "```robotframework" in joined
        assert "    Freeze Time    2026-01-01T10:00:00+00:00\n" in joined
        assert "    Freeze Time    2026-01-01T10:00:00\n" in joined
        assert "00:00+00:00 Freeze Time" not in joined

    def test_preserves_blank_lines_inside_fence(self):
        parser = RobotFrameworkDocParser()
        source = """\
Intro line.

```robot
*** Test Cases ***
Demo

    Keyword Call
```
"""
        joined = parser._join_soft_wrapped_lines(source)
        fence_body = joined.split("```robot", 1)[1].rsplit("```", 1)[0]
        assert "\n\n" in fence_body

    def test_multiple_fenced_blocks_and_adjacent_prose(self):
        parser = RobotFrameworkDocParser()
        source = """\
First paragraph
continues here.

```text
line one
line two
```

Middle paragraph
also wraps.

```robotframework
*** Test Cases ***
A
    Call One
```
"""
        joined = parser._join_soft_wrapped_lines(source)
        assert "First paragraph continues here." in joined
        assert "Middle paragraph also wraps." in joined
        assert "line one\nline two" in joined
        assert "    Call One\n" in joined
        assert joined.count("```") == 4

    def test_parse_docstring_keeps_robot_example_structure(self):
        parser = RobotFrameworkDocParser()
        html, _ = parser._parse_docstring(
            """\
Do a thing.

Examples:

```robotframework
*** Test Cases ***
Demo
    Do Thing    hello
    Do Thing    world
```
"""
        )
        plain = _plain(html)
        assert "<p>Do a thing.</p>" in html
        assert "Do Thing    hello" in plain
        assert "Do Thing    world" in plain
        # Joined-line regression: test-case name must not merge into keyword call.
        assert "Demo Do Thing" not in plain
        assert "hello Do Thing" not in plain


class TestRobotFenceHighlighting:
    def test_robotframework_alias_uses_docgen_highlighter(self):
        parser = RobotFrameworkDocParser()
        html = parser._render_code_block(
            "*** Test Cases ***\nDemo\n    Log    hi",
            "robotframework",
        )
        assert 'language-robot"' in html or "language-robot>" in html
        # Custom highlighter classes (not Pygments navy #000080).
        assert 'class="rf-section"' in html
        assert "#000080" not in html

    def test_unknown_example_keywords_highlighted_structurally(self):
        """Call-position cells are highlighted even when not in the library list."""
        parser = RobotFrameworkDocParser()
        html = parser._highlight_robot_framework(
            "*** Test Cases ***\n"
            "Demo\n"
            "    Transform Json Data    ${payload}\n"
            "    Dummy Helper Keyword\n"
            "    ${result}=    Fake Fetch Remote    /v1/items\n"
            "    [Teardown]    Dummy Cleanup\n"
        )
        assert 'class="rf-keyword"' in html
        assert "Transform Json Data" in html
        assert "Dummy Helper Keyword" in html
        assert "Fake Fetch Remote" in html
        assert "Dummy Cleanup" in html
        # Each of those names should be wrapped in the keyword span.
        for name in (
            "Transform Json Data",
            "Dummy Helper Keyword",
            "Fake Fetch Remote",
            "Dummy Cleanup",
        ):
            assert f'<span class="rf-keyword">{name}</span>' in html

    def test_harvested_example_strips_docstring_examples(self):
        info = LibraryInfo(
            name="Demo",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Call Me",
                    description=(
                        "<p>Does a thing.</p>"
                        "<p>Examples:</p>"
                        '<div class="code-block"><pre class="language-robot">'
                        "DOCSTRING EXAMPLE ONLY"
                        "</pre></div>"
                    ),
                    example="*** Test Cases ***\nHarvested\n    Call Me",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                )
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert "kw-example" in html
        assert "Harvested" in html
        assert "<p>Examples:</p>" not in html
        assert "DOCSTRING EXAMPLE ONLY" not in html
        assert "Does a thing." in html

    def test_docstring_examples_promoted_without_harvested(self):
        """Docstring Examples use the same Example section as harvested suites."""
        info = LibraryInfo(
            name="Demo",
            version="1",
            scope="GLOBAL",
            description="",
            keywords=[
                KeywordInfo(
                    name="Call Me",
                    description=(
                        "<p>Does a thing.</p>"
                        "<p>Examples:</p>"
                        '<div class="code-block"><pre class="language-robot">'
                        "DOCSTRING EXAMPLE ONLY"
                        "</pre></div>"
                    ),
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                )
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert "DOCSTRING EXAMPLE ONLY" in html
        assert "kw-example" in html
        assert "<h3>Example</h3>" in html
        assert "<p>Examples:</p>" not in html
        assert "Does a thing." in html


class TestLibraryIntroductionMarkdown:
    def test_normalize_renders_markdown_constructs(self):
        parser = RobotFrameworkDocParser()
        html = parser._normalize_library_description(MARKDOWN_INTRO)

        assert "<p>" in html
        assert "<strong>not</strong>" in html
        assert 'href="https://example.com/time-machine"' in html
        assert "<code>TimeTravel</code>" in html
        assert "```" not in html
        assert "Freeze Time" in html
        assert "Advance Time" in html
        assert "00:00+00:00 Advance Time" not in html

    def test_normalize_skips_already_rendered_html(self):
        parser = RobotFrameworkDocParser()
        original = "<p>Already rendered <code>HTML</code>.</p>"
        assert parser._normalize_library_description(original) == original

    def test_ast_fallback_renders_intro_lists_and_keyword_tables(self):
        """sample_libs/data_processor.py often hits AST when Libdoc finds 0 kws."""
        info = RobotFrameworkDocParser().parse_file("sample_libs/data_processor.py")
        assert "<ul>" in info.description
        assert "<li>Data validation and transformation</li>" in info.description
        assert "- Data validation" not in info.description

        kw = next(k for k in info.keywords if "Validate Json" in k.name)
        assert "<table>" in kw.description
        assert "<th>Field</th>" in kw.description
        assert "| Field |" not in kw.description


    def test_python_libdoc_path_renders_library_intro(self, tmp_path):
        path = tmp_path / "DynamicLib.py"
        path.write_text(_dynamic_library_source())

        info = RobotFrameworkDocParser().parse_file(str(path))
        assert len(info.keywords) == 1
        assert "<p>" in info.description
        assert "<strong>bold</strong>" in info.description
        assert 'href="https://example.com"' in info.description
        assert "<li>" in info.description
        assert "```" not in info.description
        intro_plain = _plain(info.description)
        assert "Do Thing    value" in intro_plain
        assert "Demo Do Thing" not in intro_plain
        # Library keywords in intro fences are identified (Libdoc-style nf parity).
        assert 'class="rf-keyword"' in info.description
        assert "Do Thing" in info.description

        html = DocumentationGenerator(
            info, RobotFrameworkDocParser(), config={}
        ).generate_html()
        assert 'class="intro-content"' in html
        assert "<strong>bold</strong>" in html
        assert "&lt;p&gt;" not in html
        assert "Do Thing    value" in _plain(html)

    def test_keyword_docs_still_render_after_fence_fix(self, tmp_path):
        path = tmp_path / "DynamicLib.py"
        path.write_text(_dynamic_library_source())

        info = RobotFrameworkDocParser().parse_file(str(path))
        keyword = info.keywords[0]
        plain = _plain(keyword.description)
        assert "<p>Do a thing" in keyword.description
        assert 'class="rf-keyword"' in keyword.description
        assert "Do Thing    hello" in plain
        assert "Do Thing    world" in plain
        assert "hello Do Thing" not in plain

    def test_generator_intro_still_accepts_prebuilt_html(self):
        info = LibraryInfo(
            name="DocLib",
            version="1.0.0",
            scope="GLOBAL",
            description="<p>Page object for login.</p>",
            keywords=[
                KeywordInfo(
                    name="Open",
                    description="<p>Opens</p>",
                    example="",
                    parameters=[],
                    return_type="None",
                    line_number=1,
                )
            ],
        )
        html = DocumentationGenerator(info).generate_html()
        assert '<div class="intro-content"><p>Page object for login.</p>' in html
        assert "&lt;p&gt;" not in html


class TestDynamicLibraryCliEntry:
    def test_cli_discovers_dynamic_keywords(self, tmp_path):
        library = tmp_path / "DynamicLib.py"
        library.write_text(_dynamic_library_source())
        output = tmp_path / "docs.html"

        success, path, count, _ = generate_single_library(
            input_file=str(library),
            output_file=str(output),
            output_format="html",
            config={"author": "Audit Bot", "license": "Apache-2.0"},
        )

        assert success is True
        assert count == 1
        content = Path(path).read_text(encoding="utf-8")
        plain = _plain(content)
        assert "Do Thing" in content
        assert "<strong>bold</strong>" in content
        assert "Author:" in content
        assert "Apache-2.0" in content
        assert "Do Thing    value" in plain

    def test_unimportable_composed_library_records_libdoc_error(self, tmp_path):
        """When Libdoc cannot import a library, expose the import error for CLI hints."""
        path = tmp_path / "BrokenLib.py"
        path.write_text(
            """
import definitely_missing_dependency_xyz  # noqa: F401

class BrokenLib:
    ROBOT_AUTO_KEYWORDS = False

    def __init__(self):
        pass
"""
        )
        parser = RobotFrameworkDocParser()
        info = parser.parse_file(str(path))
        assert info.keywords == []
        assert parser._last_libdoc_error
        assert "definitely_missing_dependency_xyz" in parser._last_libdoc_error
