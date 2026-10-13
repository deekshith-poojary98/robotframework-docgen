"""
Configuration validation for robotframework-libdocgen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from robotframework_docgen.theme import validate_theme_config


MULTI_LIB_TOP_LEVEL_KEYS = {
    "site",
    "libraries",
    "resources",
    "examples_from_tests",
    "theme",
    "theme_file",
}

SINGLE_LIB_TOP_LEVEL_KEYS = {
    "name",
    "version",
    "description",
    "github_url",
    "support_email",
    "author",
    "maintainer",
    "license",
    "robot_framework",
    "python",
    "library_url",
    "examples_from_tests",
    "github_branch",
    "github_file",
    "source_links",
    "theme",
    "theme_file",
    "output_file",
    "output_format",
    "group",
}

SITE_KEYS = {
    "name",
    "description",
    "github_url",
    "support_email",
    "author",
    "maintainer",
    "license",
    "robot_framework",
    "python",
    "library_url",
    "github_branch",
    "github_file",
    "source_links",
    "theme",
    "theme_file",
}

ENTRY_KEYS = {
    "name",
    "source",
    "group",
    "description",
    "author",
    "maintainer",
    "license",
    "output_file",
    "output_format",
    "library_url",
    "python",
    "robot_framework",
    "github_url",
    "support_email",
    "version",
    "examples_from_tests",
    "github_branch",
    "github_file",
    "source_links",
    "theme",
    "theme_file",
}

# Set by load_config(); ignored by unknown-key checks.
INTERNAL_KEYS = {"_config_dir"}


LIBRARY_SOURCE_EXTENSIONS = {".py"}
RESOURCE_SOURCE_EXTENSIONS = {".resource", ".robot", ".txt", ".tsv", ".rst", ".rest"}
ALLOWED_OUTPUT_FORMATS = {"html", "markdown"}


def _unknown_keys(data: Dict[str, Any], allowed: set[str]) -> List[str]:
    return sorted(
        key
        for key in data.keys()
        if key not in allowed and key not in INTERNAL_KEYS
    )


def _validate_examples_from_tests(
    value: Any, prefix: str
) -> List[str]:
    errors: List[str] = []
    if value is None:
        return errors
    paths: Sequence[Any]
    if isinstance(value, str):
        paths = [value]
    elif isinstance(value, list):
        paths = value
    else:
        return [f"{prefix}: 'examples_from_tests' must be a string or array of strings"]

    for idx, item in enumerate(paths, start=1):
        label = prefix if isinstance(value, str) else f"{prefix}[{idx}]"
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{label}: examples_from_tests entries must be non-empty strings")
            continue
        path = Path(item)
        if not path.exists():
            errors.append(f"{label}: examples_from_tests path does not exist: {item}")
        elif not (path.is_dir() or path.is_file()):
            errors.append(f"{label}: examples_from_tests path is not a file or directory: {item}")
    return errors


def _validate_source_links(data: Dict[str, Any], prefix: str) -> List[str]:
    if "source_links" not in data:
        return []
    value = data.get("source_links")
    if not isinstance(value, bool):
        return [f"{prefix}: 'source_links' must be a boolean, got {type(value).__name__}"]
    return []


def _validate_entry(
    entry: Any,
    *,
    section: str,
    index: int,
    expected_kind: str,
) -> List[str]:
    label = f"{section}[{index}]"
    errors: List[str] = []

    if not isinstance(entry, dict):
        return [f"{label}: entry must be an object, got {type(entry).__name__}"]

    unknown = _unknown_keys(entry, ENTRY_KEYS)
    if unknown:
        errors.append(
            f"{label}: unknown key(s): {', '.join(repr(k) for k in unknown)}"
        )

    source = entry.get("source")
    if not isinstance(source, str) or not source.strip():
        errors.append(f"{label}: 'source' is required and must be a non-empty string")
        return errors

    source_path = Path(source)
    if not source_path.exists():
        errors.append(f"{label}: source file does not exist: {source}")
    elif not source_path.is_file():
        errors.append(f"{label}: source path is not a file: {source}")
    else:
        suffix = source_path.suffix.lower()
        if expected_kind == "library":
            if suffix not in LIBRARY_SOURCE_EXTENSIONS:
                errors.append(
                    f"{label}: libraries entries must use a Python source "
                    f"({', '.join(sorted(LIBRARY_SOURCE_EXTENSIONS))}), got '{suffix or '(none)'}'"
                )
        else:
            if suffix not in RESOURCE_SOURCE_EXTENSIONS:
                errors.append(
                    f"{label}: resources entries must use a Robot source "
                    f"({', '.join(sorted(RESOURCE_SOURCE_EXTENSIONS))}), got '{suffix or '(none)'}'"
                )

    name = entry.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        errors.append(f"{label}: 'name' must be a non-empty string when provided")

    output_format = entry.get("output_format")
    if output_format is not None:
        if not isinstance(output_format, str) or output_format.lower() not in ALLOWED_OUTPUT_FORMATS:
            errors.append(
                f"{label}: 'output_format' must be one of "
                f"{sorted(ALLOWED_OUTPUT_FORMATS)}, got {output_format!r}"
            )

    if "examples_from_tests" in entry:
        errors.extend(_validate_examples_from_tests(entry.get("examples_from_tests"), label))

    errors.extend(_validate_source_links(entry, label))
    errors.extend(validate_theme_config(entry, label))

    return errors


def validate_multi_lib_config(config: Dict[str, Any]) -> List[str]:
    """Validate a multi-library / dashboard configuration. Returns error messages."""
    errors: List[str] = []

    if not isinstance(config, dict) or not config:
        return ["Config is empty or invalid JSON"]

    unknown_top = _unknown_keys(config, MULTI_LIB_TOP_LEVEL_KEYS)
    if unknown_top:
        errors.append(
            "Unknown top-level key(s): "
            + ", ".join(repr(k) for k in unknown_top)
        )

    site = config.get("site")
    if not isinstance(site, dict):
        errors.append("'site' is required and must be an object")
    else:
        unknown_site = _unknown_keys(site, SITE_KEYS)
        if unknown_site:
            errors.append(
                "Unknown site key(s): "
                + ", ".join(repr(k) for k in unknown_site)
            )
        if "name" in site and (not isinstance(site.get("name"), str) or not site["name"].strip()):
            errors.append("site.name must be a non-empty string when provided")
        errors.extend(_validate_source_links(site, "site"))
        errors.extend(validate_theme_config(site, "site"))

    errors.extend(validate_theme_config(config, "config"))

    for section, kind in (("libraries", "library"), ("resources", "resource")):
        items = config.get(section)
        if items is None:
            continue
        if not isinstance(items, list):
            errors.append(f"'{section}' must be an array, got {type(items).__name__}")
            continue
        for idx, entry in enumerate(items, start=1):
            errors.extend(
                _validate_entry(entry, section=section, index=idx, expected_kind=kind)
            )

    libraries = config.get("libraries") if isinstance(config.get("libraries"), list) else []
    resources = config.get("resources") if isinstance(config.get("resources"), list) else []
    if not libraries and not resources and "libraries" not in config and "resources" not in config:
        errors.append("Config must include a 'libraries' and/or 'resources' array")
    elif not libraries and not resources:
        errors.append("'libraries' / 'resources' must contain at least one entry")

    # Duplicate names across both sections
    seen_names: Dict[str, str] = {}
    for section, items in (("libraries", libraries), ("resources", resources)):
        if not isinstance(items, list):
            continue
        for idx, entry in enumerate(items, start=1):
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            key = name.strip().lower()
            previous = seen_names.get(key)
            if previous:
                errors.append(
                    f"{section}[{idx}]: duplicate name {name!r} "
                    f"(already used by {previous})"
                )
            else:
                seen_names[key] = f"{section}[{idx}]"

    if "examples_from_tests" in config:
        errors.extend(
            _validate_examples_from_tests(config.get("examples_from_tests"), "config")
        )

    return errors


def validate_single_lib_config(config: Dict[str, Any]) -> List[str]:
    """Validate optional single-library configuration metadata."""
    if not config:
        return []
    if not isinstance(config, dict):
        return ["Config must be a JSON object"]

    errors: List[str] = []
    unknown = _unknown_keys(config, SINGLE_LIB_TOP_LEVEL_KEYS)
    if unknown:
        errors.append(
            "Unknown top-level key(s) for single-library config: "
            + ", ".join(repr(k) for k in unknown)
        )

    output_format = config.get("output_format")
    if output_format is not None:
        if not isinstance(output_format, str) or output_format.lower() not in ALLOWED_OUTPUT_FORMATS:
            errors.append(
                f"'output_format' must be one of {sorted(ALLOWED_OUTPUT_FORMATS)}, "
                f"got {output_format!r}"
            )

    if "examples_from_tests" in config:
        errors.extend(
            _validate_examples_from_tests(config.get("examples_from_tests"), "config")
        )

    errors.extend(_validate_source_links(config, "config"))
    errors.extend(validate_theme_config(config, "config"))

    return errors


def format_validation_errors(errors: Sequence[str]) -> str:
    """Render validation errors as a bullet list."""
    return "\n".join(f"  - {error}" for error in errors)
