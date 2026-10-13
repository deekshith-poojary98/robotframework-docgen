"""
Load Docgen configuration / theme files from JSON or YAML.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union


JSON_SUFFIXES = {".json"}
YAML_SUFFIXES = {".yaml", ".yml"}
SUPPORTED_CONFIG_SUFFIXES = JSON_SUFFIXES | YAML_SUFFIXES


def _load_yaml(text: str, path: Path) -> Any:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ValueError(
            f"YAML config support requires PyYAML. Install with: pip install pyyaml "
            f"(while loading {path})"
        ) from exc
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file {path}: {exc}") from exc


def load_mapping_file(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a JSON or YAML file that must contain a top-level object/mapping.

    Format is chosen from the file extension (``.json``, ``.yaml``, ``.yml``).
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")

    if suffix in JSON_SUFFIXES:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in config file {file_path}: {exc}") from exc
    elif suffix in YAML_SUFFIXES:
        data = _load_yaml(text, file_path)
    else:
        raise ValueError(
            f"Unsupported config format {suffix!r} for {file_path}. "
            f"Use one of: {', '.join(sorted(SUPPORTED_CONFIG_SUFFIXES))}"
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"Config file must contain a JSON/YAML object: {file_path}"
        )
    return data
