"""Tests for documenting Robot Framework .resource and .robot keyword files."""

from pathlib import Path

import pytest

from robotframework_docgen.cli import generate_single_library
from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.parser import RobotFrameworkDocParser


FIXTURES = Path(__file__).resolve().parent.parent / "sample_libs"


def test_parse_resource_file_extracts_keywords():
    parser = RobotFrameworkDocParser()
    info = parser.parse_file(str(FIXTURES / "http_helpers.resource"))

    assert info.source_type == "RESOURCE"
    assert info.name == "http_helpers"
    assert info.scope == "GLOBAL"
    assert "Shared HTTP helper" in info.description

    keywords = {kw.name: kw for kw in info.keywords}
    assert "Get Json Value" in keywords
    assert "Create Session Headers" in keywords
    assert "Do Something With" in keywords
    assert "Undocumented Keyword" in keywords

    get_json = keywords["Get Json Value"]
    assert [name for name, _ in get_json.parameters] == ["payload", "key", "default"]
    assert get_json.parameter_defaults["default"] == "${NONE}"
    assert "Extract a value" in get_json.description

    headers = keywords["Create Session Headers"]
    assert headers.parameter_defaults["content_type"] == "application/json"

    variadic = keywords["Do Something With"]
    assert ("*items", "") in variadic.parameters
    assert ("**options", "") in variadic.parameters


def test_parse_robot_suite_extracts_user_keywords():
    parser = RobotFrameworkDocParser()
    info = parser.parse_file(str(FIXTURES / "auth_suite.robot"))

    assert info.source_type == "SUITE"
    names = {kw.name for kw in info.keywords}
    assert names == {"Login User", "Logout User"}

    login = next(kw for kw in info.keywords if kw.name == "Login User")
    assert [name for name, _ in login.parameters] == ["username", "password"]
    assert "Log in with username" in login.description

    logout = next(kw for kw in info.keywords if kw.name == "Logout User")
    assert logout.parameters == []


def test_resource_html_and_markdown_generation(tmp_path):
    parser = RobotFrameworkDocParser()
    info = parser.parse_file(str(FIXTURES / "http_helpers.resource"))
    generator = DocumentationGenerator(
        info, parser, config={"source": "sample_libs/http_helpers.resource"}
    )

    html = generator.generate_html()
    assert "Get Json Value" in html
    assert "Create Session Headers" in html
    assert "default: ${NONE}" in html or "default: application/json" in html
    assert "Version Unknown" not in html
    assert "Resource" in html
    assert "sample_libs/http_helpers.resource" in html
    assert "&lt;p&gt;" not in html
    assert "Shared HTTP helper" in html
    assert "<code>${NONE}</code>" in html or "${NONE}" in html

    markdown = generator.generate_markdown()
    assert "### Get Json Value" in markdown
    assert "`*items`" in markdown or "*items" in markdown
    assert "**Version:**" not in markdown


def test_robot_double_backtick_code_renders_cleanly():
    parser = RobotFrameworkDocParser()
    html, _ = parser._parse_docstring(
        "See ``workflow/login_workflow.robot`` for flows.", {}
    )
    assert "<code>workflow/login_workflow.robot</code>" in html
    assert "`<code>" not in html
    assert "</code>`" not in html


def test_cli_generates_docs_for_resource_file(tmp_path):
    output = tmp_path / "http_helpers.html"
    success, path, count, _ = generate_single_library(
        input_file=str(FIXTURES / "http_helpers.resource"),
        output_file=str(output),
        output_format="html",
        config={},
    )

    assert success is True
    assert count >= 3
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "Get Json Value" in content
    assert "Create Session Headers" in content


def test_embedded_argument_keywords(tmp_path):
    path = tmp_path / "embedded.resource"
    path.write_text(
        "*** Keywords ***\n"
        "Login ${user} with password ${password}\n"
        "    [Documentation]    Login using embedded arguments.\n"
        "    No Operation\n"
    )

    info = RobotFrameworkDocParser().parse_file(str(path))
    assert len(info.keywords) == 1
    keyword = info.keywords[0]
    assert "Login" in keyword.name
    assert "${user}" in keyword.name
    assert "${password}" in keyword.name
    assert "embedded arguments" in keyword.description
    # Embedded args live in the keyword name; Libdoc exposes no [Arguments].
    assert keyword.parameters == []

    html = DocumentationGenerator(info).generate_html()
    anchor = DocumentationGenerator.keyword_anchor_id(keyword.name)
    assert "${" not in anchor
    assert "}" not in anchor
    assert f'id="{anchor}"' in html
    assert f'href="#{anchor}"' in html


def test_keyword_anchor_id_slugifies_embedded_args():
    assert (
        DocumentationGenerator.keyword_anchor_id(
            "Fill ${e_type} email and ${p_type} password"
        )
        == "fill-e_type-email-and-p_type-password"
    )
    assert DocumentationGenerator.keyword_anchor_id("Simple Keyword") == "simple-keyword"


def test_empty_resource_returns_no_keywords(tmp_path):
    path = tmp_path / "empty.resource"
    path.write_text("*** Settings ***\nDocumentation    Empty resource.\n")

    info = RobotFrameworkDocParser().parse_file(str(path))
    assert info.source_type == "RESOURCE"
    assert info.keywords == []


def test_private_keywords_are_skipped(tmp_path):
    path = tmp_path / "private.resource"
    path.write_text(
        "*** Keywords ***\n"
        "Public Keyword\n"
        "    [Documentation]    Visible keyword.\n"
        "    No Operation\n"
        "\n"
        "_Private Helper\n"
        "    [Documentation]    Should be skipped.\n"
        "    No Operation\n"
        "\n"
        "Tagged Private\n"
        "    [Documentation]    Private via tag.\n"
        "    [Tags]    robot:private\n"
        "    No Operation\n"
    )

    info = RobotFrameworkDocParser().parse_file(str(path))
    names = {kw.name for kw in info.keywords}
    assert names == {"Public Keyword"}


def test_invalid_robot_source_raises(tmp_path):
    path = tmp_path / "broken.resource"
    path.write_text("*** Invalid Section ***\nFoo\n")

    with pytest.raises(ValueError, match="Failed to parse Robot Framework source"):
        RobotFrameworkDocParser().parse_file(str(path))


def test_missing_robot_source_raises(tmp_path):
    missing = tmp_path / "missing.resource"
    with pytest.raises(FileNotFoundError):
        RobotFrameworkDocParser().parse_file(str(missing))


def test_is_robot_source_file_detection():
    assert RobotFrameworkDocParser._is_robot_source_file("a.resource")
    assert RobotFrameworkDocParser._is_robot_source_file("a.ROBOT")
    assert RobotFrameworkDocParser._is_robot_source_file("/tmp/x.txt")
    assert not RobotFrameworkDocParser._is_robot_source_file("library.py")
    assert not RobotFrameworkDocParser._is_robot_source_file("notes.md")


def test_python_library_still_parses_after_resource_support():
    info = RobotFrameworkDocParser().parse_file(str(FIXTURES / "string_utils.py"))
    assert info.source_type == "LIBRARY"
    assert len(info.keywords) > 0
