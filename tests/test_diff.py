"""Tests for keyword changelog / catalog diff."""

import json
from pathlib import Path

from robotframework_docgen.catalog import (
    CatalogBundle,
    KeywordMetadata,
    LibraryCatalog,
    ParameterMetadata,
    load_catalog_bundle,
    parse_source_to_catalog,
)
from robotframework_docgen.cli import main as cli_main
from robotframework_docgen.diff import compare_keywords, diff_catalogs, diff_paths


def _catalog(name: str, keywords):
    return LibraryCatalog(name=name, keywords=list(keywords))


def test_compare_keywords_detects_signature_changes():
    old = KeywordMetadata(
        name="Open Browser",
        parameters=[
            ParameterMetadata(name="url", type="str"),
            ParameterMetadata(name="headless", type="bool", default="False"),
        ],
        return_type="None",
    )
    new = KeywordMetadata(
        name="Open Browser",
        parameters=[
            ParameterMetadata(name="url", type="str"),
            ParameterMetadata(name="headless", type="bool", default="True"),
            ParameterMetadata(name="timeout", type="int", default="30"),
        ],
        return_type="Browser",
        description="Open a browser window.",
    )

    change = compare_keywords(old, new)
    assert change is not None
    assert change.change_type == "changed"
    assert "parameters" in change.field_changes
    assert "return_type" in change.field_changes
    assert "documentation" in change.field_changes


def test_diff_catalogs_reports_added_removed_changed():
    old = CatalogBundle(
        label="v1",
        libraries=[
            _catalog(
                "Auth",
                [
                    KeywordMetadata(
                        name="Login",
                        parameters=[ParameterMetadata(name="user", type="str")],
                    ),
                    KeywordMetadata(name="Logout"),
                ],
            ),
            _catalog("Legacy", [KeywordMetadata(name="Old Keyword")]),
        ],
    )
    new = CatalogBundle(
        label="v2",
        libraries=[
            _catalog(
                "Auth",
                [
                    KeywordMetadata(
                        name="Login",
                        parameters=[
                            ParameterMetadata(name="user", type="str"),
                            ParameterMetadata(name="password", type="str"),
                        ],
                    ),
                    KeywordMetadata(name="Reset Password"),
                ],
            ),
            _catalog("Payments", [KeywordMetadata(name="Charge")]),
        ],
    )

    report = diff_catalogs(old, new)
    assert report.has_changes
    counts = report.summary_counts()
    assert counts["libraries_added"] == 1
    assert counts["libraries_removed"] == 1
    assert counts["keywords_added"] >= 2  # Reset Password + Charge (+ library adds)
    assert counts["keywords_removed"] >= 2  # Logout + Old Keyword
    assert counts["keywords_changed"] == 1

    text = report.to_text()
    assert "Login" in text
    assert "Reset Password" in text or "+ Reset Password" in text

    markdown = report.to_markdown()
    assert "## Auth" in markdown
    assert "### Changed" in markdown

    payload = report.to_dict()
    assert payload["summary"]["keywords_changed"] == 1


def test_diff_identical_catalogs_has_no_changes():
    bundle = CatalogBundle(
        label="same",
        libraries=[
            _catalog(
                "Lib",
                [
                    KeywordMetadata(
                        name="Ping",
                        parameters=[ParameterMetadata(name="host", type="str")],
                        return_type="bool",
                    )
                ],
            )
        ],
    )
    report = diff_catalogs(bundle, bundle)
    assert report.has_changes is False
    assert "No keyword signature changes" in report.to_text()


def test_diff_paths_with_source_files(tmp_path):
    old = tmp_path / "old.py"
    new = tmp_path / "new.py"
    old.write_text(
        '''
from robot.api.deco import keyword

class old:
    @keyword
    def greet(self, name: str):
        """Greet someone."""
        return name

    @keyword
    def unused(self):
        """Remove me."""
        pass
'''
    )
    new.write_text(
        '''
from robot.api.deco import keyword

class new:
    ROBOT_LIBRARY_VERSION = "2.0.0"

    @keyword
    def greet(self, name: str, excited: bool = False) -> str:
        """Greet someone loudly optionally."""
        return name

    @keyword
    def farewell(self, name: str):
        """Say goodbye."""
        return name
'''
    )

    # Force matching library names via catalogs built from files after renaming
    old_catalog = parse_source_to_catalog(old)
    new_catalog = parse_source_to_catalog(new)
    old_catalog.name = "Demo"
    new_catalog.name = "Demo"

    report = diff_catalogs(
        CatalogBundle(libraries=[old_catalog], label="v1"),
        CatalogBundle(libraries=[new_catalog], label="v2"),
    )
    names = {
        change.name: change.change_type
        for lib in report.libraries
        for change in lib.keyword_changes
    }
    assert names["Unused"] == "removed"
    assert names["Farewell"] == "added"
    assert names["Greet"] == "changed"


def test_load_catalog_from_json_and_diff(tmp_path):
    old_json = tmp_path / "old.json"
    new_json = tmp_path / "new.json"
    old_json.write_text(
        json.dumps(
            {
                "label": "v1",
                "libraries": [
                    {
                        "name": "Demo",
                        "keywords": [
                            {
                                "name": "Hello",
                                "parameters": [{"name": "name", "type": "str"}],
                                "return_type": "None",
                            }
                        ],
                    }
                ],
            }
        )
    )
    new_json.write_text(
        json.dumps(
            {
                "label": "v2",
                "libraries": [
                    {
                        "name": "Demo",
                        "keywords": [
                            {
                                "name": "Hello",
                                "parameters": [
                                    {"name": "name", "type": "str"},
                                    {"name": "title", "type": "str", "default": "Ms"},
                                ],
                                "return_type": "str",
                            }
                        ],
                    }
                ],
            }
        )
    )

    report = diff_paths(str(old_json), str(new_json))
    assert report.summary_counts()["keywords_changed"] == 1


def test_cli_diff_writes_markdown_report(tmp_path):
    old_json = tmp_path / "old.json"
    new_json = tmp_path / "new.json"
    out = tmp_path / "changelog.md"
    old_json.write_text(
        json.dumps(
            {
                "libraries": [
                    {
                        "name": "Demo",
                        "keywords": [{"name": "A", "parameters": [], "return_type": "None"}],
                    }
                ]
            }
        )
    )
    new_json.write_text(
        json.dumps(
            {
                "libraries": [
                    {
                        "name": "Demo",
                        "keywords": [
                            {"name": "A", "parameters": [], "return_type": "None"},
                            {"name": "B", "parameters": [], "return_type": "None"},
                        ],
                    }
                ]
            }
        )
    )

    code = cli_main(
        [
            "diff",
            str(old_json),
            str(new_json),
            "-f",
            "markdown",
            "-o",
            str(out),
            "--old-label",
            "v1",
            "--new-label",
            "v2",
        ]
    )
    assert code == 0
    content = out.read_text(encoding="utf-8")
    assert "Keyword changelog" in content
    assert "B" in content


def test_load_directory_of_sources(tmp_path):
    lib_dir = tmp_path / "libs"
    lib_dir.mkdir()
    (lib_dir / "alpha.resource").write_text(
        "*** Keywords ***\n"
        "Alpha Keyword\n"
        "    [Documentation]    Alpha.\n"
        "    No Operation\n"
    )
    (lib_dir / "beta.resource").write_text(
        "*** Keywords ***\n"
        "Beta Keyword\n"
        "    [Documentation]    Beta.\n"
        "    No Operation\n"
    )

    bundle = load_catalog_bundle(lib_dir, label="libs")
    names = {lib.name for lib in bundle.libraries}
    assert "alpha" in names
    assert "beta" in names
