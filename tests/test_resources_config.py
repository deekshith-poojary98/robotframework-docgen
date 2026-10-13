"""Tests for libraries vs resources config sections."""

from robotframework_docgen.cli import (
    get_documentation_entries,
    has_single_library_forbidden_keys,
    is_multi_library_mode,
    main as cli_main,
)


def test_get_documentation_entries_merges_libraries_and_resources():
    config = {
        "libraries": [
            {"name": "PyLib", "source": "lib.py"},
        ],
        "resources": [
            {"name": "Helpers", "source": "helpers.resource", "group": "API"},
            {"name": "LoginPage", "source": "login_page.robot"},
        ],
    }
    entries = get_documentation_entries(config)
    assert len(entries) == 3
    kinds = [e["_entry_kind"] for e in entries]
    assert kinds == ["library", "resource", "resource"]
    assert entries[1]["group"] == "API"
    # Default group applied when missing on resources
    assert entries[2]["group"] == "Resources"


def test_resources_only_config_is_multi_library_mode():
    config = {
        "site": {"name": "Demo"},
        "resources": [{"name": "Helpers", "source": "helpers.resource"}],
    }
    assert is_multi_library_mode(config) is True
    assert len(get_documentation_entries(config)) == 1


def test_empty_libraries_with_resources_still_works():
    config = {
        "libraries": [],
        "resources": [{"name": "Helpers", "source": "helpers.resource"}],
    }
    entries = get_documentation_entries(config)
    assert len(entries) == 1
    assert entries[0]["_entry_kind"] == "resource"


def test_single_library_mode_forbids_resources_key():
    has_forbidden, keys = has_single_library_forbidden_keys(
        {"resources": [{"source": "a.resource"}]}
    )
    assert has_forbidden is True
    assert "resources" in keys


def test_cli_accepts_resources_section(tmp_path):
    resource = tmp_path / "helpers.resource"
    resource.write_text(
        "*** Keywords ***\n"
        "Say Hello\n"
        "    [Documentation]    Greet someone.\n"
        "    [Arguments]    ${name}\n"
        "    No Operation\n"
    )
    config = tmp_path / "config.json"
    config.write_text(
        """
{
  "site": {"name": "Demo", "description": "Demo site"},
  "libraries": [],
  "resources": [
    {
      "name": "helpers",
      "source": "%s",
      "group": "Shared",
      "output_file": "index.html"
    }
  ]
}
"""
        % str(resource).replace("\\", "/")
    )
    out_dir = tmp_path / "docs"
    code = cli_main(
        ["-c", str(config), "--multi-lib", "-d", str(out_dir)]
    )
    assert code == 0
    assert (out_dir / "helpers" / "index.html").exists()
    html = (out_dir / "helpers" / "index.html").read_text(encoding="utf-8")
    assert "Say Hello" in html
