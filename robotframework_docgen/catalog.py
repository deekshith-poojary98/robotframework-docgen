"""
Machine-readable keyword catalog for Robot Framework libraries and resources.

This module is the shared snapshot model used by:
- keyword changelog / diff
- catalog JSON export
- coverage reporting
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from robotframework_docgen.parser import (
    KeywordInfo,
    LibraryInfo,
    RobotFrameworkDocParser,
)


SUPPORTED_SOURCE_SUFFIXES = {".py", ".resource", ".robot", ".txt", ".tsv", ".rst", ".rest"}


@dataclass
class ParameterMetadata:
    """Argument metadata for a single keyword parameter."""

    name: str
    type: str = "Any"
    default: Optional[str] = None
    enum_members: List[Dict[str, Any]] = field(default_factory=list)

    def signature(self) -> str:
        parts = [self.name]
        if self.type and self.type != "Any":
            parts.append(f": {self.type}")
        if self.default is not None:
            parts.append(f"={self.default}")
        return "".join(parts)


@dataclass
class KeywordMetadata:
    """Stable, comparable keyword metadata."""

    name: str
    parameters: List[ParameterMetadata] = field(default_factory=list)
    return_type: str = "None"
    description: str = ""
    line_number: int = 0
    has_documentation: bool = False

    def argument_signature(self) -> str:
        return ", ".join(param.signature() for param in self.parameters)

    def full_signature(self) -> str:
        args = self.argument_signature()
        ret = self.return_type or "None"
        return f"{self.name}({args}) -> {ret}"


@dataclass
class LibraryCatalog:
    """Catalog of keywords belonging to one library/resource/suite."""

    name: str
    version: str = "Unknown"
    scope: str = "TEST"
    source_type: str = "LIBRARY"
    description: str = ""
    source: str = ""
    keywords: List[KeywordMetadata] = field(default_factory=list)

    def keyword_map(self) -> Dict[str, KeywordMetadata]:
        return {kw.name: kw for kw in self.keywords}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LibraryCatalog":
        keywords = []
        for kw in data.get("keywords", []):
            parameters = [
                ParameterMetadata(
                    name=param.get("name", ""),
                    type=param.get("type", "Any"),
                    default=param.get("default"),
                    enum_members=list(param.get("enum_members") or []),
                )
                for param in kw.get("parameters", [])
            ]
            keywords.append(
                KeywordMetadata(
                    name=kw.get("name", ""),
                    parameters=parameters,
                    return_type=kw.get("return_type", "None") or "None",
                    description=kw.get("description", "") or "",
                    line_number=int(kw.get("line_number") or 0),
                    has_documentation=bool(
                        kw.get(
                            "has_documentation",
                            bool((kw.get("description") or "").strip()),
                        )
                    ),
                )
            )
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "Unknown") or "Unknown",
            scope=data.get("scope", "TEST") or "TEST",
            source_type=data.get("source_type", "LIBRARY") or "LIBRARY",
            description=data.get("description", "") or "",
            source=data.get("source", "") or "",
            keywords=keywords,
        )


@dataclass
class CatalogBundle:
    """One or more library catalogs, typically for a release/version snapshot."""

    libraries: List[LibraryCatalog] = field(default_factory=list)
    label: str = ""

    def library_map(self) -> Dict[str, LibraryCatalog]:
        return {lib.name: lib for lib in self.libraries}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "libraries": [lib.to_dict() for lib in self.libraries],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogBundle":
        libraries = [
            LibraryCatalog.from_dict(item) for item in data.get("libraries", [])
        ]
        return cls(libraries=libraries, label=data.get("label", "") or "")

    @classmethod
    def from_json_file(cls, path: str | Path) -> "CatalogBundle":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "libraries" in payload:
            return cls.from_dict(payload)
        if isinstance(payload, dict) and "keywords" in payload:
            # Single-library catalog export
            return cls(libraries=[LibraryCatalog.from_dict(payload)])
        raise ValueError(
            f"Unsupported catalog JSON format in {path}. "
            "Expected an object with 'libraries' or a single library catalog."
        )


def _strip_html(text: str) -> str:
    if not text:
        return ""
    import re

    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = (
        cleaned.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
    return " ".join(cleaned.split()).strip()


def keyword_info_to_metadata(keyword: KeywordInfo) -> KeywordMetadata:
    """Convert a parsed KeywordInfo into comparable KeywordMetadata."""
    parameters: List[ParameterMetadata] = []
    defaults = getattr(keyword, "parameter_defaults", {}) or {}
    enums = getattr(keyword, "parameter_enums", {}) or {}

    for entry in keyword.parameters or []:
        if isinstance(entry, tuple) and len(entry) >= 2:
            name, param_type = entry[0], entry[1]
        elif isinstance(entry, str):
            # Legacy module-level AST path stored "name: type = default"
            name = entry.split(":", 1)[0].strip()
            remainder = entry.split(":", 1)[1].strip() if ":" in entry else "Any"
            if "=" in remainder:
                param_type, default_inline = [p.strip() for p in remainder.split("=", 1)]
                defaults = {**defaults, name: default_inline}
            else:
                param_type = remainder or "Any"
        else:
            continue

        enum_info = enums.get(name) or {}
        parameters.append(
            ParameterMetadata(
                name=name,
                type=param_type or "Any",
                default=defaults.get(name),
                enum_members=list(enum_info.get("members") or []),
            )
        )

    description = _strip_html(keyword.description or "")
    return KeywordMetadata(
        name=keyword.name,
        parameters=parameters,
        return_type=keyword.return_type or "None",
        description=description,
        line_number=keyword.line_number or 0,
        has_documentation=bool(description),
    )


def library_info_to_catalog(
    library_info: LibraryInfo, source: str = ""
) -> LibraryCatalog:
    """Convert LibraryInfo into a LibraryCatalog snapshot."""
    return LibraryCatalog(
        name=library_info.name,
        version=library_info.version or "Unknown",
        scope=library_info.scope or "TEST",
        source_type=getattr(library_info, "source_type", "LIBRARY") or "LIBRARY",
        description=_strip_html(library_info.description or ""),
        source=source,
        keywords=[keyword_info_to_metadata(kw) for kw in library_info.keywords],
    )


def parse_source_to_catalog(
    source: str | Path, config: Optional[dict] = None
) -> LibraryCatalog:
    """Parse one library/resource file into a catalog."""
    source_path = str(source)
    parser = RobotFrameworkDocParser(config or {})
    library_info = parser.parse_file(source_path)
    return library_info_to_catalog(library_info, source=source_path)


def _iter_source_files(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES:
            # Skip common non-source trees
            if any(part in {".git", ".venv", "venv", "__pycache__", "node_modules"} for part in path.parts):
                continue
            yield path


def load_catalog_bundle(
    path: str | Path,
    label: str = "",
    config: Optional[dict] = None,
) -> CatalogBundle:
    """
    Load a catalog bundle from:
    - catalog JSON file
    - multi-library config JSON/YAML (`libraries` array with `source`)
    - a single source file (.py/.resource/.robot/...)
    - a directory of source files
    """
    from robotframework_docgen.config_io import SUPPORTED_CONFIG_SUFFIXES, load_mapping_file

    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Catalog path not found: {path}")

    if target.is_file() and target.suffix.lower() in SUPPORTED_CONFIG_SUFFIXES:
        try:
            payload = load_mapping_file(target)
        except ValueError as exc:
            raise ValueError(f"Invalid catalog/config: {path}: {exc}") from exc

        if isinstance(payload, dict) and (
            "libraries" in payload or "resources" in payload or "keywords" in payload
        ):
            libraries_spec = list(payload.get("libraries") or [])
            resources_spec = list(payload.get("resources") or [])
            # Multi-lib config points at sources; catalog JSON stores keyword metadata.
            source_entries = []
            for entry in libraries_spec + resources_spec:
                if isinstance(entry, dict) and entry.get("source"):
                    source_entries.append(entry)

            if source_entries:
                catalogs = []
                for entry in source_entries:
                    source = entry.get("source")
                    catalog = parse_source_to_catalog(source, config=entry)
                    if entry.get("name"):
                        catalog.name = entry["name"]
                    catalogs.append(catalog)
                return CatalogBundle(libraries=catalogs, label=label or target.stem)

            if "libraries" in payload and isinstance(payload.get("libraries"), list):
                # Catalog export JSON (already materialised keyword metadata)
                if payload["libraries"] and "keywords" in (payload["libraries"][0] or {}):
                    return CatalogBundle.from_dict(payload)

        if isinstance(payload, dict) and "keywords" in payload:
            return CatalogBundle(
                libraries=[LibraryCatalog.from_dict(payload)],
                label=label or target.stem,
            )

        raise ValueError(f"Unrecognized JSON/YAML content in {path}")

    if target.is_file():
        catalog = parse_source_to_catalog(target, config=config)
        return CatalogBundle(libraries=[catalog], label=label or catalog.name)

    if target.is_dir():
        catalogs = []
        for source in _iter_source_files(target):
            try:
                catalogs.append(parse_source_to_catalog(source, config=config))
            except Exception:
                # Skip files that are not valid RF libraries/resources.
                continue
        if not catalogs:
            raise ValueError(f"No parseable Robot Framework sources found in {path}")
        return CatalogBundle(libraries=catalogs, label=label or target.name)

    raise ValueError(f"Unsupported catalog path: {path}")
