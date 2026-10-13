"""Tests for machine-readable catalog export."""

import json
from pathlib import Path

from robotframework_docgen.catalog import (
    CatalogBundle,
    load_catalog_bundle,
    parse_source_to_catalog,
)
from robotframework_docgen.cli import main as cli_main


FIXTURES = Path(__file__).resolve().parent.parent / "sample_libs"


def test_parse_source_to_catalog_python_library():
    catalog = parse_source_to_catalog(FIXTURES / "string_utils.py")
    assert catalog.source_type == "LIBRARY"
    assert catalog.keywords
    assert all(kw.name for kw in catalog.keywords)
    # At least one keyword should expose typed parameters.
    assert any(param.type != "Any" for kw in catalog.keywords for param in kw.parameters)


def test_parse_source_to_catalog_resource_file():
    catalog = parse_source_to_catalog(FIXTURES / "http_helpers.resource")
    assert catalog.source_type == "RESOURCE"
    names = {kw.name for kw in catalog.keywords}
    assert "Get Json Value" in names
    get_json = next(kw for kw in catalog.keywords if kw.name == "Get Json Value")
    assert any(param.name == "default" and param.default == "${NONE}" for param in get_json.parameters)


def test_catalog_json_roundtrip(tmp_path):
    bundle = load_catalog_bundle(FIXTURES / "http_helpers.resource", label="helpers")
    out = tmp_path / "catalog.json"
    bundle.write_json(out)

    loaded = CatalogBundle.from_json_file(out)
    assert loaded.label == "helpers"
    assert len(loaded.libraries) == 1
    assert loaded.libraries[0].name == bundle.libraries[0].name
    assert len(loaded.libraries[0].keywords) == len(bundle.libraries[0].keywords)


def test_cli_catalog_export(tmp_path):
    out = tmp_path / "out" / "catalog.json"
    code = cli_main(["catalog", str(FIXTURES / "auth_suite.robot"), "-o", str(out)])
    assert code == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "libraries" in payload
    assert payload["libraries"][0]["source_type"] == "SUITE"
    keyword_names = {kw["name"] for kw in payload["libraries"][0]["keywords"]}
    assert "Login User" in keyword_names
    assert "Logout User" in keyword_names


def test_cli_generate_with_export_catalog(tmp_path):
    html = tmp_path / "docs.html"
    catalog = tmp_path / "catalog.json"
    code = cli_main(
        [
            str(FIXTURES / "http_helpers.resource"),
            "-o",
            str(html),
            "--export-catalog",
            str(catalog),
        ]
    )
    assert code == 0
    assert html.exists()
    assert catalog.exists()
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    assert payload["libraries"][0]["keywords"]


def test_catalog_shape_has_keyword_metadata_fields(tmp_path):
    out = tmp_path / "catalog.json"
    assert cli_main(["catalog", str(FIXTURES / "string_utils.py"), "-o", str(out)]) == 0
    library = json.loads(out.read_text(encoding="utf-8"))["libraries"][0]
    keyword = library["keywords"][0]
    assert set(keyword) >= {
        "name",
        "parameters",
        "return_type",
        "description",
        "line_number",
        "has_documentation",
    }
    if keyword["parameters"]:
        assert set(keyword["parameters"][0]) >= {"name", "type", "default", "enum_members"}
