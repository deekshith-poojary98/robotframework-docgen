"""Tests for documentation coverage reporting."""

import json
from pathlib import Path

from robotframework_docgen.catalog import (
    CatalogBundle,
    KeywordMetadata,
    LibraryCatalog,
    ParameterMetadata,
)
from robotframework_docgen.cli import main as cli_main
from robotframework_docgen.coverage import analyze_catalog, coverage_for_path


def test_coverage_detects_missing_docs_and_types():
    bundle = CatalogBundle(
        label="demo",
        libraries=[
            LibraryCatalog(
                name="Demo",
                source_type="LIBRARY",
                keywords=[
                    KeywordMetadata(
                        name="Good Keyword",
                        description="Does something with `value`.",
                        parameters=[
                            ParameterMetadata(name="value", type="str"),
                        ],
                        has_documentation=True,
                    ),
                    KeywordMetadata(
                        name="Bad Keyword",
                        description="",
                        parameters=[
                            ParameterMetadata(name="data", type="Any"),
                        ],
                        has_documentation=False,
                    ),
                    KeywordMetadata(
                        name="Partial Docs",
                        description="Processes input without naming args.",
                        parameters=[
                            ParameterMetadata(name="payload", type="dict"),
                        ],
                        has_documentation=True,
                    ),
                ],
            )
        ],
    )

    report = analyze_catalog(bundle)
    assert report.keyword_count == 3
    assert report.undocumented_keywords == 1
    assert report.documentation_coverage == 66.67
    assert report.untyped_parameters == 1

    issue_types = {issue.issue_type for issue in report.issues}
    assert "missing_doc" in issue_types
    assert "undeclared_type" in issue_types
    assert "missing_arg_doc" in issue_types


def test_resource_coverage_skips_type_and_arg_doc_checks():
    bundle = CatalogBundle(
        label="resources",
        libraries=[
            LibraryCatalog(
                name="helpers",
                source_type="RESOURCE",
                keywords=[
                    KeywordMetadata(
                        name="Get Value",
                        description="Return a value.",
                        parameters=[ParameterMetadata(name="key", type="Any")],
                        has_documentation=True,
                    ),
                    KeywordMetadata(
                        name="Silent",
                        description="",
                        parameters=[ParameterMetadata(name="x", type="Any")],
                        has_documentation=False,
                    ),
                ],
            )
        ],
    )

    report = analyze_catalog(bundle)
    issue_types = {issue.issue_type for issue in report.issues}
    assert issue_types == {"missing_doc"}
    assert report.untyped_parameters == 0


def test_coverage_for_real_resource_file():
    path = Path(__file__).resolve().parent.parent / "sample_libs" / "http_helpers.resource"
    report = coverage_for_path(str(path))
    assert report.keyword_count >= 3
    # Undocumented Keyword should be flagged.
    assert any(
        issue.issue_type == "missing_doc" and issue.keyword == "Undocumented Keyword"
        for issue in report.issues
    )


def test_cli_coverage_fail_under(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "label": "demo",
                "libraries": [
                    {
                        "name": "Demo",
                        "source_type": "LIBRARY",
                        "keywords": [
                            {
                                "name": "A",
                                "description": "documented",
                                "has_documentation": True,
                                "parameters": [],
                                "return_type": "None",
                            },
                            {
                                "name": "B",
                                "description": "",
                                "has_documentation": False,
                                "parameters": [],
                                "return_type": "None",
                            },
                        ],
                    }
                ],
            }
        )
    )
    out = tmp_path / "coverage.json"
    code = cli_main(
        [
            "coverage",
            str(catalog),
            "-f",
            "json",
            "-o",
            str(out),
            "--fail-under",
            "90",
        ]
    )
    assert code == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["documentation_coverage"] == 50.0


def test_perfect_coverage_report_text():
    bundle = CatalogBundle(
        label="perfect",
        libraries=[
            LibraryCatalog(
                name="Demo",
                source_type="LIBRARY",
                keywords=[
                    KeywordMetadata(
                        name="Ping",
                        description="Ping `host`.",
                        parameters=[ParameterMetadata(name="host", type="str")],
                        has_documentation=True,
                    )
                ],
            )
        ],
    )
    report = analyze_catalog(bundle)
    assert report.documentation_coverage == 100.0
    assert report.type_coverage == 100.0
    assert "No coverage issues found" in report.to_text()
    assert "Summary" in report.to_markdown()
