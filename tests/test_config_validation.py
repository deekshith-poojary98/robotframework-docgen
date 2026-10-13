"""Tests for configuration validation."""

import json
from pathlib import Path

from robotframework_docgen.cli import main as cli_main
from robotframework_docgen.config_validation import (
    validate_multi_lib_config,
    validate_single_lib_config,
)


def _write_resource(tmp_path: Path, name: str = "helpers.resource") -> Path:
    path = tmp_path / name
    path.write_text(
        "*** Keywords ***\n"
        "Hello\n"
        "    [Documentation]    Hi.\n"
        "    No Operation\n"
    )
    return path


def _write_library(tmp_path: Path, name: str = "demo.py") -> Path:
    path = tmp_path / name
    path.write_text(
        "from robot.api.deco import keyword\n\n"
        "class demo:\n"
        "    @keyword\n"
        "    def ping(self):\n"
        "        \"\"\"Ping.\"\"\"\n"
        "        return 'pong'\n"
    )
    return path


def test_valid_multi_lib_config(tmp_path):
    lib = _write_library(tmp_path)
    resource = _write_resource(tmp_path)
    config = {
        "site": {"name": "Demo"},
        "libraries": [{"name": "demo", "source": str(lib)}],
        "resources": [{"name": "helpers", "source": str(resource), "group": "Shared"}],
    }
    assert validate_multi_lib_config(config) == []


def test_missing_source_and_unknown_keys(tmp_path):
    resource = _write_resource(tmp_path)
    config = {
        "site": {"name": "Demo"},
        "resources": [
            {"name": "helpers", "soruce": str(resource)},
            {"name": "helpers", "source": str(resource), "output_format": "pdf"},
        ],
        "extra": True,
    }
    errors = validate_multi_lib_config(config)
    joined = "\n".join(errors)
    assert "Unknown top-level key(s): 'extra'" in joined
    assert "unknown key(s): 'soruce'" in joined
    assert "'source' is required" in joined
    assert "duplicate name 'helpers'" in joined
    assert "'output_format' must be one of" in joined


def test_extension_mismatch(tmp_path):
    lib = _write_library(tmp_path)
    resource = _write_resource(tmp_path)
    config = {
        "site": {"name": "Demo"},
        "libraries": [{"name": "wrong", "source": str(resource)}],
        "resources": [{"name": "also-wrong", "source": str(lib)}],
    }
    errors = validate_multi_lib_config(config)
    joined = "\n".join(errors)
    assert "libraries entries must use a Python source" in joined
    assert "resources entries must use a Robot source" in joined


def test_missing_source_file(tmp_path):
    config = {
        "site": {"name": "Demo"},
        "resources": [{"name": "missing", "source": str(tmp_path / "nope.resource")}],
    }
    errors = validate_multi_lib_config(config)
    assert any("does not exist" in error for error in errors)


def test_non_dict_entry(tmp_path):
    resource = _write_resource(tmp_path)
    config = {
        "site": {"name": "Demo"},
        "resources": [str(resource), {"name": "ok", "source": str(resource)}],
    }
    errors = validate_multi_lib_config(config)
    assert any("must be an object" in error for error in errors)


def test_examples_from_tests_path_validation(tmp_path):
    resource = _write_resource(tmp_path)
    config = {
        "site": {"name": "Demo"},
        "resources": [{"name": "helpers", "source": str(resource)}],
        "examples_from_tests": [str(tmp_path / "missing_tests")],
    }
    errors = validate_multi_lib_config(config)
    assert any("examples_from_tests path does not exist" in error for error in errors)


def test_single_lib_unknown_keys():
    errors = validate_single_lib_config({"libraries": [], "author": "A"})
    assert any("Unknown top-level key(s)" in error for error in errors)


def test_cli_rejects_invalid_config(tmp_path):
    config_path = tmp_path / "bad.json"
    config_path.write_text(
        json.dumps(
            {
                "site": {"name": "Demo"},
                "resources": [{"name": "x", "source": str(tmp_path / "missing.resource")}],
            }
        )
    )
    code = cli_main(["-c", str(config_path), "--multi-lib", "-d", str(tmp_path / "out")])
    assert code == 1


def test_cli_accepts_valid_split_config(tmp_path):
    lib = _write_library(tmp_path, "mylib.py")
    # class name must match module for libdoc auto discovery
    lib.write_text(
        "from robot.api.deco import keyword\n\n"
        "class mylib:\n"
        "    @keyword\n"
        "    def ping(self):\n"
        "        \"\"\"Ping.\"\"\"\n"
        "        return 'pong'\n"
    )
    resource = _write_resource(tmp_path)
    config_path = tmp_path / "good.json"
    config_path.write_text(
        json.dumps(
            {
                "site": {"name": "Demo", "description": "Demo"},
                "libraries": [{"name": "mylib", "source": str(lib)}],
                "resources": [{"name": "helpers", "source": str(resource)}],
            }
        )
    )
    out = tmp_path / "docs"
    code = cli_main(["-c", str(config_path), "--multi-lib", "-d", str(out)])
    assert code == 0
    assert (out / "helpers" / "index.html").exists()


def test_existing_sample_multi_lib_config_is_valid():
    root = Path(__file__).resolve().parent.parent
    config = json.loads(
        (root / "sample_configs" / "lib" / "multi_lib_config.json").read_text(
            encoding="utf-8"
        )
    )
    # Resolve relative sources from repo root
    for entry in config.get("libraries", []):
        entry["source"] = str(root / entry["source"])
    errors = validate_multi_lib_config(config)
    assert errors == []
