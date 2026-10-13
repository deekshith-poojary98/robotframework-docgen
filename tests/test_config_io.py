"""JSON/YAML config loading."""

import json
from pathlib import Path

import pytest

from robotframework_docgen.cli import load_config
from robotframework_docgen.config_io import load_mapping_file
from robotframework_docgen.theme import resolve_theme_tokens


def test_load_json_and_yaml_equivalent(tmp_path: Path):
    payload = {
        "author": "Ada",
        "theme": {"accent": "#22c55e"},
        "examples_from_tests": ["tests"],
    }
    json_path = tmp_path / "cfg.json"
    yaml_path = tmp_path / "cfg.yaml"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    yaml_path.write_text(
        "author: Ada\n"
        "theme:\n"
        "  accent: '#22c55e'\n"
        "examples_from_tests:\n"
        "  - tests\n",
        encoding="utf-8",
    )

    from_json = load_mapping_file(json_path)
    from_yaml = load_mapping_file(yaml_path)
    assert from_json == payload
    assert from_yaml == payload


def test_load_config_sets_config_dir(tmp_path: Path):
    path = tmp_path / "docgen.yml"
    path.write_text("author: Ada\n", encoding="utf-8")
    config = load_config(str(path))
    assert config["author"] == "Ada"
    assert config["_config_dir"] == str(tmp_path.resolve())


def test_unsupported_extension(tmp_path: Path):
    path = tmp_path / "cfg.toml"
    path.write_text("author = 'Ada'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported config format"):
        load_mapping_file(path)


def test_invalid_yaml(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("author: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_mapping_file(path)


def test_theme_file_yaml(tmp_path: Path):
    theme = tmp_path / "brand.yml"
    theme.write_text("accent: '#ef4444'\ntext: '#111827'\n", encoding="utf-8")
    tokens = resolve_theme_tokens(
        {"theme_file": "brand.yml", "_config_dir": str(tmp_path)}
    )
    assert tokens["--accent"] == "#ef4444"
    assert tokens["--text"] == "#111827"


def test_cli_accepts_yaml_multi_lib_config(tmp_path: Path):
    from robotframework_docgen.cli import main as cli_main

    lib = tmp_path / "mylib.py"
    lib.write_text(
        "from robot.api.deco import keyword\n\n"
        "class mylib:\n"
        "    @keyword\n"
        "    def ping(self):\n"
        "        \"\"\"Ping.\"\"\"\n"
        "        return 'pong'\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "good.yaml"
    config_path.write_text(
        "site:\n"
        "  name: Demo\n"
        "libraries:\n"
        f"  - name: mylib\n"
        f"    source: {lib}\n",
        encoding="utf-8",
    )
    out = tmp_path / "docs"
    assert cli_main(["-c", str(config_path), "--multi-lib", "-d", str(out)]) == 0
    assert (out / "mylib" / "index.html").exists()
