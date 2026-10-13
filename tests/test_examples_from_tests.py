"""Tests for harvesting keyword examples from Robot Framework suites."""

from pathlib import Path

from robotframework_docgen.cli import generate_single_library, main as cli_main
from robotframework_docgen.examples import (
    attach_examples_to_library,
    collect_examples_from_tests,
    normalize_keyword_name,
)
from robotframework_docgen.parser import RobotFrameworkDocParser


FIXTURES = Path(__file__).resolve().parent.parent / "sample_libs"
SUITE = FIXTURES / "tests" / "http_helpers_tests.robot"


def test_normalize_keyword_name():
    assert normalize_keyword_name("Get  Json Value") == "get json value"
    assert normalize_keyword_name("GET JSON VALUE") == "get json value"


def test_collect_examples_from_sample_suite():
    examples = collect_examples_from_tests(
        [SUITE],
        keyword_names=["Get Json Value", "Create Session Headers"],
    )
    assert "Get Json Value" in examples
    assert "Create Session Headers" in examples

    get_json = examples["Get Json Value"][0]
    assert get_json.test_name == "Extract Nested Value"
    assert "nested" in get_json.documentation.lower() or "dictionary" in get_json.documentation.lower()
    assert "*** Test Cases ***" in get_json.snippet
    assert "Get Json Value" in get_json.snippet
    assert "Extract Nested Value" in get_json.snippet


def test_attach_examples_to_resource_library():
    library = RobotFrameworkDocParser().parse_file(str(FIXTURES / "http_helpers.resource"))
    updated = attach_examples_to_library(library, [SUITE])
    assert updated >= 2

    get_json = next(kw for kw in library.keywords if kw.name == "Get Json Value")
    assert get_json.example
    assert "Get Json Value" in get_json.example
    assert "Extract Nested Value" in get_json.example


def test_does_not_overwrite_existing_example_by_default(tmp_path):
    library = RobotFrameworkDocParser().parse_file(str(FIXTURES / "http_helpers.resource"))
    target = next(kw for kw in library.keywords if kw.name == "Get Json Value")
    target.example = "existing example"
    updated = attach_examples_to_library(library, [SUITE], overwrite_existing=False)
    assert target.example == "existing example"
    # Other keywords may still be updated.
    assert updated >= 0


def test_ignores_keywords_not_called_in_suites(tmp_path):
    suite = tmp_path / "suite.robot"
    suite.write_text(
        "*** Test Cases ***\n"
        "Only Headers\n"
        "    Create Session Headers    token=abc\n"
    )
    examples = collect_examples_from_tests(
        [suite],
        keyword_names=["Get Json Value", "Create Session Headers"],
    )
    assert "Create Session Headers" in examples
    assert "Get Json Value" not in examples


def test_generate_html_includes_harvested_example(tmp_path):
    output = tmp_path / "http_helpers.html"
    success, _, _, _ = generate_single_library(
        input_file=str(FIXTURES / "http_helpers.resource"),
        output_file=str(output),
        output_format="html",
        config={},
        examples_from=[str(SUITE)],
    )
    assert success
    html = output.read_text(encoding="utf-8")
    assert "Example" in html
    assert "Get Json Value" in html
    assert "Extract Nested Value" in html


def test_cli_examples_from_flag(tmp_path):
    output = tmp_path / "out.html"
    code = cli_main(
        [
            str(FIXTURES / "http_helpers.resource"),
            "-o",
            str(output),
            "--examples-from",
            str(SUITE),
        ]
    )
    assert code == 0
    content = output.read_text(encoding="utf-8")
    assert "Create Session Headers" in content
    assert "Build Authorization Headers" in content or "secret-token" in content


def test_config_examples_from_tests(tmp_path):
    output = tmp_path / "out.md"
    success, _, _, _ = generate_single_library(
        input_file=str(FIXTURES / "http_helpers.resource"),
        output_file=str(output),
        output_format="markdown",
        config={"examples_from_tests": [str(SUITE)]},
    )
    assert success
    markdown = output.read_text(encoding="utf-8")
    assert "**Example:**" in markdown
    assert "Get Json Value" in markdown
